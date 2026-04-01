// static/js/cookie-consent-compact.js
(function(){
  const COOKIE_NAME = 'cookie_consent_v2';
  const EXPIRE_DAYS = 365;

  function setCookie(name, value, days){
    let expires = '';
    if (days){
      const d = new Date(); d.setTime(d.getTime() + days*24*60*60*1000);
      expires = '; expires=' + d.toUTCString();
    }
    document.cookie = name + '=' + encodeURIComponent(value) + expires + '; path=/; SameSite=Lax';
  }
  function getCookie(name){
    const m = document.cookie.match('(?:^|; )' + name + '=([^;]*)');
    return m ? decodeURIComponent(m[1]) : null;
  }
  function eraseCookie(name){ document.cookie = name + '=; Max-Age=-99999999; path=/'; }

  const defaultPrefs = { necessary:true, analytics:false };

  function readPrefs(){
    try { const raw = getCookie(COOKIE_NAME); return raw ? JSON.parse(raw) : null; } catch(e){ return null; }
  }
  function savePrefs(p){
    setCookie(COOKIE_NAME, JSON.stringify(p), EXPIRE_DAYS);
    if (p.analytics) loadAnalyticsScripts(); else removeAnalyticsCookies();
  }

  function removeAnalyticsCookies(){
    const names = ['_ga','_gid','_gat','_gcl_au','_ym_uid','_ym_d'];
    document.cookie.split(';').forEach(c => {
      const name = c.split('=')[0].trim();
      if (!name) return;
      if (names.includes(name) || name.indexOf('_ga')===0 || name.indexOf('_gid')===0) eraseCookie(name);
    });
  }

  function loadAnalyticsScripts(){
    document.querySelectorAll('script[data-consent="analytics"]').forEach(s=>{
      if (s.dataset.ccLoaded) return;
      const src = s.dataset.src || s.src;
      if (src){
        const ns = document.createElement('script');
        ns.src = src;
        ns.async = true;
        ns.onload = ()=>{ s.dataset.ccLoaded = '1'; };
        document.head.appendChild(ns);
      } else if (s.dataset.inline === '1' && s.textContent.trim()){
        try { (new Function(s.textContent))(); s.dataset.ccLoaded = '1'; } catch(e){ console.error(e); }
      }
    });
  }

  // UI
  document.addEventListener('DOMContentLoaded', function(){
    const banner = document.getElementById('ccBanner');
    const acceptBtn = document.getElementById('ccAcceptBtn');
    const rejectBtn = document.getElementById('ccRejectBtn');

    const stored = readPrefs();
    if (stored){
      if (stored.analytics) loadAnalyticsScripts();
      if (banner) banner.style.display = 'none';
    } else {
      if (banner) banner.style.display = 'flex';
    }

    if (acceptBtn) acceptBtn.addEventListener('click', function(){
      const prefs = { necessary:true, analytics:true };
      savePrefs(prefs);
      if (banner) banner.style.display = 'none';
    });

    if (rejectBtn) rejectBtn.addEventListener('click', function(){
      const prefs = { necessary:true, analytics:false };
      savePrefs(prefs);
      if (banner) banner.style.display = 'none';
    });

    // page settings form (if exists)
    const form = document.getElementById('cookieSettingsForm');
    if (form){
      // init
      const prefs = readPrefs() || defaultPrefs;
      const analyticsEl = form.querySelector('[name="analytics"]');
      if (analyticsEl) analyticsEl.checked = !!prefs.analytics;

      const saveBtn = document.getElementById('cookieSaveBtn');
      if (saveBtn) saveBtn.addEventListener('click', function(){
        const analyticsChecked = !!analyticsEl.checked;
        const p = { necessary:true, analytics: analyticsChecked };
        savePrefs(p);
        alert('Настройки сохранены');
      });
    }

    // expose simple API
    window.CookieConsent = {
      getPreferences: () => readPrefs() || defaultPrefs,
      openSettings: () => { window.location.href = '/cookie-settings/'; }
    };
  });
})();