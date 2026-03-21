"""
Learning Agent — analyses historical prediction accuracy and updates
model_parameters to improve future valuations.

Learning Logic (explainable, conservative):
  1. Query evaluated predictions grouped by (sector, market_condition).
  2. For each group with ≥ MIN_SAMPLES:
     a. avg_signed_error = mean(error_pct)          [+ve = overestimate]
     b. bias_correction  = -avg_signed_error         [cancel out the bias]
     c. growth_adj       = -avg_signed_error * 0.25  [partial rate correction]
     d. confidence_scaling: shrink if median_abs > HIGH_ERR, grow if < LOW_ERR
  3. Apply dampening (ALPHA) so parameters shift gradually, not all at once.
  4. Write explanatory notes for every update.

Inputs:
    min_samples         int     (default 5 — minimum predictions per group)
    dry_run             bool    (default False)
    alpha               float   (default 0.3 — dampening factor, 0<α≤1)

Outputs:
    groups_updated      int
    adjustments         list[dict] — human-readable explanation per group
    run_id              int | None
"""
from __future__ import annotations

import json
import logging
import statistics
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import db
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)

MIN_SAMPLES = 5
HIGH_ERR_THRESHOLD = 25.0   # % — shrink confidence if median abs error > this
LOW_ERR_THRESHOLD = 10.0    # % — grow confidence if median abs error < this
MAX_BIAS_CORRECTION = 30.0  # % cap on bias correction
MAX_GROWTH_ADJ = 5.0        # % cap on growth rate adjustment


class LearningAgent(BaseAgent):
    AGENT_ID = "learning_agent"

    async def _execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        min_samples: int = int(inputs.get("min_samples", MIN_SAMPLES))
        dry_run: bool = inputs.get("dry_run", False)
        alpha: float = float(inputs.get("alpha", 0.3))  # dampening

        if not db.is_available():
            return {"groups_updated": 0, "reason": "DB unavailable"}

        # ── 1. Load all evaluated predictions ──
        groups = await self._load_evaluated_groups()
        if not groups:
            return {"groups_updated": 0, "message": "No evaluated predictions found"}

        # ── 2. Compute adjustments per group ──
        adjustments: List[Dict] = []
        for (sector, condition), records in groups.items():
            if len(records) < min_samples:
                continue
            adj = self._compute_adjustment(sector, condition, records, alpha)
            adjustments.append(adj)

        if not adjustments:
            return {
                "groups_updated": 0,
                "message": f"No groups with ≥ {min_samples} evaluated predictions yet",
            }

        # ── 3. Apply to model_parameters ──
        if not dry_run:
            await self._apply_adjustments(adjustments)

        # ── 4. Log learning run ──
        run_id: Optional[int] = None
        if not dry_run:
            run_id = await self._log_run(adjustments)

        self.logger.info(
            "LearningAgent: updated %d groups (dry_run=%s)", len(adjustments), dry_run
        )
        return {
            "groups_updated": len(adjustments),
            "adjustments": adjustments,
            "run_id": run_id,
            "dry_run": dry_run,
        }

    # ──────────────────────────────────────────────────────────
    # Data loading
    # ──────────────────────────────────────────────────────────

    async def _load_evaluated_groups(self) -> Dict:
        pool = db.get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT sector, market_condition,
                       error_pct_30d, abs_error_pct_30d,
                       predicted_value, actual_price_30d
                FROM predictions
                WHERE evaluated = TRUE
                  AND error_pct_30d IS NOT NULL
                ORDER BY sector, market_condition
                """
            )
        groups: Dict = {}
        for r in rows:
            key = (r["sector"] or "Indian Equity", r["market_condition"] or "Neutral")
            groups.setdefault(key, []).append(dict(r))
        return groups

    # ──────────────────────────────────────────────────────────
    # Core learning computation (fully explainable)
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def _compute_adjustment(
        sector: str,
        condition: str,
        records: List[Dict],
        alpha: float,
    ) -> Dict:
        errors = [r["error_pct_30d"] for r in records]
        abs_errors = [r["abs_error_pct_30d"] for r in records]

        avg_signed = statistics.mean(errors)
        avg_abs = statistics.mean(abs_errors)
        median_abs = statistics.median(abs_errors)
        n = len(records)

        # ── Bias correction: cancel systematic over/under-estimation ──
        # avg_signed > 0 → model overestimates → apply negative correction
        raw_bias = -avg_signed
        bias_correction = max(-MAX_BIAS_CORRECTION, min(MAX_BIAS_CORRECTION, raw_bias))
        bias_correction = round(bias_correction * alpha, 4)   # dampened

        # ── Growth rate adjustment: if overestimating, growth was too high ──
        # Apply 25% of bias to growth rates (partial correction)
        raw_growth_adj = -avg_signed * 0.25
        growth_adj = max(-MAX_GROWTH_ADJ, min(MAX_GROWTH_ADJ, raw_growth_adj))
        growth_adj = round(growth_adj * alpha, 4)

        # ── Confidence scaling ──
        if median_abs > HIGH_ERR_THRESHOLD:
            confidence_scaling = max(0.7, round(1.0 - (median_abs - HIGH_ERR_THRESHOLD) / 100, 3))
        elif median_abs < LOW_ERR_THRESHOLD:
            confidence_scaling = min(1.2, round(1.0 + (LOW_ERR_THRESHOLD - median_abs) / 100, 3))
        else:
            confidence_scaling = 1.0

        # ── Bull/Bear probability shifts ──
        # If model consistently overestimates in bull scenario,
        # reduce bull probability slightly
        bull_prob_adj = round(-avg_signed * 0.005 * alpha, 4)   # very conservative
        bear_prob_adj = round(avg_signed * 0.005 * alpha, 4)

        explanation = (
            f"Based on {n} predictions: avg signed error {avg_signed:+.1f}% "
            f"(model {'overestimates' if avg_signed > 0 else 'underestimates'}), "
            f"median abs error {median_abs:.1f}%. "
            f"Applied bias correction {bias_correction:+.2f}%, "
            f"growth adj {growth_adj:+.2f}%, "
            f"confidence scaling ×{confidence_scaling:.3f}."
        )

        return {
            "sector": sector,
            "market_condition": condition,
            "sample_size": n,
            "avg_signed_error": round(avg_signed, 4),
            "avg_abs_error": round(avg_abs, 4),
            "median_abs_error": round(median_abs, 4),
            "bias_correction": bias_correction,
            "bull_growth_adj": growth_adj,
            "base_growth_adj": growth_adj,
            "bear_growth_adj": round(growth_adj * 0.5, 4),   # bear adj more conservative
            "bull_prob_adj": bull_prob_adj,
            "bear_prob_adj": bear_prob_adj,
            "confidence_scaling": confidence_scaling,
            "explanation": explanation,
        }

    # ──────────────────────────────────────────────────────────
    # Database writes
    # ──────────────────────────────────────────────────────────

    async def _apply_adjustments(self, adjustments: List[Dict]) -> None:
        pool = db.get_pool()
        async with pool.acquire() as conn:
            for adj in adjustments:
                await conn.execute(
                    """
                    INSERT INTO model_parameters (
                        sector, market_condition,
                        bull_growth_adj, base_growth_adj, bear_growth_adj,
                        bull_prob_adj, bear_prob_adj,
                        bias_correction, confidence_scaling,
                        sample_size, avg_signed_error, avg_abs_error, median_abs_error,
                        last_updated, update_notes
                    ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,NOW(),$14)
                    ON CONFLICT (sector, market_condition) DO UPDATE SET
                        bull_growth_adj   = EXCLUDED.bull_growth_adj,
                        base_growth_adj   = EXCLUDED.base_growth_adj,
                        bear_growth_adj   = EXCLUDED.bear_growth_adj,
                        bull_prob_adj     = EXCLUDED.bull_prob_adj,
                        bear_prob_adj     = EXCLUDED.bear_prob_adj,
                        bias_correction   = EXCLUDED.bias_correction,
                        confidence_scaling= EXCLUDED.confidence_scaling,
                        sample_size       = EXCLUDED.sample_size,
                        avg_signed_error  = EXCLUDED.avg_signed_error,
                        avg_abs_error     = EXCLUDED.avg_abs_error,
                        median_abs_error  = EXCLUDED.median_abs_error,
                        last_updated      = NOW(),
                        update_notes      = EXCLUDED.update_notes
                    """,
                    adj["sector"], adj["market_condition"],
                    adj["bull_growth_adj"], adj["base_growth_adj"], adj["bear_growth_adj"],
                    adj["bull_prob_adj"], adj["bear_prob_adj"],
                    adj["bias_correction"], adj["confidence_scaling"],
                    adj["sample_size"],
                    adj["avg_signed_error"], adj["avg_abs_error"], adj["median_abs_error"],
                    adj["explanation"],
                )
        logger.info("Applied %d parameter updates to model_parameters", len(adjustments))

    async def _log_run(self, adjustments: List[Dict]) -> Optional[int]:
        pool = db.get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO evaluation_runs (
                    run_type, predictions_evaluated, adjustments_made, run_notes
                ) VALUES ('learning', $1, $2, $3)
                RETURNING id
                """,
                sum(a["sample_size"] for a in adjustments),
                json.dumps([
                    {k: v for k, v in a.items() if k != "explanation"}
                    for a in adjustments
                ]),
                f"Updated {len(adjustments)} sector/condition groups",
            )
        return row["id"]
