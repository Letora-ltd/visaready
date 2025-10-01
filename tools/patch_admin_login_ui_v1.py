import os, sys

ADMIN = os.path.join("frontend","admin","index.html")

if not os.path.exists(ADMIN):
    print(f"ERROR: not found: {ADMIN}")
    sys.exit(1)

html = open(ADMIN, "r", encoding="utf-8").read()

# Ensure a BACKEND const exists (will not duplicate earlier definitions)
if "const BACKEND" not in html:
    html = html.replace("<script>", "<script>\n  const BACKEND='http://127.0.0.1:8000';", 1)

# Skip if already injected
if "/* v-admin-login-ui */" in html:
    print("Admin login UI patch already injected. Nothing to do.")
    sys.exit(0)

injection = r"""
<!-- v-admin-login-ui -->
<script>
/* v-admin-login-ui */
(function(){
  // ---- Helpers: token storage + whoami badge + logout ----
  function setAccessToken(tok, refresh){
    try {
      window.token = tok;
      window.VAL_TOKEN = tok;                // keep compatibility with existing admin code
      localStorage.setItem('vr_token', tok);
      if (refresh) localStorage.setItem('vr_refresh', refresh);
    } catch(e) { console.warn('token store failed', e); }
  }
  function getAccessToken(){
    return window.token || window.VAL_TOKEN || localStorage.getItem('vr_token') || '';
  }
  async function refreshAccessIfPossible(){
    const refresh = localStorage.getItem('vr_refresh');
    if (!refresh) return null;
    try{
      const r = await fetch(`${BACKEND}/auth/refresh`, {
        method: 'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ refresh })
      });
      if (!r.ok) return null;
      const j = await r.json();
      setAccessToken(j.access, j.refresh);
      return j.access;
    }catch(e){ return null; }
  }
  async function whoamiBadge(){
    try{
      const tok = getAccessToken();
      const barId = 'adm_badge';
      const ensure = ()=>{
        let bar = document.getElementById(barId);
        if (!bar){
          const main = document.querySelector('main.container');
          if (!main) return null;
          bar = document.createElement('div');
          bar.id = barId;
          bar.style.display='flex';
          bar.style.justifyContent='space-between';
          bar.style.alignItems='center';
          bar.style.margin='8px 0';
          bar.innerHTML = `
            <span class="small" id="adm_badge_text">Admin: (not signed)</span>
            <div style="display:flex;gap:8px;align-items:center;">
              <button class="btn" id="adm_logout_btn" style="padding:6px 10px;">Logout</button>
            </div>`;
          main.prepend(bar);
          const logoutBtn = document.getElementById('adm_logout_btn');
          logoutBtn.onclick = ()=>{
            localStorage.removeItem('vr_token');
            localStorage.removeItem('vr_refresh');
            window.token = null; window.VAL_TOKEN = null;
            document.getElementById('adm_badge_text').textContent = 'Admin: (not signed)';
          };
        }
        return bar;
      };
      const bar = ensure();
      if (!bar) return;
      const txt = document.getElementById('adm_badge_text');
      if (!tok){ txt.textContent = 'Admin: (not signed)'; return; }
      const r = await fetch(`${BACKEND}/auth/whoami`, { headers:{ Authorization: 'Bearer '+tok }});
      if (!r.ok){ txt.textContent = 'Admin: (token invalid)'; return; }
      const j = await r.json();
      const c = j.claims || {};
      txt.textContent = `Admin: ${c.sub||'?'}  |  Role: ${c.role||'?'} `;
    }catch(e){}
  }

  // ---- Upgrade authedFetch globally (401 -> refresh -> retry) ----
  (function ensureAuthedFetch(){
    const old = window.authedFetch;
    window.authedFetch = async function(url, options={}, relogin=true){
      const tok = getAccessToken();
      const headers = Object.assign({}, options.headers || {}, tok ? { 'Authorization':'Bearer '+tok } : {});
      let res = await fetch(url, Object.assign({}, options, { headers }));
      if (res.status === 401){
        const nt = await refreshAccessIfPossible();
        if (nt){
          const headers2 = Object.assign({}, options.headers || {}, { 'Authorization':'Bearer '+nt });
          res = await fetch(url, Object.assign({}, options, { headers: headers2 }));
        }
      }
      return res;
    };
    window.addEventListener('load', whoamiBadge);
  })();

  // ---- Inject Email field into "Admin Login" card + wire login to /auth/login ----
  function upgradeLoginCard(){
    // Find the Admin Login card - it contains #loginBtn and #password already in your page
    const btn = document.getElementById('loginBtn');
    const pwd = document.getElementById('password');
    if (!btn || !pwd) return;

    // If email input not present, inject it above password
    if (!document.getElementById('login_email')){
      const grid = btn.closest('section.card').querySelector('.grid');
      if (grid){
        const holder = document.createElement('div');
        holder.innerHTML = `<div class="label">Email</div><input id="login_email" type="email" placeholder="name@example.com">`;
        grid.prepend(holder);
      }
    }

    // Replace the click handler to call /auth/login
    btn.onclick = async ()=>{
      const email = (document.getElementById('login_email')||{}).value || '';
      const pass  = (document.getElementById('password')||{}).value || '';
      const msgEl = document.getElementById('loginMsg');

      if (!email || !pass){
        msgEl.textContent = 'Enter email and password.';
        return;
      }
      try{
        const r = await fetch(`${BACKEND}/auth/login`, {
          method:'POST',
          headers:{'Content-Type':'application/json'},
          body: JSON.stringify({ email, password: pass })
        });
        if (!r.ok){
          msgEl.textContent = 'Login failed: ' + (await r.text());
          return;
        }
        const j = await r.json();
        setAccessToken(j.access, j.refresh);
        msgEl.textContent = 'Logged in.';
        // show editor pane if hidden
        const editor = document.getElementById('editor');
        if (editor) editor.style.display = 'block';
        // re-render badge
        whoamiBadge();
        // if your code expects to call loadKeys() after login:
        if (typeof window.loadKeys === 'function') {
          try{ await window.loadKeys(); }catch(e){}
        }
      }catch(e){
        console.error(e); msgEl.textContent = 'Login failed.';
      }
    };
  }

  // ---- Ensure admin writes send X-Reason (optional) ----
  (function injectReasonHint(){
    const target = document.getElementById('validateCard');
    if (!target || document.getElementById('vr_reason')) return;
    const row = target.querySelector('div[style*="margin-top:10px;"]');
    if (!row) return;
    const wrap = document.createElement('label');
    wrap.style.display = 'inline-flex';
    wrap.style.alignItems = 'center';
    wrap.style.gap = '6px';
    wrap.style.marginLeft = '8px';
    wrap.innerHTML = `Reason: <input id="vr_reason" placeholder="optional" class="select" style="width:220px;">`;
    row.appendChild(wrap);

    // Monkey-patch fetch used by admin write actions to include X-Reason
    const _fetch = window.fetch.bind(window);
    window.fetch = async function(url, options){
      try{
        const reason = (document.getElementById('vr_reason')||{}).value || '';
        const opts = options || {};
        const headers = Object.assign({}, opts.headers || {}, reason ? { 'X-Reason': reason } : {});
        return await _fetch(url, Object.assign({}, opts, { headers }));
      }catch(e){
        return await _fetch(url, options);
      }
    };
  })();

  document.addEventListener('DOMContentLoaded', ()=>{
    upgradeLoginCard();
    // If a token was stored earlier, restore it now & refresh badge
    const t = localStorage.getItem('vr_token');
    if (t){ setAccessToken(t, localStorage.getItem('vr_refresh') || null); whoamiBadge(); }
  });
})();
</script>
"""

# Inject the script before </body>
html = html.replace("</body></html>", injection + "\n</body></html>")

open(ADMIN, "w", encoding="utf-8").write(html)
print("Admin email+password login patch injected. Reload /admin (Ctrl+F5).")
