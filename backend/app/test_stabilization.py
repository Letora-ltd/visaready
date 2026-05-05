import asyncio
import sys
import os
from datetime import datetime

# Add the current directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.queue import slot_queue, push_to_queue
from app.workers.db_worker import db_writer_worker
from unittest.mock import MagicMock, AsyncMock

async def test_stabilization():
    print("=== TESTING STABILIZATION LAYER (SPRINT 2.5) ===")
    
    # 1. Simulate Scraper pushing data to queue
    print("\n1. Simulating Scraper results...")
    mock_slots = [{"date": "2026-10-10", "time": "10:00"}]
    await push_to_queue({
        "country": "Belgium",
        "center": "London",
        "slots": mock_slots,
        "timestamp": datetime.now()
    })
    
    print(f"Queue Size after push: {slot_queue.qsize()}")
    
    # 2. Start Worker with MOCKED DB failure
    print("\n2. Starting DB Writer Worker (Simulating DB Failure)...")
    
    # Mock process_slots_lifecycle to fail twice then succeed
    mock_lifecycle = AsyncMock(side_effect=[Exception("DB Connection Timeout"), Exception("Semaphore Timeout"), 1])
    
    # We need to monkeypatch the lifecycle service inside the worker
    import app.workers.db_worker
    app.workers.db_worker.process_slots_lifecycle = mock_lifecycle
    
    # Run the worker for a short period
    worker_task = asyncio.create_task(db_writer_worker())
    
    print("Waiting for retries...")
    await asyncio.sleep(15) # Wait enough for exponential backoff (2s, 4s...)
    
    print(f"\nFinal Queue Size: {slot_queue.qsize()}")
    print(f"Lifecycle calls: {mock_lifecycle.call_count}")
    
    if mock_lifecycle.call_count >= 3:
        print("[SUCCESS] DB Worker retried after failures and eventually succeeded.")
    else:
        print("[FAILED] Worker did not retry as expected.")

    worker_task.cancel()
    print("\n=== TEST COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(test_stabilization())
