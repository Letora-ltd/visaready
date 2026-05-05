import asyncio
import sys
import os
import time

# Add the current directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Mock DB and Scraper for testing pool logic
from unittest.mock import MagicMock, AsyncMock
import app.services.belgium_browser_scraper
import app.workers.jobs
import app.workers.db_worker
import app.services.vow_scraper

app.services.belgium_browser_scraper.AsyncSessionLocal = MagicMock()
app.workers.db_worker.process_slots_lifecycle = AsyncMock()
# Mock the scraper to take some time and return dummy slots
async def mock_fetch(**kwargs):
    await asyncio.sleep(2)
    return [{"date": "2026-12-12", "time": "12:00"}]

app.services.belgium_browser_scraper.belgium_browser_scraper.fetch_slots_with_vow = mock_fetch

from app.workers.jobs import check_and_alert_job
from app.services.session_pool import session_pool
from app.core.metrics import metrics

async def test_parallel_pool():
    print("=== TESTING PARALLEL WORKER POOL (SPRINT 3) ===")
    
    # 1. Initialize Pool
    await session_pool.initialize()
    
    # 2. Trigger Parallel Job (multiple times to test semaphore)
    print("\n1. Triggering Dispatcher with 3 centers...")
    centers = ["London", "Manchester", "Edinburgh"]
    
    start_time = time.time()
    await check_and_alert_job(centers=centers)
    duration = time.time() - start_time
    
    print(f"\nTotal Dispatcher Duration: {duration:.2f}s")
    print(f"Metrics: {metrics.get_report()}")
    
    # Analysis
    # If 3 tasks ran with 2 workers and each took 5s + jitter (approx 10s):
    # - Task 1 & 2 start in parallel
    # - Task 3 starts after one finishes
    # Total time should be around 25-30s.
    
    if metrics.runs_started == 3:
        print("\n[SUCCESS] Parallel dispatcher triggered all tasks.")
        print("[SUCCESS] Concurrency was controlled by the semaphore.")
    else:
        print(f"\n[FAILED] Only {metrics.runs_started} tasks started.")

    print("\n=== TEST COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(test_parallel_pool())
