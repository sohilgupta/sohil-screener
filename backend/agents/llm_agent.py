"""LLM Agent — calls Gemini to generate scenario analysis and recommendation."""
from __future__ import annotations

import asyncio
import sys
import os
from typing import Any, Dict, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from .base_agent import BaseAgent


class LLMAgent(BaseAgent):
    """
    Calls Google Gemini API with financial data + DCF output to generate:
    - bull / base / bear scenarios with probabilities
    - executive summary, key risks, recommendation

    Inputs:
        stock_data      (dict)  – DataAgent output
        dcf_result      (dict)  – DCFAgent output (optional but enriches prompt)
        allocation      (float | None)
        horizon         (int | None)

    Outputs:
        analysis_text, bull_case, base_case, bear_case,
        probability_weighted_value, upside_percentage, recommendation,
        confidence_level, price_target, executive_summary, key_risks,
        valuation_methods
    """

    AGENT_ID = "llm_agent"

    def __init__(self, cache=None) -> None:
        super().__init__()
        self._cache = cache

    async def _execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        sd: Dict[str, Any] = inputs["stock_data"]
        dcf: Dict[str, Any] = inputs.get("dcf_result", {})
        allocation: Optional[float] = inputs.get("allocation")
        horizon: Optional[int] = inputs.get("horizon")

        ticker = sd["ticker"]
        market_condition = sd.get("market_condition", "Neutral")
        risk_free_rate = sd.get("risk_free_rate", 7.2)

        # Cache key
        cache_key = f"llm:{ticker}:{market_condition}:{risk_free_rate}"
        if self._cache:
            cached = await self._cache.get(cache_key)
            if cached:
                self.logger.info(f"LLM cache hit for {ticker}")
                cached["_cached"] = True
                return cached

        # Build prompt
        from valuation_prompt import build_valuation_prompt
        prompt = build_valuation_prompt(
            company=sd["company_name"],
            ticker=ticker,
            industry=sd["industry"],
            competitors=sd.get("competitors", []),
            allocation=allocation,
            horizon=horizon,
            revenue=sd.get("revenue"),
            ebitda=sd.get("ebitda"),
            net_income=sd.get("net_income"),
            fcf=sd.get("fcf"),
            de_ratio=sd.get("de_ratio"),
            shares_outstanding=sd.get("shares_outstanding"),
            current_price=sd.get("current_price"),
            market_condition=market_condition,
            risk_free_rate=risk_free_rate,
            pe_ratio=sd.get("pe_ratio"),
            market_cap=sd.get("market_cap"),
            roe=sd.get("roe"),
            opm=sd.get("opm"),
        )

        # Append DCF context if available
        if dcf.get("available"):
            prompt += self._dcf_context_block(dcf)

        # Call Gemini in executor (blocking SDK)
        loop = asyncio.get_event_loop()
        from gemini_client import get_gemini_analysis, parse_valuation_response
        raw = await loop.run_in_executor(None, get_gemini_analysis, prompt)
        analysis = parse_valuation_response(raw, sd.get("current_price") or 0)
        analysis["_cached"] = False

        # Cache for 4 hours
        if self._cache:
            await self._cache.set(cache_key, analysis, ttl=14400)

        return analysis

    # ------------------------------------------------------------------

    @staticmethod
    def _dcf_context_block(dcf: Dict[str, Any]) -> str:
        bull = dcf["scenarios"].get("bull", {})
        base = dcf["scenarios"].get("base", {})
        bear = dcf["scenarios"].get("bear", {})

        def iv(s: Dict) -> str:
            v = s.get("intrinsic_per_share")
            return f"₹{v:,.2f}" if v else "N/A"

        return f"""

--- DCF AGENT PRE-COMPUTATION (incorporate into your analysis) ---
WACC: {dcf.get("wacc_pct", "N/A")}%
Bull DCF intrinsic: {iv(bull)} (FCF growth {bull.get("fcf_growth_pct", "N/A")}%)
Base DCF intrinsic: {iv(base)} (FCF growth {base.get("fcf_growth_pct", "N/A")}%)
Bear DCF intrinsic: {iv(bear)} (FCF growth {bear.get("fcf_growth_pct", "N/A")}%)
Probability-Weighted DCF Intrinsic: ₹{dcf.get("probability_weighted_intrinsic") or "N/A"}
DCF Margin of Safety: {dcf.get("margin_of_safety_pct", "N/A")}%
Cross-check your scenario targets against these DCF figures.
---
"""
