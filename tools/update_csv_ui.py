import os

FRONTEND = os.path.join("frontend")
ADMIN_INDEX = os.path.join(FRONTEND, "admin", "index.html")
ADMIN_CSV = os.path.join(FRONTEND, "admin", "csv.html")

os.makedirs(os.path.join(FRONTEND, "admin"), exist_ok=True)

csv_html = """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>VisaReady — Admin CSV</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <link rel="stylesheet" href="../style.css">
</head>
<body>
<main class="container">
  <section class="card">
    <h1 class="h2">CSV Export / Import</h1>
    <p><a href="./index.html">← Back to Admin</a></p>
    <div class="grid" style="margin-top:10px;">
      <div>
        <div class="label">Admin Password</div>
        <input id="pwd" type="password" placeholder="Enter admin password">
      </div>
    </div>
    <div style="margin-top:10px; display:flex; gap:10px; flex-wrap:wrap;">
      <button class="btn" id="exportBtn">Export CSV</button>
      <label class="btn" for="file" style="display:inline-grid; place-items:center; cursor:pointer;">Choose CSV</label>
      <input id="file" type="file" accept=".csv" style="display:none;">
      <select id="mode" class="select" style="max-width:220px;">
        <option value="merge">Merge (update/add keys)</option>
        <option value="replace">Replace (overwrite all)</option>
      </select>
      <button class="btn" id="importBtn">Import CSV</button>
    </div>
    <div id="msg" class="small" style="margin-top:10px;"></div>
    <hr/>
    <details>
      <summary class="label">CSV Format (click to expand)</summary>
      <p class="small">
        Columns: <code>key,last_verified,fees,processing,items_json,sources_json</code><br/>
        <code>items_json</code> example:
        <code>[{"{"}"title":"Valid passport","details":"6+ months"{"]"}]</code><br/>
        <code>sources_json</code> example:
        <code>[{"{"}"label":"Gov page","url":"https://..."{"}"}]</code>
      </p>
    </details>
  </section>
</main>

<script>
let token = null;

async function ensureLogin() {
  const pwd = document.getElementById('pwd').value.trim();
  if (!pwd) { alert("Enter admin password"); throw new Error("no password"); }
  if (token) return token;
  const res = await fetch('/admin/login', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ password: pwd })
  });
  if (!res.ok) { alert('Login failed'); throw new Error('login failed'); }
  const data = await res.json();
  token = data.token;
  return token;
}

document.getElementById('exportBtn').addEventListener('click', async () => {
  try {
    await ensureLogin();
    const res = await fetch('/admin/export/csv', {
      headers: { 'Authorization': 'Bearer ' + token }
    });
    if (!res.ok) { alert('Export failed'); return; }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'visaready_checklists.csv'; a.click();
    URL.revokeObjectURL(url);
    document.getElementById('msg').textContent = 'Exported CSV successfully.';
  } catch (e) {
    console.error(e);
    document.getElementById('msg').textContent = 'Export failed.';
  }
});

document.getElementById('importBtn').addEventListener('click', async () => {
  try {
    await ensureLogin();
    const f = document.getElementById('file').files[0];
    if (!f) { alert('Choose a CSV file first'); return; }
    const mode = document.getElementById('mode').value;
    const form = new FormData();
    form.append('file', f);
    form.append('mode', mode);
    const res = await fetch('/admin/import/csv', {
      method:'POST',
      headers: { 'Authorization': 'Bearer ' + token },
      body: form
    });
    const msg = document.getElementById('msg');
    if (!res.ok) {
      const t = await res.text();
      msg.textContent = 'Import failed: ' + t;
      return;
    }
    const data = await res.json();
    msg.textContent = 'Import OK — ' + data.updated + ' rows, mode=' + data.mode;
  } catch (e) {
    console.error(e);
    document.getElementById('msg').textContent = 'Import failed.';
  }
});
</script>
</body>
</html>
"""

with open(ADMIN_CSV, "w", encoding="utf-8") as f:
    f.write(csv_html)

# Ensure Admin index links to CSV tool
if os.path.exists(ADMIN_INDEX):
    with open(ADMIN_INDEX, "r", encoding="utf-8") as f:
        idx = f.read()
    if 'href="./csv.html"' not in idx:
        # Insert a link below the H2 title (first occurrence)
        idx = idx.replace("</h2>", '</h2><p><a href="./csv.html">CSV Import/Export</a></p>', 1)
        with open(ADMIN_INDEX, "w", encoding="utf-8") as f:
            f.write(idx)

print("CSV UI updated: frontend/admin/csv.html ready, linked from admin.")
