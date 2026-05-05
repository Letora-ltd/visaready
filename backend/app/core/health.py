import asyncio
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import List

logger = logging.getLogger(__name__)

class SystemState(Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"

class GlobalHealthMonitor:
    """
    Monitors system-wide health and triggers Fail-Safe modes (Sprint 7).
    """
    def __init__(self):
        self.state = SystemState.HEALTHY
        self.last_runs: List[bool] = [] # List of success/fail (True/False)
        self.max_history = 20
        self.db_failures = 0
        self.lock = asyncio.Lock()
        self.last_summary_at = datetime.now()

    async def report_run(self, success: bool):
        async with self.lock:
            self.last_runs.append(success)
            if len(self.last_runs) > self.max_history:
                self.last_runs.pop(0)
            
            await self._evaluate_state()

    async def report_db_event(self, success: bool):
        async with self.lock:
            if not success:
                self.db_failures += 1
            else:
                if self.db_failures > 0: self.db_failures -= 1
            
            await self._evaluate_state()

    async def _evaluate_state(self):
        """Calculates the system health state based on recent metrics."""
        success_rate = self.get_success_rate()
        
        if self.db_failures > 5 or success_rate < 0.4:
            new_state = SystemState.CRITICAL
        elif self.db_failures > 2 or success_rate < 0.7:
            new_state = SystemState.DEGRADED
        else:
            new_state = SystemState.HEALTHY
            
        if new_state != self.state:
            logger.warning(f"🚨 SYSTEM STATE CHANGE: {self.state.value} -> {new_state.value}")
            self.state = new_state

    def get_success_rate(self) -> float:
        if not self.last_runs: return 1.0
        return sum(1 for r in self.last_runs if r) / len(self.last_runs)

    async def get_state(self) -> SystemState:
        async with self.lock:
            return self.state

# Global singleton
health_monitor = GlobalHealthMonitor()
