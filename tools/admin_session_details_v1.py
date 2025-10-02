import os, sys

ADMIN = os.path.join("frontend","admin","index.html")
if not os.path.exists(ADMIN):
    print("ERROR: frontend/admin/index.html not found")
    sys.exit(1)

html = open(ADMIN, "r", encoding="utf-8").read()
if "/* v-admin-session-details */" in html:
    print("Session Details already injected.")
    sys.exit(0)

# ensure BACKEND const exists somewhere (no-op if already present)
if "const BACKEND" not in html:
    html = html.replace("<script>", "<script>\n  const BACKEND='http://127.0.0.1:8000';", 1)

inject = r"""
<!-- v-admin-session-details -->
<style>
.vr-sess-pop {
  position:fixed; right:18px; top:70px; z-index:120;
  width: min(92vw, 520px);
  background: rgba(17,25,40,.95);
  border:1px solid rgba(255,255,255,.08);
  border-radius:16px; padding:14px;
  box-shadow:0 20px 60px rgba(0,0,0,.45);
  display:none;
}
.vr-sess-row { display:flex; gap:10px; align-items:center; margin:6px 0; color:#dbeafe }
.vr-sess-k   { min-width:120px; opacity:.8; font-size:12px }
.vr-sess-v   { font-size:14px; word-break:break-all }
.vr-sess-actions { display:flex; gap:8px; flex-wrap:wrap; justify-content:flex-end; margin-top:10px }
.vr-btn-mini{ padding:8px 10px; border:none; border-radius:10px; font-weight:700; cursor:pointer; }
.vr-btn-act { background:#60a5fa; color:#07121f; box-shadow:0 8px 22px rgba(96,165,250,.35) }
.vr-btn-ghost{ background:rgba(255,255,255,.06); border:1px solid rgba(255,255,255,.12); color:#e5f0ff }
.vr-badge-dev{ font-size:11px; padding:4px 8px; border-radius:999px; background:rgba(45,212,191,.12); border:1px solid rgba(45,212,191,.35); color:#99f6e4; }
.vr-linklike{ color:#93c5fd; cursor:pointer; text-decoration:none; }
</style>

<script>
/* v-admin-session-details */
(function(){
  const DEV = /(^|\/\/)(localhost|127\.0\.0\.1)/i.test(location.href);

  function tok(){ return window.token || window.VAL_TOKEN || localStorage.getItem('vr_token') || ''; }
  function ref(){ return localStorage.getItem('vr_refresh') || ''; }

  function toast(msg, kind='ok', ms=1600){
    let box = document.getElementById('vr_toast');
    if(!box){ box=document.createElement('div'); box.id='vr_toast'; document.body.appendChild(box);
      box.style.cssText='position:fixed;right:16px;bottom:16px;z-index:9999;padding:10px 12px;border-radius:10px;display:none' }
    box.style.display='block';
    box.style.background = (kind==='err') ? 'rgba(239,68,68,.12)' : (kind==='warn' ? 'rgba(245,158,11,.12)' : 'rgba(16,185,129,.12)');
    box.style.border = '1px solid ' + ((kind==='err')?'rgba(239,68,68,.45)':(kind==='warn'?'rgba(245,158,11,.45)':'rgba(16,185,129,.45)'));
    box.style.color = (kind==='err')?'#fecaca':(kind==='warn'?'#fde68a':'#d1fae5');
    box.textContent = msg; clearTimeout(window.__vr_toast_t);
    window.__vr_toast_t = setTimeout(()=> box.style.display='none', ms);
  }

  function parseJWT(t){
    try{
      const [h,p,s] = t.split('.'); if(!p) return null;
      const b64 = p.replace(/-/g,'+').replace(/_/g,'/'); const pad='='.repeat((4-b64.length%4)%4);
      return JSON.parse(decodeURIComponent(atob(b64+pad).split('').map(c=>'%' + ('00'+c.charCodeAt(0).toString(16)).slice(-2)).join('')));
    }catch(e){ return null; }
  }
  function fmtExp(exp){
    if(!exp) return {eta:'?', local:'?'}; 
    const now = Math.floor(Date.now()/1000), left = exp-now;
    const m = Math.max(0, Math.floor(left/60)), s = Math.max(0, left%60);
    const dt = new Date(exp*1000);
    return { eta: (m?m+'m ':'')+s+'s', local: dt.toLocaleString() };
  }

  function ensureButtonAndPanel(){
    // add button to header actions
    const header = document.querySelector('.vr-header .vr-actions');
    if (!header || document.getElementById('vr_sess_btn')) return;
    const btn = document.createElement('button');
    btn.id='vr_sess_btn'; btn.className='vr-btn'; btn.textContent='Session';
    btn.style.background = '#22d3ee'; btn.style.boxShadow = '0 8px 22px rgba(34,211,238,.35)';
    header.prepend(btn);

    // create panel
    const panel = document.createElement('div');
    panel.id='vr_sess_pop'; panel.className='vr-sess-pop';
    panel.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center">
        <h3 style="margin:0">Session details</h3>
        ${DEV?'<span class="vr-badge-dev">dev only</span>':''}
      </div>
      <div id="vr_sess_body"></div>
      <div class="vr-sess-actions">
        ${DEV?'<button id="vr_copy_access" class="vr-btn-mini vr-btn-ghost">Copy access</button>':''}
        ${DEV?'<button id="vr_copy_refresh" class="vr-btn-mini vr-btn-ghost">Copy refresh</button>':''}
        <button id="vr_sess_refresh" class="vr-btn-mini vr-btn-act">Refresh</button>
        <button id="vr_sess_close"   class="vr-btn-mini vr-btn-ghost">Close</button>
      </div>
    `;
    document.body.appendChild(panel);

    btn.onclick = ()=> { renderPanel(); panel.style.display = (panel.style.display==='none'||!panel.style.display)?'block':'none'; };
    document.getElementById('vr_sess_close').onclick = ()=> panel.style.display='none';
    document.getElementById('vr_sess_refresh').onclick = doRefresh;

    if (DEV){
      document.getElementById('vr_copy_access').onclick  = ()=> navigator.clipboard.writeText(tok()).then(()=>toast('Access copied','ok'),()=>toast('Copy failed','err'));
      document.getElementById('vr_copy_refresh').onclick = ()=> navigator.clipboard.writeText(ref()).then(()=>toast('Refresh copied','ok'),()=>toast('Copy failed','err'));
    }
  }

  async function doRefresh(){
    try{
      const rId = ref(); if(!rId){ toast('No refresh token; sign in again','warn'); location.href='/auth/'; return; }
      const r = await fetch(`${BACKEND}/auth/refresh`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({refresh:rId})});
      if(!r.ok){ toast('Refresh failed','err'); location.href='/auth/'; return; }
      const j = await r.json();
      window.token = j.access; window.VAL_TOKEN = j.access; localStorage.setItem('vr_token', j.access);
      if (j.refresh) localStorage.setItem('vr_refresh', j.refresh);
      toast('Session refreshed','ok'); renderPanel(); updateHeaderBadge();
    }catch(e){ toast('Refresh error','err'); location.href='/auth/'; }
  }

  async function updateHeaderBadge(){
    try{
      const badge = document.getElementById('vr_header_badge'); if(!badge) return;
      const t = tok(); if(!t){ badge.textContent='Not signed'; return; }
      const r = await fetch(`${BACKEND}/auth/whoami`, { headers:{ Authorization:'Bearer '+t }});
      if(!r.ok){ badge.textContent='Token invalid'; return; }
      const j = await r.json(); const c = j.claims||{};
      badge.textContent = `${c.sub||'?'}  •  ${c.role||'user'}`;
    }catch(e){}
  }

  async function renderPanel(){
    const body = document.getElementById('vr_sess_body'); if(!body) return;
    const t = tok(); const p = parseJWT(t)||{};
    const iss = p.iss || '—', exp = p.exp || 0, role = p.role || 'user', scope = p.scope || {};
    const sub = p.sub || '—'; const {eta, local} = fmtExp(exp);
    const ua = navigator.userAgent;

    body.innerHTML = `
      <div class="vr-sess-row"><div class="vr-sess-k">Email</div><div class="vr-sess-v">${sub}</div></div>
      <div class="vr-sess-row"><div class="vr-sess-k">Role</div><div class="vr-sess-v">${role}</div></div>
      <div class="vr-sess-row"><div class="vr-sess-k">Scope</div><div class="vr-sess-v"><code>${escapeHTML(JSON.stringify(scope))}</code></div></div>
      <div class="vr-sess-row"><div class="vr-sess-k">Issuer</div><div class="vr-sess-v">${iss}</div></div>
      <div class="vr-sess-row"><div class="vr-sess-k">Expires</div><div class="vr-sess-v">${local}  <span style="opacity:.8">(~${eta})</span></div></div>
      <div class="vr-sess-row"><div class="vr-sess-k">Device</div><div class="vr-sess-v">${escapeHTML(ua)}</div></div>
      <div class="vr-sess-row"><div class="vr-sess-k">Refresh</div><div class="vr-sess-v">${ref()? 'available' : '—'}</div></div>
    `;
  }

  function escapeHTML(s){ return String(s).replace(/[&<>"']/g, m=>({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[m])); }

  document.addEventListener('DOMContentLoaded', ()=>{
    try{
      ensureButtonAndPanel();
    }catch(e){ console.error('session details inject error', e); }
  });
})();
</script>
"""

html = html.replace("</body></html>", inject + "\n</body></html>")
open(ADMIN, "w", encoding="utf-8").write(html)
print("Session details popover injected. Reload /admin (Ctrl+F5).")
