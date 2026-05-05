from fastapi import APIRouter, Depends, HTTPException
from ..services.belgium_scraper import belgium_scraper
from ..services.session_generator import session_generator
from ..services.belgium_browser_scraper import belgium_browser_scraper
import logging

router = APIRouter(prefix="/internal/belgium", tags=["internal"])
logger = logging.getLogger(__name__)

@router.get("/check")
async def trigger_belgium_check(center: str = "brussels"):
    """
    Manually triggers the Belgium scraper for a specific center.
    Returns the slots found.
    """
    logger.info(f"Manual trigger for Belgium scraper check: center={center}")
    try:
        slots = await belgium_scraper.fetch_slots(center=center)
        return {
            "success": True,
            "center": center,
            "slots_count": len(slots),
            "slots": slots
        }
    except Exception as e:
        logger.error(f"Error during manual Belgium check: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/session/generate")
async def generate_new_session():
    """
    Triggers the Playwright browser to solve Cloudflare and generate fresh session cookies.
    """
    logger.info("Manual trigger for session generation...")
    try:
        session_data = await session_generator.generate_session()
        return {
            "success": True,
            "message": "Fresh session generated and stored.",
            "cookies_found": list(session_data["cookies"].keys())
        }
    except Exception as e:
        logger.error(f"Failed to generate session: {e}")
        raise HTTPException(status_code=500, detail=f"Session generation failed: {str(e)}")

@router.get("/browser-check")
async def trigger_browser_check(center: str = "London"):
    """
    Triggers the Playwright-native scraper to extract slots directly from the browser context.
    """
    logger.info(f"Manual trigger for browser-native check: center={center}")
    try:
        slots = await belgium_browser_scraper.fetch_slots(center=center)
        return {
            "success": True,
            "center": center,
            "slots_count": len(slots),
            "slots": slots,
            "method": "browser-native"
        }
    except Exception as e:
        logger.error(f"Browser check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/vow-check")
async def trigger_vow_integrated_check(center: str = "London", app_ref: str = None):
    """
    Triggers the ultimate bypass flow: 
    VOW (Get Token) -> TLS (Enter with Token) -> Capture Slots.
    """
    logger.info(f"Manual trigger for VOW integrated check: center={center}, ref={app_ref}")
    try:
        slots = await belgium_browser_scraper.fetch_slots_with_vow(app_reference=app_ref, center=center)
        return {
            "success": True,
            "center": center,
            "slots_count": len(slots),
            "slots": slots,
            "method": "vow-integrated-token"
        }
    except Exception as e:
        logger.error(f"VOW integrated check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
