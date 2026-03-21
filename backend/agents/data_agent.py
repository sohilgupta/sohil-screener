"""Data Agent — fetches and caches financial data from screener.in / trendlyne."""
from __future__ import annotations

import asyncio
import sys
import os
from typing import Any, Dict, Optional

# Allow importing sibling modules from the backend root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from .base_agent import BaseAgent


class DataAgent(BaseAgent):
    """
    Fetches structured financial data for an NSE/BSE ticker.

    Inputs:
        ticker          (str)   – NSE/BSE ticker symbol
        use_cache       (bool)  – honour Redis cache (default True)

    Outputs (dict):
        ticker, company_name, current_price, revenue, ebitda, net_income,
        fcf, de_ratio, shares_outstanding, market_cap, pe_ratio, book_value,
        roe, opm, industry, competitors, top_ratios, source
    """

    AGENT_ID = "data_agent"

    def __init__(self, cache=None) -> None:
        super().__init__()
        self._cache = cache  # optional CacheClient

    async def _execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        ticker: str = inputs["ticker"].strip().upper()
        use_cache: bool = inputs.get("use_cache", True)

        # 1. Try cache
        cache_key = f"stock_data:{ticker}"
        if use_cache and self._cache:
            cached = await self._cache.get(cache_key)
            if cached:
                self.logger.info(f"Cache hit for {ticker}")
                cached["_cached"] = True
                return cached

        # 2. Fetch live — run blocking scrapers in executor
        loop = asyncio.get_event_loop()

        from screener_scraper import fetch_screener_data, get_nifty_trend, get_risk_free_rate

        stock_data: Dict[str, Any] = await loop.run_in_executor(
            None, fetch_screener_data, ticker
        )

        # Inject market context
        market_condition: Optional[str] = inputs.get("market_condition")
        if not market_condition:
            market_condition = await loop.run_in_executor(None, get_nifty_trend)

        risk_free_rate: float = inputs.get("risk_free_rate") or get_risk_free_rate()

        stock_data["market_condition"] = market_condition
        stock_data["risk_free_rate"] = risk_free_rate
        stock_data["_cached"] = False

        # 3. Store in cache (1-hour TTL)
        if use_cache and self._cache:
            await self._cache.set(cache_key, stock_data, ttl=3600)

        return stock_data
