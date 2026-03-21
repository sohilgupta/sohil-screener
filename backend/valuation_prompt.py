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
    market: str = "IN",          # "IN" for India, "US" for US
    currency: str = "INR",       # "INR" or "USD"
    unit_label: str = "Crore",   # "Crore" or "Million"
) -> str:
    """Build the LLM valuation prompt. Works for both Indian and US equities."""

    competitors_str = ", ".join(competitors) if competitors else "Not available"
    allocation_str = f"{allocation}%" if allocation is not None else "Not specified"
    horizon_str = f"{horizon} years" if horizon is not None else "Not specified"

    is_india = (market == "IN")
    exchange_label = "NSE/BSE" if is_india else "NYSE/NASDAQ"
    rfr_label = "Indian 10Y G-Sec yield" if is_india else "US 10Y Treasury yield"
    currency_sym = "₹" if is_india else "$"

    # Count available data fields
    data_fields = [revenue, ebitda, net_income, fcf, pe_ratio, market_cap]
    available_count = sum(1 for x in data_fields if x is not None)
    has_minimal_data = current_price is not None
    has_rich_data = available_count >= 3

    def fmt_monetary(val):
        if val is None:
            return "Not available"
        return f"{currency_sym}{val:,.2f} {unit_label}"

    def fmt_ratio(val, suffix="x"):
        if val is None:
            return "Not available"
        return f"{val:.2f}{suffix}"

    def fmt_price(val):
        if val is None:
            return "Not available"
        return f"{currency_sym}{val:,.2f}"

    prob_guidance = {
        "Bullish": "Bull 35%, Base 45%, Bear 20%",
        "Bearish": "Bull 20%, Base 45%, Bear 35%",
        "Neutral": "Bull 25%, Base 50%, Bear 25%",
    }.get(market_condition, "Bull 25%, Base 50%, Bear 25%")

    # Knowledge-based instruction when financial data is limited
    if not has_rich_data:
        data_instruction = f"""
IMPORTANT — LIMITED LIVE DATA AVAILABLE:
Structured financial data is unavailable or incomplete for {company}.
You MUST still perform a complete valuation using:
1. Your training knowledge about {company}'s business model, revenue scale, and historical financials
2. Comparable company multiples for the {industry} sector
3. Current market price of {fmt_price(current_price)} as your anchor
4. Provide SPECIFIC NUMERIC price targets — do NOT use null or "N/A" for target prices

If uncertain, use conservative estimates and reflect this in the confidence level.
"""
    else:
        data_instruction = f"""
Use the financial data provided below alongside your knowledge of {company} and {industry} sector peers.
"""

    prompt = f"""You are a senior financial analyst specializing in {exchange_label} equity markets.

COMPANY:
Name: {company}
Ticker: {ticker} ({exchange_label})
Industry: {industry}
Competitors: {competitors_str}
Portfolio Allocation: {allocation_str}
Investment Horizon: {horizon_str}
{data_instruction}
FINANCIAL METRICS (monetary values in {unit_label}s of {currency}):
Revenue (TTM):        {fmt_monetary(revenue)}
EBITDA (TTM):         {fmt_monetary(ebitda)}
EBITDA Margin:        {fmt_ratio(opm, suffix="%") if opm else "Not available"}
Net Income (TTM):     {fmt_monetary(net_income)}
Free Cash Flow (TTM): {fmt_monetary(fcf)}
Debt/Equity Ratio:    {fmt_ratio(de_ratio, suffix="")}
Return on Equity:     {fmt_ratio(roe, suffix="%") if roe else "Not available"}
Market Cap:           {fmt_monetary(market_cap)}

STOCK:
Current Price:        {fmt_price(current_price)}
P/E Ratio:            {fmt_ratio(pe_ratio, suffix="x") if pe_ratio else "Not available"}
Shares Outstanding:   {f"{shares_outstanding/1e7:.2f} Cr shares" if shares_outstanding and is_india else (f"{shares_outstanding/1e6:.1f}M shares" if shares_outstanding else "Not available")}
Market Condition:     {market_condition}
{rfr_label}: {risk_free_rate}%

VALUATION TASK:
Select 2–3 appropriate methods from:
1. DCF — use {rfr_label} + equity risk premium as WACC
2. Comparable Multiples (P/E, EV/EBITDA based on sector peers)
3. P/B or PEG Ratio (for growth/financial companies)
4. Dividend Discount Model (for dividend-paying companies)

Develop 3 scenarios with DIFFERENT growth assumptions:
- Bull Case (optimistic)
- Base Case (realistic)
- Bear Case (conservative)

PROBABILITY GUIDANCE for {market_condition} market: {prob_guidance}
Bull + Base + Bear probabilities MUST sum to exactly 1.0

REQUIRED OUTPUT — narrative sections then JSON:

## 1. EXECUTIVE SUMMARY
[2-3 sentence investment thesis]

## 2. VALUATION METHODOLOGY
[Which 2-3 methods and why for this company]

## 3. SCENARIO ANALYSIS
### Bull Case (Target: {currency_sym}X, Probability: X%)
### Base Case (Target: {currency_sym}X, Probability: X%)
### Bear Case (Target: {currency_sym}X, Probability: X%)

## 4. PROBABILITY WEIGHTED VALUE
PWV = (P_bull × Bull) + (P_base × Base) + (P_bear × Bear)
Upside = (PWV − {fmt_price(current_price)}) / {fmt_price(current_price)} × 100

## 5. RISKS & RECOMMENDATION

---
After the analysis, output EXACTLY this JSON block:

```json
{{
  "bull_case": {{
    "target_price": <number in {currency}>,
    "probability": <decimal 0-1>,
    "growth_rate": <revenue CAGR % as number>,
    "key_assumptions": ["assumption 1", "assumption 2", "assumption 3"]
  }},
  "base_case": {{
    "target_price": <number in {currency}>,
    "probability": <decimal 0-1>,
    "growth_rate": <revenue CAGR % as number>,
    "key_assumptions": ["assumption 1", "assumption 2", "assumption 3"]
  }},
  "bear_case": {{
    "target_price": <number in {currency}>,
    "probability": <decimal 0-1>,
    "growth_rate": <revenue CAGR % as number>,
    "key_assumptions": ["assumption 1", "assumption 2", "assumption 3"]
  }},
  "probability_weighted_value": <computed PWV — MUST be a number>,
  "upside_percentage": <upside % from current price — MUST be a number>,
  "recommendation": "Buy",
  "confidence_level": "High",
  "price_target": <12-month target — MUST be a number>,
  "executive_summary": "<2-3 sentence summary>",
  "key_risks": ["risk 1", "risk 2", "risk 3"],
  "valuation_methods": ["Method 1", "Method 2"]
}}
```"""
    return prompt
