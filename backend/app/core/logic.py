from datetime import datetime, timezone

def calculate_confidence(last_updated: datetime | None, source_type: str) -> int:
    if not last_updated:
        return 0
    
    # Freshness Score (60% weight)
    now = datetime.now(timezone.utc)
    diff_hours = (now - last_updated).total_seconds() / 3600
    # Decay freshness score over 7 days (168 hours)
    freshness_score = max(0, 100 * (1 - (diff_hours / 168)))
    
    # Source Score (40% weight)
    # Admin = 100, System = 70
    source_score = 100 if source_type == 'admin' else 70
    
    confidence = (0.6 * freshness_score) + (0.4 * source_score)
    return int(confidence)
