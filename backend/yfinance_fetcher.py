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

    Tries in order:
      1. fast_info  (always available, gives price + market cap)
      2. info       (full financials — revenue, FCF, etc.)
      3. BSE fallback for Indian stocks (.NS → .BO)
    """
    try:
        import yfinance as yf
    except ImportError:
        logger.error("yfinance not installed")
        return None

    result = _fetch_single(yf_symbol, meta)
    if result:
        return result

    # For Indian stocks: try BSE suffix if NSE fails
    market = meta.get("market", "IN")
    if market == "IN":
        if yf_symbol.endswith(".NS"):
            alt = yf_symbol[:-3] + ".BO"
        elif yf_symbol.endswith(".BO"):
            alt = yf_symbol[:-3] + ".NS"
        else:
            alt = yf_symbol + ".NS"

        if alt != yf_symbol:
            logger.info("Retrying %s as %s", yf_symbol, alt)
            result = _fetch_single(alt, meta)
            if result:
                return result

    logger.warning("yfinance returned no usable data for %s", yf_symbol)
    return None


def _fetch_single(yf_symbol: str, meta: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Attempt to fetch data for one specific Yahoo Finance symbol."""
    import yfinance as yf

    market = meta.get("market", "IN")
    currency = meta.get("currency", "INR")

    if market == "IN":
        unit_divisor = 1e7      # raw INR → Crores
        unit_label = "Crore"
        unit_multiplier = 1e7
        default_rfr = 7.2
    else:
        unit_divisor = 1e6      # raw USD → Millions
        unit_label = "Million"
        unit_multiplier = 1e6
        default_rfr = 4.5

    try:
        ticker_obj = yf.Ticker(yf_symbol)
    except Exception as e:
        logger.warning("yf.Ticker(%s) failed: %s", yf_symbol, e)
        return None

    # ── Step 1: fast_info — always works for listed stocks ────────────────────
    current_price = None
    market_cap = None
    shares_outstanding = None

    try:
        fi = ticker_obj.fast_info
        raw_price = getattr(fi, "last_price", None) or getattr(fi, "previous_close", None)
        if raw_price and float(raw_price) > 0:
            current_price = round(float(raw_price), 2)

        raw_mcap = getattr(fi, "market_cap", None)
        if raw_mcap and float(raw_mcap) > 0:
            market_cap = round(float(raw_mcap) / unit_divisor, 2)

        raw_shares = getattr(fi, "shares", None)
        if raw_shares and float(raw_shares) > 0:
            shares_outstanding = float(raw_shares)

        logger.info("fast_info for %s: price=%s mcap=%s", yf_symbol, current_price, market_cap)
    except Exception as e:
        logger.warning("fast_info failed for %s: %s", yf_symbol, e)

    # If fast_info gave us no price at all, this ticker is invalid
    if not current_price:
        logger.warning("No price from fast_info for %s — skipping", yf_symbol)
        return None

    # ── Step 2: info — detailed financials (may be incomplete for small caps) ─
    info: Dict[str, Any] = {}
    try:
        raw_info = ticker_obj.info
        if isinstance(raw_info, dict) and len(raw_info) > 5:
            info = raw_info
            logger.info("info dict for %s has %d keys", yf_symbol, len(info))
    except Exception as e:
        logger.warning("info fetch failed for %s: %s", yf_symbol, e)

    def to_unit(val) -> Optional[float]:
        if val is None:
            return None
        try:
            f = float(val)
            return round(f / unit_divisor, 2) if f != 0 else None
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

    # Price: prefer info over fast_info (more accurate)
    info_price = safe_float(
        info.get("currentPrice") or
        info.get("regularMarketPrice") or
        info.get("navPrice")
    )
    if info_price:
        current_price = info_price

    # Market cap: prefer info
    info_mcap = to_unit(info.get("marketCap"))
    if info_mcap:
        market_cap = info_mcap

    # Financials
    revenue = to_unit(info.get("totalRevenue"))
    ebitda = to_unit(info.get("ebitda"))
    net_income = to_unit(info.get("netIncomeToCommon"))
    fcf = to_unit(info.get("freeCashflow"))

    # Ratios
    pe_ratio = safe_float(info.get("trailingPE") or info.get("forwardPE"))
    book_value = safe_float(info.get("bookValue"))

    roe_raw = info.get("returnOnEquity")
    roe = round(float(roe_raw) * 100, 2) if roe_raw else None

    opm_raw = info.get("operatingMargins")
    opm = round(float(opm_raw) * 100, 2) if opm_raw else None

    de_raw = info.get("debtToEquity")
    de_ratio = round(float(de_raw) / 100, 4) if de_raw else None

    # Shares outstanding
    info_shares = info.get("sharesOutstanding")
    if info_shares and float(info_shares) > 0:
        shares_outstanding = float(info_shares)
    elif not shares_outstanding and market_cap and current_price and current_price > 0:
        shares_outstanding = (market_cap * unit_divisor) / current_price

    # Names
    company_name = (
        info.get("longName") or
        info.get("shortName") or
        meta.get("company_name") or
        meta.get("display_ticker")
    )

    display_ticker = meta.get("display_ticker") or yf_symbol.split(".")[0].upper()

    # Industry
    industry = (
        info.get("industry") or
        info.get("sector") or
        ("Indian Equity" if market == "IN" else "US Equity")
    )

    return {
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
        "revenue_growth_pct": (
            round(float(info["revenueGrowth"]) * 100, 1)
            if info.get("revenueGrowth") else None
        ),
        "earnings_growth_pct": (
            round(float(info["earningsGrowth"]) * 100, 1)
            if info.get("earningsGrowth") else None
        ),
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
