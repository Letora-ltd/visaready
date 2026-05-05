import requests
import logging
import json
import asyncio
from datetime import datetime
from typing import List, Dict, Optional
from ..models.entities import SlotSnapshot, Slot, Session as SessionModel
from ..database.session import AsyncSessionLocal
from .session_generator import session_generator
from sqlalchemy import select, update

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BelgiumScraper:
    """
    Enhanced engine with Cloudflare bypass (Sprint 1.1).
    Reuses browser-generated sessions in requests.
    """
    def __init__(self):
        self.country = "belgium"
        self.api_url = "https://visas-be.tlscontact.com/api/v1/appointments/slots" 
        
        # Default headers (will be overridden by session UA if available)
        self.default_headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://visas-be.tlscontact.com/gb/LON/book-appointment",
            "X-Requested-With": "XMLHttpRequest"
        }

    async def fetch_raw_slots(self, center: str = "brussels", force_refresh: bool = False) -> Dict:
        """
        Fetches slot data using cookies from the SessionGenerator.
        """
        logger.info(f"Fetching Belgium slots for {center} (Cloudflare Hybrid Mode)...")
        
        # 1. Get Session (Cookies + User-Agent)
        session_data = None
        if not force_refresh:
            session_data = await session_generator.get_valid_session()
        
        if not session_data:
            logger.info("No valid session found. Triggering browser-assisted generation...")
            session_data = await session_generator.generate_session()
        
        cookies = session_data.get("cookies", {})
        user_agent = session_data.get("user_agent")

        # 2. Prepare Request
        headers = self.default_headers.copy()
        if user_agent:
            headers["User-Agent"] = user_agent

        try:
            with requests.Session() as session:
                session.headers.update(headers)
                session.cookies.update(cookies)
                
                logger.info(f"Requesting {self.api_url} with CF Clearance cookies...")
                response = session.get(self.api_url, params={"center": center}, timeout=20)
                
                logger.info(f"TLS Response: {response.status_code}")

                # 3. Handle 403 (Session Expired/Blocked)
                if response.status_code == 403:
                    if not force_refresh:
                        logger.warning("403 Detected even with cookies. Retrying with fresh session...")
                        return await self.fetch_raw_slots(center, force_refresh=True)
                    else:
                        logger.error("403 Persistent even after fresh session generation.")

                return {
                    "status_code": response.status_code,
                    "text": response.text,
                    "success": response.status_code == 200,
                    "center": center
                }
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return {
                "status_code": 0,
                "text": str(e),
                "success": False,
                "center": center
            }

    def parse_slots(self, raw_response: str, center: str) -> List[Dict]:
        """
        Parses the raw response text into a structured slot format.
        """
        logger.info(f"Parsing slots for {center}...")
        slots = []
        try:
            data = json.loads(raw_response)
            if isinstance(data, dict) and "slots" in data:
                for item in data["slots"]:
                    slots.append({
                        "country": self.country,
                        "center": center,
                        "slot_date": item.get("date"),
                        "slot_time": item.get("time", "09:00")
                    })
        except json.JSONDecodeError:
            logger.warning("Response is not JSON. Cloudflare might still be blocking.")
        return slots

    async def save_to_db(self, center: str, raw_data: str, parsed_slots: List[Dict]):
        """
        Saves snapshot and normalized slots.
        """
        async with AsyncSessionLocal() as db:
            try:
                # 1. Save Snapshot
                snapshot = SlotSnapshot(
                    country=self.country,
                    center=center,
                    raw_response=raw_data,
                    timestamp=datetime.now()
                )
                db.add(snapshot)
                
                # 2. Save Slots
                for s in parsed_slots:
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
                logger.error(f"Database error: {e}")
                await db.rollback()

    async def fetch_slots(self, center: str = "brussels") -> List[Dict]:
        """
        Entry point for the full scraper cycle.
        """
        result = await self.fetch_raw_slots(center)
        slots = []
        if result["success"]:
            slots = self.parse_slots(result["text"], center)
            await self.save_to_db(center, result["text"], slots)
        return slots

# Singleton
belgium_scraper = BelgiumScraper()
