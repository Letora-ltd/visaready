import asyncio
import logging
import time
from typing import Dict, Optional
from playwright.async_api import async_playwright
from ..models.entities import SessionRecord as SessionModel
from ..database.session import AsyncSessionLocal
from sqlalchemy import select, delete

logger = logging.getLogger(__name__)

class SessionGenerator:
    """
    Bypasses Cloudflare using Playwright to extract valid session cookies and User-Agent.
    """
    def __init__(self):
        self.country = "belgium"
        self.target_url = "https://visas-be.tlscontact.com/gb/LON/login"
        self.session_ttl = 1200 # 20 minutes

    async def generate_session(self) -> Dict:
        """
        Launches a real browser, solves the challenge, and stores cookies in the DB.
        """
        logger.info(f"Initiating Playwright session generation for {self.country}...")
        
        async with async_playwright() as p:
            # Launch Chromium (headless=False allows us to see the challenge solving if needed)
            browser = await p.chromium.launch(headless=True) # Changed to True for server environments, but can be False for local debugging
            
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                logger.info(f"Navigating to {self.target_url}")
                await page.goto(self.target_url, wait_until="domcontentloaded", timeout=60000)
                
                # Wait for Cloudflare "Just a moment" to disappear
                # We wait for the presence of a common element like the login button or a specific title
                logger.info("Waiting for Cloudflare challenge to resolve (15s sleep)...")
                await asyncio.sleep(15) 
                
                # Capture cookies
                cookies = await context.cookies()
                cookie_dict = {c['name']: c['value'] for c in cookies}
                
                # Capture User-Agent
                ua = await page.evaluate("navigator.userAgent")
                
                session_data = {
                    "cookies": cookie_dict,
                    "user_agent": ua,
                    "created_at": time.time()
                }
                
                # Save to Database
                await self._save_session_to_db(session_data)
                
                logger.info(f"Successfully obtained session. Cookies: {list(cookie_dict.keys())}")
                return session_data
                
            except Exception as e:
                logger.error(f"Playwright session generation failed: {e}")
                raise
            finally:
                await browser.close()

    async def _save_session_to_db(self, session_data: Dict):
        """
        Persists the session in the database for the scraper to use.
        """
        async with AsyncSessionLocal() as db:
            try:
                # Delete old sessions for this country
                await db.execute(delete(SessionModel).where(SessionModel.country == self.country))
                
                # Create new session record
                new_session = SessionModel(
                    country=self.country,
                    session_data={
                        "cookies": session_data["cookies"],
                        "user_agent": session_data["user_agent"]
                    },
                    status="active"
                )
                db.add(new_session)
                await db.commit()
                logger.info("Session persisted to database.")
            except Exception as e:
                logger.error(f"Failed to save session to DB: {e}")
                await db.rollback()

    async def get_valid_session(self) -> Optional[Dict]:
        """
        Retrieves the latest active session from the DB if it hasn't expired.
        """
        async with AsyncSessionLocal() as db:
            stmt = select(SessionModel).where(
                SessionModel.country == self.country,
                SessionModel.status == "active"
            ).order_by(SessionModel.created_at.desc())
            
            result = await db.execute(stmt)
            session_record = result.scalar_one_or_none()
            
            if session_record:
                # Check expiry (TTL)
                # created_at is a DateTime, last_used is DateTime
                # For simplicity, we use created_at
                from datetime import datetime, timezone
                age = (datetime.now(timezone.utc) - session_record.created_at).total_seconds()
                
                if age < self.session_ttl:
                    return session_record.session_data
                else:
                    logger.info("Database session expired. Marking as expired.")
                    session_record.status = "expired"
                    await db.commit()
                    
            return None

session_generator = SessionGenerator()
