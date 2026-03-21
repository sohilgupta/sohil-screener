"""
Fetch structured financial data via yfinance (Yahoo Finance).

Covers both Indian stocks (TCS.NS, RELIANCE.NS) and US stocks (AAPL, MSFT).
Returns a normalized dict compatible with DCFAgent and LLMAgent.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def fetch_yf_data(yf_symbol: str, meta: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Fetch financial data for a Yahoo Finance symbol.

    meta keys used: display_ticker, company_name, market, currency, exchange

    Financial figures are stored in:
        Indian stocks  → Crores INR   (unit_multiplier = 1e7)
        US stocks      → Millions USD (unit_multiplier = 1e6)

    DCFAgent uses unit_multiplier to convert EV back to per-share price.
    """
    try:
        import yfinance as yf
    except ImportError:
        logger.error("yfinance not installed — pip install yfinance")
        return None

    market = meta.get("market", "IN")
    currency = meta.get("currency", "INR")

    # Unit conventions
    if market == "IN":
        unit_divisor = 1e7      # raw INR → Crores
        unit_label = "Crore"
        unit_multiplier = 1e7   # Crores → INR (for per-share conversion)
        default_rfr = 7.2       # Indian 10Y G-Sec
    else:
        unit_divisor = 1e6      # raw USD → Millions
        unit_label = "Million"
        unit_multiplier = 1e6   # Millions → USD (for per-share conversion)
        default_rfr = 4.5       # US 10Y Treasury

    try:
        ticker_obj = yf.Ticker(yf_symbol)
        info = ticker_obj.info or {}
    except Exception as e:
        logger.warning("yfinance fetch failed for %s: %s", yf_symbol, e)
        return None

    # Validate the response is real data
    if not info or not info.get("symbol"):
        logger.warning("yfinance returned empty/invalid info for %s", yf_symbol)
        return None

    def to_unit(val) -> Optional[float]:
        if val is None:
            return None
        try:
            f = float(val)
            if f == 0:
                return None
            return round(f / unit_divisor, 2)
        except (TypeError, ValueError):
            return None

    def safe_float(val, digits=2) -> Optional[float]:
        if val is None:
            return None
        try:
            f = float(val)
            return round(f, digits) if f != 0 else None
        except (TypeError, ValueError):
            return None

    # ── Price ──────────────────────────────────────────────────────────────────
    current_price = safe_float(
        info.get("currentPrice") or
        info.get("regularMarketPrice") or
        info.get("navPrice")
    )

    # ── Market cap ─────────────────────────────────────────────────────────────
    market_cap = to_unit(info.get("marketCap"))

    # ── Income statement ───────────────────────────────────────────────────────
    revenue = to_unit(info.get("totalRevenue"))
    ebitda = to_unit(info.get("ebitda"))
    net_income = to_unit(info.get("netIncomeToCommon"))
    fcf = to_unit(info.get("freeCashflow"))

    # ── Ratios ─────────────────────────────────────────────────────────────────
    pe_ratio = safe_float(info.get("trailingPE") or info.get("forwardPE"))
    book_value = safe_float(info.get("bookValue"))

    roe = info.get("returnOnEquity")
    roe = round(float(roe) * 100, 2) if roe else None

    opm = info.get("operatingMargins")
    opm = round(float(opm) * 100, 2) if opm else None

    # yfinance returns D/E as a percentage (e.g. 125 means 1.25), normalise to ratio
    de_raw = info.get("debtToEquity")
    de_ratio = round(float(de_raw) / 100, 4) if de_raw else None

    # ── Shares outstanding ─────────────────────────────────────────────────────
    shares_outstanding = info.get("sharesOutstanding")
    if not shares_outstanding and market_cap and current_price and current_price > 0:
        # Estimate: market_cap in units × unit_divisor / price
        shares_outstanding = (float(market_cap) * unit_divisor) / float(current_price)

    # ── Names ──────────────────────────────────────────────────────────────────
    company_name = (
        info.get("longName") or
        info.get("shortName") or
        meta.get("company_name") or
        meta.get("display_ticker")
    )

    display_ticker = meta.get("display_ticker") or yf_symbol.split(".")[0].upper()

    # ── Industry / sector ──────────────────────────────────────────────────────
    industry = (
        info.get("industry") or
        info.get("sector") or
        ("Indian Equity" if market == "IN" else "US Equity")
    )

    # ── Growth metrics (supplemental) ─────────────────────────────────────────
    revenue_growth = info.get("revenueGrowth")
    earnings_growth = info.get("earningsGrowth")

    result = {
        "ticker": display_ticker,
        "yf_symbol": yf_symbol,
        "company_name": company_name,
        "current_price": current_price,
        "revenue": revenue,
        "ebitda": ebitda,
        "net_income": net_income,
        "fcf": fcf,
        "de_ratio": de_ratio,
        "shares_outstanding": shares_outstanding,
        "market_cap": market_cap,
        "pe_ratio": pe_ratio,
        "book_value": book_value,
        "roe": roe,
        "opm": opm,
        "revenue_growth_pct": round(float(revenue_growth) * 100, 1) if revenue_growth else None,
        "earnings_growth_pct": round(float(earnings_growth) * 100, 1) if earnings_growth else None,
        "industry": industry,
        "sector": info.get("sector"),
        "competitors": [],
        "top_ratios": {},
        "source": "yahoo_finance",
        "market": market,
        "currency": currency,
        "unit_label": unit_label,
        "unit_multiplier": unit_multiplier,
        "exchange": meta.get("exchange", ""),
        "risk_free_rate": default_rfr,
    }

    logger.info(
        "yfinance data for %s: price=%s rev=%s ebitda=%s fcf=%s market=%s",
        yf_symbol, current_price, revenue, ebitda, fcf, market
    )
    return result
