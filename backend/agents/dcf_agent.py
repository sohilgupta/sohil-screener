"""DCF Agent — computes intrinsic valuation using Discounted Cash Flow."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base_agent import BaseAgent

# India equity risk premium (Damodaran estimate for emerging markets)
INDIA_ERP = 6.5  # %
# Default beta for a typical Indian mid-large-cap
DEFAULT_BETA = 1.0
# Terminal growth rate ceiling (≤ long-run GDP growth)
MAX_TERMINAL_GROWTH = 0.065


class DCFAgent(BaseAgent):
    """
    Performs 5-year FCF DCF with Bull / Base / Bear scenarios.

    Inputs (from DataAgent output):
        fcf                 (float | None)  – TTM free cash flow in ₹ Crore
        net_income          (float | None)  – TTM net income in ₹ Crore
        ebitda              (float | None)  – TTM EBITDA in ₹ Crore
        revenue             (float | None)  – TTM revenue in ₹ Crore
        de_ratio            (float | None)  – debt-to-equity ratio
        shares_outstanding  (float | None)  – absolute number of shares
        current_price       (float | None)  – CMP in ₹
        market_cap          (float | None)  – in ₹ Crore
        risk_free_rate      (float)         – Indian 10Y G-Sec yield %
        market_condition    (str)           – Bullish / Bearish / Neutral

    Outputs:
        wacc, base_fcf_cr, scenarios (bull/base/bear with DCF intrinsic values),
        margin_of_safety, dcf_recommendation
    """

    AGENT_ID = "dcf_agent"

    # Growth assumptions per scenario
    SCENARIO_PARAMS = {
        "bull":  {"fcf_growth": 0.22, "terminal_growth": 0.065, "probability": 0.25},
        "base":  {"fcf_growth": 0.13, "terminal_growth": 0.055, "probability": 0.50},
        "bear":  {"fcf_growth": 0.05, "terminal_growth": 0.040, "probability": 0.25},
    }

    # Market condition adjusts the growth assumptions
    MARKET_ADJUSTMENTS = {
        "Bullish": {"fcf_growth_delta": 0.03, "probability_shift": 0.10},
        "Bearish": {"fcf_growth_delta": -0.03, "probability_shift": -0.10},
        "Neutral": {"fcf_growth_delta": 0.00, "probability_shift": 0.00},
    }

    async def _execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        risk_free_rate: float = inputs.get("risk_free_rate", 7.2) / 100
        market_condition: str = inputs.get("market_condition", "Neutral")
        shares_outstanding: Optional[float] = inputs.get("shares_outstanding")
        current_price: Optional[float] = inputs.get("current_price")

        # --- Determine base FCF (Crore) ---
        base_fcf = self._resolve_base_fcf(inputs)
        if base_fcf is None or base_fcf <= 0:
            return {
                "available": False,
                "reason": "Insufficient FCF / earnings data for DCF",
                "base_fcf_cr": base_fcf,
            }

        # --- WACC ---
        wacc = self._compute_wacc(
            risk_free_rate=risk_free_rate,
            de_ratio=inputs.get("de_ratio") or 0.5,
        )

        # --- Build scenarios ---
        adj = self.MARKET_ADJUSTMENTS.get(market_condition, self.MARKET_ADJUSTMENTS["Neutral"])
        scenarios: Dict[str, Any] = {}
        pwv_numerator = 0.0
        total_prob = 0.0

        for name, params in self.SCENARIO_PARAMS.items():
            adjusted_growth = params["fcf_growth"] + adj["fcf_growth_delta"]
            prob_shift = adj["probability_shift"] if name == "bull" else (
                -adj["probability_shift"] if name == "bear" else 0
            )
            probability = min(max(params["probability"] + prob_shift * 0.5, 0.10), 0.70)

            terminal_growth = min(params["terminal_growth"], MAX_TERMINAL_GROWTH)
            # Guard: terminal growth must be < WACC
            if terminal_growth >= wacc:
                terminal_growth = wacc - 0.01

            result = self._project_dcf(
                base_fcf_cr=base_fcf,
                fcf_growth=adjusted_growth,
                wacc=wacc,
                terminal_growth=terminal_growth,
                years=5,
                shares_outstanding=shares_outstanding,
            )
            result["probability"] = round(probability, 2)
            result["fcf_growth_pct"] = round(adjusted_growth * 100, 1)
            result["terminal_growth_pct"] = round(terminal_growth * 100, 1)
            scenarios[name] = result

            if result.get("intrinsic_per_share") is not None:
                pwv_numerator += result["intrinsic_per_share"] * probability
                total_prob += probability

        # Normalise probabilities to exactly 1.0
        if total_prob > 0:
            for s in scenarios.values():
                s["probability"] = round(s["probability"] / total_prob, 2)

        pwv = round(pwv_numerator / total_prob, 2) if total_prob > 0 else None

        margin_of_safety = None
        dcf_rec = "Insufficient data"
        if pwv and current_price and current_price > 0:
            margin_of_safety = round((pwv - current_price) / current_price * 100, 2)
            if margin_of_safety > 20:
                dcf_rec = "Buy"
            elif margin_of_safety < -10:
                dcf_rec = "Exit"
            else:
                dcf_rec = "Hold"

        return {
            "available": True,
            "wacc_pct": round(wacc * 100, 2),
            "base_fcf_cr": round(base_fcf, 2),
            "scenarios": scenarios,
            "probability_weighted_intrinsic": pwv,
            "margin_of_safety_pct": margin_of_safety,
            "dcf_recommendation": dcf_rec,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve_base_fcf(self, inputs: Dict[str, Any]) -> Optional[float]:
        """Use FCF if positive; fall back to net_income * 0.75; then ebitda * 0.55."""
        fcf = inputs.get("fcf")
        if fcf and fcf > 0:
            return fcf
        net_income = inputs.get("net_income")
        if net_income and net_income > 0:
            return net_income * 0.75
        ebitda = inputs.get("ebitda")
        if ebitda and ebitda > 0:
            return ebitda * 0.55
        return None

    def _compute_wacc(self, risk_free_rate: float, de_ratio: float) -> float:
        """Simplified WACC using CAPM for equity cost and pre-tax cost of debt."""
        beta = DEFAULT_BETA
        cost_of_equity = risk_free_rate + beta * (INDIA_ERP / 100)

        # Estimate debt weight from D/E ratio
        d_weight = de_ratio / (1 + de_ratio) if de_ratio and de_ratio > 0 else 0.3
        e_weight = 1 - d_weight

        cost_of_debt = risk_free_rate + 0.015  # spread over risk-free
        tax_rate = 0.25  # Indian corporate tax rate (default)

        wacc = e_weight * cost_of_equity + d_weight * cost_of_debt * (1 - tax_rate)
        return round(wacc, 4)

    def _project_dcf(
        self,
        base_fcf_cr: float,
        fcf_growth: float,
        wacc: float,
        terminal_growth: float,
        years: int,
        shares_outstanding: Optional[float],
    ) -> Dict[str, Any]:
        """Compute DCF: PV of projected FCFs + terminal value → equity value → per share."""
        fcf = base_fcf_cr
        pv_fcfs: List[float] = []
        projections: List[Dict[str, float]] = []

        for year in range(1, years + 1):
            fcf *= (1 + fcf_growth)
            pv = fcf / (1 + wacc) ** year
            pv_fcfs.append(pv)
            projections.append({"year": year, "fcf_cr": round(fcf, 2), "pv_cr": round(pv, 2)})

        terminal_fcf = fcf * (1 + terminal_growth)
        terminal_value = terminal_fcf / (wacc - terminal_growth)
        pv_terminal = terminal_value / (1 + wacc) ** years

        enterprise_value_cr = sum(pv_fcfs) + pv_terminal

        intrinsic_per_share = None
        if shares_outstanding and shares_outstanding > 0:
            # EV in ₹ = EV_cr * 1e7; divide by shares → per share price in ₹
            intrinsic_per_share = round((enterprise_value_cr * 1e7) / shares_outstanding, 2)

        return {
            "enterprise_value_cr": round(enterprise_value_cr, 2),
            "pv_terminal_cr": round(pv_terminal, 2),
            "intrinsic_per_share": intrinsic_per_share,
            "fcf_projections": projections,
        }
