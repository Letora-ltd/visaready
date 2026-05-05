import asyncio
import sys
import os

# Add the current directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Mock DB
from unittest.mock import MagicMock, AsyncMock
import app.services.belgium_browser_scraper
import app.services.vow_scraper
app.services.belgium_browser_scraper.AsyncSessionLocal = MagicMock()
app.services.vow_scraper.AsyncSessionLocal = MagicMock()

from app.services.belgium_browser_scraper import belgium_browser_scraper

async def test_vow_bridge():
    print("=== TESTING VOW TOKEN BRIDGE (ULTIMATE BYPASS) ===")
    
    # Disable actual DB commits
    belgium_browser_scraper._save_snapshot = AsyncMock()
    belgium_browser_scraper._save_slots = AsyncMock()
    
    app_ref = "VOWINT5997104" # From subagent discovery
    print(f"\n1. Attempting to extract onboarding token for {app_ref}...")
    
    try:
        # We test the integrated flow
        slots = await belgium_browser_scraper.fetch_slots_with_vow(app_reference=app_ref, center="London")
        
        print(f"\nFinal Results:")
        print(f"Slots Found via VOW Bridge: {len(slots)}")
        
        if slots:
            print("🎉 SUCCESS! The VOW Bridge successfully bypassed TLS protection.")
            for s in slots[:5]:
                print(f" - {s}")
        else:
            print("No slots captured. The VOW session might have expired or no slots are available.")
            
    except Exception as e:
        print(f"\n[ERROR] during VOW bridge test: {e}")

    print("\n=== TEST COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(test_vow_bridge())
