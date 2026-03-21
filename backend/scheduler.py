"""
APScheduler — background cron jobs for the learning loop.

Schedule (all times IST = UTC+5:30):
  Daily   18:00 IST (12:30 UTC) → MarketTrackingAgent  — fetch latest prices
  Daily   19:00 IST (13:30 UTC) → EvaluationAgent      — score predictions
  Weekly  Sun 20:00 IST (14:30 UTC) → LearningAgent    — update model params

The scheduler is started in main.py's lifespan context manager.
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_scheduler = None


def get_scheduler():
    return _scheduler


async def start_scheduler() -> None:
    global _scheduler
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        logger.warning("APScheduler not installed — cron jobs disabled")
        return

    _scheduler = AsyncIOScheduler(timezone="UTC")

    # ── Daily: Market Tracking — 12:30 UTC (18:00 IST) ──
    _scheduler.add_job(
        _run_market_tracking,
        CronTrigger(hour=12, minute=30),
        id="market_tracking_daily",
        name="Daily Price Tracking",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # ── Daily: Evaluation — 13:30 UTC (19:00 IST) ──
    _scheduler.add_job(
        _run_evaluation,
        CronTrigger(hour=13, minute=30),
        id="evaluation_daily",
        name="Daily Prediction Evaluation",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # ── Weekly: Learning — Sunday 14:30 UTC (20:00 IST) ──
    _scheduler.add_job(
        _run_learning,
        CronTrigger(day_of_week="sun", hour=14, minute=30),
        id="learning_weekly",
        name="Weekly Model Learning",
        replace_existing=True,
        misfire_grace_time=7200,
    )

    _scheduler.start()
    logger.info(
        "Scheduler started: market_tracking@12:30UTC · evaluation@13:30UTC · learning@Sun14:30UTC"
    )


async def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")


# ── Job functions ─────────────────────────────────────────────────────────────

async def _run_market_tracking() -> None:
    logger.info("[Scheduler] Running MarketTrackingAgent…")
    try:
        from agents.market_tracking_agent import MarketTrackingAgent
        agent = MarketTrackingAgent()
        result = await agent.run({})
        logger.info(
            "[Scheduler] MarketTracking done: %d snapshots written, %d errors",
            result.data.get("snapshots_written", 0),
            len(result.data.get("errors", [])),
        )
    except Exception as exc:
        logger.error("[Scheduler] MarketTrackingAgent failed: %s", exc, exc_info=True)


async def _run_evaluation() -> None:
    logger.info("[Scheduler] Running EvaluationAgent…")
    try:
        from agents.evaluation_agent import EvaluationAgent
        agent = EvaluationAgent()
        result = await agent.run({"min_days_old": 30})
        if result.success:
            logger.info(
                "[Scheduler] Evaluation done: %d evaluated, avg_abs_err=%.1f%%",
                result.data.get("evaluated", 0),
                result.data.get("avg_abs_error_pct", 0),
            )
        else:
            logger.warning("[Scheduler] EvaluationAgent failed: %s", result.error)
    except Exception as exc:
        logger.error("[Scheduler] EvaluationAgent failed: %s", exc, exc_info=True)


async def _run_learning() -> None:
    logger.info("[Scheduler] Running LearningAgent…")
    try:
        from agents.learning_agent import LearningAgent
        agent = LearningAgent()
        result = await agent.run({"min_samples": 5, "alpha": 0.3})
        if result.success:
            logger.info(
                "[Scheduler] Learning done: %d groups updated",
                result.data.get("groups_updated", 0),
            )
            for adj in result.data.get("adjustments", []):
                logger.info(
                    "  ↳ [%s | %s] bias=%.2f%% growth_adj=%.2f%% conf×%.3f (n=%d)",
                    adj["sector"], adj["market_condition"],
                    adj["bias_correction"], adj["base_growth_adj"],
                    adj["confidence_scaling"], adj["sample_size"],
                )
        else:
            logger.warning("[Scheduler] LearningAgent failed: %s", result.error)
    except Exception as exc:
        logger.error("[Scheduler] LearningAgent failed: %s", exc, exc_info=True)


# ── Manual trigger helpers (used by API endpoints) ───────────────────────────

async def trigger_market_tracking() -> dict:
    await _run_market_tracking()
    return {"triggered": "market_tracking"}


async def trigger_evaluation() -> dict:
    await _run_evaluation()
    return {"triggered": "evaluation"}


async def trigger_learning() -> dict:
    await _run_learning()
    return {"triggered": "learning"}
