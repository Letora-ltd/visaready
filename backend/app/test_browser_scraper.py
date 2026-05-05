import asyncio
import sys
import os

# Add the current directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.belgium_browser_scraper import belgium_browser_scraper

async def test_browser_scraper():
    print("=== TESTING BROWSER-NATIVE SCRAPER (SPRINT 1.2) ===")
    
    center = "London"
    print(f"\n1. Navigating and intercepting for {center}...")
    
    try:
        slots = await belgium_browser_scraper.fetch_slots(center=center)
        
        print(f"\nResults:")
        print(f"Slots Found: {len(slots)}")
        
        if slots:
            print("Successfully captured slots!")
            for s in slots[:5]: # Show first 5
                print(f" - {s}")
        else:
            print("No slots captured. This could mean:")
            print(" - No slots are currently available on the portal.")
            print(" - The API endpoint URL has changed.")
            print(" - The challenge (Cloudflare) is still active.")
            
    except Exception as e:
        print(f"\n[ERROR] during browser test: {e}")

    print("\n=== TEST COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(test_browser_scraper())
