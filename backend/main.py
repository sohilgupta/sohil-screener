"""
AI Stock Valuation Engine v4 — FastAPI application
Multi-agent + self-improving learning loop
"""
import logging
import os
from contextlib import asynccontextmanager
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import db
from agents.orchestrator import Orchestrator
from agents.evaluation_agent import EvaluationAgent
from agents.learning_agent import LearningAgent
from agents.market_tracking_agent import MarketTrackingAgent
from agents.memory_agent import MemoryAgent
from cache import CacheClient
import scheduler as sched

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

_cache: Optional[CacheClient] = None
_orchestrator: Optional[Orchestrator] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _cache, _orchestrator

    # Cache
    _cache = await CacheClient.from_env()

    # PostgreSQL + migrations
    db_ok = await db.init_pool()
    if db_ok:
        await db.run_migrations()

    # Orchestrator
    _orchestrator = Orchestrator(cache=_cache)

    # Scheduler (cron jobs)
    await sched.start_scheduler()

    logger.info(
        "v4 ready — cache=%s db=%s scheduler=%s",
        _cache.backend_name,
        "connected" if db_ok else "disabled",
        "running" if sched.get_scheduler() else "disabled",
    )
    yield

    await sched.stop_scheduler()
    await db.close_pool()
    logger.info("Shutdown complete")


app = FastAPI(
    title="AI Stock Valuation API",
    version="4.0.0",
    description="Multi-agent + self-improving learning loop",
    lifespan=lifespan,
)

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class StockAnalysisRequest(BaseModel):
    ticker: str = Field(..., description="NSE/BSE ticker symbol")
    allocation: Optional[float] = None
    horizon: Optional[int] = None
    market_condition: Optional[str] = None
    risk_free_rate: Optional[float] = None


class MultipleStocksRequest(BaseModel):
    tickers: List[str]
    market_condition: Optional[str] = None


def _orch() -> Orchestrator:
    if _orchestrator is None:
        raise HTTPException(status_code=503, detail="Service not ready. Retry in a moment.")
    return _orchestrator


# ---------------------------------------------------------------------------
# Core valuation endpoints (unchanged interface)
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": "4.0.0",
        "cache_backend": _cache.backend_name if _cache else "not_ready",
        "db": "connected" if db.is_available() else "disabled",
        "scheduler": "running" if sched.get_scheduler() else "disabled",
    }


@app.post("/analyze-stock")
async def analyze_stock(req: StockAnalysisRequest):
    ticker = req.ticker.strip()
    if not ticker:
        raise HTTPException(status_code=400, detail="Ticker is required")
    try:
        result = await _orch().run_single_stock(
            ticker=ticker,
            allocation=req.allocation,
            horizon=req.horizon,
            market_condition=req.market_condition,
            risk_free_rate=req.risk_free_rate,
        )
        return {"success": True, "data": result}
    except Exception as exc:
        logger.error("/analyze-stock error for %s: %s", ticker, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/analyze-multiple")
@app.post("/analyze-multiple-stocks")
async def analyze_multiple_stocks(req: MultipleStocksRequest):
    tickers = [t.strip() for t in req.tickers if t.strip()]
    if not tickers:
        raise HTTPException(status_code=400, detail="At least one ticker is required")
    tickers = tickers[:12]
    try:
        rows = await _orch().run_multiple_stocks(tickers=tickers, market_condition=req.market_condition)
        return {"success": True, "data": rows}
    except Exception as exc:
        logger.error("/analyze-multiple error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/upload-portfolio")
@app.post("/upload-portfolio-screenshot")
async def upload_portfolio(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image (PNG/JPG/WEBP)")
    try:
        image_bytes = await file.read()
        result = await _orch().run_portfolio(image_bytes=image_bytes)
        return result
    except Exception as exc:
        logger.error("/upload-portfolio error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Learning loop endpoints
# ---------------------------------------------------------------------------

@app.get("/predictions/{ticker}")
async def get_predictions(ticker: str, limit: int = 20):
    """Retrieve prediction history for a ticker."""
    agent = MemoryAgent()
    result = await agent.run({"mode": "history", "ticker": ticker.upper(), "limit": limit})
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return {"success": True, **result.data}


@app.get("/learning/parameters")
async def get_learning_parameters():
    """View all learned model parameters."""
    if not db.is_available():
        return {"success": True, "parameters": [], "db": "disabled"}
    pool = db.get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT sector, market_condition, bias_correction,
                   bull_growth_adj, base_growth_adj, bear_growth_adj,
                   confidence_scaling, sample_size,
                   avg_signed_error, avg_abs_error, median_abs_error,
                   last_updated, update_notes
            FROM model_parameters
            WHERE sample_size > 0
            ORDER BY sector, market_condition
            """
        )
    params = []
    for r in rows:
        p = dict(r)
        if p.get("last_updated"):
            p["last_updated"] = p["last_updated"].isoformat()
        params.append(p)
    return {"success": True, "parameters": params, "count": len(params)}


@app.get("/learning/accuracy")
async def get_accuracy_report():
    """View accuracy metrics across all evaluated predictions."""
    if not db.is_available():
        return {"success": True, "report": {}, "db": "disabled"}
    pool = db.get_pool()
    async with pool.acquire() as conn:
        overall = await conn.fetchrow(
            """
            SELECT
                COUNT(*) AS total_predictions,
                COUNT(*) FILTER (WHERE evaluated) AS evaluated,
                AVG(error_pct_30d) AS avg_signed_error,
                AVG(abs_error_pct_30d) AS avg_abs_error,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY abs_error_pct_30d) AS median_abs_error,
                COUNT(*) FILTER (WHERE abs_error_pct_30d <= 10) AS within_10pct,
                COUNT(*) FILTER (WHERE abs_error_pct_30d <= 20) AS within_20pct
            FROM predictions
            WHERE evaluated = TRUE
            """
        )
        by_sector = await conn.fetch(
            """
            SELECT sector,
                   COUNT(*) AS count,
                   AVG(error_pct_30d) AS avg_signed,
                   AVG(abs_error_pct_30d) AS avg_abs
            FROM predictions
            WHERE evaluated = TRUE
            GROUP BY sector ORDER BY count DESC
            """
        )
        recent_runs = await conn.fetch(
            """
            SELECT run_type, run_at, predictions_evaluated,
                   avg_signed_error, avg_abs_error, median_abs_error
            FROM evaluation_runs
            ORDER BY run_at DESC LIMIT 10
            """
        )

    def fmt(r):
        d = dict(r)
        for k, v in d.items():
            if hasattr(v, "isoformat"):
                d[k] = v.isoformat()
            elif isinstance(v, float):
                d[k] = round(v, 4)
        return d

    return {
        "success": True,
        "overall": fmt(overall) if overall else {},
        "by_sector": [fmt(r) for r in by_sector],
        "recent_runs": [fmt(r) for r in recent_runs],
    }


@app.post("/learning/evaluate")
async def trigger_evaluate(dry_run: bool = False):
    """Manually trigger the EvaluationAgent."""
    agent = EvaluationAgent()
    result = await agent.run({"min_days_old": 30, "dry_run": dry_run})
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return {"success": True, **result.data}


@app.post("/learning/run")
async def trigger_learning(dry_run: bool = False, min_samples: int = 3):
    """Manually trigger the LearningAgent to update model parameters."""
    agent = LearningAgent()
    result = await agent.run({"dry_run": dry_run, "min_samples": min_samples, "alpha": 0.3})
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return {"success": True, **result.data}


@app.post("/learning/track")
async def trigger_tracking(dry_run: bool = False):
    """Manually trigger the MarketTrackingAgent to fetch latest prices."""
    agent = MarketTrackingAgent()
    result = await agent.run({"dry_run": dry_run})
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return {"success": True, **result.data}


@app.delete("/cache")
async def flush_cache():
    if _cache:
        await _cache.flush()
    return {"flushed": True}


@app.get("/debug/{ticker}")
async def debug_ticker(ticker: str):
    """Diagnostic endpoint — resolve ticker and show raw yfinance data."""
    import asyncio
    loop = asyncio.get_event_loop()
    try:
        from ticker_resolver import resolve_ticker
        meta = await loop.run_in_executor(None, resolve_ticker, ticker.strip())

        from yfinance_fetcher import fetch_yf_data
        data = await loop.run_in_executor(None, fetch_yf_data, meta["yf_symbol"], meta)

        return {
            "input": ticker,
            "resolved": meta,
            "yf_data": data,
            "has_price": bool(data and data.get("current_price")),
        }
    except Exception as exc:
        return {"input": ticker, "error": str(exc)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
