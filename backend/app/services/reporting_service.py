import hashlib
import logging
from datetime import datetime, timedelta
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.entities import User, SlotReport, SlotEvent
from ..services.telegram_service import send_telegram_message
from ..models.entities import AlertPreference

def generate_fingerprint(country: str, center: str, visa_type: str, slot_date: datetime, slot_time: str) -> str:
    """
    Generates a unique hash for a slot based on country, center, date, and rounded time.
    """
    normalized_time = slot_time.split(':')[0] # Use just the hour for fingerprinting
    raw_str = f"{country}|{center}|{visa_type}|{slot_date.strftime('%Y-%m-%d')}|{normalized_time}"
    return hashlib.sha256(raw_str.encode()).hexdigest()

def calculate_report_score(user: User, report_data: dict, has_duplicate: bool, matches_pattern: bool) -> int:
    """
    Implements the scoring engine logic.
    """
    score = 50
    if user.trust_score > 50: score += 20
    elif user.trust_score < 10: score -= 20
    if report_data.get("screenshot_url"): score += 15
    if has_duplicate: score += 30
    if matches_pattern: score += 10
    return score

from ..core.logging import logger
from ..services.subscription_service import is_premium

async def process_slot_report(db: AsyncSession, user: User, report_in: dict):
    """
    Main logic for handling a slot report submission (Async).
    """
    fingerprint = generate_fingerprint(
        report_in['country'], report_in['center'], report_in['visa_type'],
        report_in['slot_date'], report_in['slot_time']
    )
    
    # 0. Idempotency: User cannot report the same fingerprint twice
    existing_report_res = await db.execute(select(SlotReport).where(
        and_(SlotReport.user_id == user.id, SlotReport.fingerprint_hash == fingerprint)
    ))
    if existing_report_res.scalar_one_or_none():
        return {"status": "error", "message": "You have already reported this slot."}

    if user.account_status == 'shadow_banned':
        status, score = 'rejected', 0
    else:
        # Anti-Spam: Max 5 reports per 5 minutes
        recent_res = await db.execute(select(SlotReport).where(
            and_(SlotReport.user_id == user.id, SlotReport.reported_at > datetime.utcnow() - timedelta(minutes=5))
        ))
        if len(recent_res.scalars().all()) >= 5:
            return {"status": "error", "message": "Too many reports. Please wait."}

        # Consensus check
        dup_res = await db.execute(select(SlotReport).where(
            and_(SlotReport.fingerprint_hash == fingerprint, SlotReport.status == 'valid')
        ))
        has_duplicate = len(dup_res.scalars().all()) > 0
        
        score = calculate_report_score(user, report_in, has_duplicate, matches_pattern=True)
        status = "valid" if score >= 70 else ("pending" if score >= 40 else "rejected")

    report = SlotReport(
        user_id=user.id, country=report_in['country'], center=report_in['center'],
        visa_type=report_in['visa_type'], slot_date=report_in['slot_date'],
        slot_time=report_in['slot_time'], screenshot_url=report_in.get('screenshot_url'),
        confidence_score=score, status=status, fingerprint_hash=fingerprint
    )
    db.add(report)
    
    user.reports_submitted += 1
    if status == 'valid':
        user.reports_accepted += 1
        user.trust_score += 10
        logger.info(f"Valid report from user {user.id} for {report_in['country']}. Score: {score}")
    elif status == 'rejected':
        user.reports_rejected += 1
        user.trust_score -= 15
        if user.trust_score < -50: user.account_status = 'shadow_banned'
        logger.warning(f"Rejected report from user {user.id}. Trust Score dropped to {user.trust_score}")
            
    if status == 'valid':
        event_res = await db.execute(select(SlotEvent).where(SlotEvent.fingerprint_hash == fingerprint))
        event = event_res.scalar_one_or_none()
        
        if event:
            event.sources_count += 1
            event.confidence_score = (event.confidence_score + score) // 2
            event.last_updated = datetime.utcnow()
        else:
            event = SlotEvent(
                country=report.country, center=report.center, visa_type=report.visa_type,
                slot_date=report.slot_date, time_window=report.slot_time.split(':')[0] + ":00",
                confidence_score=score, sources_count=1, fingerprint_hash=fingerprint
            )
            db.add(event)
        
        await db.flush()
        if event.confidence_score >= 80 or event.sources_count >= 3:
            await trigger_event_alerts(db, event)

    await db.commit()
    return {"status": status, "score": score, "report_id": str(report.id)}

async def trigger_event_alerts(db: AsyncSession, event: SlotEvent):
    from ..services.telegram_service import send_telegram_message
    from ..services.slot_lifecycle_service import slot_lifecycle # For background task scheduling if needed
    from ..workers.scheduler import scheduler

    # Find users with matching preferences
    alert_res = await db.execute(select(User).join(AlertPreference).where(
        and_(AlertPreference.country == event.country, AlertPreference.center == event.center, User.telegram_chat_id != None)
    ))
    users_to_alert = alert_res.scalars().all()
    
    for user in users_to_alert:
        message = (
            f"🌟 <b>Crowd Verified Slot Found!</b>\n"
            f"Confidence: {event.confidence_score}%\n\n"
            f"📍 <b>Country:</b> {event.country}\n"
            f"🏢 <b>Center:</b> {event.center}\n"
            f"📅 <b>Date:</b> {event.slot_date.strftime('%Y-%m-%d')}\n"
            f"⏰ <b>Window:</b> {event.time_window}\n\n"
            f"Verified by {event.sources_count} users."
        )

        # Priority Gating
        if is_premium(user):
            send_telegram_message(user.telegram_chat_id, message)
        else:
            # Delay for free users: 3 minutes
            delay_msg = message + "\n\n⚡ <i>Upgrade to Premium for instant alerts!</i>"
            scheduler.add_job(
                send_telegram_message,
                'date',
                run_date=datetime.now() + timedelta(minutes=3),
                args=[user.telegram_chat_id, delay_msg]
            )
