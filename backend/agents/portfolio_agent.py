"""Portfolio Agent — aggregates valuations into portfolio-level analytics."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base_agent import BaseAgent


class PortfolioAgent(BaseAgent):
    """
    Computes portfolio-level metrics after each holding has been analysed.

    Inputs:
        valuations  – list of per-stock dicts, each containing:
            ticker, stock_name, quantity, buy_price, current_price,
            probability_weighted_value, recommendation, confidence_level,
            industry, dcf_result (optional)

    Outputs:
        summary         – portfolio totals (invested, current, P&L, upside)
        holdings        – enriched per-holding rows with allocation %, actions
        allocation      – sector breakdown
        rebalance       – ordered rebalancing suggestions
        concentration   – Herfindahl index (portfolio diversification score)
    """

    AGENT_ID = "portfolio_agent"

    async def _execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        valuations: List[Dict[str, Any]] = inputs.get("valuations", [])

        if not valuations:
            return {"summary": {}, "holdings": [], "allocation": {}, "rebalance": []}

        # ── Pass 1: compute per-holding metrics ──────────────────────────────
        enriched: List[Dict[str, Any]] = []
        total_invested = 0.0
        total_current = 0.0
        total_target = 0.0  # PWV-based

        for v in valuations:
            qty: float = v.get("quantity", 0)
            buy_price: float = v.get("buy_price") or 0
            current: float = v.get("current_price") or 0
            pwv: float = v.get("probability_weighted_value") or 0

            invested = round(buy_price * qty, 2)
            curr_val = round(current * qty, 2)
            target_val = round(pwv * qty, 2) if pwv else curr_val

            pnl = round(curr_val - invested, 2)
            pnl_pct = round((current - buy_price) / buy_price * 100, 2) if buy_price > 0 else 0

            upside_from_current = (
                round((pwv - current) / current * 100, 2)
                if pwv and current > 0 else None
            )
            upside_from_buy = (
                round((pwv - buy_price) / buy_price * 100, 2)
                if pwv and buy_price > 0 else None
            )

            total_invested += invested
            total_current += curr_val
            total_target += target_val

            enriched.append({
                **v,
                "invested_value": invested,
                "current_value": curr_val,
                "target_value": target_val,
                "pnl": pnl,
                "pnl_pct": pnl_pct,
                "upside_from_current_pct": upside_from_current,
                "upside_from_buy_pct": upside_from_buy,
                "allocation_pct": None,  # filled in pass 2
                "action": self._decide_action(v),
            })

        # ── Pass 2: allocation percentages (by current value) ────────────────
        sector_map: Dict[str, float] = {}
        for h in enriched:
            alloc = round(h["current_value"] / total_current * 100, 2) if total_current > 0 else 0
            h["allocation_pct"] = alloc
            sector = h.get("industry", "Other")
            sector_map[sector] = round(sector_map.get(sector, 0) + alloc, 2)

        # ── Herfindahl concentration index (0=diversified, 1=concentrated) ──
        hhi = round(sum((h["allocation_pct"] / 100) ** 2 for h in enriched), 4)
        diversification = "Good" if hhi < 0.15 else "Moderate" if hhi < 0.30 else "Concentrated"

        # ── Rebalancing suggestions ──────────────────────────────────────────
        rebalance = self._build_rebalance(enriched)

        # ── Portfolio summary ────────────────────────────────────────────────
        portfolio_pnl = round(total_current - total_invested, 2)
        portfolio_pnl_pct = (
            round(portfolio_pnl / total_invested * 100, 2) if total_invested > 0 else 0
        )
        total_upside_pct = (
            round((total_target - total_current) / total_current * 100, 2)
            if total_current > 0 else None
        )

        summary = {
            "total_invested": round(total_invested, 2),
            "total_current_value": round(total_current, 2),
            "total_target_value": round(total_target, 2),
            "portfolio_pnl": portfolio_pnl,
            "portfolio_pnl_pct": portfolio_pnl_pct,
            "total_upside_pct": total_upside_pct,
            "num_holdings": len(enriched),
            "hhi_concentration": hhi,
            "diversification": diversification,
        }

        return {
            "summary": summary,
            "holdings": enriched,
            "allocation": sector_map,
            "rebalance": rebalance,
        }

    # ------------------------------------------------------------------

    @staticmethod
    def _decide_action(v: Dict[str, Any]) -> str:
        """Simple heuristic: combine recommendation + upside to suggest action."""
        rec = (v.get("recommendation") or "Hold").lower()
        upside = v.get("upside_from_current_pct")
        dcf_rec = (v.get("dcf_recommendation") or "").lower()

        if rec == "exit" or dcf_rec == "exit":
            return "Exit"
        if rec == "buy" and (upside is None or upside > 10):
            return "Add"
        if upside is not None and upside > 25:
            return "Add"
        if upside is not None and upside < -15:
            return "Trim"
        return "Hold"

    @staticmethod
    def _build_rebalance(holdings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort holdings by action priority and return structured suggestions."""
        priority_order = {"Exit": 0, "Trim": 1, "Hold": 2, "Add": 3}
        sorted_h = sorted(holdings, key=lambda h: priority_order.get(h.get("action", "Hold"), 2))

        suggestions = []
        for h in sorted_h:
            action = h.get("action", "Hold")
            if action == "Hold":
                continue  # omit neutral holds from rebalance list

            upside = h.get("upside_from_current_pct")
            rationale = {
                "Exit": f"Recommendation: Exit. Upside: {upside}%",
                "Trim": f"Limited upside ({upside}%). Consider reducing position.",
                "Add": f"Strong upside ({upside}%). Recommendation: {h.get('recommendation')}.",
            }.get(action, "")

            suggestions.append({
                "ticker": h["ticker"],
                "company_name": h.get("company_name", h["ticker"]),
                "action": action,
                "current_allocation_pct": h.get("allocation_pct"),
                "upside_from_current_pct": upside,
                "recommendation": h.get("recommendation"),
                "rationale": rationale,
            })

        return suggestions
