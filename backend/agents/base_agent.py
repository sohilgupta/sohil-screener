"""Base agent contract shared by all agents in the valuation system."""
from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    """Standardised output envelope returned by every agent."""

    agent_id: str
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    duration_ms: float = 0.0
    cached: bool = False

    def raise_if_failed(self) -> "AgentResult":
        """Propagate agent failure as a RuntimeError."""
        if not self.success:
            raise RuntimeError(f"[{self.agent_id}] {self.error}")
        return self


class BaseAgent(ABC):
    """Abstract base class — all agents implement `_execute`."""

    #: Override in subclasses with a unique snake_case name.
    AGENT_ID: str = "base_agent"

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)

    async def run(self, inputs: Dict[str, Any]) -> AgentResult:
        """Entry point: calls `_execute` and wraps exceptions into AgentResult."""
        start = time.perf_counter()
        try:
            data = await self._execute(inputs)
            duration = (time.perf_counter() - start) * 1000
            self.logger.info(f"{self.AGENT_ID} completed in {duration:.0f}ms")
            return AgentResult(
                agent_id=self.AGENT_ID,
                success=True,
                data=data,
                duration_ms=round(duration, 2),
            )
        except Exception as exc:
            duration = (time.perf_counter() - start) * 1000
            self.logger.error(f"{self.AGENT_ID} failed: {exc}", exc_info=True)
            return AgentResult(
                agent_id=self.AGENT_ID,
                success=False,
                error=str(exc),
                duration_ms=round(duration, 2),
            )

    @abstractmethod
    async def _execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Implement the agent's core logic here. Must return a plain dict."""
