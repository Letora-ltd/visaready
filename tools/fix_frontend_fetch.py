import os, re, sys

FILES = [
    os.path.join("frontend","admin","index.html"),
    os.path.join("frontend","admin","csv.html"),
]

BACKEND_DEFAULT = "http://127.0.0.1:8000"

def ensure_backend_const(html: str) -> str:
    if "const BACKEND" not in html:
        # insert after first <script> tag
        html = html.replace("<script>", f"<script>\n  const BACKEND='{BACKEND_DEFAULT}';", 1)
    return html

def fix_fetch_lines(html: str) -> str:
    """
    Normalize common broken patterns to:
      fetch(`${BACKEND}/path`, { ... })
    Keeps existing options object intact.
    """

    # 1) fetch(${BACKEND}/path", {...})  -> fetch(`${BACKEND}/path`, {...})
    html = re.sub(
        r'fetch\(\s*\$\{BACKEND\}(/[^\'"`\)]*)["\']\s*,',
        r'fetch(`${BACKEND}\1`,',
        html
    )

    # 2) fetch(${BACKEND}/path)          -> fetch(`${BACKEND}/path`)
    html = re.sub(
        r'fetch\(\s*\$\{BACKEND\}(/[^\'"`\)]*)\s*\)',
        r'fetch(`${BACKEND}\1`)',
        html
    )

    # 3) fetch('/admin/...') or fetch("/admin/...") -> fetch(`${BACKEND}/admin/...`)
    html = re.sub(
        r'fetch\(\s*[\'"](/admin/[^\'"]*)[\'"]\s*,',
        r'fetch(`${BACKEND}\1`,',
        html
    )
    html = re.sub(
        r'fetch\(\s*[\'"](/admin/[^\'"]*)[\'"]\s*\)',
        r'fetch(`${BACKEND}\1`)',
        html
    )

    # 4) fetch('/api/...') or fetch("/api/...") -> fetch(`${BACKEND}/api/...`)  (only in admin pages)
    html = re.sub(
        r'fetch\(\s*[\'"](/api/[^\'"]*)[\'"]\s*,',
        r'fetch(`${BACKEND}\1`,',
        html
    )
    html = re.sub(
        r'fetch\(\s*[\'"](/api/[^\'"]*)[\'"]\s*\)',
        r'fetch(`${BACKEND}\1`)',
        html
    )

    # 5) fetch($`{BACKEND}/path`...) accidental '$`' -> proper template
    html = re.sub(
        r'fetch\(\s*\$`(\{BACKEND\}[^`]*)`\s*,',
        r'fetch(`\1`,',
        html
    )
    html = re.sub(
        r'fetch\(\s*\$`(\{BACKEND\}[^`]*)`\s*\)',
        r'fetch(`\1`)',
        html
    )

    # 6) Ensure we didn’t leave mixed quote after template literal comma
    #    e.g., fetch(`${BACKEND}/x", { ... }) -> fetch(`${BACKEND}/x`, { ... })
    html = re.sub(
        r'fetch\(`\$\{BACKEND\}([^`]*)["\']\s*,',
        r'fetch(`${BACKEND}\1`,',
        html
    )

    return html

def process_file(path: str):
    if not os.path.exists(path):
        return False, f"skip {path} (not found)"
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()
    orig = html
    html = ensure_backend_const(html)
    html = fix_fetch_lines(html)
    if html != orig:
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        return True, f"fixed {path}"
    return False, f"no changes {path}"

def main():
    changed = 0
    for p in FILES:
        ok, msg = process_file(p)
        print(msg)
        if ok: changed += 1
    print(f"Done. Files changed: {changed}")

if __name__ == "__main__":
    main()
