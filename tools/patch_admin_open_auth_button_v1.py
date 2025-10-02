import os, sys

ADMIN = os.path.join("frontend","admin","index.html")
if not os.path.exists(ADMIN):
    print("ERROR: frontend/admin/index.html not found")
    sys.exit(1)

html = open(ADMIN, "r", encoding="utf-8").read()

if "/* v-open-auth-portal */" in html:
    print("Open Auth Portal patch already injected.")
    sys.exit(0)

# Ensure BACKEND const exists (no-op if already present elsewhere)
if "const BACKEND" not in html:
    html = html.replace("<script>", "<script>\n  const BACKEND='http://127.0.0.1:8000';", 1)

inject = r"""
<!-- v-open-auth-portal -->
<script>
/* v-open-auth-portal */
(function(){
  function injectOpenAuth(){
    const loginBtn = document.getElementById('loginBtn');
    if(!loginBtn) return;
    const row = loginBtn.parentElement;
    if(!row || document.getElementById('open_auth_btn')) return;
    const a = document.createElement('a');
    a.id = 'open_auth_btn';
    a.textContent = 'Open Auth Portal';
    a.href = '/auth/';
    a.className = 'btn';
    a.style.marginLeft = '10px';
    row.appendChild(a);
  }

  function autoRedirectIfNoToken(){
    try{
      const tok = window.token || window.VAL_TOKEN || localStorage.getItem('vr_token') || '';
      if(!tok){
        // only redirect when user actually hits /admin/ landing and is not logged in
        // leave editors alone if they are already on a deep admin screen with UI open
        if (location.pathname.replace(/\/+$/,'') === '/admin'){
          setTimeout(()=>{ location.href = '/auth/'; }, 400);
        }
      }
    }catch(e){}
  }

  document.addEventListener('DOMContentLoaded', ()=>{
    injectOpenAuth();
    autoRedirectIfNoToken();
  });
})();
</script>
"""

html = html.replace("</body></html>", inject + "\n</body></html>")
open(ADMIN, "w", encoding="utf-8").write(html)
print("Injected 'Open Auth Portal' button and auto-redirect to /auth when no token.")
