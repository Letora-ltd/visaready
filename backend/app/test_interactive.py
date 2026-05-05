import asyncio
import sys
import os
from unittest.mock import MagicMock, AsyncMock

# Add the current directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Mock the database and session generator before importing the scraper
import app.services.belgium_browser_scraper
app.services.belgium_browser_scraper.AsyncSessionLocal = MagicMock()
app.services.belgium_browser_scraper.session_generator = AsyncMock()
app.services.belgium_browser_scraper.session_generator.get_valid_session = AsyncMock(return_value=None)

from app.services.belgium_browser_scraper import belgium_browser_scraper

async def test_interactive_scraper():
    print("=== TESTING INTERACTIVE SCRAPER (SPRINT 1.3) ===")
    
    # Disable actual DB commits for this test
    belgium_browser_scraper._save_snapshot = AsyncMock()
    belgium_browser_scraper._save_slots = AsyncMock()
    
    center = "London"
    print(f"\n1. Executing interaction flow for {center}...")
    
    try:
        slots = await belgium_browser_scraper.fetch_slots(center=center)
        
        print(f"\nResults:")
        print(f"Slots Found: {len(slots)}")
        
        if slots:
            print("Successfully triggered API and captured slots!")
            for s in slots[:5]:
                print(f" - {s}")
        else:
            print("No slots captured. API might be gated by login/captcha.")
            
    except Exception as e:
        print(f"\n[ERROR] during interactive test: {e}")

    print("\n=== TEST COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(test_interactive_scraper())
