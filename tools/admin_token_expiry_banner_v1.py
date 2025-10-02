import os, sys

ADMIN = os.path.join("frontend","admin","index.html")
if not os.path.exists(ADMIN):
    print("ERROR: frontend/admin/index.html not found")
    sys.exit(1)

html = open(ADMIN, "r", encoding="utf-8").read()
if "/* v-admin-expiry-banner */" in html:
    print("Token expiry banner already injected.")
    sys.exit(0)

# Ensure BACKEND const exists (no-op if already in file)
if "const BACKEND" not in html:
    html = html.replace("<script>", "<script>\n  const BACKEND='http://127.0.0.1:8000';", 1)

inject = r"""
<!-- v-admin-expiry-banner -->
<style>
.vr-expiry {
  position: sticky; top: 0; z-index: 120;
  display:none; align-items:center; justify-content:space-between; gap:10px;
  padding:10px 12px; margin:0;
  background: rgba(59,130,246,.12);
  border-bottom: 1px solid rgba(59,130,246,.35);
  color: #dbeafe; backdrop-filter: blur(6px);
}
.vr-expiry .vr-row {display:flex; gap:10px; align-items:center; flex-wrap:wrap}
.vr-expiry .vr-btn {
  padding:8px 10px; border:none; border-radius:10px; font-weight:700; cursor:pointer;
  background:#60a5fa; color:#07121f; box-shadow:0 8px 22px rgba(96,165,250,.35);
}
.vr-expiry .vr-ghost {
  background:rgba(255,255,255,.06); border:1px solid rgba(255,255,255,.12); color:#e5f0ff;
}
</style>

<script>
/* v-admin-expiry-banner */
(function(){
  const CHECK_MS = 15000;          // 15s
  const SOON_SECONDS = 180;         // < 3 min -> warn
  const AUTH_PATH = '/auth/';

  function token(){ return window.token || window.VAL_TOKEN || localStorage.getItem('vr_token') || ''; }
  function refreshId(){ return localStorage.getItem('vr_refresh') || ''; }

  // Minimal toast (reuse if exists)
  function toast(msg, kind='ok', ms=1600){
    let box = document.getElementById('vr_toast');
    if(!box){
      box = document.createElement('div'); box.id='vr_toast'; document.body.appendChild(box);
      box.style.cssText='position:fixed;right:16px;bottom:16px;z-index:9999;padding:10px 12px;border-radius:10px;display:none';
    }
    box.style.display='block';
    box.style.background = (kind==='err') ? 'rgba(239,68,68,.12)' : (kind==='warn' ? 'rgba(245,158,11,.12)' : 'rgba(16,185,129,.12)');
    box.style.border = '1px solid ' + ((kind==='err')?'rgba(239,68,68,.45)':(kind==='warn'?'rgba(245,158,11,.45)':'rgba(16,185,129,.45)'));
    box.style.color = (kind==='err')?'#fecaca':(kind==='warn'?'#fde68a':'#d1fae5');
    box.textContent = msg;
    clearTimeout(window.__vr_toast_t);
    window.__vr_toast_t = setTimeout(()=> box.style.display='none', ms);
  }

  // Base64URL -> JSON payload parser for JWT
  function parseJwtPayload(t){
    try{
      const parts = t.split('.'); if(parts.length<2) return null;
      const b64 = parts[1].replace(/-/g,'+').replace(/_/g,'/');
      const pad = '='.repeat((4 - b64.length % 4) % 4);
      const json = decodeURIComponent(atob(b64 + pad).split('').map(c=>'%' + ('00'+c.charCodeAt(0).toString(16)).slice(-2)).join(''));
      return JSON.parse(json);
    }catch(e){ return null; }
  }

  // Banner DOM
  function ensureBanner(){
    if (document.getElementById('vr_expiry')) return document.getElementById('vr_expiry');
    const bar = document.createElement('div');
    bar.id = 'vr_expiry';
    bar.className = 'vr-expiry';
    bar.innerHTML = `
      <div class="vr-row">
        <strong>Session: token expiring soon</strong>
        <span id="vr_expiry_eta" style="opacity:.85"></span>
      </div>
      <div class="vr-row">
        <button id="vr_expiry_refresh" class="vr-btn">Refresh now</button>
        <button id="vr_expiry_logout" class="vr-btn vr-ghost">Logout</button>
      </div>`;
    // put banner just under our header (if exists), else at top of body
    const header = document.querySelector('.vr-header');
    if (header && header.parentNode) header.parentNode.insertBefore(bar, header.nextSibling);
    else document.body.prepend(bar);
    document.getElementById('vr_expiry_refresh').onclick = doRefresh;
    document.getElementById('vr_expiry_logout').onclick = ()=>{
      localStorage.removeItem('vr_token'); localStorage.removeItem('vr_refresh');
      window.token=null; window.VAL_TOKEN=null;
      location.href = AUTH_PATH;
    };
    return bar;
  }

  async function doRefresh(){
    try{
      const rid = refreshId();
      if(!rid){ toast('No refresh token; please sign in again','warn'); location.href = AUTH_PATH; return; }
      const r = await fetch(`${BACKEND}/auth/refresh`, {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ refresh: rid })
      });
      if(!r.ok){ toast('Refresh failed','err'); location.href = AUTH_PATH; return; }
      const j = await r.json();
      // store tokens
      window.token = j.access; window.VAL_TOKEN = j.access;
      localStorage.setItem('vr_token', j.access);
      if (j.refresh) localStorage.setItem('vr_refresh', j.refresh);
      toast('Session refreshed','ok');
      // recompute
      checkExpiry(true);
      // update header badge if present
      updateHeaderBadge();
    }catch(e){
      toast('Refresh error','err');
      location.href = AUTH_PATH;
    }
  }

  // Optional: refresh header badge
  async function updateHeaderBadge(){
    try{
      const badge = document.getElementById('vr_header_badge'); if(!badge) return;
      const t = token(); if(!t){ badge.textContent = 'Not signed'; return; }
      const r = await fetch(`${BACKEND}/auth/whoami`, { headers:{ Authorization:'Bearer '+t }});
      if(!r.ok){ badge.textContent='Token invalid'; return; }
      const j = await r.json(); const c = j.claims||{};
      badge.textContent = `${c.sub||'?'}  •  ${c.role||'user'}`;
    }catch(e){}
  }

  function fmtSeconds(s){
    if (s <= 0) return 'expired';
    const m = Math.floor(s/60), sec = s%60;
    return (m?m+'m ':'') + sec + 's';
  }

  function checkExpiry(forceUpdate=false){
    const t = token();
    const bar = ensureBanner();
    if(!t){ bar.style.display='flex'; document.getElementById('vr_expiry_eta').textContent = 'expired'; return; }
    const payload = parseJwtPayload(t);
    if(!payload || !payload.exp){ bar.style.display='flex'; document.getElementById('vr_expiry_eta').textContent = 'unknown'; return; }
    const now = Math.floor(Date.now()/1000);
    const remain = payload.exp - now;
    if (remain <= SOON_SECONDS){
      bar.style.display='flex';
      document.getElementById('vr_expiry_eta').textContent = `~${fmtSeconds(Math.max(remain,0))} left`;
    }else{
      // hide unless forced to show after refresh
      bar.style.display = forceUpdate ? 'flex' : 'none';
      if (forceUpdate){
        document.getElementById('vr_expiry_eta').textContent = `~${fmtSeconds(remain)} left`;
      }
    }
  }

  // Re-check on certain admin actions (validation / save etc.)
  function wireActionRechecks(){
    ['ie_saveBtn','val_btn','val_dry_btn','val_fix_btn','dup_btn','bdup_btn'].forEach(id=>{
      const el = document.getElementById(id);
      if(!el || el.__vr_exp_recheck) return;
      const old = el.onclick;
      el.onclick = (e)=>{ if(old) old.call(el, e); setTimeout(()=> checkExpiry(), 400); };
      el.__vr_exp_recheck = true;
    });
  }

  document.addEventListener('DOMContentLoaded', ()=>{
    try{
      ensureBanner();
      checkExpiry(true);                // initial
      wireActionRechecks();
      setInterval(checkExpiry, CHECK_MS);
    }catch(e){ console.error('expiry banner inject error', e); }
  });
})();
</script>
"""

html = html.replace("</body></html>", inject + "\n</body></html>")
open(ADMIN, "w", encoding="utf-8").write(html)
print("Token expiry banner injected. Reload /admin (Ctrl+F5).")
