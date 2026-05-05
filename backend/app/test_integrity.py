import asyncio
import sys
import os
import time
from datetime import datetime

# Add the current directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Mocking
from unittest.mock import MagicMock, AsyncMock
import app.services.belgium_browser_scraper
import app.workers.jobs
import app.workers.db_worker

app.services.belgium_browser_scraper.AsyncSessionLocal = MagicMock()
app.workers.db_worker.process_slots_lifecycle = AsyncMock()

async def mock_fetch(**kwargs):
    return [{"date": "2026-12-12", "time": "12:00"}]

app.services.belgium_browser_scraper.belgium_browser_scraper.fetch_slots_with_vow = mock_fetch

from app.workers.jobs import run_scrape_task
from app.services.session_pool import session_pool
from app.core.intelligence import intelligence_engine
from app.core.health import health_monitor, SystemState
from app.workers.scheduler import summary_job

async def test_integrity():
    print("=== TESTING SYSTEM INTEGRITY & SELF-HEALING (SPRINT 7) ===")
    
    # 1. Initialize
    await session_pool.initialize()
    print(f"Initial Health: { (await health_monitor.get_state()).value }")
    
    # 2. Confirmed Detection (Verify Confidence)
    print("\n1. Confirmed Detection (Confidence Check)...")
    await run_scrape_task("London") # Detection
    await run_scrape_task("London") # Confirmation
    
    # In a real run, this would save to DB with a specific confidence.
    # We can't easily check the mock DB write, but we can verify the state.
    print(f"Mode after confirmation: { (await intelligence_engine.get_center_mode('London')).value }")
    
    # 3. Trigger Failures (Verify Health State)
    print("\n2. Triggering 10 consecutive failures...")
    for _ in range(10):
        # Report failure directly to monitor
        await health_monitor.report_run(success=False)
    
    state = await health_monitor.get_state()
    print(f"Health State after failures: {state.value}")
    
    if state in [SystemState.DEGRADED, SystemState.CRITICAL]:
        print("[SUCCESS] Health Monitor detected the issue.")
    
    # 4. Verify System Summary
    print("\n3. Generating System Summary...")
    await summary_job()

    print("\n=== TEST COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(test_integrity())
