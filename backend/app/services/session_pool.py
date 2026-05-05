import asyncio
import random
import os
import logging
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class SessionPool:
    """
    Manages a pool of persistent browser contexts for session reuse (Sprint 3).
    Each session points to a unique user-data-dir.
    """
    def __init__(self, size: int = 2):
        self.size = size
        self.sessions: List[Dict] = []
        self.lock = asyncio.Lock()
        self.base_dir = os.path.join(os.getcwd(), ".playwright_sessions")
        
        # Ensure base directory exists
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)

    async def initialize(self):
        """Pre-populates session metadata."""
        async with self.lock:
            if self.sessions:
                return
            for i in range(self.size):
                session_path = os.path.join(self.base_dir, f"session_{i}")
                self.sessions.append({
                    "id": i,
                    "path": session_path,
                    "in_use": False,
                    "is_valid": True,
                    "success_count": 0,
                    "fail_count": 0,
                    "last_success": None
                })
            logger.info(f"🏊 Session Pool initialized with {self.size} persistent slots.")

    async def acquire(self) -> Optional[Dict]:
        """Rotates among the healthiest available sessions (Sprint 5)."""
        async with self.lock:
            available = [s for s in self.sessions if not s["in_use"] and s["is_valid"]]
            if not available:
                return None
            
            # 1. Sort by health
            available.sort(key=lambda x: (x["fail_count"], -x["success_count"]))
            
            # 2. Pick from top 2 (or 1 if only one available)
            # This avoids overusing the single 'best' session
            top_threshold = min(len(available), 2)
            selected = random.choice(available[:top_threshold])
            
            selected["in_use"] = True
            logger.info(f"🔄 Session Rotation: Selected Session {selected['id']} (Rank 1-{top_threshold})")
            return selected

    async def report_health(self, session_id: int, success: bool):
        """Updates health metrics for a session."""
        async with self.lock:
            for s in self.sessions:
                if s["id"] == session_id:
                    if success:
                        s["success_count"] += 1
                        s["last_success"] = datetime.now()
                    else:
                        s["fail_count"] += 1
                        
                    # Auto-invalidate if too many consecutive failures
                    if s["fail_count"] > 10 and s["success_count"] < 2:
                        s["is_valid"] = False
                    break

    async def release(self, session_id: int):
        """Returns a session to the pool."""
        async with self.lock:
            for s in self.sessions:
                if s["id"] == session_id:
                    s["in_use"] = False
                    break

    async def invalidate(self, session_id: int):
        """Marks a session for re-authentication."""
        async with self.lock:
            for s in self.sessions:
                if s["id"] == session_id:
                    s["is_valid"] = False
                    logger.warning(f"⚠️ Session {session_id} marked as INVALID.")
                    break

    async def refresh(self, session_id: int):
        """Resets the valid flag once re-authentication is done."""
        async with self.lock:
            for s in self.sessions:
                if s["id"] == session_id:
                    s["is_valid"] = True
                    logger.info(f"🔄 Session {session_id} refreshed and valid.")
                    break

# Global singleton
session_pool = SessionPool(size=2)
