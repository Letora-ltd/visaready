import asyncio
import logging
import os
from typing import Optional
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

class VOWScraper:
    """
    Visa On Web (VOW) Scraper with automated login (Sprint 2).
    """
    def __init__(self):
        self.login_url = "https://visaonweb.diplomatie.be/en/Account/Login"
        self.index_url = "https://visaonweb.diplomatie.be/en/VisaApplication/IndexByUserId"
        self.email = os.getenv("VOW_EMAIL")
        self.password = os.getenv("VOW_PASSWORD")
        self.default_data_dir = os.path.join(os.getcwd(), ".playwright_vow_session")

    async def get_onboarding_token(self, app_reference: Optional[str] = None, session_path: Optional[str] = None) -> Optional[str]:
        """
        Navigates to the VOW index, finds the application, and triggers the token redirect.
        """
        target_session_dir = session_path or self.default_data_dir
        logger.info(f"Starting VOW extraction using session: {target_session_dir}")
        
        async with async_playwright() as p:
            # Use provided session path or default
            context = await p.chromium.launch_persistent_context(
                target_session_dir, 
                headless=True,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            try:
                # 1. Navigate to Index
                logger.info(f"Navigating to VOW Application Index: {self.index_url}")
                await page.goto(self.index_url, wait_until="domcontentloaded", timeout=60000)
                
                # 2. Automated Login if needed
                if "/Account/Login" in page.url:
                    logger.info("VOW Session expired or missing. Attempting automated login...")
                    if not self.email or not self.password:
                        logger.error("VOW credentials missing in .env. Cannot automate login.")
                        return None
                    
                    await page.get_by_label("Email").fill(self.email)
                    await page.get_by_label("Password").fill(self.password)
                    await page.get_by_role("button", name="Log in").click()
                    
                    # Wait for redirect back to index
                    await page.wait_for_url("**/VisaApplication/**", timeout=30000)
                    logger.info("VOW login successful.")
                
                # 3. Locate the application row
                logger.info("Locating application row...")
                if app_reference:
                    row = page.locator('tr').filter(has_text=app_reference)
                else:
                    # Default to the first row with a calendar icon
                    row = page.locator('tr').filter(has=page.locator('i.fa-calendar')).first
                
                if await row.count() == 0:
                    logger.error("Could not find a valid application with a calendar icon.")
                    return None
                
                # 4. Trigger Token Request (Click Calendar Icon)
                logger.info("Clicking Calendar icon (Token Request)...")
                calendar_btn = row.locator('button:has(i.fa-calendar)')
                await calendar_btn.wait_for(state="visible")
                
                # Click and wait for the redirect to TLS
                await calendar_btn.click()
                
                # Wait for the redirect to land on the TLS consent page
                logger.info("Waiting for redirect to TLS portal...")
                await page.wait_for_url("**/consent**", timeout=30000)
                
                # 5. Extract Token from URL
                # URL structure: .../consent?onboarding_token=XYZ
                final_url = page.url
                logger.info(f"Land URL: {final_url}")
                
                if "onboarding_token=" in final_url:
                    token = final_url.split("onboarding_token=")[1].split("&")[0]
                    logger.info(f"Successfully extracted Token: {token[:8]}...")
                    return token
                else:
                    logger.error("No onboarding_token found in final URL.")
                    return None
                    
            except Exception as e:
                logger.error(f"VOW Token Extraction failed: {e}")
                return None
            finally:
                await context.close()

# Singleton
vow_scraper = VOWScraper()
