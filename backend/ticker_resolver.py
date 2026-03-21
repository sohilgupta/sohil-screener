"""
Resolve user input (company name or ticker symbol) to a canonical
Yahoo Finance symbol.

Resolution order:
  1. Known ticker table   (instant — exact uppercase match)
  2. Known name table     (instant — substring match on company name)
  3. yfinance Search      (fast ~500ms — fuzzy text search on Yahoo Finance)
  4. Gemini LLM           (slower ~2s — last resort for ambiguous inputs)
  5. Heuristic fallback   (always returns something)
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# ── Known tickers (exact uppercase match, spaces stripped) ────────────────────
_KNOWN: Dict[str, Dict[str, str]] = {
    # Indian stocks
    "TCS":          {"yf_symbol": "TCS.NS",         "display_ticker": "TCS",         "company_name": "Tata Consultancy Services",     "exchange": "NSE", "market": "IN", "currency": "INR"},
    "RELIANCE":     {"yf_symbol": "RELIANCE.NS",     "display_ticker": "RELIANCE",    "company_name": "Reliance Industries",           "exchange": "NSE", "market": "IN", "currency": "INR"},
    "HDFCBANK":     {"yf_symbol": "HDFCBANK.NS",     "display_ticker": "HDFCBANK",    "company_name": "HDFC Bank",                     "exchange": "NSE", "market": "IN", "currency": "INR"},
    "ICICIBANK":    {"yf_symbol": "ICICIBANK.NS",    "display_ticker": "ICICIBANK",   "company_name": "ICICI Bank",                    "exchange": "NSE", "market": "IN", "currency": "INR"},
    "INFY":         {"yf_symbol": "INFY.NS",         "display_ticker": "INFY",        "company_name": "Infosys",                       "exchange": "NSE", "market": "IN", "currency": "INR"},
    "INFOSYS":      {"yf_symbol": "INFY.NS",         "display_ticker": "INFY",        "company_name": "Infosys",                       "exchange": "NSE", "market": "IN", "currency": "INR"},
    "WIPRO":        {"yf_symbol": "WIPRO.NS",        "display_ticker": "WIPRO",       "company_name": "Wipro",                         "exchange": "NSE", "market": "IN", "currency": "INR"},
    "BAJFINANCE":   {"yf_symbol": "BAJFINANCE.NS",   "display_ticker": "BAJFINANCE",  "company_name": "Bajaj Finance",                 "exchange": "NSE", "market": "IN", "currency": "INR"},
    "ZOMATO":       {"yf_symbol": "ZOMATO.NS",       "display_ticker": "ZOMATO",      "company_name": "Zomato",                        "exchange": "NSE", "market": "IN", "currency": "INR"},
    "ADANIENT":     {"yf_symbol": "ADANIENT.NS",     "display_ticker": "ADANIENT",    "company_name": "Adani Enterprises",             "exchange": "NSE", "market": "IN", "currency": "INR"},
    "TATAMOTORS":   {"yf_symbol": "TATAMOTORS.NS",   "display_ticker": "TATAMOTORS",  "company_name": "Tata Motors",                   "exchange": "NSE", "market": "IN", "currency": "INR"},
    "MARUTI":       {"yf_symbol": "MARUTI.NS",       "display_ticker": "MARUTI",      "company_name": "Maruti Suzuki",                 "exchange": "NSE", "market": "IN", "currency": "INR"},
    "OLAELEC":      {"yf_symbol": "OLAELEC.NS",      "display_ticker": "OLAELEC",     "company_name": "Ola Electric Mobility",         "exchange": "NSE", "market": "IN", "currency": "INR"},
    "PAYTM":        {"yf_symbol": "PAYTM.NS",        "display_ticker": "PAYTM",       "company_name": "One 97 Communications (Paytm)", "exchange": "NSE", "market": "IN", "currency": "INR"},
    "NYKAA":        {"yf_symbol": "NYKAA.NS",        "display_ticker": "NYKAA",       "company_name": "Nykaa (FSN E-Commerce)",        "exchange": "NSE", "market": "IN", "currency": "INR"},
    "ELECON":       {"yf_symbol": "ELECON.NS",       "display_ticker": "ELECON",      "company_name": "Elecon Engineering",            "exchange": "NSE", "market": "IN", "currency": "INR"},
    "SBIN":         {"yf_symbol": "SBIN.NS",         "display_ticker": "SBIN",        "company_name": "State Bank of India",           "exchange": "NSE", "market": "IN", "currency": "INR"},
    "AXISBANK":     {"yf_symbol": "AXISBANK.NS",     "display_ticker": "AXISBANK",    "company_name": "Axis Bank",                     "exchange": "NSE", "market": "IN", "currency": "INR"},
    "KOTAKBANK":    {"yf_symbol": "KOTAKBANK.NS",    "display_ticker": "KOTAKBANK",   "company_name": "Kotak Mahindra Bank",           "exchange": "NSE", "market": "IN", "currency": "INR"},
    "SUNPHARMA":    {"yf_symbol": "SUNPHARMA.NS",    "display_ticker": "SUNPHARMA",   "company_name": "Sun Pharmaceutical",            "exchange": "NSE", "market": "IN", "currency": "INR"},
    "HCLTECH":      {"yf_symbol": "HCLTECH.NS",      "display_ticker": "HCLTECH",     "company_name": "HCL Technologies",              "exchange": "NSE", "market": "IN", "currency": "INR"},
    "TECHM":        {"yf_symbol": "TECHM.NS",        "display_ticker": "TECHM",       "company_name": "Tech Mahindra",                 "exchange": "NSE", "market": "IN", "currency": "INR"},
    "ASIANPAINT":   {"yf_symbol": "ASIANPAINT.NS",   "display_ticker": "ASIANPAINT",  "company_name": "Asian Paints",                  "exchange": "NSE", "market": "IN", "currency": "INR"},
    "ULTRACEMCO":   {"yf_symbol": "ULTRACEMCO.NS",   "display_ticker": "ULTRACEMCO",  "company_name": "UltraTech Cement",              "exchange": "NSE", "market": "IN", "currency": "INR"},
    "NESTLEIND":    {"yf_symbol": "NESTLEIND.NS",    "display_ticker": "NESTLEIND",   "company_name": "Nestle India",                  "exchange": "NSE", "market": "IN", "currency": "INR"},
    "DMART":        {"yf_symbol": "DMART.NS",        "display_ticker": "DMART",       "company_name": "Avenue Supermarts (DMart)",     "exchange": "NSE", "market": "IN", "currency": "INR"},
    "IRCTC":        {"yf_symbol": "IRCTC.NS",        "display_ticker": "IRCTC",       "company_name": "IRCTC",                         "exchange": "NSE", "market": "IN", "currency": "INR"},
    # US stocks
    "AAPL":         {"yf_symbol": "AAPL",            "display_ticker": "AAPL",        "company_name": "Apple Inc",                     "exchange": "NASDAQ", "market": "US", "currency": "USD"},
    "MSFT":         {"yf_symbol": "MSFT",            "display_ticker": "MSFT",        "company_name": "Microsoft",                     "exchange": "NASDAQ", "market": "US", "currency": "USD"},
    "GOOGL":        {"yf_symbol": "GOOGL",           "display_ticker": "GOOGL",       "company_name": "Alphabet (Google)",             "exchange": "NASDAQ", "market": "US", "currency": "USD"},
    "GOOG":         {"yf_symbol": "GOOG",            "display_ticker": "GOOG",        "company_name": "Alphabet (Google)",             "exchange": "NASDAQ", "market": "US", "currency": "USD"},
    "AMZN":         {"yf_symbol": "AMZN",            "display_ticker": "AMZN",        "company_name": "Amazon",                        "exchange": "NASDAQ", "market": "US", "currency": "USD"},
    "NVDA":         {"yf_symbol": "NVDA",            "display_ticker": "NVDA",        "company_name": "NVIDIA",                        "exchange": "NASDAQ", "market": "US", "currency": "USD"},
    "TSLA":         {"yf_symbol": "TSLA",            "display_ticker": "TSLA",        "company_name": "Tesla",                         "exchange": "NASDAQ", "market": "US", "currency": "USD"},
    "META":         {"yf_symbol": "META",            "display_ticker": "META",        "company_name": "Meta Platforms",                "exchange": "NASDAQ", "market": "US", "currency": "USD"},
    "NFLX":         {"yf_symbol": "NFLX",            "display_ticker": "NFLX",        "company_name": "Netflix",                       "exchange": "NASDAQ", "market": "US", "currency": "USD"},
    "UBER":         {"yf_symbol": "UBER",            "display_ticker": "UBER",        "company_name": "Uber Technologies",             "exchange": "NYSE",   "market": "US", "currency": "USD"},
    "BABA":         {"yf_symbol": "BABA",            "display_ticker": "BABA",        "company_name": "Alibaba Group",                 "exchange": "NYSE",   "market": "US", "currency": "USD"},
}

# ── Known company names (substring match, lowercase) ─────────────────────────
# Maps name fragment → entry key in _KNOWN
_NAME_MAP: Dict[str, str] = {
    # Indian
    "ola electric":         "OLAELEC",
    "ola mobility":         "OLAELEC",
    "tata consultancy":     "TCS",
    "tata consult":         "TCS",
    "reliance industries":  "RELIANCE",
    "reliance ind":         "RELIANCE",
    "hdfc bank":            "HDFCBANK",
    "icici bank":           "ICICIBANK",
    "infosys":              "INFY",
    "bajaj finance":        "BAJFINANCE",
    "tata motors":          "TATAMOTORS",
    "maruti suzuki":        "MARUTI",
    "state bank":           "SBIN",
    "axis bank":            "AXISBANK",
    "kotak":                "KOTAKBANK",
    "sun pharma":           "SUNPHARMA",
    "hcl tech":             "HCLTECH",
    "tech mahindra":        "TECHM",
    "asian paints":         "ASIANPAINT",
    "ultratech":            "ULTRACEMCO",
    "nestle india":         "NESTLEIND",
    "avenue supermart":     "DMART",
    "dmart":                "DMART",
    "elecon engineer":      "ELECON",
    "paytm":                "PAYTM",
    "nykaa":                "NYKAA",
    "zomato":               "ZOMATO",
    "adani enterprises":    "ADANIENT",
    # US
    "apple":                "AAPL",
    "microsoft":            "MSFT",
    "google":               "GOOGL",
    "alphabet":             "GOOGL",
    "amazon":               "AMZN",
    "nvidia":               "NVDA",
    "tesla":                "TSLA",
    "meta":                 "META",
    "facebook":             "META",
    "netflix":              "NFLX",
    "uber":                 "UBER",
    "alibaba":              "BABA",
}

# NSE exchange codes Yahoo Finance uses
_NSE_EXCHANGES = {"NSI", "NSE", "BSE", "BOM", "BSE_EQ"}


def resolve_ticker(user_input: str) -> Dict[str, Any]:
    """Resolve company name or ticker → canonical Yahoo Finance symbol."""
    raw = user_input.strip()
    upper = raw.upper().replace(" ", "").replace("-", "")
    lower = raw.lower()

    # 1. Exact ticker table lookup
    if upper in _KNOWN:
        logger.info("Known-ticker hit: %s → %s", raw, _KNOWN[upper]["yf_symbol"])
        return dict(_KNOWN[upper])

    # Also try with .NS / .BO suffix stripped
    stripped = upper.replace(".NS", "").replace(".BO", "")
    if stripped in _KNOWN:
        return dict(_KNOWN[stripped])

    # 2. Known name table (substring match)
    for fragment, key in _NAME_MAP.items():
        if fragment in lower and key in _KNOWN:
            logger.info("Name-map hit: '%s' → %s", raw, _KNOWN[key]["yf_symbol"])
            return dict(_KNOWN[key])

    # 3. yfinance Search
    result = _search_yfinance(raw)
    if result:
        return result

    # 4. Gemini LLM
    result = _resolve_via_gemini(raw)
    if result:
        return result

    # 5. Heuristic fallback
    return _heuristic(raw, upper)


# ── yfinance Search ───────────────────────────────────────────────────────────

def _search_yfinance(query: str) -> Optional[Dict[str, Any]]:
    """Use yfinance.Search to find the best matching ticker."""
    try:
        import yfinance as yf
        search = yf.Search(query, max_results=8, news_count=0)
        quotes = getattr(search, "quotes", []) or []

        if not quotes:
            logger.info("yfinance Search returned no results for '%s'", query)
            return None

        # Prefer Indian exchange results when query doesn't look like a US company
        query_upper = query.upper().replace(" ", "")
        looks_us = any(t in query.lower() for t in ["apple", "microsoft", "google", "amazon", "nvidia", "tesla", "meta", "netflix", "uber"])

        for q in quotes:
            symbol = q.get("symbol", "")
            exchange = q.get("exchange", "")
            name = q.get("longname") or q.get("shortname") or symbol

            if not symbol:
                continue

            # Classify market
            if exchange in _NSE_EXCHANGES or symbol.endswith(".NS") or symbol.endswith(".BO"):
                market = "IN"
                currency = "INR"
                # Ensure .NS suffix
                if not (symbol.endswith(".NS") or symbol.endswith(".BO")):
                    symbol = symbol + ".NS"
            elif looks_us or exchange in {"NMS", "NYQ", "NGM", "PCX", "NASDAQ", "NYSE"}:
                market = "US"
                currency = "USD"
            else:
                # Skip unknown exchanges unless it's the only result
                if len(quotes) > 1:
                    continue
                market = "US"
                currency = "USD"

            display = symbol.split(".")[0]
            logger.info("yfinance Search: '%s' → %s (%s)", query, symbol, exchange)
            return {
                "yf_symbol": symbol,
                "display_ticker": display,
                "company_name": name,
                "exchange": exchange,
                "market": market,
                "currency": currency,
            }

    except Exception as e:
        logger.warning("yfinance Search failed for '%s': %s", query, e)
    return None


# ── Gemini LLM ────────────────────────────────────────────────────────────────

_PROMPT = """\
Identify the stock for "{input}" and return its Yahoo Finance ticker symbol.

Return ONLY a valid JSON object — no markdown, no explanation:
{{
  "yf_symbol": "OLAELEC.NS",
  "display_ticker": "OLAELEC",
  "company_name": "Ola Electric Mobility Ltd",
  "exchange": "NSE",
  "market": "IN",
  "currency": "INR"
}}

Rules:
- Indian NSE stocks → append .NS (TCS → TCS.NS, HDFCBANK → HDFCBANK.NS)
- Indian BSE-only stocks → append .BO
- US stocks → plain symbol (AAPL, MSFT, NVDA)
- market: "IN" for India, "US" for United States
- OLA ELECTRIC / Ola Electric → OLAELEC.NS (NSE ticker is OLAELEC, not OLAELECTRIC)"""


def _resolve_via_gemini(raw: str) -> Optional[Dict[str, Any]]:
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return None
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        for model_id in ["gemini-2.0-flash", "gemini-1.5-flash-latest"]:
            try:
                model = genai.GenerativeModel(model_id)
                resp = model.generate_content(
                    _PROMPT.format(input=raw),
                    generation_config={"temperature": 0.05, "max_output_tokens": 200},
                )
                text = re.sub(r"^```[a-z]*\n?", "", resp.text.strip())
                text = re.sub(r"\n?```$", "", text)
                result = json.loads(text.strip())
                logger.info("Gemini resolved '%s' → %s", raw, result.get("yf_symbol"))
                return result
            except Exception as e:
                logger.warning("Gemini model %s failed: %s", model_id, e)
    except Exception as e:
        logger.warning("Gemini resolver error for '%s': %s", raw, e)
    return None


# ── Heuristic fallback ────────────────────────────────────────────────────────

def _heuristic(raw: str, upper_nospace: str) -> Dict[str, Any]:
    """Last-resort: guess Indian NSE if it looks like a ticker, else treat as search query."""
    # Already has suffix
    if raw.upper().endswith(".NS"):
        display = raw.upper()[:-3]
        return {"yf_symbol": raw.upper(), "display_ticker": display, "company_name": display,
                "exchange": "NSE", "market": "IN", "currency": "INR"}
    if raw.upper().endswith(".BO"):
        display = raw.upper()[:-3]
        return {"yf_symbol": raw.upper(), "display_ticker": display, "company_name": display,
                "exchange": "BSE", "market": "IN", "currency": "INR"}

    # Short all-caps no-space → likely Indian NSE ticker
    if re.match(r"^[A-Z0-9&]{1,15}$", upper_nospace):
        return {"yf_symbol": upper_nospace + ".NS", "display_ticker": upper_nospace,
                "company_name": upper_nospace, "exchange": "NSE", "market": "IN", "currency": "INR"}

    # Has spaces or mixed case → unknown, try as-is on Yahoo Finance
    return {"yf_symbol": upper_nospace, "display_ticker": upper_nospace, "company_name": raw,
            "exchange": "UNKNOWN", "market": "IN", "currency": "INR"}
