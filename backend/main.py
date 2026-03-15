import asyncio
import logging
import os
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from gemini_client import get_gemini_analysis, parse_valuation_response
from portfolio_ocr import extract_portfolio_from_screenshot
from screener_scraper import fetch_screener_data, get_nifty_trend, get_risk_free_rate
from valuation_prompt import build_valuation_prompt

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Stock Valuation API", version="2.0.0", description="Screener.in + Gemini powered stock analysis")

# ---------------------------------------------------------------------------
# CORS — allow all origins in development; tighten for production via env var
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
# Core analysis helper
# ---------------------------------------------------------------------------
async def _analyze_ticker(
    ticker: str,
    allocation: Optional[float] = None,
    horizon: Optional[int] = None,
    market_condition: Optional[str] = None,
    risk_free_rate: Optional[float] = None,
) -> dict:
    """Fetch data, build prompt, call Gemini, parse response."""
    # 1. Fetch financial data
    stock_data = await asyncio.get_event_loop().run_in_executor(
        None, fetch_screener_data, ticker
    )

    # 2. Auto-fill optional params
    if not market_condition:
        market_condition = await asyncio.get_event_loop().run_in_executor(
            None, get_nifty_trend
        )
    if not risk_free_rate:
        risk_free_rate = get_risk_free_rate()

    # 3. Build prompt
    prompt = build_valuation_prompt(
        company=stock_data["company_name"],
        ticker=ticker,
        industry=stock_data["industry"],
        competitors=stock_data["competitors"],
        allocation=allocation,
        horizon=horizon,
        revenue=stock_data["revenue"],
        ebitda=stock_data["ebitda"],
        net_income=stock_data["net_income"],
        fcf=stock_data["fcf"],
        de_ratio=stock_data["de_ratio"],
        shares_outstanding=stock_data["shares_outstanding"],
        current_price=stock_data["current_price"],
        market_condition=market_condition,
        risk_free_rate=risk_free_rate,
        pe_ratio=stock_data.get("pe_ratio"),
        market_cap=stock_data.get("market_cap"),
        roe=stock_data.get("roe"),
        opm=stock_data.get("opm"),
    )

    # 4. Call Gemini
    raw_response = await asyncio.get_event_loop().run_in_executor(
        None, get_gemini_analysis, prompt
    )

    # 5. Parse
    analysis = parse_valuation_response(raw_response, stock_data["current_price"] or 0)

    return {
        "stock_data": stock_data,
        "analysis": analysis,
        "market_condition_used": market_condition,
        "risk_free_rate_used": risk_free_rate,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}


@app.post("/analyze-stock")
async def analyze_stock(req: StockAnalysisRequest):
    """Run full AI valuation analysis for a single stock."""
    ticker = req.ticker.strip().upper()
    if not ticker:
        raise HTTPException(status_code=400, detail="Ticker is required")
    try:
        result = await _analyze_ticker(
            ticker=ticker,
            allocation=req.allocation,
            horizon=req.horizon,
            market_condition=req.market_condition,
            risk_free_rate=req.risk_free_rate,
        )
        return {"success": True, "data": result}
    except Exception as exc:
        logger.error(f"/analyze-stock error for {ticker}: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/analyze-multiple-stocks")
async def analyze_multiple_stocks(req: MultipleStocksRequest):
    """Analyze multiple stocks concurrently and return a comparison table."""
    tickers = [t.strip().upper() for t in req.tickers if t.strip()]
    if not tickers:
        raise HTTPException(status_code=400, detail="At least one ticker is required")
    if len(tickers) > 12:
        tickers = tickers[:12]  # Guard against excessive requests

    tasks = [
        _analyze_ticker(ticker=t, market_condition=req.market_condition)
        for t in tickers
    ]
    raw_results = await asyncio.gather(*tasks, return_exceptions=True)

    rows = []
    for ticker, res in zip(tickers, raw_results):
        if isinstance(res, Exception):
            logger.error(f"Error analyzing {ticker}: {res}")
            rows.append({"ticker": ticker, "error": str(res)})
            continue
        sd = res["stock_data"]
        an = res["analysis"]
        rows.append({
            "ticker": ticker,
            "company_name": sd["company_name"],
            "industry": sd["industry"],
            "current_price": sd["current_price"],
            "bull_target": an["bull_case"].get("target_price"),
            "base_target": an["base_case"].get("target_price"),
            "bear_target": an["bear_case"].get("target_price"),
            "probability_weighted_value": an["probability_weighted_value"],
            "upside_percentage": an["upside_percentage"],
            "recommendation": an["recommendation"],
            "confidence_level": an["confidence_level"],
        })

    return {"success": True, "data": rows}


@app.post("/upload-portfolio-screenshot")
async def upload_portfolio_screenshot(file: UploadFile = File(...)):
    """OCR a portfolio screenshot, extract holdings, and run analysis on each."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image (PNG/JPG/WEBP)")

    try:
        image_bytes = await file.read()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not read uploaded file: {exc}")

    # OCR → holdings
    holdings = extract_portfolio_from_screenshot(image_bytes)
    if not holdings:
        return {
            "success": True,
            "holdings": [],
            "analysis": [],
            "message": (
                "No holdings could be extracted from the screenshot. "
                "Ensure the image clearly shows stock names, quantities, and buy prices."
            ),
        }

    # Analyze each holding concurrently
    tasks = [_analyze_ticker(ticker=h["ticker"]) for h in holdings]
    raw_results = await asyncio.gather(*tasks, return_exceptions=True)

    portfolio_analysis = []
    for holding, res in zip(holdings, raw_results):
        if isinstance(res, Exception):
            logger.error(f"Error analyzing holding {holding['ticker']}: {res}")
            portfolio_analysis.append({**holding, "error": str(res)})
            continue

        sd = res["stock_data"]
        an = res["analysis"]
        current = sd["current_price"] or 0
        buy = holding["buy_price"]
        pwv = an["probability_weighted_value"] or 0
        qty = holding["quantity"]

        portfolio_analysis.append({
            "ticker": holding["ticker"],
            "stock_name": holding["stock_name"],
            "quantity": qty,
            "buy_price": buy,
            "current_price": current,
            "total_current_value": round(current * qty, 2),
            "total_invested_value": round(buy * qty, 2),
            "pnl": round((current - buy) * qty, 2),
            "pnl_percentage": round((current - buy) / buy * 100, 2) if buy > 0 else None,
            "probability_weighted_value": pwv,
            "upside_from_current": (
                round((pwv - current) / current * 100, 2) if current > 0 and pwv else None
            ),
            "upside_from_buy": (
                round((pwv - buy) / buy * 100, 2) if buy > 0 and pwv else None
            ),
            "recommendation": an["recommendation"],
            "confidence_level": an["confidence_level"],
            "industry": sd["industry"],
        })

    return {"success": True, "holdings": holdings, "analysis": portfolio_analysis}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
