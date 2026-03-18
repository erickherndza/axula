/* ═══════════════════════════════════════════════════════════════════════════
   MultimediaTrack — Motor de Temas
   ☀️  Día   (7:00 am – 7:00 pm)  →  [data-theme="light"]
   🌙  Noche (7:00 pm – 7:00 am)  →  [data-theme="dark"]
   🕐  Auto  (detecta hora automáticamente, con override manual)
   ═══════════════════════════════════════════════════════════════════════════ */
(function () {
  'use strict';

  var HORA_DIA_INICIO = 7;
  var HORA_DIA_FIN    = 19;
  var STORAGE_KEY     = 'mt_theme_pref';  // 'light' | 'dark' | 'auto'
  var CHECK_INTERVAL  = 60 * 1000;

  /* ── HELPERS ── */
  function getHora()       { return new Date().getHours(); }
  function temaSegunHora() { var h = getHora(); return (h >= HORA_DIA_INICIO && h < HORA_DIA_FIN) ? 'light' : 'dark'; }
  function getPref()       { try { return localStorage.getItem(STORAGE_KEY) || 'auto'; } catch(e) { return 'auto'; } }
  function setPref(v)      { try { localStorage.setItem(STORAGE_KEY, v); } catch(e) {} }
  function temaActivo()    { var p = getPref(); return p === 'auto' ? temaSegunHora() : p; }

  /* ── APLICAR ── */
  function aplicarTema(tema, notif) {
    var prev = document.documentElement.getAttribute('data-theme');
    document.documentElement.setAttribute('data-theme', tema);
    sincronizarBotones(tema);
    actualizarBadge();
    if (notif && prev && prev !== tema) {
      var msg = tema === 'light' ? '☀️ Tema claro activado' : '🌙 Tema oscuro activado';
      if (typeof tk === 'function') tk(msg, 'info');
    }
  }

  /* ── SINCRONIZAR TODOS LOS BOTONES DE TOGGLE EN CUALQUIER PÁGINA ── */
  function sincronizarBotones(tema) {
    var pref = getPref();
    document.querySelectorAll('[data-theme-btn]').forEach(function(btn) {
      var val = btn.getAttribute('data-theme-btn');
      var activo = (val === pref) || (val === tema && pref === 'auto');
      btn.classList.toggle('theme-btn-active', activo);
    });
    // Texto del botón auto
    document.querySelectorAll('[data-theme-btn="auto"]').forEach(function(btn) {
      var esHoraDia = getHora() >= HORA_DIA_INICIO && getHora() < HORA_DIA_FIN;
      btn.textContent = '🕐 Auto (' + (esHoraDia ? '☀️' : '🌙') + ')';
    });
  }

  function actualizarBadge() {
    document.querySelectorAll('.theme-time-badge').forEach(function(el) {
      var pref = getPref();
      var now  = new Date();
      if (pref === 'auto') {
        el.textContent = now.getHours() + ':' + ('0'+now.getMinutes()).slice(-2);
        el.title = 'Automático según hora';
      } else {
        el.textContent = pref === 'light' ? '☀️' : '🌙';
        el.title = 'Manual — click Auto para restaurar';
      }
    });
  }

  /* ── API PÚBLICA ── */
  window.mtSetTema = function(valor) {
    setPref(valor);
    aplicarTema(valor === 'auto' ? temaSegunHora() : valor, false);
  };

  /* ── INYECCIÓN DEL TOGGLE ──
     Busca el primer contenedor de la derecha del nav en cualquier página.
     Soporta: .nav-right, .nav-r, .nav-links (último elemento), <nav> directo.
  ── */
  function buildToggleHTML() {
    var pref = getPref();
    var h    = getHora();
    var esDia = h >= HORA_DIA_INICIO && h < HORA_DIA_FIN;

    return (
      '<div class="mt-theme-toggle" id="mt-theme-toggle">' +
        '<span class="theme-time-badge">' +
          (pref === 'auto'
            ? h + ':' + ('0'+new Date().getMinutes()).slice(-2)
            : pref === 'light' ? '☀️' : '🌙') +
        '</span>' +
        '<button class="mt-tbtn' + (pref==='light'?' theme-btn-active':'') +
          '" data-theme-btn="light" onclick="mtSetTema(\'light\')" title="Día">☀️</button>' +
        '<button class="mt-tbtn' + (pref==='auto'?' theme-btn-active':'') +
          '" data-theme-btn="auto"  onclick="mtSetTema(\'auto\')"  title="Automático">🕐 Auto (' + (esDia?'☀️':'🌙') + ')</button>' +
        '<button class="mt-tbtn' + (pref==='dark'?' theme-btn-active':'') +
          '" data-theme-btn="dark"  onclick="mtSetTema(\'dark\')"  title="Noche">🌙</button>' +
      '</div>'
    );
  }

  function inyectarToggle() {
    if (document.getElementById('mt-theme-toggle')) return;

    // Buscar contenedor en orden de prioridad
    var contenedor = (
      document.querySelector('.nav-right') ||
      document.querySelector('.nav-r')     ||
      document.querySelector('nav')
    );

    if (!contenedor) return;

    var div = document.createElement('div');
    div.innerHTML = buildToggleHTML();
    var toggle = div.firstChild;

    // Insertar al inicio del contenedor derecho
    contenedor.insertBefore(toggle, contenedor.firstChild);

    // Separador visual después del toggle
    var sep = document.createElement('div');
    sep.style.cssText = 'width:1px;height:20px;background:var(--border);flex-shrink:0;';
    toggle.after(sep);
  }

  /* ── CHEQUEO PERIÓDICO ── */
  var _ultimoTema = null;
  function chequearAuto() {
    if (getPref() !== 'auto') return;
    var nuevo = temaSegunHora();
    if (nuevo !== _ultimoTema) {
      _ultimoTema = nuevo;
      aplicarTema(nuevo, true);
    }
    actualizarBadge();
  }

  /* ── INIT: aplica tema ANTES del paint para evitar flash ── */
  var temaInicial = temaActivo();
  _ultimoTema = temaInicial;
  document.documentElement.setAttribute('data-theme', temaInicial);

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
      inyectarToggle();
      actualizarBadge();
    });
  } else {
    inyectarToggle();
    actualizarBadge();
  }

  setInterval(chequearAuto, CHECK_INTERVAL);
  document.addEventListener('visibilitychange', function() {
    if (document.visibilityState === 'visible') chequearAuto();
  });

})();
