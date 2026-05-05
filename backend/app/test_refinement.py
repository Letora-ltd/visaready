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
    print(f"[MOCK] Scraper found SLOTS for {kwargs.get('center', 'unknown')}!")
    return [{"date": "2026-12-12", "time": "12:00"}]

app.services.belgium_browser_scraper.belgium_browser_scraper.fetch_slots_with_vow = mock_fetch

from app.workers.jobs import run_scrape_task
from app.services.session_pool import session_pool
from app.core.intelligence import intelligence_engine, MonitoringMode

async def test_refinement():
    print("=== TESTING SIGNAL REFINEMENT & LEARNING (SPRINT 5) ===")
    
    # 1. Initialize
    await session_pool.initialize()
    print(f"Initial Mode: {intelligence_engine.mode.value}")
    
    # 2. First Detection (Should stay NORMAL/Pending)
    print("\n1. First Detection Scan...")
    await run_scrape_task("London")
    mode = await intelligence_engine.get_current_mode()
    print(f"Mode after 1st detection: {mode.value} (Should be NORMAL)")
    
    if mode == MonitoringMode.NORMAL:
        print("[SUCCESS] Signal Confidence Filter working (ignored 1st signal).")
    
    # 3. Second Detection (Confirmation)
    print("\n2. Second Detection Scan (Confirmation)...")
    await run_scrape_task("London")
    mode = await intelligence_engine.get_current_mode()
    print(f"Mode after 2nd detection: {mode.value} (Should be BOOST)")
    
    if mode == MonitoringMode.BOOST:
        print("[SUCCESS] Signal Refinement confirmed slot and triggered BOOST.")

    # 4. Activity Memory Check
    print("\n3. Activity Memory Check...")
    print(f"History for London: {intelligence_engine.activity_history.get('London')}")
    if intelligence_engine.activity_history.get('London'):
        print("[SUCCESS] Activity Memory recorded the pattern.")

    # 5. Session Rotation Check
    print("\n4. Session Rotation Check...")
    # Run a few more tasks and see which sessions are used
    # (Logs will show "Session Rotation: Selected Session X")
    for i in range(3):
        await run_scrape_task("Manchester")

    print("\n=== TEST COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(test_refinement())
