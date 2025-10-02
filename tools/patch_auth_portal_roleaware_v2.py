import os, sys

AUTH_HTML = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")), "frontend", "auth", "index.html")
if not os.path.exists(AUTH_HTML):
    print("ERROR: frontend/auth/index.html not found"); sys.exit(1)

html = open(AUTH_HTML, "r", encoding="utf-8").read()
if "/* v-auth-roleaware-v2 */" in html:
    print("Auth portal role-aware patch already applied.")
    sys.exit(0)

inject = r"""
<!-- v-auth-roleaware-v2 -->
<script>
/* v-auth-roleaware-v2 */
(function(){
  const BACKEND = (typeof BACKEND!=='undefined') ? BACKEND : 'http://127.0.0.1:8000';
  function byId(id){ return document.getElementById(id); }
  function show(id,b=true){ const el=byId(id); if(!el) return; el.style.display=b?'':'none'; }
  function setText(id,txt){ const el=byId(id); if(!el) return; el.textContent=txt; }

  // Role-aware routing
  function routeForRole(role){
    const r = String(role||'user').toLowerCase();
    if (r==='super_admin' || r.endsWith('_admin')) return '/admin/';
    return '/'; // your app portal later (/app/)
  }

  // Patch post-login buttons to be role aware
  (function wireRoleAware(){
    const goAdmin = byId('pf_to_admin');
    const goApp = byId('pf_to_app');
    if (!goAdmin || !goApp) return;
    goAdmin.onclick = async ()=>{
      const tok = localStorage.getItem('vr_token');
      if(!tok){ location.href='/auth/'; return; }
      location.href = '/admin/';
    };
    goApp.onclick = ()=>{
      const tok = localStorage.getItem('vr_token');
      if(!tok){ location.href='/auth/'; return; }
      location.href = '/';
    };
  })();

  // Auto-redirect immediately after login based on role
  (function roleAutoRedirect(){
    const okEl = document.getElementById('si_ok');
    if(!okEl) return;
    const old = document.getElementById('btnSignIn').onclick;
    document.getElementById('btnSignIn').onclick = async ()=>{
      const email = byId('si_email').value.trim();
      const pass  = byId('si_password').value;
      setText('si_err',''); setText('si_ok',''); show('si_err',false); show('si_ok',false);
      if(!email || !pass){ setText('si_err','Enter email & password'); show('si_err'); return; }
      try{
        const r = await fetch(BACKEND+'/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email,password:pass})});
        if(!r.ok){ setText('si_err','Login failed: '+(await r.text())); show('si_err'); return; }
        const j = await r.json();
        window.token = j.access; window.VAL_TOKEN = j.access;
        localStorage.setItem('vr_token', j.access);
        if(j.refresh) localStorage.setItem('vr_refresh', j.refresh);
        // whoami and route
        const w = await fetch(BACKEND+'/auth/whoami',{headers:{Authorization:'Bearer '+j.access}});
        const cj = await w.json(); const claims = cj.claims||{};
        setText('si_ok','Welcome back'); show('si_ok');
        // hydrate profile pane
        const pfe = byId('pf_email'); const pfr = byId('pf_role'); const pfs = byId('pf_scope');
        if (pfe) pfe.value = claims.sub||''; if (pfr) pfr.value = claims.role||''; if (pfs) pfs.value = JSON.stringify(claims.scope||{});
        // role-aware redirect (you can comment next line if you prefer to stay on profile)
        setTimeout(()=>{ location.href = routeForRole(claims.role); }, 600);
      }catch(e){ setText('si_err','Network error'); show('si_err'); }
    };
  })();

  // Forgot password flow (two-step modal: request -> confirm)
  (function forgotFlow(){
    const link = document.getElementById('si_forgot');
    if(!link) return;

    // Build modal
    const modal = document.createElement('div');
    modal.id = 'vr_forgot_modal';
    modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.45);display:none;z-index:9999;align-items:center;justify-content:center;';
    modal.innerHTML = `
      <div style="width:95%;max-width:520px;background:rgba(17,25,40,.95);border:1px solid rgba(255,255,255,.08);border-radius:16px;padding:20px;box-shadow:0 20px 60px rgba(0,0,0,.45)">
        <h3 style="margin:0 0 8px 0">Reset your password</h3>
        <div id="vr_step1">
          <div class="row"><label>Email</label><input id="vr_fp_email" type="email" placeholder="you@example.com"></div>
          <div class="helper"><span class="small">We’ll generate a one-time reset token (dev mode: shown here).</span></div>
          <div style="display:flex;gap:8px;margin-top:10px;">
            <button id="vr_fp_request" class="btn">Send reset</button>
            <button id="vr_fp_close" class="btn" style="background:#94a3b8">Close</button>
          </div>
          <div id="vr_fp_msg" class="ok" style="display:none"></div>
          <div id="vr_fp_err" class="error" style="display:none"></div>
        </div>
        <hr style="opacity:.15;margin:16px 0;">
        <div id="vr_step2">
          <div class="row"><label>Reset token</label><input id="vr_fp_token" placeholder="paste the token"></div>
          <div class="row"><label>New password</label><input id="vr_fp_new" type="password" placeholder="at least 12 chars"></div>
          <div class="helper"><span class="small">After reset, all sessions will be logged out.</span></div>
          <div style="display:flex;gap:8px;margin-top:10px;">
            <button id="vr_fp_confirm" class="btn">Reset password</button>
          </div>
          <div id="vr_fp_done" class="ok" style="display:none"></div>
          <div id="vr_fp_err2" class="error" style="display:none"></div>
        </div>
      </div>`;
    document.body.appendChild(modal);

    link.onclick = (e)=>{ e.preventDefault(); modal.style.display='flex'; };

    document.getElementById('vr_fp_close').onclick = ()=>{ modal.style.display='none'; };

    document.getElementById('vr_fp_request').onclick = async ()=>{
      const email = (document.getElementById('vr_fp_email')||{}).value||'';
      const msg = document.getElementById('vr_fp_msg'); const err = document.getElementById('vr_fp_err');
      msg.style.display='none'; err.style.display='none';
      if(!email){ err.textContent='Enter email'; err.style.display=''; return; }
      try{
        const r = await fetch(BACKEND+'/auth/request_reset',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email})});
        const j = await r.json();
        msg.textContent = j.dev_token ? ('Token (dev): '+j.dev_token) : 'If the account exists, a reset link was sent.';
        msg.style.display=''; 
      }catch(e){ err.textContent='Failed'; err.style.display=''; }
    };

    document.getElementById('vr_fp_confirm').onclick = async ()=>{
      const token = (document.getElementById('vr_fp_token')||{}).value||'';
      const newp  = (document.getElementById('vr_fp_new')||{}).value||'';
      const ok = document.getElementById('vr_fp_done'); const er2 = document.getElementById('vr_fp_err2');
      ok.style.display='none'; er2.style.display='none';
      if(!token || !newp){ er2.textContent='Provide token and new password'; er2.style.display=''; return; }
      try{
        const r = await fetch(BACKEND+'/auth/reset_password',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token, new_password:newp})});
        if(!r.ok){ er2.textContent='Reset failed: '+(await r.text()); er2.style.display=''; return; }
        ok.textContent='Password changed. Please sign in again.'; ok.style.display='';
      }catch(e){ er2.textContent='Failed'; er2.style.display=''; }
    };
  })();

  // Switch account (force login)
  (function addSwitchAccountToProfile(){
    const pf = document.getElementById('paneProfile');
    if(!pf) return;
    let btn = document.getElementById('pf_switch');
    if(!btn){
      btn = document.createElement('button');
      btn.id='pf_switch';
      btn.className='btn';
      btn.style.background='#fbbf24';
      btn.style.boxShadow='0 12px 28px rgba(251,191,36,.35)';
      btn.textContent='Switch account';
      const helper = pf.querySelector('.helper');
      if(helper) helper.appendChild(btn);
      btn.onclick = ()=>{
        localStorage.removeItem('vr_token'); localStorage.removeItem('vr_refresh');
        window.token=null; window.VAL_TOKEN=null;
        location.href = '/auth/';  // always require login
      };
    }
  })();
})();
</script>
"""

html = html.replace("</body>\n</html>", inject + "\n</body>\n</html>")
open(AUTH_HTML, "w", encoding="utf-8").write(html)
print("Auth portal patched: role-aware redirect, forgot password modal, switch account.")
