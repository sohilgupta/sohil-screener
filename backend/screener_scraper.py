import requests
from bs4 import BeautifulSoup
import re
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

REQUEST_TIMEOUT = 20


def clean_number(text: str) -> Optional[float]:
    """Parse Indian-format numbers (commas, ₹, Cr suffix, %)."""
    if not text or str(text).strip() in ["-", "N/A", "", "--"]:
        return None
    text = str(text).strip()
    text = text.replace("₹", "").replace(",", "").replace(" ", "")
    text = text.rstrip("Cr").rstrip("%").strip()
    try:
        return float(text)
    except (ValueError, TypeError):
        return None


def _get_last_col(cells) -> str:
    """Return text from the last meaningful table cell."""
    if len(cells) < 2:
        return ""
    return cells[-1].get_text(strip=True)


def fetch_screener_data(ticker: str) -> Dict[str, Any]:
    """Fetch comprehensive financial data from screener.in for an NSE/BSE ticker."""
    ticker = ticker.upper().strip()
    urls = [
        f"https://www.screener.in/company/{ticker}/consolidated/",
        f"https://www.screener.in/company/{ticker}/",
    ]

    soup = None
    for url in urls:
        try:
            session = requests.Session()
            resp = session.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.content, "lxml")
                logger.info(f"Fetched screener.in data for {ticker} from {url}")
                break
            elif resp.status_code == 404:
                continue
        except requests.RequestException as exc:
            logger.warning(f"Request failed for {url}: {exc}")

    if not soup:
        logger.warning(f"Falling back for {ticker} — screener.in unavailable")
        return _try_trendlyne(ticker)

    return _parse_page(soup, ticker)


def _parse_page(soup: BeautifulSoup, ticker: str) -> Dict[str, Any]:
    """Parse a screener.in company page into a structured dict."""

    # --- Company name ---
    # Older pages use class="company-name"; newer listings use class="h2 shrink-text"
    company_name = ticker
    h1 = soup.find("h1", class_="company-name") or soup.find("h1")
    if h1:
        name = h1.get_text(strip=True)
        if name and len(name) < 120:
            company_name = name

    # --- Top ratios (key metrics list) ---
    ratios: Dict[str, str] = {}
    ratios_section = soup.find("section", id="top-ratios")
    if ratios_section:
        for li in ratios_section.find_all("li"):
            name_s = li.find("span", class_="name")
            val_spans = li.find_all("span", class_="number")
            if name_s and val_spans:
                key = name_s.get_text(strip=True).lower()
                val = val_spans[-1].get_text(strip=True)
                ratios[key] = val

    current_price = None
    for k in ["current price", "price", "ltp", "cmp"]:
        if k in ratios:
            current_price = clean_number(ratios[k])
            if current_price:
                break

    market_cap = clean_number(ratios.get("mar cap", ratios.get("market cap", "")))
    pe_ratio = clean_number(ratios.get("stock p/e", ratios.get("p/e", "")))
    book_value = clean_number(ratios.get("book value", ""))
    roe = clean_number(ratios.get("roe", ""))

    # --- Fallback price/market-cap for new listings (no #top-ratios section) ---
    # span.number elements: price has parent text "₹X" (no Cr, no /, no %)
    if current_price is None:
        for span in soup.find_all("span", class_="number"):
            parent_text = span.parent.get_text(strip=True) if span.parent else ""
            num_text = span.get_text(strip=True)
            if (parent_text.startswith("₹") and
                    "Cr" not in parent_text and
                    "/" not in parent_text and
                    "%" not in parent_text):
                val = clean_number(num_text)
                if val and 0.5 < val < 200_000:
                    current_price = val
                    break

    if market_cap is None:
        for span in soup.find_all("span", class_="number"):
            parent_text = span.parent.get_text(strip=True) if span.parent else ""
            if parent_text.startswith("₹") and "Cr" in parent_text:
                market_cap = clean_number(span.get_text(strip=True))
                break

    # --- P&L ---
    revenue = ebitda = net_income = opm = None
    pl_section = soup.find("section", id="profit-loss")
    if pl_section:
        for row in (pl_section.find("table") or BeautifulSoup("", "lxml")).find_all("tr"):
            cells = row.find_all(["td", "th"])
            if len(cells) < 2:
                continue
            rn = cells[0].get_text(strip=True).lower()
            val_text = _get_last_col(cells)
            # Revenue: "Sales+" (no space), "Sales +", "Net Sales", "Revenue from …", "Total Income"
            if not revenue and any(k in rn for k in ["sales+", "sales +", "net sales", "total revenue", "revenue from", "total income"]):
                revenue = clean_number(val_text)
            elif "operating profit" in rn and "%" not in rn:
                ebitda = clean_number(val_text)
            elif "opm %" in rn or "opm%" in rn or "opm" == rn.strip():
                opm = clean_number(val_text)
            elif ("net profit" in rn or "profit after tax" in rn or "profit before tax" in rn) and "%" not in rn:
                if not net_income:
                    net_income = clean_number(val_text)

    # --- Balance Sheet ---
    total_debt = de_ratio = None
    bs_section = soup.find("section", id="balance-sheet")
    if bs_section:
        for row in (bs_section.find("table") or BeautifulSoup("", "lxml")).find_all("tr"):
            cells = row.find_all(["td", "th"])
            if len(cells) < 2:
                continue
            rn = cells[0].get_text(strip=True).lower()
            val_text = _get_last_col(cells)
            if "borrowings" in rn:
                total_debt = clean_number(val_text)

    for k in ["debt to equity", "debt / equity", "d/e"]:
        if k in ratios:
            de_ratio = clean_number(ratios[k])
            break

    # --- Cash Flow ---
    fcf = cash_ops = cash_inv = None
    cf_section = soup.find("section", id="cash-flow")
    if cf_section:
        for row in (cf_section.find("table") or BeautifulSoup("", "lxml")).find_all("tr"):
            cells = row.find_all(["td", "th"])
            if len(cells) < 2:
                continue
            rn = cells[0].get_text(strip=True).lower()
            val_text = _get_last_col(cells)
            if "operating" in rn:
                cash_ops = clean_number(val_text)
            elif "investing" in rn:
                cash_inv = clean_number(val_text)
        if cash_ops is not None:
            fcf = cash_ops + (cash_inv or 0)

    # --- Shares outstanding (estimated from market cap & price) ---
    shares_outstanding = None
    if market_cap and current_price and current_price > 0:
        shares_outstanding = (market_cap * 1e7) / current_price

    # --- Industry ---
    industry = "Indian Equity"
    sub = soup.find("a", class_="sub")
    if sub:
        industry = sub.get_text(strip=True)
    else:
        bc = soup.find("div", class_="breadcrumb")
        if bc:
            links = bc.find_all("a")
            if len(links) > 1:
                industry = links[-1].get_text(strip=True)

    # --- Peers ---
    competitors: List[str] = []
    peers_section = soup.find("section", id="peers")
    if peers_section:
        for row in (peers_section.find("table") or BeautifulSoup("", "lxml")).find_all("tr")[1:5]:
            cells = row.find_all("td")
            if cells:
                link = cells[0].find("a")
                if link:
                    name = link.get_text(strip=True)
                    if name and name != ticker:
                        competitors.append(name)

    return {
        "ticker": ticker,
        "company_name": company_name,
        "current_price": current_price,
        "revenue": revenue,
        "ebitda": ebitda,
        "net_income": net_income,
        "fcf": fcf,
        "de_ratio": de_ratio,
        "shares_outstanding": shares_outstanding,
        "market_cap": market_cap,
        "pe_ratio": pe_ratio,
        "book_value": book_value,
        "roe": roe,
        "opm": opm,
        "industry": industry,
        "competitors": competitors[:3],
        "top_ratios": ratios,
        "source": "screener.in",
    }


def _try_trendlyne(ticker: str) -> Dict[str, Any]:
    """Fallback scraper for trendlyne.com."""
    url = f"https://trendlyne.com/equity/detail/{ticker}/"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.content, "lxml")
            # Basic price extraction
            price_tag = soup.find("span", class_=re.compile(r"price|current", re.I))
            price = clean_number(price_tag.get_text()) if price_tag else None
            company = soup.find("h1")
            cname = company.get_text(strip=True) if company else ticker
            return _empty_data(ticker, company_name=cname, current_price=price, source="trendlyne.com")
    except Exception as exc:
        logger.warning(f"Trendlyne fallback failed for {ticker}: {exc}")
    return _empty_data(ticker)


def _empty_data(
    ticker: str,
    company_name: str = "",
    current_price: Optional[float] = None,
    source: str = "fallback",
) -> Dict[str, Any]:
    return {
        "ticker": ticker,
        "company_name": company_name or ticker,
        "current_price": current_price,
        "revenue": None,
        "ebitda": None,
        "net_income": None,
        "fcf": None,
        "de_ratio": None,
        "shares_outstanding": None,
        "market_cap": None,
        "pe_ratio": None,
        "book_value": None,
        "roe": None,
        "opm": None,
        "industry": "Indian Equity",
        "competitors": [],
        "top_ratios": {},
        "source": source,
    }


def get_nifty_trend() -> str:
    """Detect current Nifty 50 market trend from screener or default to Neutral."""
    try:
        resp = requests.get(
            "https://www.screener.in/company/NIFTY50/",
            headers=HEADERS,
            timeout=10,
        )
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.content, "lxml")
            # Try to find 52-week position
            ratios: Dict[str, str] = {}
            rs = soup.find("section", id="top-ratios")
            if rs:
                for li in rs.find_all("li"):
                    ns = li.find("span", class_="name")
                    vs = li.find_all("span", class_="number")
                    if ns and vs:
                        ratios[ns.get_text(strip=True).lower()] = vs[-1].get_text(strip=True)
            high_52 = clean_number(ratios.get("52 week high", ""))
            low_52 = clean_number(ratios.get("52 week low", ""))
            current = clean_number(ratios.get("current price", ""))
            if high_52 and low_52 and current:
                position = (current - low_52) / (high_52 - low_52)
                if position > 0.75:
                    return "Bullish"
                elif position < 0.35:
                    return "Bearish"
    except Exception:
        pass
    return "Neutral"


def get_risk_free_rate() -> float:
    """Return Indian 10-year government bond yield as risk-free rate."""
    # Current approximate Indian 10Y G-Sec yield
    return 7.2
