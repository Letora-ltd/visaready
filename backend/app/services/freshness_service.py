from datetime import datetime, timezone
from ..core.config import settings


def stale_minutes(last_updated) -> float:
    if not last_updated:
        return 10_000
    now = datetime.now(timezone.utc)
    lu = last_updated if last_updated.tzinfo else last_updated.replace(tzinfo=timezone.utc)
    return (now - lu).total_seconds() / 60


def compute_is_stale(last_updated) -> bool:
    return stale_minutes(last_updated) > settings.stale_threshold_minutes


def compute_priority(country: str, mins: float) -> str:
    importance = settings.country_importance.get(country.upper(), 1)
    score = mins * importance
    if score > settings.stale_threshold_minutes * 6:
        return 'high'
    if score > settings.stale_threshold_minutes * 2:
        return 'medium'
    return 'low'


def confidence_score(source_type: str) -> float:
    return {'admin': 0.95, 'automated': 0.7, 'fallback': 0.45}.get(source_type, 0.4)
