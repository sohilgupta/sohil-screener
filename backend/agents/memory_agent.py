"""
Memory Agent — persists valuation predictions to PostgreSQL and
retrieves historical records for a given ticker.

Inputs (save mode):
    mode            "save"
    ticker, company_name, sector, market_condition, risk_free_rate,
    price_at_prediction, predicted_value, price_target, recommendation,
    confidence, bull_case, base_case, bear_case,
    dcf_intrinsic, wacc_pct, dcf_margin_of_safety,
    bias_correction_applied, growth_adj_applied

Inputs (history mode):
    mode            "history"
    ticker          str
    limit           int (default 20)

Outputs (save mode):
    prediction_id   int | None

Outputs (history mode):
    predictions     list[dict]
    count           int
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import db
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class MemoryAgent(BaseAgent):
    AGENT_ID = "memory_agent"

    async def _execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        mode = inputs.get("mode", "save")
        if mode == "history":
            return await self._fetch_history(inputs)
        return await self._save_prediction(inputs)

    # ──────────────────────────────────────────────────────────
    # Save
    # ──────────────────────────────────────────────────────────

    async def _save_prediction(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        if not db.is_available():
            return {"prediction_id": None, "stored": False, "reason": "DB unavailable"}

        pool = db.get_pool()
        bull = inputs.get("bull_case", {})
        base = inputs.get("base_case", {})
        bear = inputs.get("bear_case", {})

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO predictions (
                    ticker, company_name, sector, predicted_at, market_condition,
                    risk_free_rate, price_at_prediction, predicted_value, price_target,
                    recommendation, confidence,
                    bull_target, bull_probability, bull_growth_rate,
                    base_target, base_probability, base_growth_rate,
                    bear_target, bear_probability, bear_growth_rate,
                    dcf_intrinsic, wacc_pct, dcf_margin_of_safety,
                    bias_correction_applied, growth_adj_applied
                ) VALUES (
                    $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,
                    $11,$12,$13,$14,$15,$16,$17,$18,$19,$20,
                    $21,$22,$23,$24,$25
                )
                RETURNING id
                """,
                inputs.get("ticker"),
                inputs.get("company_name"),
                inputs.get("sector", "Indian Equity"),
                datetime.now(timezone.utc),
                inputs.get("market_condition", "Neutral"),
                inputs.get("risk_free_rate", 7.2),
                inputs.get("price_at_prediction"),
                inputs.get("predicted_value"),
                inputs.get("price_target"),
                inputs.get("recommendation"),
                inputs.get("confidence"),
                bull.get("target_price"),
                bull.get("probability"),
                bull.get("growth_rate"),
                base.get("target_price"),
                base.get("probability"),
                base.get("growth_rate"),
                bear.get("target_price"),
                bear.get("probability"),
                bear.get("growth_rate"),
                inputs.get("dcf_intrinsic"),
                inputs.get("wacc_pct"),
                inputs.get("dcf_margin_of_safety"),
                inputs.get("bias_correction_applied", 0.0),
                inputs.get("growth_adj_applied", 0.0),
            )

        pred_id = row["id"]
        self.logger.info("Prediction saved: id=%s ticker=%s", pred_id, inputs.get("ticker"))
        return {"prediction_id": pred_id, "stored": True}

    # ──────────────────────────────────────────────────────────
    # Fetch history
    # ──────────────────────────────────────────────────────────

    async def _fetch_history(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        ticker = inputs.get("ticker", "").upper()
        limit = int(inputs.get("limit", 20))

        if not db.is_available():
            return {"predictions": [], "count": 0, "reason": "DB unavailable"}

        pool = db.get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, ticker, company_name, sector, predicted_at,
                       market_condition, price_at_prediction, predicted_value,
                       price_target, recommendation, confidence,
                       bull_target, base_target, bear_target,
                       dcf_intrinsic, wacc_pct, dcf_margin_of_safety,
                       bias_correction_applied, growth_adj_applied,
                       evaluated, evaluation_date, actual_price_30d,
                       error_pct_30d, abs_error_pct_30d
                FROM predictions
                WHERE ticker = $1
                ORDER BY predicted_at DESC
                LIMIT $2
                """,
                ticker, limit,
            )

        predictions = [dict(r) for r in rows]
        # Convert datetimes to ISO strings for JSON serialisation
        for p in predictions:
            for k in ("predicted_at", "evaluation_date"):
                if p.get(k) is not None:
                    p[k] = p[k].isoformat()

        return {"predictions": predictions, "count": len(predictions)}

    # ──────────────────────────────────────────────────────────
    # Load learned parameters for a sector (called by Orchestrator)
    # ──────────────────────────────────────────────────────────

    @staticmethod
    async def load_parameters(sector: str, market_condition: str = "Neutral") -> Dict[str, float]:
        """
        Returns the learned model parameters for the given sector + market condition.
        Falls back to 'Indian Equity' / 'Neutral' if no specific match.
        Returns all-zeros if DB unavailable.
        """
        defaults: Dict[str, float] = {
            "bull_growth_adj": 0.0, "base_growth_adj": 0.0, "bear_growth_adj": 0.0,
            "bull_prob_adj": 0.0,   "bear_prob_adj": 0.0,
            "bias_correction": 0.0, "confidence_scaling": 1.0,
            "sample_size": 0,
        }
        if not db.is_available():
            return defaults

        pool = db.get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT bull_growth_adj, base_growth_adj, bear_growth_adj,
                       bull_prob_adj, bear_prob_adj, bias_correction,
                       confidence_scaling, sample_size
                FROM model_parameters
                WHERE sector = $1 AND market_condition = $2
                """,
                sector, market_condition,
            )
            if row is None:
                # Fall back to generic Indian Equity
                row = await conn.fetchrow(
                    """
                    SELECT bull_growth_adj, base_growth_adj, bear_growth_adj,
                           bull_prob_adj, bear_prob_adj, bias_correction,
                           confidence_scaling, sample_size
                    FROM model_parameters
                    WHERE sector = 'Indian Equity' AND market_condition = $1
                    """,
                    market_condition,
                )

        if row:
            defaults.update({k: (v or 0.0) for k, v in dict(row).items()})
        return defaults
