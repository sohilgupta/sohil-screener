"""Orchestrator — routes requests through the agent pipeline."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from .data_agent import DataAgent
from .dcf_agent import DCFAgent
from .llm_agent import LLMAgent
from .memory_agent import MemoryAgent
from .ocr_agent import OCRAgent
from .portfolio_agent import PortfolioAgent

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Central coordinator.  Decides which agents to run based on request type:

    single_stock   → DataAgent → DCFAgent  → LLMAgent
    multiple_stocks→ loop above concurrently
    portfolio      → OCRAgent → [DataAgent → DCFAgent → LLMAgent] → PortfolioAgent
    """

    def __init__(self, cache=None) -> None:
        self._cache = cache
        self._data = DataAgent(cache=cache)
        self._dcf = DCFAgent()
        self._llm = LLMAgent(cache=cache)
        self._memory = MemoryAgent()
        self._ocr = OCRAgent()
        self._portfolio = PortfolioAgent()

    # ──────────────────────────────────────────────────────────────────
    # Public entry points
    # ──────────────────────────────────────────────────────────────────

    async def run_single_stock(
        self,
        ticker: str,
        allocation: Optional[float] = None,
        horizon: Optional[int] = None,
        market_condition: Optional[str] = None,
        risk_free_rate: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Run the full valuation pipeline for one ticker."""
        result = await self._valuation_pipeline(
            ticker=ticker,
            allocation=allocation,
            horizon=horizon,
            market_condition=market_condition,
            risk_free_rate=risk_free_rate,
        )
        result["agents_used"] = ["DataAgent", "DCFAgent", "LLMAgent"]
        return result

    async def run_multiple_stocks(
        self,
        tickers: List[str],
        market_condition: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Run valuations for multiple tickers concurrently."""
        tasks = [
            self._valuation_pipeline(ticker=t, market_condition=market_condition)
            for t in tickers
        ]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        rows = []
        for ticker, res in zip(tickers, raw_results):
            if isinstance(res, Exception):
                logger.error(f"Pipeline error for {ticker}: {res}")
                rows.append({"ticker": ticker, "error": str(res), "success": False})
                continue

            sd = res.get("stock_data", {})
            an = res.get("analysis", {})
            dcf = res.get("dcf_result", {})

            rows.append({
                "success": True,
                "ticker": ticker,
                "company_name": sd.get("company_name", ticker),
                "industry": sd.get("industry"),
                "current_price": sd.get("current_price"),
                "bull_target": an.get("bull_case", {}).get("target_price"),
                "base_target": an.get("base_case", {}).get("target_price"),
                "bear_target": an.get("bear_case", {}).get("target_price"),
                "probability_weighted_value": an.get("probability_weighted_value"),
                "dcf_intrinsic": dcf.get("probability_weighted_intrinsic"),
                "upside_percentage": an.get("upside_percentage"),
                "recommendation": an.get("recommendation"),
                "confidence_level": an.get("confidence_level"),
                "dcf_recommendation": dcf.get("dcf_recommendation"),
                "margin_of_safety_pct": dcf.get("margin_of_safety_pct"),
            })

        return rows

    async def run_portfolio(self, image_bytes: bytes) -> Dict[str, Any]:
        """OCR → per-holding valuation → portfolio analytics."""
        # Step 1: OCR
        ocr_result = await self._ocr.run({"image_bytes": image_bytes})
        if not ocr_result.success:
            return {
                "success": False,
                "error": ocr_result.error,
                "holdings": [],
                "analysis": [],
                "portfolio": {},
            }

        holdings: List[Dict[str, Any]] = ocr_result.data.get("holdings", [])
        if not holdings:
            return {
                "success": True,
                "holdings": [],
                "analysis": [],
                "portfolio": {},
                "ocr_engine": ocr_result.data.get("ocr_engine", "tesseract"),
                "message": (
                    "No holdings could be extracted from the screenshot. "
                    "Ensure the image clearly shows stock names, quantities, and buy prices."
                ),
            }

        # Step 2: concurrent valuations for each holding
        tasks = [
            self._valuation_pipeline(ticker=h["ticker"])
            for h in holdings
        ]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Step 3: merge OCR data + valuation
        merged: List[Dict[str, Any]] = []
        for holding, res in zip(holdings, raw_results):
            if isinstance(res, Exception):
                logger.error(f"Portfolio valuation error for {holding['ticker']}: {res}")
                merged.append({
                    **holding,
                    "error": str(res),
                    "current_price": None,
                    "probability_weighted_value": None,
                    "recommendation": None,
                    "confidence_level": None,
                    "industry": "Unknown",
                    "dcf_recommendation": None,
                })
                continue

            sd = res.get("stock_data", {})
            an = res.get("analysis", {})
            dcf = res.get("dcf_result", {})
            current = sd.get("current_price") or 0
            buy = holding.get("buy_price") or 0
            qty = holding.get("quantity") or 0
            pwv = an.get("probability_weighted_value")

            merged.append({
                **holding,
                "company_name": sd.get("company_name", holding["ticker"]),
                "current_price": current,
                "total_current_value": round(current * qty, 2),
                "total_invested_value": round(buy * qty, 2),
                "pnl": round((current - buy) * qty, 2),
                "pnl_percentage": (
                    round((current - buy) / buy * 100, 2) if buy > 0 else None
                ),
                "probability_weighted_value": pwv,
                "upside_from_current": (
                    round((pwv - current) / current * 100, 2)
                    if current > 0 and pwv else None
                ),
                "upside_from_buy": (
                    round((pwv - buy) / buy * 100, 2)
                    if buy > 0 and pwv else None
                ),
                "recommendation": an.get("recommendation"),
                "confidence_level": an.get("confidence_level"),
                "industry": sd.get("industry", "Unknown"),
                "dcf_intrinsic": dcf.get("probability_weighted_intrinsic"),
                "dcf_recommendation": dcf.get("dcf_recommendation"),
                "margin_of_safety_pct": dcf.get("margin_of_safety_pct"),
            })

        # Step 4: PortfolioAgent analytics
        port_result = await self._portfolio.run({"valuations": merged})

        return {
            "success": True,
            "ocr_engine": ocr_result.data.get("ocr_engine", "tesseract"),
            "holdings": holdings,
            "analysis": merged,
            "portfolio": port_result.data if port_result.success else {},
            "agents_used": ["OCRAgent", "DataAgent", "DCFAgent", "LLMAgent", "PortfolioAgent"],
        }

    # ──────────────────────────────────────────────────────────────────
    # Internal pipeline
    # ──────────────────────────────────────────────────────────────────

    async def _valuation_pipeline(
        self,
        ticker: str,
        allocation: Optional[float] = None,
        horizon: Optional[int] = None,
        market_condition: Optional[str] = None,
        risk_free_rate: Optional[float] = None,
    ) -> Dict[str, Any]:
        """DataAgent → load learned params → DCFAgent → LLMAgent → MemoryAgent."""

        # Step A: Fetch data
        data_result = await self._data.run({
            "ticker": ticker,
            "market_condition": market_condition,
            "risk_free_rate": risk_free_rate,
        })
        data_result.raise_if_failed()
        stock_data = data_result.data

        sector = stock_data.get("industry", "Indian Equity")
        cond = stock_data.get("market_condition", "Neutral")

        # Step B: Load learned parameters for this sector + condition
        learned_params = await MemoryAgent.load_parameters(sector, cond)
        bias_correction = learned_params.get("bias_correction", 0.0)
        growth_adj = learned_params.get("base_growth_adj", 0.0)

        # Step C: DCF with learned growth adjustments
        dcf_result = await self._dcf.run({**stock_data, "param_overrides": learned_params})
        dcf_data = dcf_result.data if dcf_result.success else {"available": False}

        # Step D: LLM analysis (enriched with DCF)
        llm_result = await self._llm.run({
            "stock_data": stock_data,
            "dcf_result": dcf_data,
            "allocation": allocation,
            "horizon": horizon,
        })
        analysis = llm_result.data if llm_result.success else {
            "recommendation": "Hold",
            "confidence_level": "Low",
            "executive_summary": "LLM analysis unavailable.",
            "error": llm_result.error,
        }

        # Step E: Apply bias correction to probability-weighted value
        pwv = analysis.get("probability_weighted_value")
        if pwv and bias_correction != 0.0:
            corrected_pwv = round(pwv * (1 + bias_correction / 100), 2)
            analysis["probability_weighted_value"] = corrected_pwv
            analysis["_bias_correction_applied"] = bias_correction
            analysis["_uncorrected_pwv"] = pwv
            current = stock_data.get("current_price") or 0
            if current > 0:
                analysis["upside_percentage"] = round(
                    (corrected_pwv - current) / current * 100, 2
                )

        # Step F: Save prediction to memory (fire-and-forget, non-blocking)
        asyncio.create_task(self._save_prediction(
            stock_data=stock_data,
            analysis=analysis,
            dcf_data=dcf_data,
            bias_correction_applied=bias_correction,
            growth_adj_applied=growth_adj,
        ))

        return {
            "stock_data": stock_data,
            "dcf_result": dcf_data,
            "analysis": analysis,
            "market_condition_used": cond,
            "risk_free_rate_used": stock_data.get("risk_free_rate", 7.2),
            "learning_applied": {
                "bias_correction_pct": bias_correction,
                "growth_adj_pct": growth_adj,
                "sample_size": learned_params.get("sample_size", 0),
            },
            "pipeline_durations_ms": {
                "data_agent": data_result.duration_ms,
                "dcf_agent": dcf_result.duration_ms,
                "llm_agent": llm_result.duration_ms,
            },
        }

    async def _save_prediction(
        self,
        stock_data: Dict,
        analysis: Dict,
        dcf_data: Dict,
        bias_correction_applied: float = 0.0,
        growth_adj_applied: float = 0.0,
    ) -> None:
        """Persist the valuation to PostgreSQL via MemoryAgent (non-blocking)."""
        try:
            await self._memory.run({
                "mode": "save",
                "ticker": stock_data.get("ticker"),
                "company_name": stock_data.get("company_name"),
                "sector": stock_data.get("industry", "Indian Equity"),
                "market_condition": stock_data.get("market_condition", "Neutral"),
                "risk_free_rate": stock_data.get("risk_free_rate", 7.2),
                "price_at_prediction": stock_data.get("current_price"),
                "predicted_value": analysis.get("probability_weighted_value"),
                "price_target": analysis.get("price_target"),
                "recommendation": analysis.get("recommendation"),
                "confidence": analysis.get("confidence_level"),
                "bull_case": analysis.get("bull_case", {}),
                "base_case": analysis.get("base_case", {}),
                "bear_case": analysis.get("bear_case", {}),
                "dcf_intrinsic": dcf_data.get("probability_weighted_intrinsic"),
                "wacc_pct": dcf_data.get("wacc_pct"),
                "dcf_margin_of_safety": dcf_data.get("margin_of_safety_pct"),
                "bias_correction_applied": bias_correction_applied,
                "growth_adj_applied": growth_adj_applied,
            })
        except Exception as exc:
            logger.warning("MemoryAgent save failed (non-fatal): %s", exc)
