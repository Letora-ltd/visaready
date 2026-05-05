import asyncio
import sys
import os

# Add the current directory to sys.path to allow imports from app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.belgium_scraper import belgium_scraper

async def test_scraper():
    print("=== STARTING SCRAPER TEST ===")
    center = "London"
    
    # 1. Test Fetching Raw Data
    print(f"\n1. Fetching raw data for {center}...")
    result = await belgium_scraper.fetch_raw_slots(center=center)
    
    print(f"Status Code: {result['status_code']}")
    print(f"Success: {result['success']}")
    print(f"Raw Snippet (first 200 chars): {result['text'][:200]}")
    
    # 2. Test Parsing
    print(f"\n2. Parsing raw data...")
    slots = belgium_scraper.parse_slots(result['text'], center)
    
    print(f"Parsed Slots Count: {len(slots)}")
    if slots:
        print(f"First Slot: {slots[0]}")
    else:
        print("No slots parsed (This is expected if the raw response is HTML or an error page)")

    print("\n=== TEST COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(test_scraper())
