import hashlib
import json
import os
import secrets
import time
from typing import Any

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
APPLICATIONS_FILE = os.path.join(DATA_DIR, "applications.json")
PAYMENTS_FILE = os.path.join(DATA_DIR, "payments.json")


def _ensure(path: str, default: Any):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=2)


def _read(path: str, default=None):
    if default is None:
        default = []
    _ensure(path, default)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write(path: str, value: Any):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(value, f, indent=2)
    os.replace(tmp, path)


def _hash(password: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()


def create_user(name: str, email: str, password: str, country_code: str):
    users = _read(USERS_FILE)
    if any(u["email"].lower() == email.lower() for u in users):
        return None
    salt = secrets.token_hex(8)
    user = {
        "id": secrets.token_hex(8),
        "name": name,
        "email": email.lower(),
        "country_code": country_code.upper(),
        "salt": salt,
        "password_hash": _hash(password, salt),
        "created_at": int(time.time()),
    }
    users.append(user)
    _write(USERS_FILE, users)
    return sanitize_user(user)


def sanitize_user(user):
    return {k: v for k, v in user.items() if k not in {"salt", "password_hash"}}


def login(email: str, password: str):
    users = _read(USERS_FILE)
    for user in users:
        if user["email"].lower() == email.lower() and user["password_hash"] == _hash(password, user["salt"]):
            return sanitize_user(user)
    return None


_SESSIONS: dict[str, tuple[str, float]] = {}


def new_session(user_id: str):
    token = secrets.token_hex(16)
    _SESSIONS[token] = (user_id, time.time() + 7 * 24 * 3600)
    return token


def get_user_by_token(token: str):
    ses = _SESSIONS.get(token)
    if not ses:
        return None
    user_id, expires = ses
    if expires < time.time():
        _SESSIONS.pop(token, None)
        return None
    users = _read(USERS_FILE)
    for user in users:
        if user["id"] == user_id:
            return sanitize_user(user)
    return None


def add_application(user_id: str, payload: dict):
    items = _read(APPLICATIONS_FILE)
    app = {
        "id": f"VX-{secrets.token_hex(3).upper()}",
        "user_id": user_id,
        "origin": payload["origin"].upper(),
        "destination": payload["destination"].upper(),
        "visa_type": payload.get("visa_type", "TOURIST").upper(),
        "travel_date": payload.get("travel_date", ""),
        "status": "DRAFT",
        "documents": payload.get("documents", []),
        "created_at": int(time.time()),
    }
    items.append(app)
    _write(APPLICATIONS_FILE, items)
    return app


def list_applications(user_id: str):
    return [a for a in _read(APPLICATIONS_FILE) if a["user_id"] == user_id]


def _find_owned(user_id: str, app_id: str):
    items = _read(APPLICATIONS_FILE)
    for i, app in enumerate(items):
        if app["id"] == app_id and app["user_id"] == user_id:
            return items, i
    return None, None


def attach_document(user_id: str, app_id: str, name: str):
    items, idx = _find_owned(user_id, app_id)
    if items is None:
        return {"error": "Application not found"}
    items[idx].setdefault("documents", []).append(name)
    _write(APPLICATIONS_FILE, items)
    return items[idx]


def create_payment_intent(user_id: str, app_id: str):
    items, idx = _find_owned(user_id, app_id)
    if items is None:
        return {"error": "Application not found"}
    intent = {"id": f"pi_{secrets.token_hex(6)}", "app_id": app_id, "user_id": user_id, "amount": 49, "currency": "USD", "status": "requires_payment_method"}
    intents = _read(PAYMENTS_FILE)
    intents.append(intent)
    _write(PAYMENTS_FILE, intents)
    items[idx]["payment_status"] = "PENDING"
    _write(APPLICATIONS_FILE, items)
    return intent


def update_status(user_id: str, app_id: str, status: str):
    items, idx = _find_owned(user_id, app_id)
    if items is None:
        return {"error": "Application not found"}
    items[idx]["status"] = status
    _write(APPLICATIONS_FILE, items)
    return items[idx]
