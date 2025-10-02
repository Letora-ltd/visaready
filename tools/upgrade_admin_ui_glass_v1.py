import os, sys

ADMIN = os.path.join("frontend","admin","index.html")
if not os.path.exists(ADMIN):
    print("ERROR: frontend/admin/index.html not found")
    sys.exit(1)

html = open(ADMIN, "r", encoding="utf-8").read()

# Only inject once
if "/* v-admin-glass-v1 */" in html:
    print("Admin glass UI already injected. Nothing to do.")
    sys.exit(0)

# Ensure BACKEND const (no duplicate explosion)
if "const BACKEND" not in html:
    html = html.replace("<script>", "<script>\n  const BACKEND='http://127.0.0.1:8000';", 1)

inject = r"""
<!-- v-admin-glass-v1 -->
<style>
/* ===== Admin Glass UI (matches Auth) ===== */
:root{
  --bg1:#0B3C5D; --bg2:#13293D; --glass:rgba(255,255,255,0.08);
  --txt:#e7eef6; --muted:#99A4B2; --accent:#A3E635; --bad:#ef4444; --ok:#22c55e; --warn:#f59e0b;
}
body { background:#0b1a2a; color:var(--txt); }
#vr_admin_bg, #vr_admin_fog { position:fixed; inset:0; pointer-events:none; z-index:-2; }
#vr_admin_bg {
  background: radial-gradient(1000px 1000px at 10% 10%, #153e5f 0%, transparent 60%),
              radial-gradient(1000px 1000px at 90% 10%, #0c4855 0%, transparent 60%),
              radial-gradient(1200px 1200px at 50% 100%, #0a3f84 0%, transparent 60%),
              linear-gradient(180deg, #0b1a2a, #0a1220);
  filter:saturate(1.1) brightness(0.95);
}
#vr_admin_fog {
  z-index:-1; opacity:.5;
  background: radial-gradient(50% 30% at 20% 30%, rgba(163,230,53,.15) 0%, transparent 60%),
              radial-gradient(40% 30% at 80% 20%, rgba(14,165,233,.18) 0%, transparent 60%),
              radial-gradient(40% 30% at 50% 80%, rgba(255,255,255,.06) 0%, transparent 60%);
  filter: blur(40px);
  animation: vr_drift 18s ease-in-out infinite alternate;
}
@keyframes vr_drift{from{transform:translate3d(-10px,0,0)}to{transform:translate3d(10px,8px,0)}}

.vr-shell { display:grid; grid-template-columns: 220px 1fr; gap:18px; min-height:100vh; }
.vr-header {
  position:sticky; top:0; z-index:100;
  background:linear-gradient(180deg, rgba(255,255,255,.06), rgba(255,255,255,.02));
  border-bottom:1px solid rgba(255,255,255,.08);
  backdrop-filter: blur(6px);
  display:flex; align-items:center; justify-content:space-between; padding:16px 18px;
}
.vr-brand { display:flex; align-items:center; gap:10px; }
.vr-logo { width:28px; height:28px; border-radius:8px; background:linear-gradient(135deg, var(--accent), #4ade80); box-shadow:0 6px 16px rgba(163,230,53,.35);}
.vr-title { font-weight:800; letter-spacing:.3px; }
.vr-badge { font-size:12px; color:#cbd5e1; }
.vr-actions { display:flex; gap:8px; align-items:center; }
.vr-btn { padding:8px 10px; border:none; border-radius:10px; font-weight:700; cursor:pointer;
  background:var(--accent); color:#09121e; box-shadow:0 10px 20px rgba(163,230,53,.35); }

.vr-sidebar {
  position:sticky; top:68px;
  align-self:start; height:max-content;
  background:linear-gradient(180deg, rgba(255,255,255,.06), rgba(255,255,255,.02));
  border:1px solid rgba(255,255,255,.08); border-radius:16px; padding:12px; margin-left:18px;
}
.vr-nav { display:flex; flex-direction:column; gap:6px; }
.vr-link { display:flex; gap:10px; align-items:center; padding:10px 12px; border-radius:12px;
  cursor:pointer; color:#dbebff; text-decoration:none; background:rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.06); }
.vr-link:hover { background:rgba(255,255,255,.08); }
.vr-main { padding:18px; padding-top:0; }

.vr-card { background:linear-gradient(180deg, rgba(255,255,255,.06), rgba(255,255,255,.02));
  border:1px solid rgba(255,255,255,.08); border-radius:16px; box-shadow:0 12px 34px rgba(0,0,0,.35); padding:16px; margin-bottom:18px; }

.vr-input, .vr-select, .vr-textarea, .btn, .select, input, select, textarea {
  border-radius:12px !important; border:1px solid rgba(255,255,255,.12) !important;
  background:rgba(255,255,255,.06) !important; color:#dbeafe !important; outline:none;
}
.btn { box-shadow:0 10px 24px rgba(163,230,53,.25) !important; }

.vr-table thead th { text-align:left; font-weight:700; color:#cbd5e1; }
.vr-table tr:nth-child(even) { background:rgba(255,255,255,.03); }
.vr-toast {
  position:fixed; right:16px; bottom:16px; min-width:240px; padding:12px 14px; border-radius:12px;
  background:rgba(16,185,129,.12); border:1px solid rgba(16,185,129,.45); color:#d1fae5; display:none; z-index:9999;
}
.vr-top { position:fixed; right:16px; bottom:72px; background:#0ea5e9; color:#06121f; border-radius:999px; width:40px; height:40px; display:grid; place-items:center; cursor:pointer; box-shadow:0 8px 22px rgba(14,165,233,.35); }
@media (max-width: 980px){
  .vr-shell { grid-template-columns: 1fr; }
  .vr-sidebar { position:static; margin:0 18px; }
}
</style>

<script>
/* v-admin-glass-v1 */
(function(){
  // Insert animated background
  if(!document.getElementById('vr_admin_bg')){
    const bg = document.createElement('div'); bg.id='vr_admin_bg';
    const fg = document.createElement('div'); fg.id='vr_admin_fog';
    document.body.prepend(fg); document.body.prepend(bg);
  }

  // Wrap existing <main> content into shell (header + sidebar)
  function buildShell(){
    const main = document.querySelector('main.container');
    if(!main) return;
    if(document.querySelector('.vr-shell')) return;

    // Header
    const header = document.createElement('div');
    header.className='vr-header';
    header.innerHTML = `
      <div class="vr-brand">
        <div class="vr-logo"></div>
        <div>
          <div class="vr-title">VisaReady Admin</div>
          <div class="vr-badge" id="vr_header_badge">Welcome</div>
        </div>
      </div>
      <div class="vr-actions">
        <button class="vr-btn" id="vr_open_auth">Open Auth</button>
        <button class="vr-btn" id="vr_to_top" title="Back to top">Top</button>
      </div>
    `;

    // Sidebar
    const sidebar = document.createElement('aside');
    sidebar.className='vr-sidebar';
    sidebar.innerHTML = `
      <nav class="vr-nav">
        <a class="vr-link" href="#keySearchCard">🔎 Search & Filters</a>
        <a class="vr-link" href="#inlineEditor">📝 Inline Editor</a>
        <a class="vr-link" href="#dupCard">📄 Duplicate</a>
        <a class="vr-link" href="#bulkDupCard">📦 Bulk Duplicate</a>
        <a class="vr-link" href="#validateCard">✅ Validation</a>
        <a class="vr-link" href="./csv.html">🗂 CSV Import/Export</a>
      </nav>
    `;

    // Main wrapper
    const wrapper = document.createElement('div');
    wrapper.className='vr-main';

    // Move all existing children of main into wrapper sections to get glass cards look
    const kids = Array.from(main.children);
    kids.forEach(el=>{
      if(el.classList && el.classList.contains('card')) {
        el.classList.add('vr-card');
      }
      wrapper.appendChild(el);
    });

    // Build shell
    const shell = document.createElement('div');
    shell.className='vr-shell';
    document.body.insertBefore(header, document.body.firstChild);
    const page = document.createElement('div');
    page.style.marginTop = '68px';
    shell.appendChild(sidebar);
    shell.appendChild(wrapper);
    document.body.appendChild(shell);
  }

  // Enhance table class
  function styleTable(){
    const table = document.querySelector('#keysBody')?.closest('table');
    if(table){
      table.classList.add('vr-table');
      const ths = table.querySelectorAll('thead th');
      ths.forEach(th => th.style.padding = '10px 8px');
      const tds = table.querySelectorAll('tbody td');
      tds.forEach(td => td.style.padding = '10px 8px');
    }
  }

  // Toast utility
  function toast(msg, kind='ok'){
    let box = document.getElementById('vr_toast');
    if(!box){
      box = document.createElement('div');
      box.id='vr_toast'; box.className='vr-toast';
      document.body.appendChild(box);
    }
    box.textContent = msg;
    box.style.display = 'block';
    box.style.background = kind==='ok' ? 'rgba(16,185,129,.12)' : (kind==='warn' ? 'rgba(245,158,11,.12)' : 'rgba(239,68,68,.12)');
    box.style.borderColor = kind==='ok' ? 'rgba(16,185,129,.45)' : (kind==='warn' ? 'rgba(245,158,11,.45)' : 'rgba(239,68,68,.45)');
    setTimeout(()=>{ box.style.display='none'; }, 2400);
  }

  // Header badge
  async function headerBadge(){
    const el = document.getElementById('vr_header_badge');
    if(!el) return;
    try{
      const tok = window.token || window.VAL_TOKEN || localStorage.getItem('vr_token') || '';
      if(!tok){ el.textContent='Not signed'; return; }
      const r = await fetch(`${BACKEND}/auth/whoami`, { headers:{ Authorization:'Bearer '+tok } });
      if(!r.ok){ el.textContent='Token invalid'; return; }
      const j = await r.json(); const c = j.claims||{};
      el.textContent = `${c.sub||'?'}  •  ${c.role||'user'}`;
    }catch(e){ el.textContent='Error'; }
  }

  // Keyboard navigation
  function wireShortcuts(){
    let gPressed = false;
    window.addEventListener('keydown', e=>{
      if(e.key.toLowerCase()==='g'){ gPressed=true; setTimeout(()=>gPressed=false, 600); return; }
      if(!gPressed) return;
      const K = e.key.toLowerCase();
      if(K==='s'){ location.hash = '#keySearchCard'; toast('Jump: Search & Filters'); }
      if(K==='i'){ location.hash = '#inlineEditor'; toast('Jump: Inline Editor'); }
      if(K==='d'){ location.hash = '#dupCard'; toast('Jump: Duplicate'); }
      if(K==='b'){ location.hash = '#bulkDupCard'; toast('Jump: Bulk Duplicate'); }
      if(K==='v'){ location.hash = '#validateCard'; toast('Jump: Validation'); }
    });
  }

  // Actions
  function wireHeaderActions(){
    const openAuth = document.getElementById('vr_open_auth');
    const toTop = document.getElementById('vr_to_top');
    if(openAuth) openAuth.onclick = ()=> location.href = '/auth/';
    if(toTop) toTop.onclick = ()=> window.scrollTo({top:0, behavior:'smooth'});
  }

  document.addEventListener('DOMContentLoaded', ()=>{
    try{
      buildShell();
      styleTable();
      headerBadge();
      wireShortcuts();
      wireHeaderActions();
      // Apply glass to any late-rendered .card blocks
      setTimeout(()=>{ document.querySelectorAll('section.card').forEach(c=>c.classList.add('vr-card')); }, 50);
    }catch(e){ console.error('Admin Glass UI error', e); }
  });
})();
</script>
"""

# Inject before </body>
html = html.replace("</body></html>", inject + "\n</body></html>")
open(ADMIN, "w", encoding="utf-8").write(html)
print("Admin glass UI injected. Reload /admin (Ctrl+F5).")
