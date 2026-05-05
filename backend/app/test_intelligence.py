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
import app.services.vow_scraper

app.services.belgium_browser_scraper.AsyncSessionLocal = MagicMock()
app.workers.db_worker.process_slots_lifecycle = AsyncMock()

# Global to track re-check
recheck_called = False

async def mock_fetch(**kwargs):
    print("[MOCK] Scraper found SLOTS!")
    return [{"date": "2026-12-12", "time": "12:00"}]

app.services.belgium_browser_scraper.belgium_browser_scraper.fetch_slots_with_vow = mock_fetch

from app.workers.jobs import run_scrape_task, delayed_recheck
from app.services.session_pool import session_pool
from app.core.intelligence import intelligence_engine, MonitoringMode

async def test_intelligence():
    print("=== TESTING INTELLIGENCE ENGINE (SPRINT 4) ===")
    
    # 1. Initialize
    await session_pool.initialize()
    print(f"Initial Mode: {intelligence_engine.mode.value}")
    
    # 2. Trigger Task that finds slots
    print("\n1. Running task with SLOTS...")
    await run_scrape_task("London")
    
    # 3. Check Mode
    mode = await intelligence_engine.get_current_mode()
    print(f"Mode after slot: {mode.value}")
    
    # 4. Check Health
    session = session_pool.sessions[0]
    print(f"Session 0 Health: Success={session['success_count']}, Fail={session['fail_count']}")
    
    # 5. Verify Fast Re-check logic
    # Since we can't easily wait for the background task in a script, we'll check if the signal was sent
    if mode == MonitoringMode.BOOST:
        print("[SUCCESS] Intelligence Engine entered BOOST mode.")
    else:
        print("[FAILED] Intelligence Engine stayed in NORMAL mode.")

    # 6. Test Safe Mode (Simulate failures)
    print("\n2. Simulating 6 failures...")
    for _ in range(6):
        await intelligence_engine.report_signal("failure")
    
    mode = await intelligence_engine.get_current_mode()
    print(f"Mode after failures: {mode.value}")
    
    if mode == MonitoringMode.SAFE:
        print("[SUCCESS] Intelligence Engine entered SAFE mode.")
    else:
        print("[FAILED] Intelligence Engine did not enter SAFE mode.")

    print("\n=== TEST COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(test_intelligence())
