/* ═══════════════════════════════════════════════════════════════════════════
   Axula — theme.js  (v2 — lógica pura, sin inyección de DOM)
   El widget HTML está en cada template directamente.
   ─────────────────────────────────────────────────────────────────────────
   API pública:
     setTheme('light' | 'dark' | 'auto')
     getTheme()
   Auto: claro 6:00–18:59, oscuro el resto. Re-evalúa cada minuto.
   ═══════════════════════════════════════════════════════════════════════════ */
(function () {
  'use strict';
  var KEY       = 'axula_theme';
  var DAY_START = 6;
  var DAY_END   = 19;

  function resolveAuto() {
    var h = new Date().getHours();
    return (h >= DAY_START && h < DAY_END) ? 'light' : 'dark';
  }
  function saved() {
    try { return localStorage.getItem(KEY) || 'auto'; } catch(e) { return 'auto'; }
  }
  function persist(v) {
    try { localStorage.setItem(KEY, v); } catch(e) {}
  }
  function apply(pref) {
    var resolved = (pref === 'auto') ? resolveAuto() : pref;
    document.documentElement.setAttribute('data-theme', resolved);
    syncUI(pref);
  }
  function syncUI(pref) {
    document.querySelectorAll('[data-mt]').forEach(function(btn) {
      btn.classList.toggle('theme-btn-active', btn.getAttribute('data-mt') === pref);
    });
  }
  window.setTheme = function(pref) { persist(pref); apply(pref); };
  window.getTheme = function() { return saved(); };

  /* Aplicar antes del primer paint */
  apply(saved());

  document.addEventListener('DOMContentLoaded', function() {
    syncUI(saved());
    setInterval(function() { if (saved() === 'auto') apply('auto'); }, 60000);
  });
})();
