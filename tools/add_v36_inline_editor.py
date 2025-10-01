import os, re

ADMIN_PATH = os.path.join("frontend","admin","index.html")

html = ""
with open(ADMIN_PATH, "r", encoding="utf-8") as f:
    html = f.read()

# Ensure BACKEND const exists (re-use what you set for CSV)
if "const BACKEND" not in html:
    html = html.replace("<script>", "<script>\n  const BACKEND='http://127.0.0.1:8000';", 1)

# Add an Inline Editor card if missing
if "id=\"inlineEditor\"" not in html:
    injection = """
<section class="card" id="inlineEditor">
  <h2 class="h2">Inline Editor (Friendly)</h2>
  <p class="small">Edit with plain text. Format each line as <code>Title :: Details</code> for items and <code>Label :: URL</code> for sources.</p>
  <div class="grid">
    <div>
      <div class="label">Key (e.g., IN-&gt;DE::TOURIST)</div>
      <input id="ie_key" placeholder="IN->DE::TOURIST" />
    </div>
    <div>
      <div class="label">Admin Password</div>
      <input id="ie_pwd" type="password" placeholder="Enter admin password" />
    </div>
  </div>

  <div style="margin-top:10px;">
    <button class="btn" id="ie_loadBtn">Load</button>
    <button class="btn" id="ie_saveBtn" style="margin-left:10px;">Save</button>
    <span id="ie_msg" class="small" style="margin-left:12px;"></span>
  </div>

  <div class="grid" style="margin-top:12px;">
    <div>
      <div class="label">Items (one per line: Title :: Details)</div>
      <textarea id="ie_items" rows="10" placeholder="Valid passport :: 6+ months validity&#10;Travel insurance :: Must cover stay"></textarea>
      <div id="ie_items_warn" class="small" style="color:#b91c1c; margin-top:6px;"></div>
    </div>
    <div>
      <div class="label">Sources (one per line: Label :: URL)</div>
      <textarea id="ie_sources" rows="10" placeholder="Gov portal :: https://example.gov/apply&#10;VFS Centre :: https://vfsglobal.com/ind/en/xyz"></textarea>
      <div id="ie_sources_warn" class="small" style="color:#b91c1c; margin-top:6px;"></div>
    </div>
  </div>

  <div class="grid" style="margin-top:12px;">
    <div>
      <div class="label">Fees</div>
      <input id="ie_fees" placeholder="Consular fee + service charge (varies)" />
    </div>
    <div>
      <div class="label">Processing</div>
      <input id="ie_proc" placeholder="Typically 3–15 working days" />
    </div>
    <div>
      <div class="label">Last Verified</div>
      <input id="ie_last" placeholder="YYYY-MM-DD (auto if blank)" />
    </div>
  </div>
</section>
"""
    # Insert just before closing </main> or at end of first admin card
    html = html.replace("</main>", injection + "\n</main>")

# Add helper JS only once
if "function ie_parseItemsText(" not in html:
    js_block = """
<script>
// ---- Inline Editor helpers ----
let IE_TOKEN = null;

async function ie_login() {
  const pwd = document.getElementById('ie_pwd').value.trim();
  if (!pwd) throw new Error("Enter admin password");
  const res = await fetch(`${BACKEND}/admin/login`, {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ password: pwd })
  });
  if (!res.ok) throw new Error('Login failed: ' + (await res.text()));
  IE_TOKEN = (await res.json()).token;
  return IE_TOKEN;
}

function ie_parseItemsText(text) {
  const lines = (text || '').split(/\\r?\\n/);
  const items = [];
  const warnings = [];
  lines.forEach((ln, i) => {
    const line = ln.trim();
    if (!line) return;
    let title = '', details = '';
    if (line.includes('::')) {
      [title, details] = line.split('::', 1).concat(line.split('::').slice(1).join('::'));
      // The above preserves extra '::' in details gracefully
    } else if (line.includes(' - ')) {
      [title, details] = line.split(' - ', 2);
    } else {
      // Warn user: no delimiter
      warnings.push(`Line ${i+1}: missing " :: " — "${line}"`);
      title = line; details = '';
    }
    items.push({ title: (title||'').trim(), details: (details||'').trim() });
  });
  return { items, warnings };
}

function ie_parseSourcesText(text) {
  const lines = (text || '').split(/\\r?\\n/);
  const sources = [];
  const warnings = [];
  lines.forEach((ln, i) => {
    const line = ln.trim();
    if (!line) return;
    let label = '', url = '';
    if (line.includes('::')) {
      [label, url] = line.split('::', 1).concat(line.split('::').slice(1).join('::'));
    } else if (line.includes('|')) {
      [label, url] = line.split('|', 2);
    } else {
      warnings.push(`Line ${i+1}: missing " :: " — "${line}"`);
      label = line; url = line; // best-effort
    }
    sources.push({ label: (label||'').trim(), url: (url||'').trim() });
  });
  return { sources, warnings };
}

document.getElementById('ie_loadBtn').onclick = async () => {
  const key = document.getElementById('ie_key').value.trim();
  const msg = document.getElementById('ie_msg');
  const iw = document.getElementById('ie_items_warn');
  const sw = document.getElementById('ie_sources_warn');
  iw.textContent = ''; sw.textContent = ''; msg.textContent = '';
  if (!key) { msg.textContent = 'Enter a key'; return; }
  try {
    // split key parts
    const [corr, purpose] = key.split('::');
    const [origin, dest] = (corr||'').split('->');
    if (!origin || !dest || !purpose) { msg.textContent = 'Bad key format'; return; }

    // Try to login if no token
    if (!IE_TOKEN) await ie_login();

    // Fetch via public API
    const url = `${BACKEND}/api/checklist?origin=${encodeURIComponent(origin)}&dest=${encodeURIComponent(dest)}&category=${encodeURIComponent(purpose)}`;
    const res = await fetch(url);
    if (!res.ok) { msg.textContent = 'Not found'; return; }
    const data = await res.json();

    // Fill fields
    document.getElementById('ie_fees').value = data.fees || '';
    document.getElementById('ie_proc').value = data.processing || '';
    document.getElementById('ie_last').value = data.last_verified || '';

    const items_text = (data.items||[]).map(it => `${it.title||''} :: ${it.details||''}`.trim()).join('\\n');
    const sources_text = (data.sources||[]).map(s => `${s.label||''} :: ${s.url||''}`.trim()).join('\\n');
    document.getElementById('ie_items').value = items_text;
    document.getElementById('ie_sources').value = sources_text;

    msg.textContent = 'Loaded.';
  } catch (e) {
    console.error(e); msg.textContent = 'Load failed.';
  }
};

document.getElementById('ie_saveBtn').onclick = async () => {
  const key = document.getElementById('ie_key').value.trim();
  const msg = document.getElementById('ie_msg');
  const iw = document.getElementById('ie_items_warn');
  const sw = document.getElementById('ie_sources_warn');
  iw.textContent = ''; sw.textContent = ''; msg.textContent = '';
  if (!key) { msg.textContent = 'Enter a key'; return; }

  // Parse text areas
  const { items, warnings: iwarn } = ie_parseItemsText(document.getElementById('ie_items').value);
  const { sources, warnings: swarn } = ie_parseSourcesText(document.getElementById('ie_sources').value);

  // Show warnings (but allow save)
  if (iwarn.length) iw.textContent = 'Items: ' + iwarn.join(' | ');
  if (swarn.length) sw.textContent = 'Sources: ' + swarn.join(' | ');

  const payload = {
    key,
    data: {
      items,
      sources,
      fees: document.getElementById('ie_fees').value.trim(),
      processing: document.getElementById('ie_proc').value.trim(),
      last_verified: document.getElementById('ie_last').value.trim()
    }
  };

  // Login if needed then save
  try {
    if (!IE_TOKEN) await ie_login();
    const res = await fetch(`${BACKEND}/admin/checklists`, {
      method:'PUT',
      headers:{
        'Content-Type':'application/json',
        'Authorization':'Bearer ' + IE_TOKEN
      },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      msg.textContent = 'Save failed: ' + (await res.text());
      return;
    }
    msg.textContent = 'Saved ✔';
  } catch (e) {
    console.error(e); msg.textContent = 'Save failed.';
  }
};
</script>
"""
    # append before closing body
    html = html.replace("</body>", js_block + "\n</body>")

with open(ADMIN_PATH, "w", encoding="utf-8") as f:
    f.write(html)

print("v3.6 Inline Editor + validation added to frontend/admin/index.html")
