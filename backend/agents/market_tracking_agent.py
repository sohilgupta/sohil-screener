"""
Market Tracking Agent — runs nightly to fetch current prices for all
tickers with un-evaluated predictions in the last 90 days.

Inputs:
    tickers     list[str]   (optional, overrides DB-derived list)
    dry_run     bool        (default False — if True, fetches but doesn't store)

Outputs:
    snapshots_written   int
    tickers_tracked     list[str]
    errors              list[dict]
    skipped             int     (already have today's price)
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

import db
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class MarketTrackingAgent(BaseAgent):
    AGENT_ID = "market_tracking_agent"

    async def _execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        dry_run: bool = inputs.get("dry_run", False)

        # 1. Determine which tickers to track
        tickers: List[str] = inputs.get("tickers") or await self._active_tickers()
        if not tickers:
            return {"snapshots_written": 0, "tickers_tracked": [], "errors": [], "skipped": 0}

        today = date.today()
        already_fetched = await self._already_fetched_today(tickers, today)
        to_fetch = [t for t in tickers if t not in already_fetched]
        skipped = len(tickers) - len(to_fetch)

        self.logger.info(
            "Tracking %d tickers (%d already done today, %d to fetch)",
            len(tickers), skipped, len(to_fetch),
        )

        # 2. Fetch prices concurrently in batches of 5 (respect rate limits)
        errors: List[Dict] = []
        snapshots: List[Dict] = []

        for i in range(0, len(to_fetch), 5):
            batch = to_fetch[i:i + 5]
            results = await asyncio.gather(
                *[self._fetch_price(ticker) for ticker in batch],
                return_exceptions=True,
            )
            for ticker, result in zip(batch, results):
                if isinstance(result, Exception):
                    errors.append({"ticker": ticker, "error": str(result)})
                    self.logger.warning("Price fetch failed for %s: %s", ticker, result)
                elif result is not None:
                    snapshots.append({"ticker": ticker, "price": result, "date": today})

            # Brief pause between batches to avoid hammering screener.in
            if i + 5 < len(to_fetch):
                await asyncio.sleep(2)

        # 3. Store snapshots
        written = 0
        if not dry_run and snapshots and db.is_available():
            written = await self._store_snapshots(snapshots, today)

        return {
            "snapshots_written": written,
            "tickers_tracked": [s["ticker"] for s in snapshots],
            "prices_fetched": {s["ticker"]: s["price"] for s in snapshots},
            "errors": errors,
            "skipped": skipped,
            "dry_run": dry_run,
        }

    # ──────────────────────────────────────────────────────────

    async def _active_tickers(self) -> List[str]:
        """
        Return distinct tickers that have predictions in the last 90 days
        and have not been fully evaluated yet.
        """
        if not db.is_available():
            return []
        pool = db.get_pool()
        cutoff = datetime.now(timezone.utc) - timedelta(days=90)
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT DISTINCT ticker FROM predictions
                WHERE predicted_at > $1 AND evaluated = FALSE
                ORDER BY ticker
                """,
                cutoff,
            )
        return [r["ticker"] for r in rows]

    async def _already_fetched_today(self, tickers: List[str], today: date) -> set:
        """Return set of tickers already having a price_snapshot for today."""
        if not tickers or not db.is_available():
            return set()
        pool = db.get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT ticker FROM price_snapshots WHERE price_date = $1 AND ticker = ANY($2)",
                today, tickers,
            )
        return {r["ticker"] for r in rows}

    async def _fetch_price(self, ticker: str) -> Optional[float]:
        """Fetch current price via screener_scraper (runs in executor)."""
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from screener_scraper import fetch_screener_data

        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, fetch_screener_data, ticker)
        price = data.get("current_price")
        if price:
            self.logger.info("Fetched %s = ₹%.2f", ticker, price)
        return price

    async def _store_snapshots(self, snapshots: List[Dict], today: date) -> int:
        """Upsert price snapshots. Returns number of rows written."""
        pool = db.get_pool()
        written = 0
        async with pool.acquire() as conn:
            for snap in snapshots:
                if snap["price"] is None:
                    continue
                await conn.execute(
                    """
                    INSERT INTO price_snapshots (ticker, price_date, price)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (ticker, price_date) DO UPDATE SET price = EXCLUDED.price
                    """,
                    snap["ticker"], today, snap["price"],
                )
                written += 1
        self.logger.info("Stored %d price snapshots", written)
        return written
