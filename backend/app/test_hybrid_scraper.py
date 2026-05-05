import asyncio
import sys
import os
from datetime import datetime

# Add the current directory to sys.path to allow imports from app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.belgium_scraper import belgium_scraper
from app.database.init_db import init_db

async def test_hybrid_scraper():
    print("=== STARTING HYBRID SCRAPER TEST (SPRINT 1.1) ===")
    
    # Initialize DB (create tables if needed)
    print("Initializing database...")
    await init_db()
    
    center = "London"
    
    # 1. Trigger Fetch (which will trigger session generation if needed)
    print(f"\n1. Fetching slots for {center} using hybrid approach...")
    result = await belgium_scraper.fetch_raw_slots(center=center)
    
    print(f"Status Code: {result['status_code']}")
    print(f"Success: {result['success']}")
    
    if result['success']:
        print("\n🎉 SUCCESS! Requests-based scraper bypassed Cloudflare using browser session.")
        print(f"Raw Snippet (first 200 chars): {result['text'][:200]}")
        
        # 2. Test Parsing
        print(f"\n2. Parsing real data...")
        slots = belgium_scraper.parse_slots(result['text'], center)
        print(f"Parsed Slots Count: {len(slots)}")
        if slots:
            for s in slots[:3]: # Show first 3
                print(f" - {s}")
    else:
        print(f"\n❌ FAILED. Still getting {result['status_code']}")
        if result['status_code'] == 403:
            print("Cloudflare is still blocking. We might need to adjust the wait time or use stealth mode.")
        print(f"Raw Snippet: {result['text'][:200]}")

    print("\n=== TEST COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(test_hybrid_scraper())
