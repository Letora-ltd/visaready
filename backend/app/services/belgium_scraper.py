import requests
import logging
import json
import asyncio
from datetime import datetime
from typing import List, Dict, Optional
from ..models.entities import SlotSnapshot, SlotEvent, SessionRecord as SessionModel
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
        self.api_url = "https://visas-be.tlscontact.com/gb/LON/api/slot"
        self.headers_template = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-GB,en;q=0.9",
            "Referer": "https://visas-be.tlscontact.com/gb/LON/login",
            "X-Requested-With": "XMLHttpRequest"
        }

    async def fetch_slots(self, center="London") -> List[Dict]:
        """
        Orchestrates session retrieval and API requests.
        """
        # 1. Get/Generate Session
        session_data = await session_generator.get_valid_session()
        if not session_data:
            logger.info("No valid session found. Generating new session...")
            session_data = await session_generator.generate_session()

        # 2. Prepare Request
        headers = self.headers_template.copy()
        headers["User-Agent"] = session_data["user_agent"]
        
        # 3. Perform Request (Using requests in a thread to keep it async-friendly)
        loop = asyncio.get_event_loop()
        try:
            # We use a POST for slot retrieval on the actual API
            # For this MVP, we simulate the TLS request structure
            response = await loop.run_in_executor(
                None, 
                lambda: requests.get(
                    self.api_url, 
                    headers=headers, 
                    cookies=session_data["cookies"],
                    timeout=15
                )
            )
            
            if response.status_code == 200:
                data = response.json()
                await self._persist_snapshot(center, data)
                return self._parse_slots(data)
            elif response.status_code == 403:
                logger.warning("Session expired or Cloudflare blocked. Marking session for refresh.")
                # Logic to invalidate session in DB
                return []
            else:
                logger.error(f"API Error {response.status_code}: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return []

    async def _persist_snapshot(self, center: str, data: Dict):
        async with AsyncSessionLocal() as db:
            snapshot = SlotSnapshot(center=center, raw_data=data)
            db.add(snapshot)
            await db.commit()

    def _parse_slots(self, data: Dict) -> List[Dict]:
        """
        Maps raw TLS JSON to Vixaa SlotEvent format.
        """
        slots = []
        # TLS response structure varies, but usually: data['slots'] or similar
        # For simulation, we assume a list of objects with 'date' and 'times'
        raw_slots = data.get("slots", [])
        for rs in raw_slots:
            slots.append({
                "slot_date": datetime.strptime(rs["date"], "%Y-%m-%d"),
                "time_window": f"{rs.get('start_time', '09:00')} - {rs.get('end_time', '10:00')}",
                "confidence_score": 90
            })
        return slots

belgium_scraper = BelgiumScraper()
