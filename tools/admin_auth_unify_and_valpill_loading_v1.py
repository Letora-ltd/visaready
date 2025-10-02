import os, sys

ADMIN = os.path.join("frontend","admin","index.html")
if not os.path.exists(ADMIN):
    print("ERROR: frontend/admin/index.html not found")
    sys.exit(1)

html = open(ADMIN, "r", encoding="utf-8").read()
if "/* v-admin-auth-unify-v1 */" in html:
    print("Auth unify + loading pill already injected.")
    sys.exit(0)

# make sure BACKEND const exists (no-op if already present)
if "const BACKEND" not in html:
    html = html.replace("<script>", "<script>\n  const BACKEND='http://127.0.0.1:8000';", 1)

inject = r"""
<!-- v-admin-auth-unify -->
<style>
/* loading state for validation pill */
.vr-pill.load {
  background: rgba(59,130,246,.12); border-color: rgba(59,130,246,.45); color: #bfdbfe;
}
.vr-pill .vr-spin {
  width:12px; height:12px; display:inline-block; margin-left:8px; border-radius:999px;
  border:2px solid rgba(255,255,255,.35); border-top-color: rgba(59,130,246,1);
  animation: vr_spin 0.8s linear infinite; vertical-align: -2px;
}
@keyframes vr_spin { to { transform: rotate(360deg); } }
</style>

<script>
/* v-admin-auth-unify-v1 */
(function(){
  // --------- helpers ----------
  function getAccess(){ return window.token || window.VAL_TOKEN || localStorage.getItem('vr_token') || ''; }
  function ensureSignedIn(){
    if (!getAccess()){
      // redirect to Auth portal; force login
      if (location.pathname.replace(/\/+$/,'') === '/admin') {
        setTimeout(()=>{ location.href = '/auth/'; }, 300);
      }
      return false;
    }
    return true;
  }
  function toast(msg, kind='ok', ms=1600){
    let box = document.getElementById('vr_toast');
    if(!box){
      box = document.createElement('div'); box.id='vr_toast';
      box.style.cssText='position:fixed;right:16px;bottom:16px;z-index:9999;padding:10px 12px;border-radius:10px;display:none';
      document.body.appendChild(box);
    }
    box.style.display='block';
    box.style.background = (kind==='err') ? 'rgba(239,68,68,.12)' : (kind==='warn' ? 'rgba(245,158,11,.12)' : 'rgba(16,185,129,.12)');
    box.style.border = '1px solid ' + ((kind==='err')?'rgba(239,68,68,.45)':(kind==='warn'?'rgba(245,158,11,.45)':'rgba(16,185,129,.45)'));
    box.style.color = (kind==='err')?'#fecaca':(kind==='warn'?'#fde68a':'#d1fae5');
    box.textContent = msg;
    clearTimeout(window.__vr_toast_t);
    window.__vr_toast_t = setTimeout(()=> box.style.display='none', ms);
  }
  function addAuthToFetch(){
    // augment fetch to add Authorization if missing; preserve existing X-Reason patch
    const _fetch = window.fetch.bind(window);
    window.fetch = async function(url, options){
      const opts = options || {};
      const headers = Object.assign({},
        opts.headers || {},
        !('Authorization' in (opts.headers||{})) && getAccess() ? { 'Authorization': 'Bearer ' + getAccess() } : {}
      );
      return _fetch(url, Object.assign({}, opts, { headers }));
    };
  }

  // --------- remove per-tool passwords; force token -----------
  function hideLegacyPasswordRows(){
    ['ie_pwd','dup_pwd','bdup_pwd','val_pwd'].forEach(id=>{
      const el = document.getElementById(id);
      if(el){
        const row = el.closest('.grid') || el.parentElement;
        // hide input only
        el.type = 'password';
        el.value = '';
        el.placeholder = '(using Auth token)';
        el.disabled = true;
        el.style.opacity = .45;
      }
    });
  }
  function overrideLegacyLoginFns(){
    const t = getAccess();
    if (!t) return;

    // Override per-tool login functions to simply return the access token
    window.ie_login = async ()=> (window.IE_TOKEN = getAccess());
    window.dup_login = async ()=> (window.DUP_TOKEN = getAccess());
    window.bdup_login = async ()=> (window.BDUP_TOKEN = getAccess());
    window.val_login = async ()=> (window.VAL_TOKEN = getAccess());

    // Also set the tokens now for immediate use
    window.IE_TOKEN = t; window.DUP_TOKEN = t; window.BDUP_TOKEN = t; window.VAL_TOKEN = t;
  }

  // --------- validation pill loading state ----------
  function pill(){ return document.getElementById('vr_val_pill'); }
  function setPillLoading(isLoading, label){
    const p = pill(); if(!p) return;
    p.classList.remove('ok','warn');
    if(isLoading){
      p.classList.add('load');
      p.textContent = (label || 'Running…');
      const spin = document.createElement('span'); spin.className='vr-spin';
      p.appendChild(spin);
    } else {
      p.classList.remove('load');
    }
  }
  function wirePillLoading(){
    const dry = document.getElementById('val_dry_btn');
    const run = document.getElementById('val_btn');
    if(dry && !dry.__vr_patched){
      const old = dry.onclick;
      dry.onclick = (e)=>{
        setPillLoading(true, 'Dry-run…');
        if(old) old.call(dry, e);
        setTimeout(()=> setPillLoading(false), 1800);
      };
      dry.__vr_patched = true;
    }
    if(run && !run.__vr_patched){
      const old = run.onclick;
      run.onclick = (e)=>{
        setPillLoading(true, 'Validating…');
        if(old) old.call(run, e);
        setTimeout(()=> setPillLoading(false), 1500);
      };
      run.__vr_patched = true;
    }
  }

  document.addEventListener('DOMContentLoaded', ()=>{
    try{
      if (!ensureSignedIn()) return;
      addAuthToFetch();          // Authorization auto-added
      hideLegacyPasswordRows();  // visually deprecate per-tool password inputs
      overrideLegacyLoginFns();  // IE/VAL/DUP/BDUP -> access token
      wirePillLoading();         // loading state on pill
      toast('Admin now uses Auth token (no per-tool passwords).','ok', 1600);
    }catch(e){ console.error('auth-unify patch error', e); }
  });
})();
</script>
"""

html = html.replace("</body></html>", inject + "\n</body></html>")
open(ADMIN, "w", encoding="utf-8").write(html)
print("Auth unify + validation loading pill injected. Reload /admin (Ctrl+F5).")
