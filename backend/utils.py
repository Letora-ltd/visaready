import os, json, time, secrets

# Where your seed JSON files live
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "seed")

def load_json(name: str):
    with open(os.path.join(DATA_DIR, name), "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(name: str, obj):
    tmp = os.path.join(DATA_DIR, name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
    os.replace(tmp, os.path.join(DATA_DIR, name))

# Admin password from env
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

# Very simple token store (in-memory)
_TOKENS: dict[str, float] = {}

def add_token(hours: int = 24) -> str:
    expiry = time.time() + hours * 3600
    token = secrets.token_hex(16)
    _TOKENS[token] = expiry
    return token

def verify_token(token: str) -> bool:
    exp = _TOKENS.get(token)
    return bool(exp and exp > time.time())
