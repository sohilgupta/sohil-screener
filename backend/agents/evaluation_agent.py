"""
Evaluation Agent — compares stored predictions against actual prices
and computes accuracy metrics.

Logic:
  1. Find predictions that are ≥ 30 days old and not yet evaluated.
  2. For each, look up the closest available price_snapshot after 30 days.
  3. Compute signed error% and absolute error%.
  4. Write back to the predictions table.
  5. Return an aggregate accuracy report.

Inputs:
    min_days_old    int     (default 30 — evaluate predictions at least this old)
    dry_run         bool    (default False)

Outputs:
    evaluated       int
    avg_signed_error_pct    float
    avg_abs_error_pct       float
    median_abs_error_pct    float
    within_10pct            int
    within_20pct            int
    by_sector               dict
    by_market_condition     dict
    run_id                  int | None
"""
from __future__ import annotations

import logging
import statistics
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import db
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class EvaluationAgent(BaseAgent):
    AGENT_ID = "evaluation_agent"

    async def _execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        min_days_old: int = int(inputs.get("min_days_old", 30))
        dry_run: bool = inputs.get("dry_run", False)

        if not db.is_available():
            return {"evaluated": 0, "reason": "DB unavailable"}

        pool = db.get_pool()
        cutoff = datetime.now(timezone.utc) - timedelta(days=min_days_old)

        # ── 1. Fetch un-evaluated predictions older than cutoff ──
        async with pool.acquire() as conn:
            preds = await conn.fetch(
                """
                SELECT id, ticker, sector, market_condition,
                       predicted_at, predicted_value, price_at_prediction
                FROM predictions
                WHERE evaluated = FALSE
                  AND predicted_at <= $1
                  AND predicted_value IS NOT NULL
                ORDER BY predicted_at
                """,
                cutoff,
            )

        if not preds:
            return {"evaluated": 0, "message": "No un-evaluated predictions ready"}

        self.logger.info("Evaluating %d predictions", len(preds))

        # ── 2. Resolve actual prices and compute errors ──
        eval_records: List[Dict] = []
        for pred in preds:
            actual = await self._actual_price(pred["ticker"], pred["predicted_at"], min_days_old)
            if actual is None:
                self.logger.debug("No actual price found for %s (id=%s)", pred["ticker"], pred["id"])
                continue

            pv = pred["predicted_value"]
            signed_err = round((pv - actual) / actual * 100, 4)
            abs_err = round(abs(signed_err), 4)

            eval_records.append({
                "id": pred["id"],
                "ticker": pred["ticker"],
                "sector": pred["sector"] or "Indian Equity",
                "market_condition": pred["market_condition"] or "Neutral",
                "actual_price": actual,
                "predicted_value": pv,
                "error_pct": signed_err,
                "abs_error_pct": abs_err,
            })

        if not eval_records:
            return {"evaluated": 0, "message": "No price data available yet for pending predictions"}

        # ── 3. Write back to predictions table ──
        if not dry_run:
            await self._write_evaluations(eval_records)

        # ── 4. Aggregate metrics ──
        errors = [r["error_pct"] for r in eval_records]
        abs_errors = [r["abs_error_pct"] for r in eval_records]
        avg_signed = round(statistics.mean(errors), 4)
        avg_abs = round(statistics.mean(abs_errors), 4)
        median_abs = round(statistics.median(abs_errors), 4)
        within_10 = sum(1 for e in abs_errors if e <= 10)
        within_20 = sum(1 for e in abs_errors if e <= 20)

        by_sector = self._group_errors(eval_records, "sector")
        by_condition = self._group_errors(eval_records, "market_condition")

        # ── 5. Log evaluation run ──
        run_id: Optional[int] = None
        if not dry_run and db.is_available():
            run_id = await self._log_run(
                len(eval_records), avg_signed, avg_abs, median_abs,
                within_10, within_20, by_sector,
            )

        return {
            "evaluated": len(eval_records),
            "avg_signed_error_pct": avg_signed,
            "avg_abs_error_pct": avg_abs,
            "median_abs_error_pct": median_abs,
            "within_10pct": within_10,
            "within_20pct": within_20,
            "accuracy_rate_10pct": round(within_10 / len(eval_records) * 100, 1),
            "accuracy_rate_20pct": round(within_20 / len(eval_records) * 100, 1),
            "by_sector": by_sector,
            "by_market_condition": by_condition,
            "run_id": run_id,
            "dry_run": dry_run,
        }

    # ──────────────────────────────────────────────────────────

    async def _actual_price(
        self,
        ticker: str,
        predicted_at: datetime,
        target_days: int,
    ) -> Optional[float]:
        """
        Return the price snapshot closest to (predicted_at + target_days),
        within a ±5-day window.
        """
        pool = db.get_pool()
        target_date = (predicted_at + timedelta(days=target_days)).date()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT price
                FROM price_snapshots
                WHERE ticker = $1
                  AND price_date BETWEEN ($2::date - 5) AND ($2::date + 5)
                ORDER BY ABS(price_date - $2::date)
                LIMIT 1
                """,
                ticker, target_date,
            )
        return row["price"] if row else None

    async def _write_evaluations(self, records: List[Dict]) -> None:
        pool = db.get_pool()
        async with pool.acquire() as conn:
            for r in records:
                await conn.execute(
                    """
                    UPDATE predictions SET
                        evaluated = TRUE,
                        evaluation_date = NOW(),
                        actual_price_30d = $1,
                        error_pct_30d = $2,
                        abs_error_pct_30d = $3
                    WHERE id = $4
                    """,
                    r["actual_price"], r["error_pct"], r["abs_error_pct"], r["id"],
                )

    @staticmethod
    def _group_errors(records: List[Dict], key: str) -> Dict[str, Dict]:
        groups: Dict[str, List] = {}
        for r in records:
            k = r.get(key, "Unknown") or "Unknown"
            groups.setdefault(k, []).append(r["abs_error_pct"])
        return {
            k: {
                "count": len(v),
                "avg_abs_error_pct": round(statistics.mean(v), 2),
                "median_abs_error_pct": round(statistics.median(v), 2),
            }
            for k, v in groups.items()
        }

    async def _log_run(
        self, count: int, avg_signed: float, avg_abs: float,
        median_abs: float, w10: int, w20: int, by_sector: Dict,
    ) -> Optional[int]:
        import json
        pool = db.get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO evaluation_runs (
                    run_type, predictions_evaluated,
                    avg_signed_error, avg_abs_error, median_abs_error,
                    within_10pct, within_20pct, adjustments_made
                ) VALUES ('evaluation', $1, $2, $3, $4, $5, $6, $7)
                RETURNING id
                """,
                count, avg_signed, avg_abs, median_abs, w10, w20,
                json.dumps({"by_sector": by_sector}),
            )
        return row["id"]
