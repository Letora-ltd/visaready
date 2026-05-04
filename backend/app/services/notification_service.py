import json
import urllib.request
from ..core.config import settings


def notify(event_type: str, message: str, payload: dict | None = None):
    body = {"event_type": event_type, "message": message, "payload": payload or {}}
    if settings.alert_webhook_url:
        req = urllib.request.Request(
            settings.alert_webhook_url,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req, timeout=5)
        except Exception:
            pass
    return body
