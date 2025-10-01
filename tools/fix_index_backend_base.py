import os, re
INDEX = os.path.join("frontend","index.html")
BACKEND_DEFAULT = "http://127.0.0.1:8000"

s = open(INDEX, "r", encoding="utf-8").read()

# ensure BACKEND const exists
if "const BACKEND" not in s:
    s = s.replace("<script>", f"<script>\n  const BACKEND='{BACKEND_DEFAULT}';", 1)

# change /api/... to use BACKEND (only for JS fetch calls)
s = re.sub(r'fetch\(\s*[\'"]\s*/api/seed\s*[\'"]\s*\)',
           r'fetch(`${BACKEND}/api/seed`)', s)
s = re.sub(r'fetch\(\s*[\'"]\s*/api/countries\s*[\'"]\s*\)',
           r'fetch(`${BACKEND}/api/countries`)', s)
s = re.sub(r'fetch\(\s*[\'"]\s*/api/corridors\s*[\'"]\s*\)',
           r'fetch(`${BACKEND}/api/corridors`)', s)
# GET checklist calls: replace "/api/checklist" variants inside string concatenations if any
s = s.replace('`${BACKEND}/api/checklist', '`${BACKEND}/api/checklist')  # idempotent no-op
s = s.replace('"/api/checklist', '`${BACKEND}/api/checklist')            # fallback pattern
# (If your code builds the URL via template already, this won't change anything.)

open(INDEX, "w", encoding="utf-8").write(s)
print("Patched frontend/index.html to use BACKEND for API calls.")
