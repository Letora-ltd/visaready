import asyncio
import logging
import json
from typing import List, Dict, Optional
from playwright.async_api import async_playwright, Response
from datetime import datetime
from ..models.entities import SlotSnapshot, Slot
from ..database.session import AsyncSessionLocal
from .session_generator import session_generator
from .vow_scraper import vow_scraper

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BelgiumBrowserScraper:
    """
    Interaction-based Browser Scraper (Sprint 1.3).
    Simulates real user flow on the TLS SPA to trigger slot API calls.
    Uses resilient role-based and text-based selectors.
    """
    def __init__(self):
        self.country = "belgium"
        self.portal_url = "https://visas-be.tlscontact.com/"
        self.target_api_pattern = "/appointments/slots"

    async def fetch_slots(self, center: str = "London") -> List[Dict]:
        """
        Full Interaction Flow: Navigation -> Selection -> API Interception
        """
        logger.info(f"Starting interactive extraction for {self.country}/{center}...")
        
        captured_data = []
        raw_responses = []

        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(headless=True)
            
            # 1. Load Stored Session (Sprint 1.1 integration)
            # If we have valid cookies, we inject them to skip login/captcha
            session_data = await session_generator.get_valid_session()
            
            context_args = {
                "viewport": {"width": 1280, "height": 800},
                "user_agent": session_data.get("user_agent") if session_data else "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            
            context = await browser.new_context(**context_args)
            if session_data and "cookies" in session_data:
                # Convert dict cookies to list format required by playwright
                pw_cookies = [{"name": k, "value": v, "url": self.portal_url} for k, v in session_data["cookies"].items()]
                await context.add_cookies(pw_cookies)
                logger.info("Injected stored session cookies into browser context.")

            page = await context.new_page()

            # Network Interception Handler
            async def handle_response(response: Response):
                if self.target_api_pattern in response.url:
                    logger.info(f"Captured Slot API Response: {response.url}")
                    try:
                        text = await response.text()
                        raw_responses.append(text)
                        data = json.loads(text)
                        
                        # Parsing JSON Structure
                        if isinstance(data, dict) and "slots" in data:
                            for s in data["slots"]:
                                captured_data.append({
                                    "country": self.country,
                                    "center": center,
                                    "slot_date": datetime.strptime(s.get("date"), "%Y-%m-%d") if s.get("date") and isinstance(s, dict) else None,
                                    "slot_time": s.get("time", "09:00") if isinstance(s, dict) else "09:00"
                                })
                        elif isinstance(data, list):
                            for item in data:
                                # If it's a list of strings (dates)
                                if isinstance(item, str):
                                    captured_data.append({
                                        "country": self.country,
                                        "center": center,
                                        "slot_date": datetime.strptime(item, "%Y-%m-%d"),
                                        "slot_time": "09:00"
                                    })
                    except Exception as e:
                        logger.error(f"Failed to parse API response: {e}")

            page.on("response", handle_response)

            try:
                # STEP 1: Portal Entry
                logger.info(f"Navigating to portal: {self.portal_url}")
                await page.goto(self.portal_url, wait_until="domcontentloaded")
                
                # STEP 2: Start Booking Flow
                logger.info("Clicking 'Book an appointment'...")
                apply_btn = page.locator("#btn-apply-for-a-visa")
                await apply_btn.wait_for(state="visible", timeout=15000)
                await apply_btn.click()

                # STEP 3: Select Center (Simulated Interaction)
                # Note: The subagent found a country selection might appear first
                try:
                    logger.info("Selecting country/center...")
                    # The subagent identified id="select-country"
                    await page.select_option("#select-country", label="United Kingdom")
                        
                    # Find 'Continue' for specific center
                    continue_btn = page.get_by_role("button", name="Continue")
                    if await continue_btn.count() > 0:
                        await continue_btn.first.click()
                except Exception as e:
                    logger.info(f"Optional selection step skipped or failed: {e}")

                # STEP 4 & 5: Interaction to Trigger API
                logger.info("Simulating Visa Type selection and waiting for API...")
                
                try:
                    async with page.expect_response(
                        lambda r: self.target_api_pattern in r.url,
                        timeout=25000
                    ) as response_info:
                        
                        # Resilient text-based selector for Short Stay
                        visa_type_btn = page.get_by_text("Short Stay", exact=False)
                        if await visa_type_btn.count() > 0:
                            await visa_type_btn.first.click()
                            logger.info("Clicked 'Short Stay' option.")
                        
                        response = await response_info.value
                        logger.info(f"Captured Slot API response: {response.url}")
                except asyncio.TimeoutError:
                    logger.warning("Timed out waiting for Slot API after interaction.")
                except Exception as e:
                    logger.error(f"Error during interaction/waiting: {e}")

                # 4. Fallback: DOM Extraction
                if not captured_data:
                    logger.info("No API data captured. Attempting DOM fallback...")
                    # logic for parsing rendered slots table could go here
                
                # 5. Persistence
                if raw_responses:
                    await self._save_snapshot(center, "\n---\n".join(raw_responses))
                
                if captured_data:
                    await self._save_slots(captured_data)

                return captured_data

            except Exception as e:
                logger.error(f"Interactive scraper failed: {e}")
                return []
            finally:
                await browser.close()

    async def fetch_slots_with_vow(self, app_reference: Optional[str] = None, center: str = "London", session_info: Optional[Dict] = None) -> List[Dict]:
        """
        Integrated flow: VOW Token -> TLS Interaction -> Slot Capture.
        Uses SessionPool for parallel stability.
        """
        session_path = session_info["path"] if session_info else None
        session_id = session_info["id"] if session_info else "default"

        # 1. Get Token from VOW
        token = await vow_scraper.get_onboarding_token(app_reference=app_reference, session_path=session_path)
        
        if not token:
            logger.error(f"[{session_id}] Could not obtain VOW token. Terminating task.")
            return []

        # 2. Use Token to enter TLS
        token_url = f"https://visas-be.tlscontact.com/visa/gbr/lon-be/en-us/consent?onboarding_token={token}"
        logger.info(f"[{session_id}] Using VOW token to enter TLS booking flow.")
        
        captured_data = []
        async with async_playwright() as p:
            # Re-use the same session path for TLS to maintain 'known device' status
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            # Response handler
            page.on("response", lambda r: captured_data.append(r) if self.target_api_pattern in r.url else None)

            try:
                # 1. Enter via Token
                await page.goto(token_url, wait_until="networkidle", timeout=60000)
                
                # Check for login redirect (Session Invalidation)
                if "/login" in page.url:
                    logger.warning(f"[{session_id}] TLS session invalidated or token rejected.")
                    from .session_pool import session_pool
                    await session_pool.invalidate(session_id)
                    return []

                # 2. Click Consent (Accept all)
                accept_btn = page.get_by_role("button", name="Accept")
                if await accept_btn.count() > 0:
                    await accept_btn.first.click()
                
                # 3. Navigate/Interact to Slots
                logger.info(f"[{session_id}] Inside TLS booking area. Waiting for slots...")
                
                try:
                    async with page.expect_response(lambda r: self.target_api_pattern in r.url, timeout=45000) as response_info:
                        # Interaction to force API call
                        visa_type_btn = page.get_by_text("Short Stay", exact=False)
                        if await visa_type_btn.count() > 0:
                            await visa_type_btn.first.click()
                        
                        resp = await response_info.value
                        data = await resp.json()
                        
                        final_slots = []
                        if isinstance(data, dict) and "slots" in data:
                            for s in data["slots"]:
                                final_slots.append({
                                    "country": self.country,
                                    "center": center,
                                    "slot_date": datetime.strptime(s.get("date"), "%Y-%m-%d") if s.get("date") else None,
                                    "slot_time": s.get("time")
                                })
                            return final_slots
                except Exception as e:
                    logger.warning(f"[{session_id}] No slots captured: {e}")
                
                return []
            finally:
                await browser.close()

    async def _save_snapshot(self, center: str, raw_data: str):
        async with AsyncSessionLocal() as db:
            try:
                snapshot = SlotSnapshot(
                    country=self.country,
                    center=center,
                    raw_response=raw_data,
                    timestamp=datetime.now()
                )
                db.add(snapshot)
                await db.commit()
            except Exception as e:
                logger.error(f"Snapshot DB Error: {e}")

    async def _save_slots(self, slots_data: List[Dict]):
        async with AsyncSessionLocal() as db:
            try:
                for s in slots_data:
                    if not s.get("slot_date"): continue
                    new_slot = Slot(
                        country=s["country"],
                        center=s["center"],
                        visa_type="Schengen",
                        slot_date=datetime.strptime(s["slot_date"], "%Y-%m-%d"),
                        slot_time=s["slot_time"],
                        last_checked=datetime.now()
                    )
                    db.add(new_slot)
                await db.commit()
            except Exception as e:
                logger.error(f"Slot DB Error: {e}")

# Singleton
belgium_browser_scraper = BelgiumBrowserScraper()
