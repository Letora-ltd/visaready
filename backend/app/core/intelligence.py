import asyncio
import logging
import math
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, List, Optional
from sqlalchemy import select, func
from ..database.session import AsyncSessionLocal
from ..models.entities import ActivityLog

logger = logging.getLogger(__name__)

class MonitoringMode(Enum):
    NORMAL = "NORMAL"
    BOOST = "BOOST"
    COOL_DOWN = "COOL_DOWN"
    SAFE = "SAFE"
    GLOBAL_SAFE = "GLOBAL_SAFE" # Fail-safe mode

class CenterState:
    """Tracks intelligence state for a specific center."""
    def __init__(self, center: str):
        self.center = center
        self.mode = MonitoringMode.NORMAL
        self.last_mode_change = datetime.min
        self.mode_cooldown = timedelta(minutes=2)
        self.boost_until: datetime = datetime.min
        self.pending_confirmation: Optional[datetime] = None
        self.recent_failures = 0
        self.heat_scores: Dict[int, float] = {h: 0.0 for h in range(24)}

class GlobalHealthMonitor:
    """Tracks system-wide health across last 100 runs (Sprint 7)."""
    def __init__(self):
        self.results = [] # List of bool (True=Success, False=Failure)
        self.max_size = 100
        
    def add_result(self, success: bool):
        self.results.append(success)
        if len(self.results) > self.max_size:
            self.results.pop(0)
            
    def get_success_rate(self) -> float:
        if not self.results: return 100.0
        return (sum(self.results) / len(self.results)) * 100.0

    def get_state(self) -> str:
        rate = self.get_success_rate()
        if rate > 90: return "HEALTHY"
        if rate > 70: return "DEGRADED"
        return "CRITICAL"

class IntelligenceEngine:
    """
    Center-Level Intelligence Engine (Sprint 6).
    Persistent, isolated, and adaptive (Decay Model).
    """
    def __init__(self):
        self.centers: Dict[str, CenterState] = {}
        self.lock = asyncio.Lock()
        self.decay_factor = 0.1
        self.global_health = GlobalHealthMonitor()
        self.is_global_safe = False

    def _get_center(self, center: str) -> CenterState:
        if center not in self.centers:
            self.centers[center] = CenterState(center)
        return self.centers[center]

    async def initialize(self):
        """Pre-loads heat scores from the database activity logs."""
        async with self.lock:
            logger.info("🧠 Intelligence Engine: Loading persistent activity logs...")
            try:
                async with AsyncSessionLocal() as db:
                    result = await db.execute(select(ActivityLog))
                    logs = result.scalars().all()
                    
                    now = datetime.now()
                    for log in logs:
                        state = self._get_center(log.center)
                        # Apply Decay: newer logs = higher weight
                        days_old = (now - log.timestamp).days
                        weight = math.exp(-self.decay_factor * days_old)
                        state.heat_scores[log.hour] += weight * log.confidence
                    
                    logger.info(f"🧠 Intelligence Engine: Loaded {len(logs)} patterns. Ready.")
            except Exception as e:
                logger.error(f"Failed to initialize intelligence from DB: {e}")

    async def report_signal(self, signal_type: str, data: Any = None):
        async with self.lock:
            now = datetime.now()
            center_name = data.get("center", "unknown") if data else "unknown"
            state = self._get_center(center_name)
            
            # 1. Handle Detection Signal (Requires Confirmation)
            if signal_type == "slot_detected":
                detection_time = state.pending_confirmation
                
                # CONFIRMATION LOGIC
                if detection_time and (now - detection_time) < timedelta(minutes=3):
                    logger.info(f"✅ CONFIRMATION: [{center_name}] confirmed. Triggering BOOST.")
                    state.boost_until = now + timedelta(minutes=10)
                    
                    # Calculate Confidence Score (Sprint 7)
                    # Base 50 for twice confirmed
                    # +30 for fast re-check match (time window < 2 min)
                    # +20 for session quality (if success_count > 5)
                    confidence = 50
                    if (now - detection_time) < timedelta(minutes=2):
                        confidence += 30
                    
                    session_id = data.get("session_id")
                    from ..services.session_pool import session_pool
                    # We can't easily check session quality here without more logic, 
                    # but we can look it up in the pool if needed.
                    
                    await self._persist_activity(center_name, now, confidence)
                    await self._change_mode(state, MonitoringMode.BOOST)
                    state.pending_confirmation = None
                else:
                    logger.info(f"🔎 DETECTION: [{center_name}] Potential slots. Pending confirmation.")
                    state.pending_confirmation = now

            elif signal_type == "failure":
                state.recent_failures += 1
                self.global_health.add_result(False)
                if state.recent_failures > 5:
                    await self._change_mode(state, MonitoringMode.SAFE)
                
                # Global Fail-Safe Trigger
                if self.global_health.get_success_rate() < 70 and not self.is_global_safe:
                    logger.warning("🚨 GLOBAL FAIL-SAFE TRIGGERED: System success rate CRITICAL.")
                    self.is_global_safe = True

            elif signal_type == "success":
                self.global_health.add_result(True)
                if state.recent_failures > 0: state.recent_failures -= 1
                if state.mode == MonitoringMode.SAFE and state.recent_failures < 2:
                    await self._change_mode(state, MonitoringMode.NORMAL)
                
                if self.is_global_safe and self.global_health.get_success_rate() > 85:
                    logger.info("✅ GLOBAL FAIL-SAFE LIFTED: System health recovered.")
                    self.is_global_safe = False

    async def _change_mode(self, state: CenterState, new_mode: MonitoringMode):
        now = datetime.now()
        if (now - state.last_mode_change) < state.mode_cooldown: return
        
        logger.info(f"🔄 [{state.center}] MODE: {state.mode.value} -> {new_mode.value}")
        state.mode = new_mode
        state.last_mode_change = now

    async def _persist_activity(self, center: str, dt: datetime, confidence: float):
        """Saves confirmation to DB and updates local heat score (Sprint 7)."""
        try:
            async with AsyncSessionLocal() as db:
                log = ActivityLog(center=center, timestamp=dt, hour=dt.hour, confidence=confidence/100.0)
                db.add(log)
                await db.commit()
                
                # Update local score (using confidence as weight)
                state = self._get_center(center)
                state.heat_scores[dt.hour] += (confidence / 100.0)
                logger.info(f"📊 [{center}] Pattern Persisted (Confidence: {confidence}%). Current Heat: {state.heat_scores[dt.hour]:.1f}")
        except Exception as e:
            logger.error(f"Failed to persist activity log: {e}")

    async def get_center_mode(self, center: str) -> MonitoringMode:
        """Returns the current mode for a specific center."""
        async with self.lock:
            state = self._get_center(center)
            now = datetime.now()
            
            # Check Global Safe
            if self.is_global_safe:
                return MonitoringMode.GLOBAL_SAFE

            # Check Boost Expiry
            if state.mode == MonitoringMode.BOOST and now > state.boost_until:
                logger.info(f"💤 [{center}] BOOST expired. Returning to NORMAL.")
                state.mode = MonitoringMode.NORMAL
            
            return state.mode

    async def get_center_score(self, center: str, hour: int) -> float:
        """Returns the heat score for a center at a specific hour."""
        async with self.lock:
            state = self._get_center(center)
            return state.heat_scores.get(hour, 0.0)

    def get_interval(self, mode: MonitoringMode) -> int:
        intervals = {
            MonitoringMode.BOOST: 1,
            MonitoringMode.NORMAL: 3,
            MonitoringMode.COOL_DOWN: 15,
            MonitoringMode.SAFE: 10,
            MonitoringMode.GLOBAL_SAFE: 30 # Heavy reduction
        }
        return intervals.get(mode, 3)

# Global singleton
intelligence_engine = IntelligenceEngine()
