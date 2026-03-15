import io
import re
import logging
from typing import List, Dict, Any, Optional

import pytesseract
from PIL import Image, ImageFilter, ImageEnhance

logger = logging.getLogger(__name__)

# NSE ticker lookup for common Indian stocks
NAME_TO_TICKER: Dict[str, str] = {
    "hdfc bank": "HDFCBANK",
    "hdfcbank": "HDFCBANK",
    "reliance industries": "RELIANCE",
    "reliance": "RELIANCE",
    "tata consultancy": "TCS",
    "tcs": "TCS",
    "infosys": "INFY",
    "infy": "INFY",
    "itc": "ITC",
    "state bank": "SBIN",
    "sbi": "SBIN",
    "sbin": "SBIN",
    "kotak mahindra": "KOTAKBANK",
    "kotak bank": "KOTAKBANK",
    "kotakbank": "KOTAKBANK",
    "icici bank": "ICICIBANK",
    "icicibank": "ICICIBANK",
    "wipro": "WIPRO",
    "hcl technologies": "HCLTECH",
    "hcltech": "HCLTECH",
    "axis bank": "AXISBANK",
    "axisbank": "AXISBANK",
    "bajaj finance": "BAJFINANCE",
    "bajfinance": "BAJFINANCE",
    "bharti airtel": "BHARTIARTL",
    "airtel": "BHARTIARTL",
    "asian paints": "ASIANPAINT",
    "asianpaint": "ASIANPAINT",
    "maruti suzuki": "MARUTI",
    "maruti": "MARUTI",
    "titan company": "TITAN",
    "titan": "TITAN",
    "nestle india": "NESTLEIND",
    "nestle": "NESTLEIND",
    "ultratech cement": "ULTRACEMCO",
    "sun pharma": "SUNPHARMA",
    "sunpharma": "SUNPHARMA",
    "dr reddy": "DRREDDY",
    "divi's lab": "DIVISLAB",
    "divis": "DIVISLAB",
    "cipla": "CIPLA",
    "larsen": "LT",
    "l&t": "LT",
    "lt": "LT",
    "ongc": "ONGC",
    "ntpc": "NTPC",
    "power grid": "POWERGRID",
    "tata motors": "TATAMOTORS",
    "tatamotors": "TATAMOTORS",
    "tata steel": "TATASTEEL",
    "tatasteel": "TATASTEEL",
    "hindalco": "HINDALCO",
    "jsw steel": "JSWSTEEL",
    "jswsteel": "JSWSTEEL",
    "bajaj auto": "BAJAJ-AUTO",
    "hero motocorp": "HEROMOTOCO",
    "mahindra": "M&M",
    "m&m": "M&M",
    "eicher motors": "EICHERMOT",
    "britannia": "BRITANNIA",
    "godrej consumer": "GODREJCP",
    "pidilite": "PIDILITIND",
    "berger paints": "BERGEPAINT",
    "zomato": "ZOMATO",
    "paytm": "PAYTM",
    "nykaa": "FSN",
    "adani ports": "ADANIPORTS",
    "adani enterprises": "ADANIENT",
    "dmart": "DMART",
    "avenue supermarts": "DMART",
    "hdfc life": "HDFCLIFE",
    "sbi life": "SBILIFE",
    "icici prudential": "ICICIPRULI",
    "indusind bank": "INDUSINDBK",
    "bandhan bank": "BANDHANBNK",
    "federal bank": "FEDERALBNK",
    "muthoot finance": "MUTHOOTFIN",
    "shriram finance": "SHRIRAMFIN",
    "page industries": "PAGEIND",
    "info edge": "NAUKRI",
    "naukri": "NAUKRI",
    "polycab": "POLYCAB",
    "abbott india": "ABBOTINDIA",
    "pfizer": "PFIZER",
    "colgate": "COLPAL",
    "hindustan unilever": "HINDUNILVR",
    "hul": "HINDUNILVR",
}


def _preprocess_image(img: Image.Image) -> Image.Image:
    """Enhance image quality for OCR accuracy."""
    # Convert to RGB
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    # Upscale small images
    w, h = img.size
    if w < 1200:
        scale = 1200 / w
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    # Sharpen and increase contrast
    img = img.filter(ImageFilter.SHARPEN)
    img = ImageEnhance.Contrast(img).enhance(1.5)

    return img


def extract_text_from_image(image_bytes: bytes) -> str:
    """Run Tesseract OCR on the image bytes."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img = _preprocess_image(img)
        text = pytesseract.image_to_string(img, lang="eng", config="--psm 6 --oem 3")
        logger.info(f"OCR extracted {len(text)} characters")
        return text
    except Exception as exc:
        logger.error(f"OCR failed: {exc}")
        return ""


def _normalize_ticker(raw_name: str) -> str:
    """Map a stock name string to its NSE ticker symbol."""
    name_lower = raw_name.lower().strip()

    # Direct lookup
    if name_lower in NAME_TO_TICKER:
        return NAME_TO_TICKER[name_lower]

    # Partial match
    for key, ticker in NAME_TO_TICKER.items():
        if key in name_lower:
            return ticker

    # Clean and return as-is (likely already a ticker)
    cleaned = re.sub(r"[^A-Z0-9&\-]", "", raw_name.upper())
    return cleaned if cleaned else raw_name.upper()


def _parse_line(line: str) -> Optional[Dict[str, Any]]:
    """
    Attempt to parse a single text line into a holding dict.
    Supports patterns like:
      HDFCBANK  120  1420.50
      HDFC Bank  120  ₹1,420
    """
    line = line.strip()
    if not line or len(line) < 5:
        return None

    # Skip obvious headers / labels
    lower = line.lower()
    if any(h in lower for h in [
        "stock", "symbol", "ticker", "shares", "quantity", "qty",
        "avg price", "avg. price", "buy price", "ltp", "p&l",
        "invested", "current value", "returns", "portfolio",
        "holdings", "gain", "loss", "day's",
    ]):
        if len(line) < 40:  # Short header line — skip
            return None

    # Extract all numbers (including decimals)
    numbers = re.findall(r"[\d,]+(?:\.\d+)?", line)
    numbers = [float(n.replace(",", "")) for n in numbers]

    if len(numbers) < 2:
        return None

    # Extract leading text (stock name)
    name_match = re.match(r"^([A-Za-z][A-Za-z0-9\s&./\-]+?)\s+(?=\d)", line)
    if not name_match:
        return None

    stock_name = name_match.group(1).strip()
    if len(stock_name) < 2 or len(stock_name) > 50:
        return None

    # Heuristic: quantity is usually an integer, price is usually larger
    int_numbers = [n for n in numbers if n == int(n) and 1 <= n <= 100000]
    price_numbers = [n for n in numbers if n > 10]

    if not int_numbers or not price_numbers:
        return None

    quantity = int(int_numbers[0])
    # Price = largest number that isn't the quantity (or largest float)
    candidate_prices = [n for n in price_numbers if n != quantity]
    if not candidate_prices:
        candidate_prices = price_numbers
    buy_price = max(candidate_prices)

    if not (1 < buy_price < 1_000_000) or quantity < 1:
        return None

    return {
        "stock_name": stock_name,
        "ticker": _normalize_ticker(stock_name),
        "quantity": quantity,
        "buy_price": round(buy_price, 2),
    }


def parse_holdings_from_text(text: str) -> List[Dict[str, Any]]:
    """Parse OCR text into a list of portfolio holdings."""
    holdings: List[Dict[str, Any]] = []
    seen_tickers: set = set()

    for line in text.splitlines():
        holding = _parse_line(line)
        if holding and holding["ticker"] not in seen_tickers:
            seen_tickers.add(holding["ticker"])
            holdings.append(holding)

    logger.info(f"Parsed {len(holdings)} holdings from OCR text")
    return holdings


def extract_portfolio_from_screenshot(image_bytes: bytes) -> List[Dict[str, Any]]:
    """Top-level function: OCR → parse → return holdings list."""
    text = extract_text_from_image(image_bytes)
    if not text.strip():
        logger.warning("OCR returned empty text")
        return []
    return parse_holdings_from_text(text)
