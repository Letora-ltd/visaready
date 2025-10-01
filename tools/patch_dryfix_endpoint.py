import os, textwrap

BACKEND_DIR = "backend"
VALIDATE = os.path.join(BACKEND_DIR, "admin_validate.py")
APP = os.path.join(BACKEND_DIR, "app.py")

# 1) Ensure admin_validate.py exists and has dryfix + fix endpoints
if not os.path.exists(VALIDATE):
    raise SystemExit("backend/admin_validate.py not found. Run earlier scripts or create the file first.")

src = open(VALIDATE, "r", encoding="utf-8").read()

# Make sure imports include save_json and verify_token
if "from .utils import load_json, save_json, verify_token" not in src:
    src = src.replace(
        "from .utils import load_json, verify_token",
        "from .utils import load_json, save_json, verify_token"
    )

# Ensure router definition exists
if "router = APIRouter()" not in src:
    src = src.replace("APIRouter", "APIRouter\n\nrouter = APIRouter()")

# Ensure /admin/validate route exists (from v4.2)
if "@router.get(\"/admin/validate\")" not in src:
    # Minimal validator if missing
    block_validate = textwrap.dedent("""
    @router.get("/admin/validate")
    def admin_validate(authorization: str | None = Header(default=None)):
        _auth(authorization)
        data = load_json("checklists.json")
        return {"ok": True, "count": 0, "issues": []}
    """).strip()
    src += "\n\n" + block_validate + "\n"

# Ensure /admin/validate/fix exists (from v4.3)
if "@router.post(\"/admin/validate/fix\")" not in src:
    block_fix = textwrap.dedent("""
    @router.post("/admin/validate/fix")
    def admin_validate_fix(authorization: str | None = Header(default=None)):
        _auth(authorization)
        data = load_json("checklists.json")
        # no-op default (will be overwritten if you already added the full fixer)
        return {"ok": True, "fixed": 0, "normalized": 0}
    """).strip()
    src += "\n\n" + block_fix + "\n"

# Ensure /admin/validate/dryfix exists (this is the endpoint your UI calls)
if "@router.post(\"/admin/validate/dryfix\")" not in src:
    block_dryfix = textwrap.dedent("""
    @router.post("/admin/validate/dryfix")
    def admin_validate_dryfix(authorization: str | None = Header(default=None)):
        _auth(authorization)
        data = load_json("checklists.json")
        # no-op preview; replace with your detailed diff logic if already added
        return {"ok": True, "fixed": 0, "normalized": 0, "changes": []}
    """).strip()
    src += "\n\n" + block_dryfix + "\n"

open(VALIDATE, "w", encoding="utf-8").write(src)

# 2) Ensure backend/app.py includes the admin_validate router
app = open(APP, "r", encoding="utf-8").read()
if "include_router(admin_validate.router)" not in app:
    if "from . import admin_validate" not in app and "import admin_validate" not in app:
        app += "\ntry:\n    from . import admin_validate\nexcept Exception:\n    import admin_validate\n"
    app += "app.include_router(admin_validate.router)\n"
    open(APP, "w", encoding="utf-8").write(app)

print("Dryfix endpoint ensured and router included. Restart the backend.")
