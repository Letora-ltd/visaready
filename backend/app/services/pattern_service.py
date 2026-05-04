import logging
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.entities import SlotEvent, SlotHistory, SlotPattern

async def analyze_and_update_patterns(db: AsyncSession):
    """
    Analyzes SlotEvent data to detect peak windows and historical trends.
    """
    logging.info("Starting Pattern Detection Engine...")
    
    # 1. Aggregate Slot History (Last 24h)
    yesterday = datetime.utcnow() - timedelta(days=1)
    
    # Group by country, center to update history
    history_stmt = select(
        SlotEvent.country, 
        SlotEvent.center, 
        func.count(SlotEvent.id).label('total_events'),
        func.avg(SlotEvent.confidence_score).label('avg_confidence')
    ).where(SlotEvent.last_updated > yesterday).group_by(SlotEvent.country, SlotEvent.center)
    
    history_results = await db.execute(history_stmt)
    for row in history_results:
        # Save to history
        history = SlotHistory(
            country=row.country,
            center=row.center,
            date=yesterday,
            total_events=row.total_events,
            avg_confidence=int(row.avg_confidence)
        )
        db.add(history)

    # 2. Pattern Detection (Group by Hour)
    # find highest frequency window for each country/center
    # This is a simplified version
    pattern_stmt = select(
        SlotEvent.country,
        SlotEvent.center,
        func.extract('hour', SlotEvent.slot_date).label('hour'),
        func.count(SlotEvent.id).label('freq')
    ).group_by(SlotEvent.country, SlotEvent.center, 'hour').order_by('freq', 'hour')
    
    pattern_results = await db.execute(pattern_stmt)
    
    # Process results to find the peak hour for each corridor
    peaks = {} # (country, center) -> (peak_hour, freq)
    for row in pattern_results:
        key = (row.country, row.center)
        if key not in peaks or row.freq > peaks[key][1]:
            peaks[key] = (int(row.hour), row.freq)
            
    for (country, center), (peak_hour, freq) in peaks.items():
        # Update or create pattern
        stmt = select(SlotPattern).where(
            and_(SlotPattern.country == country, SlotPattern.center == center)
        )
        pattern_res = await db.execute(stmt)
        pattern = pattern_res.scalar_one_or_none()
        
        peak_start = f"{peak_hour:02d}:00"
        peak_end = f"{(peak_hour + 2) % 24:02d}:00"
        
        if pattern:
            pattern.peak_start_time = peak_start
            pattern.peak_end_time = peak_end
            pattern.confidence_score = min(freq * 10, 100) # Simple scaling
            pattern.last_updated = datetime.utcnow()
        else:
            pattern = SlotPattern(
                country=country,
                center=center,
                peak_start_time=peak_start,
                peak_end_time=peak_end,
                confidence_score=min(freq * 10, 100)
            )
            db.add(pattern)

    await db.commit()
    logging.info("Pattern Detection Engine complete.")

async def get_recommendation(db: AsyncSession, country: str, center: str):
    """
    Returns a recommendation based on current time vs peak patterns.
    """
    stmt = select(SlotPattern).where(
        and_(SlotPattern.country == country, SlotPattern.center == center)
    )
    result = await db.execute(stmt)
    pattern = result.scalar_one_or_none()
    
    if not pattern:
        return {
            "peak_time_window": "N/A",
            "confidence_score": 0,
            "recommendation_message": "Not enough data yet. Keep reporting!"
        }
    
    current_hour = datetime.utcnow().hour
    start_hour = int(pattern.peak_start_time.split(':')[0])
    end_hour = int(pattern.peak_end_time.split(':')[0])
    
    is_peak = False
    if start_hour <= end_hour:
        is_peak = start_hour <= current_hour <= end_hour
    else: # Wraps around midnight
        is_peak = current_hour >= start_hour or current_hour <= end_hour
        
    return {
        "peak_time_window": f"{pattern.peak_start_time} - {pattern.peak_end_time}",
        "confidence_score": pattern.confidence_score,
        "recommendation_message": "🔥 HIGH CHANCE NOW" if is_peak else "💤 LOW ACTIVITY"
    }
