import os, sys

ADMIN = os.path.join("frontend", "admin", "index.html")

if not os.path.exists(ADMIN):
    print(f"ERROR: not found: {ADMIN}")
    sys.exit(1)

html = open(ADMIN, "r", encoding="utf-8").read()

# If already injected, do nothing.
if "/* v-status-dashboard */" in html:
    print("Status dashboard already injected. Nothing to do.")
    sys.exit(0)

# Ensure BACKEND const exists (won't duplicate if already present earlier)
if "const BACKEND" not in html:
    html = html.replace("<script>", "<script>\n  const BACKEND='http://127.0.0.1:8000';", 1)

injection = r"""
<!-- v-status dashboard -->
<script>
/* v-status-dashboard */
(function(){
  // Insert a Diagnostics card at the end of <main>
  function ensureDiagnosticsCard(){
    const main = document.querySelector('main.container');
    if(!main || document.getElementById('diagCard')) return;
    const sec = document.createElement('section');
    sec.className = 'card';
    sec.id = 'diagCard';
    sec.innerHTML = `
      <h2 class="h2">Diagnostics / Status</h2>
      <p class="small">Check what features are active and which endpoints are live.</p>
      <div style="display:flex; gap:10px; flex-wrap:wrap; margin-bottom:8px;">
        <button class="btn" id="diag_run">Run Status Check</button>
        <span id="diag_msg" class="small"></span>
      </div>
      <pre id="diag_out" class="small" style="white-space:pre-wrap;"></pre>
    `;
    main.appendChild(sec);
  }

  // Reuse helpers if they exist
  async function ensureToken(){
    // prefer VAL_TOKEN (validate tools) → fallback to generic login form token if present
    if (window.VAL_TOKEN) return window.VAL_TOKEN;
    if (window.token) return window.token;

    // If there's a known password field in Validate card, try that
    const pwdEl = document.getElementById('val_pwd') || document.getElementById('password');
    const pwd = pwdEl ? (pwdEl.value || '').trim() : '';
    if (!pwd) throw new Error('Enter admin password (in Validate card or Login box), then click Run again.');

    const res = await fetch(`${BACKEND}/admin/login`, {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ password: pwd })
    });
    if(!res.ok) throw new Error('Login failed: ' + (await res.text()));
    const tok = (await res.json()).token;
    window.VAL_TOKEN = tok;
    window.token = tok; // keep both for compatibility
    return tok;
  }

  async function authed(url, opts){
    const tok = await ensureToken();
    opts = opts || {};
    const headers = Object.assign({}, opts.headers || {}, { 'Authorization': 'Bearer ' + tok });
    let r = await fetch(url, Object.assign({}, opts, { headers }));
    if (r.status === 401) { // retry once
      window.VAL_TOKEN = null; window.token = null;
      const t2 = await ensureToken();
      const headers2 = Object.assign({}, opts.headers || {}, { 'Authorization': 'Bearer ' + t2 });
      r = await fetch(url, Object.assign({}, opts, { headers: headers2 }));
    }
    return r;
  }

  function yes(cond){ return cond ? 'YES' : 'no'; }

  function featureScan(){
    // UI presence
    const features = {
      searchFilters: !!document.getElementById('keySearchCard'),
      sortControl: !!document.getElementById('ks_sort'),
      outdatedToggle: !!document.getElementById('ks_outdated_only'),
      dryRunButton: !!document.getElementById('val_dry_btn'),
      dryRunApply: !!document.getElementById('val_dry_apply_btn'),
      inlineEditor: !!document.getElementById('inlineEditor'),
      csvLink: !!document.querySelector('a[href="./csv.html"]'),
      duplicateCard: !!document.getElementById('dupCard'),
      bulkDuplicateCard: !!document.getElementById('bulkDupCard'),
      keyBuilder: !!document.getElementById('keyBuilderCard'),
      authedFetchHelper: (typeof window.authedFetch === 'function'),
    };
    return features;
  }

  async function endpointScan(){
    try{
      const r = await fetch(`${BACKEND}/openapi.json`);
      if (!r.ok) return { ok:false, reason:`openapi ${r.status}` };
      const spec = await r.json();
      const paths = spec.paths || {};
      function has(p, m){ return !!(paths[p] && paths[p][m]); }

      const endpoints = {
        checklists: has('/admin/checklists','get') || has('/admin/checklists','put') || has('/admin/checklists','post'),
        exportCsv: has('/admin/export/csv','get'),
        importCsv: has('/admin/import/csv','post'),
        validate: has('/admin/validate','get'),
        dryfix: has('/admin/validate/dryfix','post'),
        fix: has('/admin/validate/fix','post'),
        duplicate: has('/admin/duplicate','post'),
        duplicateBulk: has('/admin/duplicate/bulk','post'),
        seed: has('/api/seed','get'),
      };
      return { ok:true, endpoints };
    }catch(e){
      return { ok:false, reason: String(e) };
    }
  }

  async function collectStats(){
    try{
      const r = await authed(`${BACKEND}/admin/checklists`, { method:'GET' });
      if(!r.ok) return { ok:false, reason: `checklists ${r.status}` };
      const data = await r.json();
      const keys = Object.keys(data||{});
      const sample = keys.slice(0, 10);
      return { ok:true, total: keys.length, sample };
    }catch(e){
      return { ok:false, reason: String(e) };
    }
  }

  function renderReport(outEl, msgEl, features, ep, stats){
    const l = [];
    l.push('=== ADMIN UI FEATURES ===');
    l.push(`Search & Filters: ${yes(features.searchFilters)}  | Sort: ${yes(features.sortControl)}  | Outdated toggle: ${yes(features.outdatedToggle)}`);
    l.push(`Dry-run Fix: ${yes(features.dryRunButton)}  | Dry-run + Apply: ${yes(features.dryRunApply)}  | Inline Editor: ${yes(features.inlineEditor)}`);
    l.push(`CSV page link: ${yes(features.csvLink)}  | Duplicate: ${yes(features.duplicateCard)}  | Bulk Duplicate: ${yes(features.bulkDuplicateCard)}  | Key Builder: ${yes(features.keyBuilder)}`);
    l.push(`authedFetch helper: ${yes(features.authedFetchHelper)}`);
    l.push('');

    l.push('=== BACKEND ENDPOINTS ===');
    if (ep.ok){
      const e = ep.endpoints;
      l.push(`/admin/checklists: ${yes(e.checklists)}   /admin/export/csv: ${yes(e.exportCsv)}   /admin/import/csv: ${yes(e.importCsv)}`);
      l.push(`/admin/validate: ${yes(e.validate)}   /admin/validate/dryfix: ${yes(e.dryfix)}   /admin/validate/fix: ${yes(e.fix)}`);
      l.push(`/admin/duplicate: ${yes(e.duplicate)}   /admin/duplicate/bulk: ${yes(e.duplicateBulk)}   /api/seed: ${yes(e.seed)}`);
    }else{
      l.push(`openapi unavailable (${ep.reason||'unknown'})`);
    }
    l.push('');

    l.push('=== DATA SNAPSHOT ===');
    if (stats.ok){
      l.push(`Total keys: ${stats.total}`);
      if (stats.sample && stats.sample.length){
        l.push('Sample:');
        stats.sample.forEach(k => l.push(`  • ${k}`));
      }
    }else{
      l.push(`Could not load (/admin/checklists): ${stats.reason||'unknown'}`);
    }

    outEl.textContent = l.join('\n');
    msgEl.textContent = 'Done.';
  }

  function wireRun(){
    const btn = document.getElementById('diag_run');
    const msg = document.getElementById('diag_msg');
    const out = document.getElementById('diag_out');
    if(!btn) return;
    btn.onclick = async ()=>{
      msg.textContent = 'Running…';
      out.textContent = '';
      try{
        const features = featureScan();
        const [ep, stats] = await Promise.all([endpointScan(), collectStats()]);
        renderReport(out, msg, features, ep, stats);
      }catch(e){
        console.error(e);
        msg.textContent = 'Failed (see console).';
      }
    };
  }

  document.addEventListener('DOMContentLoaded', ()=>{
    ensureDiagnosticsCard();
    wireRun();
  });
})();
</script>
"""

# Inject before </body>
html = html.replace("</body></html>", injection + "\n</body></html>")

open(ADMIN, "w", encoding="utf-8").write(html)
print("Admin diagnostics/status injected. Reload /admin -> 'Run Status Check'.")
