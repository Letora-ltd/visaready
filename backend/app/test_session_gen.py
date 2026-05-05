import asyncio
import sys
import os
import requests
import time

# Add the current directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.session_generator import session_generator

async def test_session_bypass():
    print("=== TESTING CLOUDFLARE BYPASS (NO DB) ===")
    
    try:
        # 1. Generate Session
        print("\n1. Generating session via Playwright...")
        session_data = await session_generator.generate_session()
        
        cookies = session_data["cookies"]
        ua = session_data["user_agent"]
        
        print(f"Session obtained. UA: {ua[:50]}...")
        print(f"Cookies: {list(cookies.keys())}")
        
        # 2. Test with Requests
        print("\n2. Testing requests with obtained session...")
        api_url = "https://visas-be.tlscontact.com/api/v1/appointments/slots"
        headers = {
            "User-Agent": ua,
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://visas-be.tlscontact.com/gb/LON/book-appointment",
            "X-Requested-With": "XMLHttpRequest"
        }
        
        response = requests.get(api_url, params={"center": "London"}, headers=headers, cookies=cookies, timeout=20)
        
        print(f"Response Status: {response.status_code}")
        print(f"Success: {response.status_code == 200}")
        print(f"Response Snippet: {response.text[:200]}")
        
        if response.status_code == 200:
            print("\n[SUCCESS] Cloudflare bypassed.")
        else:
            print("\n[FAILED] Cloudflare still blocking or URL changed.")

    except Exception as e:
        print(f"\n[ERROR] during test: {e}")

    print("\n=== TEST COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(test_session_bypass())
