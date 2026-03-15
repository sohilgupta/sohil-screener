from typing import Optional, List


def build_valuation_prompt(
    company: str,
    ticker: str,
    industry: str = "Unknown",
    competitors: Optional[List[str]] = None,
    allocation: Optional[float] = None,
    horizon: Optional[int] = None,
    revenue: Optional[float] = None,
    ebitda: Optional[float] = None,
    net_income: Optional[float] = None,
    fcf: Optional[float] = None,
    de_ratio: Optional[float] = None,
    shares_outstanding: Optional[float] = None,
    current_price: Optional[float] = None,
    market_condition: str = "Neutral",
    risk_free_rate: float = 7.2,
    pe_ratio: Optional[float] = None,
    market_cap: Optional[float] = None,
    roe: Optional[float] = None,
    opm: Optional[float] = None,
) -> str:
    """Build the comprehensive LLM valuation prompt for Indian equity analysis."""

    competitors_str = ", ".join(competitors) if competitors else "Data not available"
    allocation_str = f"{allocation}%" if allocation is not None else "Not specified"
    horizon_str = f"{horizon} years" if horizon is not None else "Not specified"

    def fmt_cr(val):
        if val is None:
            return "Data not available"
        return f"₹{val:,.2f} Cr"

    def fmt_ratio(val, suffix="x"):
        if val is None:
            return "Data not available"
        return f"{val:.2f}{suffix}"

    def fmt_price(val):
        if val is None:
            return "Data not available"
        return f"₹{val:,.2f}"

    # Probability guidance based on market condition
    prob_guidance = {
        "Bullish": "Bull 35%, Base 45%, Bear 20%",
        "Bearish": "Bull 20%, Base 45%, Bear 35%",
        "Neutral": "Bull 25%, Base 50%, Bear 25%",
    }.get(market_condition, "Bull 25%, Base 50%, Bear 25%")

    prompt = f"""You are a senior financial analyst specializing in Indian equity markets with deep expertise in company valuations.

COMPANY INFORMATION:
Company: {company}
Ticker: {ticker} (NSE/BSE)
Industry: {industry}
Competitors: {competitors_str}
Portfolio Allocation: {allocation_str}
Investment Horizon: {horizon_str}

FINANCIAL METRICS (all figures in Indian Rupees, monetary values in Crores):
Revenue (TTM): {fmt_cr(revenue)}
EBITDA (TTM): {fmt_cr(ebitda)}
EBITDA Margin: {fmt_ratio(opm, suffix="%") if opm else "Data not available"}
Net Income (TTM): {fmt_cr(net_income)}
Free Cash Flow (TTM): {fmt_cr(fcf)}
Debt/Equity Ratio: {fmt_ratio(de_ratio, suffix="")}
Return on Equity: {fmt_ratio(roe, suffix="%") if roe else "Data not available"}
Market Capitalization: {fmt_cr(market_cap)}

STOCK INFORMATION:
Current Market Price: {fmt_price(current_price)}
P/E Ratio: {fmt_ratio(pe_ratio, suffix="x") if pe_ratio else "Data not available"}
Shares Outstanding: {f"{shares_outstanding/1e7:.2f} Cr shares" if shares_outstanding else "Data not available"}
Market Condition: {market_condition}
Risk-Free Rate (Indian 10Y Bond): {risk_free_rate}%

ANALYSIS REQUIREMENTS:
Use financial data context from Screener.in, Trendlyne, or Finology. Apply your knowledge of Indian market valuations.

Perform valuation using 2–3 of these frameworks (select most appropriate for this company type):
1. DCF (Discounted Cash Flow) — use risk_free_rate + equity risk premium as WACC
2. Comparable Multiples (P/E, P/B based on sector peers)
3. EV/EBITDA Analysis
4. PEG Ratio (for growth companies)

Develop 3 scenarios with DIFFERENT growth rate assumptions:
- Bull Case (optimistic, higher growth/margin expansion)
- Base Case (realistic, moderate growth)
- Bear Case (conservative, growth slowdown/margin pressure)

PROBABILITY GUIDANCE for {market_condition} market: {prob_guidance}
Bull + Base + Bear probabilities MUST sum to exactly 1.0

REQUIRED OUTPUT STRUCTURE:

## 1. EXECUTIVE SUMMARY
[2-3 sentences summarizing investment thesis]

## 2. VALUATION FRAMEWORK SELECTION
[Explain which 2-3 methods you chose and why they suit this company]

## 3. DETAILED CALCULATIONS
[Show key numbers for each valuation method]

## 4. SCENARIO ANALYSIS
### Bull Case (Target: ₹X, Probability: X%)
- Revenue CAGR assumption: X%
- Key assumptions: [list]
- Valuation rationale

### Base Case (Target: ₹X, Probability: X%)
- Revenue CAGR assumption: X%
- Key assumptions: [list]
- Valuation rationale

### Bear Case (Target: ₹X, Probability: X%)
- Revenue CAGR assumption: X%
- Key assumptions: [list]
- Valuation rationale

## 5. PROBABILITY WEIGHTED EXPECTED VALUE
PWV = (P_bull × Bull Target) + (P_base × Base Target) + (P_bear × Bear Target)
Upside/Downside = (PWV − Current Price) / Current Price × 100%

## 6. RISK ASSESSMENT
[Key risks: regulatory, competitive, macro, company-specific]

## 7. RECOMMENDATION
[Buy / Hold / Exit with rationale]

## 8. PRICE TARGET
[12-month price target]

## 9. CONFIDENCE LEVEL
[High / Medium / Low with explanation]

## 10. PORTFOLIO IMPLICATIONS
[How this fits in a portfolio given allocation and horizon]

---
IMPORTANT: After your analysis, include EXACTLY this JSON block (no modifications to structure):

```json
{{
  "bull_case": {{
    "target_price": <number in INR>,
    "probability": <decimal 0-1>,
    "growth_rate": <annual revenue CAGR as percentage number>,
    "key_assumptions": ["assumption 1", "assumption 2", "assumption 3"]
  }},
  "base_case": {{
    "target_price": <number in INR>,
    "probability": <decimal 0-1>,
    "growth_rate": <annual revenue CAGR as percentage number>,
    "key_assumptions": ["assumption 1", "assumption 2", "assumption 3"]
  }},
  "bear_case": {{
    "target_price": <number in INR>,
    "probability": <decimal 0-1>,
    "growth_rate": <annual revenue CAGR as percentage number>,
    "key_assumptions": ["assumption 1", "assumption 2", "assumption 3"]
  }},
  "probability_weighted_value": <computed PWV as number in INR>,
  "upside_percentage": <upside from current price as percentage number, negative if downside>,
  "recommendation": "Buy",
  "confidence_level": "High",
  "price_target": <12-month price target as number in INR>,
  "executive_summary": "<2-3 sentence summary>",
  "key_risks": ["risk 1", "risk 2", "risk 3"],
  "valuation_methods": ["Method 1", "Method 2"]
}}
```"""
    return prompt
