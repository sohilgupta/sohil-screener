"""
Resolve user input (company name or ticker symbol) to a canonical
Yahoo Finance symbol using Gemini LLM.

Returns a dict with:
    yf_symbol      str   e.g. "TCS.NS" or "AAPL"
    display_ticker str   e.g. "TCS" or "AAPL"
    company_name   str   e.g. "Tata Consultancy Services"
    exchange       str   e.g. "NSE" / "NASDAQ"
    market         str   "IN" or "US" or "OTHER"
    currency       str   "INR" or "USD"
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Dict, Any

logger = logging.getLogger(__name__)

_PROMPT = """\
You are a financial data expert. The user entered: "{input}"

Determine the correct Yahoo Finance ticker symbol for this stock.

Rules:
- Indian NSE stocks → append .NS  (e.g. TCS → TCS.NS, HDFCBANK → HDFCBANK.NS, RELIANCE → RELIANCE.NS)
- Indian BSE-only stocks → append .BO
- US stocks → plain symbol, no suffix  (e.g. AAPL, MSFT, GOOGL, NVDA, TSLA)
- If the input is already a correct ticker, confirm it with the right suffix
- If the input is a company name, find the most likely publicly traded company
- market: "IN" for India, "US" for United States, "OTHER" for everything else

Return ONLY a valid JSON object — no markdown, no explanation:
{{
  "yf_symbol": "TCS.NS",
  "display_ticker": "TCS",
  "company_name": "Tata Consultancy Services Ltd",
  "exchange": "NSE",
  "market": "IN",
  "currency": "INR",
  "confidence": "high"
}}"""

# Well-known tickers for instant resolution without LLM
_KNOWN: Dict[str, Dict[str, str]] = {
    "TCS":        {"yf_symbol": "TCS.NS",        "display_ticker": "TCS",        "company_name": "Tata Consultancy Services",    "exchange": "NSE",    "market": "IN", "currency": "INR"},
    "RELIANCE":   {"yf_symbol": "RELIANCE.NS",   "display_ticker": "RELIANCE",   "company_name": "Reliance Industries",          "exchange": "NSE",    "market": "IN", "currency": "INR"},
    "HDFCBANK":   {"yf_symbol": "HDFCBANK.NS",   "display_ticker": "HDFCBANK",   "company_name": "HDFC Bank",                    "exchange": "NSE",    "market": "IN", "currency": "INR"},
    "ICICIBANK":  {"yf_symbol": "ICICIBANK.NS",  "display_ticker": "ICICIBANK",  "company_name": "ICICI Bank",                   "exchange": "NSE",    "market": "IN", "currency": "INR"},
    "INFY":       {"yf_symbol": "INFY.NS",       "display_ticker": "INFY",       "company_name": "Infosys",                      "exchange": "NSE",    "market": "IN", "currency": "INR"},
    "WIPRO":      {"yf_symbol": "WIPRO.NS",      "display_ticker": "WIPRO",      "company_name": "Wipro",                        "exchange": "NSE",    "market": "IN", "currency": "INR"},
    "BAJFINANCE": {"yf_symbol": "BAJFINANCE.NS", "display_ticker": "BAJFINANCE", "company_name": "Bajaj Finance",                "exchange": "NSE",    "market": "IN", "currency": "INR"},
    "ZOMATO":     {"yf_symbol": "ZOMATO.NS",     "display_ticker": "ZOMATO",     "company_name": "Zomato",                       "exchange": "NSE",    "market": "IN", "currency": "INR"},
    "ADANIENT":   {"yf_symbol": "ADANIENT.NS",   "display_ticker": "ADANIENT",   "company_name": "Adani Enterprises",            "exchange": "NSE",    "market": "IN", "currency": "INR"},
    "TATAMOTORS": {"yf_symbol": "TATAMOTORS.NS", "display_ticker": "TATAMOTORS", "company_name": "Tata Motors",                  "exchange": "NSE",    "market": "IN", "currency": "INR"},
    "MARUTI":     {"yf_symbol": "MARUTI.NS",     "display_ticker": "MARUTI",     "company_name": "Maruti Suzuki",                "exchange": "NSE",    "market": "IN", "currency": "INR"},
    "OLAELEC":    {"yf_symbol": "OLAELEC.NS",    "display_ticker": "OLAELEC",    "company_name": "Ola Electric Mobility",        "exchange": "NSE",    "market": "IN", "currency": "INR"},
    "PAYTM":      {"yf_symbol": "PAYTM.NS",      "display_ticker": "PAYTM",      "company_name": "One 97 Communications",        "exchange": "NSE",    "market": "IN", "currency": "INR"},
    "NYKAA":      {"yf_symbol": "NYKAA.NS",      "display_ticker": "NYKAA",      "company_name": "FSN E-Commerce Ventures",      "exchange": "NSE",    "market": "IN", "currency": "INR"},
    "AAPL":       {"yf_symbol": "AAPL",          "display_ticker": "AAPL",       "company_name": "Apple Inc",                    "exchange": "NASDAQ", "market": "US", "currency": "USD"},
    "MSFT":       {"yf_symbol": "MSFT",          "display_ticker": "MSFT",       "company_name": "Microsoft",                    "exchange": "NASDAQ", "market": "US", "currency": "USD"},
    "GOOGL":      {"yf_symbol": "GOOGL",         "display_ticker": "GOOGL",      "company_name": "Alphabet Inc",                 "exchange": "NASDAQ", "market": "US", "currency": "USD"},
    "AMZN":       {"yf_symbol": "AMZN",          "display_ticker": "AMZN",       "company_name": "Amazon",                       "exchange": "NASDAQ", "market": "US", "currency": "USD"},
    "NVDA":       {"yf_symbol": "NVDA",          "display_ticker": "NVDA",       "company_name": "NVIDIA",                       "exchange": "NASDAQ", "market": "US", "currency": "USD"},
    "TSLA":       {"yf_symbol": "TSLA",          "display_ticker": "TSLA",       "company_name": "Tesla",                        "exchange": "NASDAQ", "market": "US", "currency": "USD"},
    "META":       {"yf_symbol": "META",          "display_ticker": "META",       "company_name": "Meta Platforms",               "exchange": "NASDAQ", "market": "US", "currency": "USD"},
}


def resolve_ticker(user_input: str) -> Dict[str, Any]:
    """Resolve company name or ticker to canonical Yahoo Finance symbol."""
    raw = user_input.strip()
    upper = raw.upper().replace(" ", "")

    # 1. Direct lookup in known-ticker table
    if upper in _KNOWN:
        logger.info("Resolved '%s' via known-ticker lookup → %s", raw, _KNOWN[upper]["yf_symbol"])
        return dict(_KNOWN[upper])

    # 2. Call Gemini for name resolution
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY not set")

        import google.generativeai as genai
        genai.configure(api_key=api_key)

        for model_id in ["gemini-2.0-flash", "gemini-1.5-flash-latest"]:
            try:
                model = genai.GenerativeModel(model_id)
                resp = model.generate_content(
                    _PROMPT.format(input=raw),
                    generation_config={"temperature": 0.1, "max_output_tokens": 256},
                )
                text = resp.text.strip()
                text = re.sub(r"^```[a-z]*\n?", "", text)
                text = re.sub(r"\n?```$", "", text)
                result = json.loads(text.strip())
                logger.info("Resolved '%s' via LLM → %s", raw, result.get("yf_symbol"))
                return result
            except (json.JSONDecodeError, Exception) as e:
                logger.warning("LLM model %s failed for '%s': %s", model_id, raw, e)
                continue
    except Exception as e:
        logger.warning("Gemini ticker resolution failed for '%s': %s", raw, e)

    # 3. Heuristic fallback — no spaces = likely a ticker
    if " " not in raw:
        # Check if it already has a yfinance suffix
        if raw.endswith(".NS") or raw.endswith(".BO"):
            display = raw.split(".")[0].upper()
            return {"yf_symbol": raw.upper(), "display_ticker": display,
                    "company_name": display, "exchange": "NSE", "market": "IN", "currency": "INR"}
        # Assume Indian NSE by default for short all-caps codes
        if re.match(r"^[A-Z0-9&]{1,15}$", upper):
            return {"yf_symbol": upper + ".NS", "display_ticker": upper,
                    "company_name": upper, "exchange": "NSE", "market": "IN", "currency": "INR"}

    # Ultimate fallback — treat as US ticker
    return {"yf_symbol": upper, "display_ticker": upper, "company_name": raw,
            "exchange": "UNKNOWN", "market": "US", "currency": "USD"}
