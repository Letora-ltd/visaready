import os, sys

ADMIN = os.path.join("frontend","admin","index.html")
if not os.path.exists(ADMIN):
    print("ERROR: frontend/admin/index.html not found")
    sys.exit(1)

html = open(ADMIN, "r", encoding="utf-8").read()
if "/* v-admin-session-palette-enhance */" in html:
    print("Session palette enhance already injected.")
    sys.exit(0)

# Ensure BACKEND const (no-op if already present earlier)
if "const BACKEND" not in html:
    html = html.replace("<script>", "<script>\n  const BACKEND='http://127.0.0.1:8000';", 1)

inject = r"""
<!-- v-admin-session-palette-enhance -->
<script>
/* v-admin-session-palette-enhance */
(function(){
  const AUTH_PATH = '/auth/';
  function tok(){ return window.token || window.VAL_TOKEN || localStorage.getItem('vr_token') || ''; }
  function ref(){ return localStorage.getItem('vr_refresh') || ''; }
  function toast(msg, kind='ok', ms=1500){
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
    clearTimeout(window.__vr_toast_t); window.__vr_toast_t=setTimeout(()=>{box.style.display='none'}, ms);
  }

  // Open session panel (works with your session popover patch; otherwise creates a minimal panel)
  function toggleSession(){
    let btn = document.getElementById('vr_sess_btn');
    let panel = document.getElementById('vr_sess_pop');
    if (!btn || !panel){
      // Minimal fallback panel
      if (!panel){
        panel = document.createElement('div');
        panel.id='vr_sess_pop';
        panel.style.cssText='position:fixed;right:18px;top:70px;z-index:120;width:min(92vw,520px);display:none;background:rgba(17,25,40,.95);border:1px solid rgba(255,255,255,.08);border-radius:16px;padding:14px;box-shadow:0 20px 60px rgba(0,0,0,.45);color:#dbeafe';
        panel.innerHTML = '<h3 style="margin:0 0 8px 0">Session details</h3><div class="small" style="opacity:.8">Use the Auth portal to sign in.</div>';
        document.body.appendChild(panel);
      }
      panel.style.display = (panel.style.display==='none'||!panel.style.display) ? 'block' : 'none';
      return;
    }
    btn.click(); // uses full Session popover logic if present
  }

  async function doRefresh(){
    try{
      const rid = ref();
      if(!rid){ toast('No refresh token; sign in again','warn'); location.href = AUTH_PATH; return; }
      const r = await fetch(`${BACKEND}/auth/refresh`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ refresh: rid }) });
      if(!r.ok){ toast('Refresh failed','err'); location.href = AUTH_PATH; return; }
      const j = await r.json();
      window.token = j.access; window.VAL_TOKEN = j.access; localStorage.setItem('vr_token', j.access);
      if (j.refresh) localStorage.setItem('vr_refresh', j.refresh);
      toast('Session refreshed','ok');
      // Update header badge if present
      try{
        const badge = document.getElementById('vr_header_badge');
        if(badge){
          const wr = await fetch(`${BACKEND}/auth/whoami`, { headers:{ Authorization:'Bearer '+j.access }});
          if (wr.ok) { const cj = await wr.json(); const c = cj.claims||{}; badge.textContent = `${c.sub||'?'}  •  ${c.role||'user'}`; }
        }
      }catch(_){}
    }catch(e){
      toast('Refresh error','err'); location.href = AUTH_PATH;
    }
  }

  function doLogout(){
    localStorage.removeItem('vr_token'); localStorage.removeItem('vr_refresh');
    window.token = null; window.VAL_TOKEN = null;
    location.href = AUTH_PATH;
  }

  // Add or extend palette registry
  if (!window.__vr_cmd_extend) window.__vr_cmd_extend = [];
  const reg = window.__vr_cmd_extend;
  const add = (k, a)=>{
    if (!reg.some(x => x && x.k === k)){
      reg.push({ k, a });
    }
  };
  add('Session: Show details', toggleSession);
  add('Session: Refresh token', doRefresh);
  add('Session: Logout', doLogout);

  // Rebuild palette if commandPalette builder exists
  if (typeof window.commandPalette === 'function'){
    try{ window.commandPalette(); }catch(_){}
  }

  // Prefill palette with "session" when Ctrl+Shift+S is pressed
  if (!window.__vr_prefill_session_bound){
    window.__vr_prefill_session_bound = true;
    window.addEventListener('keydown', (e)=>{
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === 's'){
        e.preventDefault();
        // Trigger the palette (same as Ctrl+K) then prefill 'session'
        const ke = new KeyboardEvent('keydown', { key:'k', ctrlKey: true, metaKey: e.metaKey });
        window.dispatchEvent(ke);
        // Fill input after it renders
        setTimeout(()=>{
          const inp = document.getElementById('vr_k_input');
          if (inp){
            inp.value = 'session';
            inp.dispatchEvent(new Event('input', {bubbles:true}));
            inp.focus();
            inp.select();
          } else {
            // no palette → fall back to toggling session panel
            toggleSession();
          }
        }, 80);
      }
    }, true);
  }
})();
</script>
"""

html = html.replace("</body></html>", inject + "\n</body></html>")
open(ADMIN, "w", encoding="utf-8").write(html)
print("Session palette enhance injected. Reload /admin (Ctrl+F5).")
