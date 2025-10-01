import os, re

FILES = [
    os.path.join("frontend","admin","index.html"),
    os.path.join("frontend","admin","csv.html"),
]

BACKEND_DEFAULT = "http://127.0.0.1:8000"

def ensure_backend_const(html: str) -> str:
    if "const BACKEND" not in html:
        html = html.replace("<script>", f"<script>\n  const BACKEND='{BACKEND_DEFAULT}';", 1)
    return html

def normalize_backend_placeholders(html: str) -> str:
    # Turn `{BACKEND}` or $`{BACKEND}` into `${BACKEND}` inside backticks
    html = re.sub(r'`{BACKEND}(/[^`"]*)`', r'`${BACKEND}\1`', html)
    html = re.sub(r'\$`{BACKEND}(/[^`"]*)`', r'`${BACKEND}\1`', html)
    # Fix cases like fetch({BACKEND}/path -> fetch(`${BACKEND}/path`
    html = re.sub(r'fetch\(\s*\{BACKEND\}(/[^,)\s]*)', r'fetch(`${BACKEND}\1`', html)
    return html

def normalize_fetch_calls(html: str) -> str:
    # fetch(${BACKEND}/path", {...})  →  fetch(`${BACKEND}/path`, {...})
    html = re.sub(r'fetch\(\s*\$\{BACKEND\}(/[^\'"`)]*)["\']\s*,', r'fetch(`${BACKEND}\1`,', html)
    # fetch(${BACKEND}/path) → fetch(`${BACKEND}/path`)
    html = re.sub(r'fetch\(\s*\$\{BACKEND\}(/[^\'"`)]*)\s*\)', r'fetch(`${BACKEND}\1`)', html)
    # fetch('/admin/...') → fetch(`${BACKEND}/admin/...`)
    html = re.sub(r'fetch\(\s*[\'"](/admin/[^\'"]*)[\'"]\s*,', r'fetch(`${BACKEND}\1`,', html)
    html = re.sub(r'fetch\(\s*[\'"](/admin/[^\'"]*)[\'"]\s*\)', r'fetch(`${BACKEND}\1`)', html)
    # fetch('/api/...') → fetch(`${BACKEND}/api/...`)
    html = re.sub(r'fetch\(\s*[\'"](/api/[^\'"]*)[\'"]\s*,', r'fetch(`${BACKEND}\1`,', html)
    html = re.sub(r'fetch\(\s*[\'"](/api/[^\'"]*)[\'"]\s*\)', r'fetch(`${BACKEND}\1`)', html)
    # Clean up mismatched quotes after template
    html = re.sub(r'fetch\(`\$\{BACKEND\}([^`]*)["\']\s*,', r'fetch(`${BACKEND}\1`,', html)
    return html

def process(path):
    if not os.path.exists(path): return False, f"skip {path}"
    s = open(path, "r", encoding="utf-8").read()
    orig = s
    s = ensure_backend_const(s)
    s = normalize_backend_placeholders(s)
    s = normalize_fetch_calls(s)
    if s != orig:
        open(path, "w", encoding="utf-8").write(s)
        return True, f"fixed {path}"
    return False, f"no changes {path}"

def main():
    changed = 0
    for p in FILES:
        ok, msg = process(p)
        print(msg)
        if ok: changed += 1
    print(f"Done. Files changed: {changed}")

if __name__ == "__main__":
    main()
