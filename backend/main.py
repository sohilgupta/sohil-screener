"""
AI Stock Valuation Engine — FastAPI application
Multi-agent architecture: DataAgent → DCFAgent → LLMAgent → PortfolioAgent
"""
import logging
import os
from contextlib import asynccontextmanager
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agents.orchestrator import Orchestrator
from cache import CacheClient

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App state (cache + orchestrator are singletons created at startup)
# ---------------------------------------------------------------------------
_cache: Optional[CacheClient] = None
_orchestrator: Optional[Orchestrator] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _cache, _orchestrator
    _cache = await CacheClient.from_env()
    _orchestrator = Orchestrator(cache=_cache)
    logger.info("Orchestrator ready — cache backend: %s", _cache.backend_name)
    yield
    logger.info("Shutting down…")


app = FastAPI(
    title="AI Stock Valuation API",
    version="3.0.0",
    description="Multi-agent valuation engine: Data → DCF → Gemini LLM → Portfolio",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
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
    allocation: Optional[float] = Field(None, description="Portfolio allocation %")
    horizon: Optional[int] = Field(None, description="Investment horizon in years")
    market_condition: Optional[str] = Field(None, description="Bullish / Bearish / Neutral")
    risk_free_rate: Optional[float] = Field(None, description="Risk-free rate %")


class MultipleStocksRequest(BaseModel):
    tickers: List[str] = Field(..., description="List of NSE/BSE tickers")
    market_condition: Optional[str] = None


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------
def _orch() -> Orchestrator:
    if _orchestrator is None:
        raise HTTPException(status_code=503, detail="Service not ready yet. Retry in a moment.")
    return _orchestrator


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": "3.0.0",
        "cache_backend": _cache.backend_name if _cache else "not_ready",
    }


# ── Single Stock ─────────────────────────────────────────────────────────────

@app.post("/analyze-stock")
async def analyze_stock(req: StockAnalysisRequest):
    """Full agent pipeline for one stock: Data → DCF → LLM analysis."""
    ticker = req.ticker.strip().upper()
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


# ── Multiple Stocks ──────────────────────────────────────────────────────────

@app.post("/analyze-multiple")
@app.post("/analyze-multiple-stocks")  # backward-compat alias
async def analyze_multiple_stocks(req: MultipleStocksRequest):
    """Concurrent agent pipeline for ≤ 12 tickers."""
    tickers = [t.strip().upper() for t in req.tickers if t.strip()]
    if not tickers:
        raise HTTPException(status_code=400, detail="At least one ticker is required")
    tickers = tickers[:12]

    try:
        rows = await _orch().run_multiple_stocks(
            tickers=tickers,
            market_condition=req.market_condition,
        )
        return {"success": True, "data": rows}
    except Exception as exc:
        logger.error("/analyze-multiple error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


# ── Portfolio Upload ─────────────────────────────────────────────────────────

@app.post("/upload-portfolio")
@app.post("/upload-portfolio-screenshot")  # backward-compat alias
async def upload_portfolio(file: UploadFile = File(...)):
    """OCR screenshot → per-holding valuation → portfolio analytics."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image (PNG/JPG/WEBP)")
    try:
        image_bytes = await file.read()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not read uploaded file: {exc}")

    try:
        result = await _orch().run_portfolio(image_bytes=image_bytes)
        return result
    except Exception as exc:
        logger.error("/upload-portfolio error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


# ── Cache management ─────────────────────────────────────────────────────────

@app.delete("/cache")
async def flush_cache():
    """Flush all cached data (admin use only)."""
    if _cache:
        await _cache.flush()
    return {"flushed": True}


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
