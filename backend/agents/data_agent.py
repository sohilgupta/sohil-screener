"""Data Agent — resolves ticker/company name then fetches financial data.

Resolution order:
  1. ticker_resolver (Gemini LLM + known-ticker table) → canonical yf_symbol
  2. yfinance_fetcher  (Yahoo Finance, covers Indian NSE + US stocks)
  3. screener_scraper  (fallback for Indian stocks only)
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from typing import Any, Dict, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class DataAgent(BaseAgent):
    """
    Fetches structured financial data for any publicly traded stock.

    Inputs:
        ticker          str   – ticker symbol OR company name (any case, spaces OK)
        market_condition str  – override auto-detected market trend
        risk_free_rate  float – override default risk-free rate
        use_cache       bool  – honour Redis cache (default True)

    Outputs:
        ticker, yf_symbol, company_name, current_price, revenue, ebitda,
        net_income, fcf, de_ratio, shares_outstanding, market_cap, pe_ratio,
        book_value, roe, opm, industry, competitors, source, market, currency,
        unit_label, unit_multiplier, market_condition, risk_free_rate
    """

    AGENT_ID = "data_agent"

    def __init__(self, cache=None) -> None:
        super().__init__()
        self._cache = cache

    async def _execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        raw_input: str = inputs["ticker"].strip()
        use_cache: bool = inputs.get("use_cache", True)

        # ── Step 1: Resolve to canonical yfinance symbol ───────────────────────
        loop = asyncio.get_event_loop()

        from ticker_resolver import resolve_ticker
        meta = await loop.run_in_executor(None, resolve_ticker, raw_input)
        yf_symbol: str = meta["yf_symbol"]
        display_ticker: str = meta["display_ticker"]

        # ── Step 2: Cache lookup ────────────────────────────────────────────────
        cache_key = f"stock_data:{yf_symbol}"
        if use_cache and self._cache:
            cached = await self._cache.get(cache_key)
            if cached:
                logger.info("Cache hit for %s", yf_symbol)
                cached["_cached"] = True
                return self._inject_market_context(cached, inputs)

        # ── Step 3: Fetch from Yahoo Finance (primary) ─────────────────────────
        from yfinance_fetcher import fetch_yf_data
        stock_data: Optional[Dict[str, Any]] = await loop.run_in_executor(
            None, fetch_yf_data, yf_symbol, meta
        )

        # ── Step 4: Supplement with screener.in for Indian stocks ──────────────
        # Even when yfinance has the price, screener.in often has better
        # financial data (revenue, EBITDA, FCF) for Indian mid/small-caps.
        if meta.get("market") == "IN":
            from screener_scraper import fetch_screener_data
            try:
                screener_data = await loop.run_in_executor(
                    None, fetch_screener_data, display_ticker
                )
                if stock_data is None:
                    # yfinance completely failed — use screener.in as primary
                    if self._has_price(screener_data):
                        screener_data.setdefault("unit_multiplier", 1e7)
                        screener_data.setdefault("unit_label", "Crore")
                        screener_data.setdefault("market", "IN")
                        screener_data.setdefault("currency", "INR")
                        stock_data = screener_data
                else:
                    # yfinance has price but may lack financials — fill gaps
                    for field in ["revenue", "ebitda", "net_income", "fcf",
                                  "de_ratio", "pe_ratio", "roe", "opm",
                                  "book_value", "competitors"]:
                        if stock_data.get(field) is None and screener_data.get(field) is not None:
                            stock_data[field] = screener_data[field]
                    # Prefer screener.in company name if yfinance gave a generic one
                    if (screener_data.get("company_name") and
                            screener_data["company_name"] != display_ticker and
                            stock_data.get("company_name") == display_ticker):
                        stock_data["company_name"] = screener_data["company_name"]
                    stock_data["source"] = "yahoo_finance+screener.in"
            except Exception as e:
                logger.warning("screener.in supplement failed for %s: %s", display_ticker, e)

        # ── Step 5: Last-resort empty dict ─────────────────────────────────────
        if stock_data is None:
            stock_data = self._empty(display_ticker, meta)

        stock_data["_cached"] = False

        # ── Step 6: Inject market context ──────────────────────────────────────
        stock_data = self._inject_market_context(stock_data, inputs)

        # ── Step 7: Cache result (1-hour TTL) ──────────────────────────────────
        if use_cache and self._cache and self._has_price(stock_data):
            await self._cache.set(cache_key, stock_data, ttl=3600)

        return stock_data

    # ── Helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def _has_price(data: Optional[Dict]) -> bool:
        return bool(data and data.get("current_price"))

    @staticmethod
    def _inject_market_context(
        stock_data: Dict[str, Any], inputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add market_condition and risk_free_rate (non-blocking defaults)."""
        # Market condition
        mc = inputs.get("market_condition") or stock_data.get("market_condition")
        if not mc:
            mc = "Neutral"  # safe default; market tracking agent refines this
        stock_data["market_condition"] = mc

        # Risk-free rate — yfinance_fetcher already sets a default, respect it
        rfr = inputs.get("risk_free_rate") or stock_data.get("risk_free_rate")
        if not rfr:
            rfr = 4.5 if stock_data.get("market") == "US" else 7.2
        stock_data["risk_free_rate"] = float(rfr)

        return stock_data

    @staticmethod
    def _empty(ticker: str, meta: Dict) -> Dict[str, Any]:
        return {
            "ticker": ticker,
            "yf_symbol": meta.get("yf_symbol", ticker),
            "company_name": meta.get("company_name", ticker),
            "current_price": None,
            "revenue": None, "ebitda": None, "net_income": None, "fcf": None,
            "de_ratio": None, "shares_outstanding": None, "market_cap": None,
            "pe_ratio": None, "book_value": None, "roe": None, "opm": None,
            "industry": "Indian Equity" if meta.get("market") == "IN" else "US Equity",
            "competitors": [], "top_ratios": {},
            "source": "unavailable",
            "market": meta.get("market", "IN"),
            "currency": meta.get("currency", "INR"),
            "unit_label": "Crore" if meta.get("market") == "IN" else "Million",
            "unit_multiplier": 1e7 if meta.get("market") == "IN" else 1e6,
            "exchange": meta.get("exchange", ""),
        }
