// ── ESTADO GLOBAL ──────────────────────────────────────────────
var TODOS_DATOS = [];
var filtroActivo = 'todos';
var filtroEstado = 'todos';
var filtroCiclo   = '';
var filtroSeccion = ''; // '' = todas, 'A','B','C','D','E'
var gradosActivos = [];
var mencionesActivas = [];
var vistaActual = 'tabla';

// Inicializar filtros desde perfil del profesor

var CACHE_KEY = 'mt_datos_v4';
var CACHE_TTL = 90000; // 90 segundos
function clearCache() {
  try { sessionStorage.removeItem(CACHE_KEY); } catch(e) {}
}

// ── INICIALIZACIÓN ─────────────────────────────────────────────

// ── WELCOME SCREEN ──────────────────────────────────────────────────────────
var _enWelcome = true;

function irAListado() {
  _enWelcome = false;
  document.getElementById('welcome-screen').style.display  = 'none';
  document.getElementById('toolbar-bar').style.display     = '';
  document.getElementById('kpi-bar').style.display         = '';
  document.getElementById('actions-bar').style.display     = '';
  document.getElementById('estudiantes-section').style.display = '';
  cargarDatos(false);
}

function cargarStatsWelcome(datos) {
  if (!datos || !datos.length) return;
  var total      = datos.length;
  var alertas    = datos.filter(function(d){ return d.p_acad > 0 && d.p_acad < 70; }).length;
  var obs        = datos.filter(function(d){ return d.p_acad >= 70 && d.p_acad < 80; }).length;
  var excelentes = datos.filter(function(d){ return d.p_acad >= 85; }).length;
  var conNotas   = datos.filter(function(d){ return d.p_acad > 0; });
  var prom       = conNotas.length ? (conNotas.reduce(function(s,d){ return s+d.p_acad; },0)/conNotas.length).toFixed(1) : '—';

  // Use textContent only — colors handled by CSS classes (no inline colors)
  var set = function(id, val) { var el=document.getElementById(id); if(el) el.textContent=val; };
  set('wc-total',   total);
  set('wc-alertas', alertas);
  set('wc-obs',     obs);
  set('wc-prom',    prom);

  // Sub-info
  var kiTotal = document.getElementById('wc-ki-total');
  if (kiTotal) kiTotal.textContent = conNotas.length + ' con notas cargadas';
  var kiProm = document.getElementById('wc-ki-prom');
  if (kiProm) kiProm.textContent = excelentes + ' excelentes (≥85)';

  // Alert strip — use CSS class .visible
  var strip = document.getElementById('wc-alert-strip');
  var alertTxt = document.getElementById('wc-alert-txt');
  if (strip) {
    if (alertas > 0) {
      strip.classList.add('visible');
      if (alertTxt) alertTxt.textContent = alertas + ' estudiante' + (alertas>1?'s':'') + ' en alerta crítica (promedio < 70).';
    } else {
      strip.classList.remove('visible');
    }
  }
}

function cargarCasosWelcome() {
  fetch('/api/casos?estado=Abierto')
    .then(function(r){ return r.json(); })
    .then(function(d){
      if (!Array.isArray(d)) return;
      var n = d.length;
      var el = document.getElementById('wc-casos');
      if (el) { el.textContent = n; el.style.color = n > 0 ? '#818cf8' : 'var(--muted)'; }
      var badge = document.getElementById('wc-badge-casos');
      if (badge) {
        if (n > 0) { badge.textContent = n; badge.style.display = 'block'; }
        else badge.style.display = 'none';
      }
    }).catch(function(){});
}

// Override procesarDatos to also load welcome stats
var _origProcesar = null;
window.addEventListener('DOMContentLoaded', function() {
  // ── Reloj en tiempo real ──────────────────────────────────────────────
  function actualizarReloj() {
    var now  = new Date();
    var dias = ['Domingo','Lunes','Martes','Miércoles','Jueves','Viernes','Sábado'];
    var meses= ['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre'];
    var dEl  = document.getElementById('wc-dia');
    var hEl  = document.getElementById('wc-hora');
    if (dEl) dEl.textContent = dias[now.getDay()] + ', ' + now.getDate() + ' de ' + meses[now.getMonth()];
    if (hEl) hEl.textContent = now.toLocaleTimeString('es-DO', {hour:'2-digit',minute:'2-digit'});
  }
  actualizarReloj();
  setInterval(actualizarReloj, 30000);

  // Load stats in background for welcome screen without triggering full render
  fetch('/api/datos')
    .then(function(r){ return r.json(); })
    .then(function(d){
      cargarStatsWelcome(d);
      // Store for when user clicks "ir al listado"
      window._datosPreloaded = d;
    }).catch(function(){});

  cargarCasosWelcome();
});

window.addEventListener('DOMContentLoaded', function() {
  if (ES_PROFESOR) {
    if (PROF_GRADO)   gradosActivos   = [PROF_GRADO.toLowerCase()];
    if (PROF_MENCION) mencionesActivas = [PROF_MENCION.toUpperCase()];
    // Profesores go straight to listado
    irAListado();
  }
  // Coordinadores y directora: welcome screen loads stats in background (already done above)
  // They click "ir al listado" manually
});

// ── CARGAR DATOS DESDE API ──────────────────────────────────────
function cargarDatos(forzar) {
  // Use preloaded data from welcome screen if available and fresh
  if (!forzar && window._datosPreloaded) {
    procesarDatos(window._datosPreloaded);
    window._datosPreloaded = null;
    return;
  }
  if (!forzar) {
    try {
      var raw = sessionStorage.getItem(CACHE_KEY);
      if (raw) {
        var cached = JSON.parse(raw);
        if (Date.now() - cached.ts < CACHE_TTL) {
          procesarDatos(cached.data);
          return;
        }
      }
    } catch(e) {}
  }

  document.getElementById('tabla-container').innerHTML =
    '<div class="empty-state"><div class="ei">⏳</div><div class="et">Cargando...</div></div>';

  fetch('/api/datos')
    .then(function(r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    })
    .then(function(d) {
      try { sessionStorage.setItem(CACHE_KEY, JSON.stringify({ts:Date.now(), data:d})); } catch(e) {}
      procesarDatos(d);
    })
    .catch(function(err) {
      document.getElementById('tabla-container').innerHTML =
        '<div class="empty-state"><div class="ei">⚠</div>' +
        '<div class="et">Sin conexión</div>' +
        '<div class="es">' + err.message + '</div></div>';
    });
}

// ── PROCESAR Y RENDERIZAR ───────────────────────────────────────
function procesarDatos(data) {
  TODOS_DATOS = data || [];
  actualizarContadoresSidebar();
  actualizarKPIs();
  filtrar();
}

function actualizarContadoresSidebar() {
  var cnts = {todos:0,
              '1ro':0,'2do':0,'3ro':0,'4to':0,'5to':0,'6to':0,
              ciclo1:0, ciclo2:0,
              mm:0, th:0, mu:0, av:0, allM:0};
  TODOS_DATOS.forEach(function(e) {
    cnts.todos++;
    var g = (e.grado || '').toLowerCase();
    if (g.includes('1'))      cnts['1ro']++;
    if (g.includes('2'))      cnts['2do']++;
    if (g.includes('3'))      cnts['3ro']++;
    if (g.includes('4'))      cnts['4to']++;
    if (g.includes('5'))      cnts['5to']++;
    if (g.includes('6'))      cnts['6to']++;
    var ec = (e.ciclo || 'segundo_ciclo');
    if (ec === 'primer_ciclo') cnts.ciclo1++; else cnts.ciclo2++;
    var cc = (e.curso || '').toUpperCase();
    cnts.allM++;
    if (cc.includes('MULTIMEDIA')) cnts.mm++;
    if (cc.includes('TEATRO'))     cnts.th++;
    if (cc.includes('MUSICA') || cc.includes('MÚSICA')) cnts.mu++;
    if (cc.includes('VISUAL') || cc.includes('ARTES')) cnts.av++;
  });
  function setc(id, v) { var el = document.getElementById(id); if(el) el.textContent = v; }
  setc('sb-cnt-todos',  cnts.todos);
  setc('sb-cnt-1ro',    cnts['1ro']);
  setc('sb-cnt-2do',    cnts['2do']);
  setc('sb-cnt-3ro',    cnts['3ro']);
  setc('sb-cnt-4to',    cnts['4to']);
  setc('sb-cnt-5to',    cnts['5to']);
  setc('sb-cnt-6to',    cnts['6to']);
  setc('sb-cnt-ciclo1', cnts.ciclo1);
  setc('sb-cnt-ciclo2', cnts.ciclo2);
  setc('sb-cnt-all-m',  cnts.allM);
  setc('sb-cnt-mm',     cnts.mm);
  setc('sb-cnt-th',     cnts.th);
  setc('sb-cnt-mu',     cnts.mu);
  setc('sb-cnt-av',     cnts.av);

  // Seccion counters + show/hide panel
  var secciones = {A:0, B:0, C:0, D:0, E:0};
  var totalPrimerCiclo = cnts.ciclo1;
  TODOS_DATOS.forEach(function(e) {
    if ((e.ciclo||'segundo_ciclo') === 'primer_ciclo') {
      var sec = (e.seccion||'').toUpperCase();
      if (secciones[sec] !== undefined) secciones[sec]++;
    }
  });
  setc('sb-cnt-sec-todas', totalPrimerCiclo);
  setc('sb-cnt-sec-a', secciones.A);
  setc('sb-cnt-sec-b', secciones.B);
  setc('sb-cnt-sec-c', secciones.C);
  setc('sb-cnt-sec-d', secciones.D);
  setc('sb-cnt-sec-e', secciones.E);
  var panelSec = document.getElementById('sb-secciones-panel');
  if (panelSec) panelSec.style.display = (totalPrimerCiclo > 0) ? 'block' : 'none';
}

function actualizarKPIs() {
  var total = TODOS_DATOS.length;
  var conNotas = TODOS_DATOS.filter(function(e) { return e.tiene_notas; }).length;
  var alertas  = TODOS_DATOS.filter(function(e) { return e.categoria === 'ALERTA DE REPROBACIÓN'; }).length;
  var silenc   = TODOS_DATOS.filter(function(e) { return e.categoria === 'CASO SILENCIOSO'; }).length;
  var sinNotas = total - conNotas;
  var promsArr = TODOS_DATOS.filter(function(e) { return (e.p_acad||0) > 0; }).map(function(e){ return e.p_acad; });
  var promGen  = promsArr.length ? (promsArr.reduce(function(a,b){return a+b;}, 0) / promsArr.length).toFixed(1) : '—';

  function setk(id, v) { var el = document.getElementById(id); if(el) el.textContent = v; }
  setk('kpi-total',      total);
  setk('kpi-con-notas',  conNotas);
  setk('kpi-prom',       promGen);
  setk('kpi-alertas',    alertas);
  setk('kpi-silenciosos',silenc);
  setk('kpi-sin-notas',  sinNotas);
}

// ── FILTROS ────────────────────────────────────────────────────
function filtrar() {
  var q      = (document.getElementById('busqueda').value || '').toLowerCase().trim();
  var orden  = document.getElementById('ordenar').value;

  var datos = TODOS_DATOS.filter(function(e) {
    // Búsqueda de texto
    if (q) {
      var nombre = ((e.nombre||'') + ' ' + (e.apellido||'')).toLowerCase();
      var curso  = (e.curso || '').toLowerCase();
      if (!nombre.includes(q) && !curso.includes(q)) return false;
    }

    // Filtro de categoría (chips principales)
    if (filtroActivo !== 'todos') {
      if ((e.categoria || '') !== filtroActivo) return false;
    }

    // Filtro de estado (sidebar)
    if (filtroEstado !== 'todos') {
      var cat = (e.categoria || '').toLowerCase();
      if (filtroEstado === 'alerta'     && !cat.includes('alerta'))     return false;
      if (filtroEstado === 'silencioso' && !cat.includes('silencioso')) return false;
      if (filtroEstado === 'estable'    && cat !== '')                  return false;
    }

    // Filtro de grados (chips)
    if (gradosActivos.length > 0) {
      var g = (e.grado || '').toLowerCase();
      var gradoNorm = g.replace('1ero','1ro').replace('3ero','3ro').replace('2do','2do');
      var match = gradosActivos.some(function(ga) { return gradoNorm.includes(ga.toLowerCase()); });
      if (!match) return false;
    }

    // Filtro de menciones (chips)
    if (mencionesActivas.length > 0) {
      var c = (e.curso || '').toUpperCase();
      var match2 = mencionesActivas.some(function(ma) {
        if (ma === 'VISUAL') return c.includes('VISUAL') || c.includes('ARTES');
        if (ma === 'MUSICA') return c.includes('MUSICA') || c.includes('MÚSICA');
        return c.includes(ma);
      });
      if (!match2) return false;
    }

    // Filtro de ciclo
    if (filtroCiclo) {
      if ((e.ciclo || 'segundo_ciclo') !== filtroCiclo) return false;
    }

    // Filtro de sección (A-E, primer ciclo)
    if (filtroSeccion) {
      if ((e.seccion || '').toUpperCase() !== filtroSeccion.toUpperCase()) return false;
    }

    return true;
  });

  // Ordenar
  datos.sort(function(a, b) {
    if (orden === 'p_acad_desc')     return (b.p_acad||0)      - (a.p_acad||0);
    if (orden === 'p_acad_asc')      return (a.p_acad||0)      - (b.p_acad||0);
    if (orden === 'riesgo_desc')     return (b.indice_riesgo||0)- (a.indice_riesgo||0);
    if (orden === 'riesgo_asc')      return (a.indice_riesgo||0)- (b.indice_riesgo||0);
    if (orden === 'proyeccion_desc') return (b.proyeccion||0)   - (a.proyeccion||0);
    if (orden === 'nombre_asc') {
      var na = ((a.apellido||'') + ' ' + (a.nombre||'')).toLowerCase();
      var nb = ((b.apellido||'') + ' ' + (b.nombre||'')).toLowerCase();
      return na < nb ? -1 : na > nb ? 1 : 0;
    }
    return 0;
  });

  document.getElementById('total-info').textContent =
    datos.length + ' de ' + TODOS_DATOS.length + ' estudiantes';

  if (vistaActual === 'cards') {
    renderCards(datos);
  } else {
    renderTabla(datos);
  }
}

// ── RENDERIZAR TABLA ───────────────────────────────────────────
function renderTabla(datos) {
  var cont = document.getElementById('tabla-container');
  if (!datos || datos.length === 0) {
    cont.innerHTML = '<div class="empty-state">' +
      '<div class="ei">🔍</div>' +
      '<div class="et">Sin resultados</div>' +
      '<div class="es">Prueba otro filtro</div></div>';
    return;
  }

  var html = '<table><thead><tr>' +
    '<th>#</th>' +
    '<th>Estudiante</th>' +
    '<th>Grado / Mención</th>' +
    '<th>Prom. Acad.</th>' +
    '<th>Módulos</th>' +
    '<th>Proyección</th>' +
    '<th>Conducta</th>' +
    '<th>Estado</th>' +
    '<th>Notas</th>' +
    '</tr></thead><tbody>';

  datos.forEach(function(e, i) {
    var acad  = (e.p_acad  || 0).toFixed(1);
    var mods  = (e.prom_modulos || 0).toFixed(1);
    var proy  = (e.proyeccion || 0).toFixed(1);
    var cond  = (e.p_cond || 0).toFixed(1);
    var cat   = e.categoria || '';
    var tend  = e.tendencia || 'igual';
    var tendIcon = tend === 'subiendo' ? '↗' : tend === 'bajando' ? '↘' : '→';
    var tendColor= tend === 'subiendo' ? 'var(--accent)' : tend === 'bajando' ? '#ff6b6b' : 'var(--muted)';

    var badge = '';
    var alerta = e.alerta_nivel || 0;
    var cat_display = e.categoria || cat;
    if (alerta === 2 || cat === 'ALERTA CRÍTICA' || cat === 'ALERTA DE REPROBACIÓN') {
      badge = '<span class="badge" style="background:rgba(239,68,68,.2);color:#ef4444;border:1px solid rgba(239,68,68,.4);">🔴 Alerta Crítica</span>';
    } else if (alerta === 1 || cat === 'ESTUDIANTE EN OBSERVACIÓN') {
      badge = '<span class="badge" style="background:rgba(249,115,22,.2);color:#f97316;border:1px solid rgba(249,115,22,.4);">🟠 En Observación</span>';
    } else if (cat === 'EXCELENTE') {
      badge = '<span class="badge" style="background:rgba(34,197,94,.15);color:#22c55e;border:1px solid rgba(34,197,94,.3);">⭐ Excelente</span>';
    } else if (e.tiene_notas) {
      badge = '<span class="badge badge-estable">✓ Regular</span>';
    } else {
      badge = '<span class="badge badge-sin">sin datos</span>';
    }

    var notasIcon = e.tiene_notas
      ? '<i class="fas fa-check-circle" style="color:var(--accent);font-size:13px;"></i>'
      : '<i class="fas fa-circle" style="color:#333;font-size:13px;"></i>';

    var inicial = ((e.nombre||'X')[0] + (e.apellido||'X')[0]).toUpperCase();
    var acadColor = bc(parseFloat(acad));

    var rowBg = (alerta===2) ? 'rgba(239,68,68,.07)' : (alerta===1) ? 'rgba(249,115,22,.07)' : 'transparent';
    html += '<tr onclick="irAPerfil(' + e.id + ')" style="cursor:pointer;background:' + rowBg + ';">' +
      '<td style="color:var(--muted);font-size:11px;font-family:\'DM Mono\',monospace;">' + (i+1) + '</td>' +
      '<td class="td-nombre">' +
        '<div style="display:flex;align-items:center;gap:8px;">' +
        '<div style="width:30px;height:30px;border-radius:50%;background:rgba(var(--accent-rgb),.15);' +
          'display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:800;' +
          'color:var(--accent);flex-shrink:0;">' + inicial + '</div>' +
        '<div>' +
          '<div style="font-weight:600;">' + (e.nombre||'') + ' ' + (e.apellido||'') + '</div>' +
          '<div style="font-size:10px;color:var(--muted);">' + (e.cedula || '') + '</div>' +
        '</div></div>' +
      '</td>' +
      '<td>' +
        '<div style="font-weight:600;font-size:12px;">' + (e.grado||'') + '</div>' +
        '<div style="font-size:10px;color:var(--muted);">' + (e.curso||'') + '</div>' +
        (e.seccion ? '<div style="font-size:9px;color:#6366f1;font-weight:700;">Sec. ' + e.seccion + '</div>' : '') +
      '</td>' +
      '<td>' +
        '<span style="font-size:15px;font-weight:800;color:' + acadColor + ';font-family:\'DM Mono\',monospace;">' + (e.p_acad > 0 ? acad : '—') + '</span>' +
        (e.p_acad > 0 ? '<div class="mini-bar"><div class="mini-bar-fill" style="width:' + acad + '%;background:' + acadColor + ';"></div></div>' : '') +
      '</td>' +
      '<td>' +
        '<span style="font-size:13px;font-weight:700;font-family:\'DM Mono\',monospace;color:' + bc(parseFloat(mods)) + ';">' +
        (e.prom_modulos > 0 ? mods : '—') + '</span>' +
      '</td>' +
      '<td>' +
        '<span style="font-size:12px;font-weight:700;color:' + tendColor + ';">' + tendIcon + ' ' +
        (e.proyeccion > 0 ? proy : '—') + '</span>' +
      '</td>' +
      '<td>' +
        '<span style="font-size:12px;color:' + bc(parseFloat(cond)) + ';">' +
        (e.p_cond > 0 ? cond : '—') + '</span>' +
      '</td>' +
      '<td>' + badge + '</td>' +
      '<td style="text-align:center;">' + notasIcon + '</td>' +
      '</tr>';
  });

  html += '</tbody></table>';
  cont.innerHTML = html;
}

// ── RENDERIZAR CARDS ───────────────────────────────────────────
function renderCards(datos) {
  var grid = document.getElementById('cards-grid');
  if (!datos || datos.length === 0) {
    grid.innerHTML = '<div class="empty-state"><div class="ei">🔍</div><div class="et">Sin resultados</div></div>';
    return;
  }

  var html = '';
  datos.forEach(function(e) {
    var acad = (e.p_acad || 0).toFixed(1);
    var cat  = e.categoria || '';
    var inicial = ((e.nombre||'X')[0] + (e.apellido||'X')[0]).toUpperCase();
    var acadColor = bc(parseFloat(acad));

    var alerta    = e.alerta_nivel || 0;
    var badgeTxt  = '';
    var cardBorder = '';
    var cardGlow   = '';
    if (alerta === 2 || cat === 'ALERTA CRÍTICA' || cat === 'ALERTA DE REPROBACIÓN') {
      badgeTxt   = '🔴 Alerta Crítica';
      cardBorder = 'border-color:rgba(239,68,68,.5);';
      cardGlow   = 'box-shadow:0 0 0 1px rgba(239,68,68,.2);';
    } else if (alerta === 1 || cat === 'ESTUDIANTE EN OBSERVACIÓN') {
      badgeTxt   = '🟠 En Observación';
      cardBorder = 'border-color:rgba(249,115,22,.4);';
      cardGlow   = 'box-shadow:0 0 0 1px rgba(249,115,22,.15);';
    } else if (cat === 'EXCELENTE') {
      badgeTxt = '⭐ Excelente';
    } else if (e.tiene_notas) {
      badgeTxt = '✓ Regular';
    }

    // Indicadores del expediente
    var indBadges = '';
    var indMap = {
      conducta:  { critico:'🔴', alerta:'🟠', observacion:'🟡', neutro:'' },
      psico:     { critico:'🔵', alerta:'🔵', observacion:'🔵', neutro:'' },
      academico: { critico:'🔴', alerta:'🟠', observacion:'🟡', neutro:'' },
      logros:    { destacado:'⭐⭐', activo:'⭐', neutro:'' }
    };
    var indLabels = {
      conducta:'Conducta', psico:'Psico', academico:'Académico', logros:'Logros'
    };
    var indColors = {
      critico:'rgba(239,68,68,.18)', alerta:'rgba(249,115,22,.18)',
      observacion:'rgba(255,196,77,.15)', destacado:'rgba(55,138,221,.18)',
      activo:'rgba(55,138,221,.1)', neutro:''
    };
    var indTextColors = {
      critico:'#ef4444', alerta:'#f97316', observacion:'#ffc44d',
      destacado:'#378ADD', activo:'#a8d04a', neutro:''
    };
    [['conducta', e.ind_conducta], ['psico', e.ind_psico],
     ['academico', e.ind_academico], ['logros', e.ind_logros]].forEach(function(pair) {
      var key = pair[0]; var val = pair[1] || 'neutro';
      var icon = (indMap[key]||{})[val] || '';
      if (!icon && val === 'neutro') return;
      var bg = indColors[val] || '';
      var tc = indTextColors[val] || 'var(--muted)';
      if (bg) {
        indBadges += '<span style="background:'+bg+';color:'+tc+';padding:1px 6px;border-radius:10px;font-size:9px;font-weight:700;margin-right:3px;">'+icon+' '+indLabels[key]+'</span>';
      }
    });

    html += '<div class="est-card" onclick="irAPerfil(' + e.id + ')" style="' + cardBorder + cardGlow + '">' +
      '<div class="ec-header">' +
        '<div class="ec-avatar">' + inicial + '</div>' +
        '<div>' +
          '<div class="ec-name">' + (e.nombre||'') + ' ' + (e.apellido||'') + '</div>' +
          '<div class="ec-course">' + (e.grado||'') + ' · ' + (e.curso||'') + '</div>' +
        '</div>' +
      '</div>' +
      '<div class="ec-stat"><span class="ec-stat-lbl">Promedio</span>' +
        '<span class="ec-stat-val" style="color:' + acadColor + ';">' + (e.p_acad > 0 ? acad : '—') + '</span></div>' +
      '<div class="ec-stat"><span class="ec-stat-lbl">Proyección</span>' +
        '<span class="ec-stat-val">' + (e.proyeccion > 0 ? (e.proyeccion).toFixed(1) : '—') + '</span></div>' +
      (indBadges ? '<div style="margin-top:8px;display:flex;flex-wrap:wrap;gap:3px;">' + indBadges + '</div>' : '') +
      (badgeTxt ? '<div style="margin-top:6px;font-size:10px;font-weight:700;color:' + (alerta===2?'#ef4444':alerta===1?'#f97316':'var(--muted)') + ';">' + badgeTxt + '</div>' : '') +
      '</div>';
  });

  grid.innerHTML = html;
}

// ── COLOR HELPER ───────────────────────────────────────────────
function bc(v) {
  var isDark = document.documentElement.getAttribute('data-theme') !== 'light';
  if (isNaN(v) || v === 0) return 'var(--muted)';
  if (isDark) return v >= 85 ? '#4dffb4' : v >= 70 ? '#378ADD' : '#ff4d4d';
  return v >= 85 ? '#2563EB' : v >= 70 ? '#0284C7' : '#EF4444';
}

// ── NAVEGACIÓN ─────────────────────────────────────────────────
function irAPerfil(id) {
  window.location.href = '/perfil/' + id;
}

// ── SETTERS DE FILTRO ──────────────────────────────────────────
function setFiltro(btn) {
  document.querySelectorAll('.chip[data-filtro]').forEach(function(c) { c.classList.remove('active'); });
  btn.classList.add('active');
  filtroActivo = btn.getAttribute('data-filtro') || 'todos';
  filtrar();
}

function setFiltro2(estado) {
  filtroEstado = estado;
  document.querySelectorAll('.sb-section .sb-item').forEach(function(b) {
    b.classList.remove('active');
  });
  filtrar();
}

function toggleGrado(btn) {
  var g = btn.getAttribute('data-grado');
  if (btn.classList.contains('active')) {
    btn.classList.remove('active');
    gradosActivos = gradosActivos.filter(function(x) { return x !== g; });
  } else {
    btn.classList.add('active');
    gradosActivos.push(g);
  }
  filtrar();
}

function toggleMencion(btn) {
  var m = btn.getAttribute('data-mencion');
  if (btn.classList.contains('active')) {
    btn.classList.remove('active');
    mencionesActivas = mencionesActivas.filter(function(x) { return x !== m; });
  } else {
    btn.classList.add('active');
    mencionesActivas.push(m);
  }
  filtrar();
}

function sbSetGrado(g) {
  // Limpiar chips de grado activos en toolbar
  document.querySelectorAll('.chip[data-grado]').forEach(function(c) { c.classList.remove('active'); });
  gradosActivos = g ? [g] : [];
  if (g) {
    var chip = document.querySelector('.chip[data-grado="' + g + '"]');
    if (chip) chip.classList.add('active');
  }
  // Sincronizar filtroCiclo automáticamente
  if (g) {
    var pc = ['1ro','2do','3ro'];
    filtroCiclo = pc.includes(g.toLowerCase()) ? 'primer_ciclo' : 'segundo_ciclo';
  } else {
    filtroCiclo = '';
  }
  // Actualizar indicador de ciclo activo en sidebar
  document.querySelectorAll('[id^="sb-ciclo-"]').forEach(function(b){ b.classList.remove('active'); });
  var cicloMap = {'primer_ciclo':'sb-ciclo-primero','segundo_ciclo':'sb-ciclo-segundo','':'sb-ciclo-todos'};
  var cicloEl = document.getElementById(cicloMap[filtroCiclo]||'sb-ciclo-todos');
  if(cicloEl) cicloEl.classList.add('active');
  // Actualizar grado activo en sidebar
  document.querySelectorAll('[id^="sb-1ro"],[id^="sb-2do"],[id^="sb-3ro"],[id^="sb-4to"],[id^="sb-5to"],[id^="sb-6to"],#sb-todos').forEach(function(b) {
    b.classList.remove('active');
  });
  var sbId = g ? 'sb-' + g.toLowerCase() : 'sb-todos';
  var sbEl = document.getElementById(sbId);
  if (sbEl) sbEl.classList.add('active');
  filtrar();
}

function sbSetCiclo(ciclo) {
  filtroCiclo = ciclo;
  document.querySelectorAll('[id^="sb-ciclo-"]').forEach(function(b){b.classList.remove('active');});
  var map = {'':'sb-ciclo-todos','primer_ciclo':'sb-ciclo-primero','segundo_ciclo':'sb-ciclo-segundo'};
  var el = document.getElementById(map[ciclo]||'sb-ciclo-todos');
  if(el) el.classList.add('active');
  gradosActivos=[]; mencionesActivas=[]; filtroSeccion='';
  document.querySelectorAll('.sb-item[id^="sb-"]:not([id^="sb-ciclo"])').forEach(function(b){b.classList.remove('active');});
  var todosEl = document.getElementById('sb-todos');
  if(todosEl) todosEl.classList.add('active');
  var secTodas = document.getElementById('sb-sec-todas');
  if(secTodas) secTodas.classList.add('active');
  filtrar();
}

function sbSetSeccion(s) {
  filtroSeccion = s;
  document.querySelectorAll('[id^="sb-sec-"]').forEach(function(b){ b.classList.remove('active'); });
  var target = document.getElementById(s ? 'sb-sec-'+s.toLowerCase() : 'sb-sec-todas');
  if (target) target.classList.add('active');
  filtrar();
}

function sbSetMencion(m) {
  document.querySelectorAll('.chip[data-mencion]').forEach(function(c) { c.classList.remove('active'); });
  mencionesActivas = m ? [m] : [];
  if (m) {
    var chip = document.querySelector('.chip[data-mencion="' + m + '"]');
    if (chip) chip.classList.add('active');
  }
  // Actualizar sidebar
  ['sb-all-m','sb-multimedia','sb-teatro','sb-musica','sb-visual'].forEach(function(id) {
    var el = document.getElementById(id);
    if (el) el.classList.remove('active');
  });
  if (!m && document.getElementById('sb-all-m')) document.getElementById('sb-all-m').classList.add('active');
  var sbMap = {'MULTIMEDIA':'sb-multimedia','TEATRO':'sb-teatro','MUSICA':'sb-musica','VISUAL':'sb-visual'};
  if (sbMap[m] && document.getElementById(sbMap[m])) document.getElementById(sbMap[m]).classList.add('active');
  filtrar();
}

function setVista(v) {
  vistaActual = v;
  var cont  = document.getElementById('tabla-container');
  var cards = document.getElementById('cards-grid');
  if (v === 'cards') {
    cont.style.display  = 'none';
    cards.style.display = 'flex';
  } else {
    cont.style.display  = '';
    cards.style.display = 'none';
  }
  document.getElementById('btn-vista-tabla').classList.toggle('active', v === 'tabla');
  document.getElementById('btn-vista-cards').classList.toggle('active', v === 'cards');
  filtrar();
}

// ── SECCIONES ──────────────────────────────────────────────────
function showSection(sec) {
  document.getElementById('estudiantes-section').style.display = 'none';
  document.getElementById('upload-section').style.display     = 'none';
  document.getElementById('usuarios-section').style.display   = 'none';

  if (sec === 'students') {
    document.getElementById('estudiantes-section').style.display = 'block';
  } else if (sec === 'upload') {
    document.getElementById('upload-section').style.display = 'block';
  } else if (sec === 'usuarios') {
    document.getElementById('usuarios-section').style.display = 'block';
    cargarUsuarios();
  }
}

// ── CARGAS DE ARCHIVOS ─────────────────────────────────────────
function mostrarStatus(id, msg, tipo) {
  var el = document.getElementById(id);
  el.textContent = msg;
  el.className = 'upload-status ' + (tipo === 'ok' ? 'ok' : 'err');
  el.style.display = 'block';
}

function cargarBoletinIndex(input) {
  if (!input.files[0]) return;
  var fd = new FormData();
  fd.append('file', input.files[0]);
  mostrarStatus('status-boletin', '⏳ Procesando boletín...', 'ok');
  fetch('/api/cargar-boletin', {method:'POST', body:fd})
    .then(function(r){ return r.json(); })
    .then(function(d){
      if (d.ok) {
        var msg = '✓ ' + (d.mensaje || (d.estudiantes_procesados+' estudiantes, '+d.materias_guardadas+' calificaciones cargadas.'));
        mostrarStatus('status-boletin', msg, 'ok');
        if (d.errores && d.errores.length) {
          var el = document.getElementById('status-boletin');
          el.innerHTML += '<div style="font-size:10px;color:#ffc44d;margin-top:4px;">⚠ ' + d.errores[0] + '</div>';
        }
        clearCache(); cargarDatos(true);
      } else {
        var errMsg = (d.error || 'Error al cargar el boletín');
        mostrarStatus('status-boletin', '✗ ' + errMsg, 'err');
      }
      input.value = '';
    })
    .catch(function(e){
      mostrarStatus('status-boletin', '✗ Error de conexión: ' + e.message, 'err');
    });
}

function cargarListado(input) {
  var file = input.files[0];
  if (!file) return;
  mostrarStatus('status-listado', '⏳ Procesando listado...', 'ok');
  var fd = new FormData();
  fd.append('file', file);
  fetch('/api/cargar-listado', {method:'POST', body:fd})
    .then(function(r) { return r.json(); })
    .then(function(d) {
      if (d.ok || d.status === 'success') {
        mostrarStatus('status-listado', '✓ ' + (d.mensaje || 'Listado cargado'), 'ok');
        toast('Listado cargado correctamente', 'ok');
        clearCache(); cargarDatos(true);
      } else {
        mostrarStatus('status-listado', '✗ ' + (d.error || 'Error'), 'err');
      }
    })
    .catch(function(e) { mostrarStatus('status-listado', '✗ Error: ' + e.message, 'err'); });
}

function cargarPlantilla(input) {
  var file = input.files[0];
  if (!file) return;
  mostrarStatus('status-plantilla', '⏳ Analizando plantilla BJ...', 'ok');
  var fd = new FormData();
  fd.append('file', file);
  fetch('/api/cargar-plantilla-bj', {method:'POST', body:fd})
    .then(function(r) { return r.json(); })
    .then(function(d) {
      if (d.ok) {
        var msg = '✓ ' + (d.mensaje || 'Plantilla cargada');
        mostrarStatus('status-plantilla', msg, 'ok');
        toast(msg, 'ok');
        clearCache(); cargarDatos(true);
      } else {
        // Fallback: try old /cargar endpoint for legacy Plantilla Axula
        var fd2 = new FormData();
        fd2.append('file', input.files[0]);
        fetch('/cargar', {method:'POST', body:fd2})
          .then(function(r2) { return r2.json(); })
          .then(function(d2) {
            if (d2.status === 'success') {
              mostrarStatus('status-plantilla', '✓ ' + (d2.mensaje || 'Plantilla cargada'), 'ok');
              toast('Plantilla cargada: ' + (d2.actualizados || 0) + ' estudiantes', 'ok');
              clearCache(); cargarDatos(true);
            } else {
              mostrarStatus('status-plantilla', '✗ ' + (d.error || d2.error || 'Error'), 'err');
            }
          });
      }
    })
    .catch(function(e) { mostrarStatus('status-plantilla', '✗ ' + e.message, 'err'); });
}

function cargarRegistro(input) {
  var file = input.files[0];
  if (!file) return;
  mostrarStatus('status-registro', '⏳ Detectando formato automáticamente...', 'ok');
  var fd = new FormData();
  fd.append('file', file);
  fetch('/api/cargar-plantilla-bj', {method:'POST', body:fd})
    .then(function(r) { return r.json(); })
    .then(function(d) {
      if (d.ok) {
        var msg = '✓ ' + (d.mensaje || 'Archivo cargado correctamente');
        mostrarStatus('status-registro', msg, 'ok');
        toast(msg, 'ok');
        if (typeof cargarEstadoDB === 'function' &&
            document.getElementById('modal-db').classList.contains('open')) {
          cargarEstadoDB();
        }
        clearCache(); cargarDatos(true);
      } else {
        // Fallback: legacy cargar-registro (formato MINERD estándar)
        var fd2 = new FormData();
        fd2.append('file', file);
        fetch('/api/cargar-registro', {method:'POST', body:fd2})
          .then(function(r2) { return r2.json(); })
          .then(function(d2) {
            if (d2.ok || d2.status === 'success') {
              var msg2 = '✓ ' + (d2.mensaje || 'Cargado');
              mostrarStatus('status-registro', msg2, 'ok');
              toast(msg2, 'ok');
              clearCache(); cargarDatos(true);
            } else {
              mostrarStatus('status-registro',
                '✗ ' + (d2.error || d.error || 'No se reconoció el formato'), 'err');
            }
          })
          .catch(function(e) { mostrarStatus('status-registro', '✗ ' + e.message, 'err'); });
      }
    })
    .catch(function(e) { mostrarStatus('status-registro', '✗ ' + e.message, 'err'); });
}

function rolLabel(rol) {
  var labels = {
    'directora':                  '👑 Directora',
    'coordinador_general':        '🏛 Coord. General',
    'coordinador_primer_ciclo':   '📚 Coord. 1er Ciclo',
    'coordinador_segundo_ciclo':  '🎓 Coord. 2do Ciclo',
    'psicologa_primer_ciclo':     '🧠 Psicóloga 1er Ciclo',
    'psicologa_segundo_ciclo':    '🧠 Psicóloga 2do Ciclo',
    'coordinador':                '🏛 Coord. General',
    'profesor':                   '👨‍🏫 Profesor/a',
    'secretaria':                 '📋 Secretaria',
    'secretaria_docente':         '📋 Secretaria Docente',
    'digitador':                  '💻 Digitador/a',
    'auxiliar_contabilidad':      '📊 Aux. Contabilidad'
  };
  return labels[rol] || rol;
}

function rolStyle(rol) {
  var cols = {
    'directora':                  'background:rgba(251,191,36,.15);color:#fbbf24;border-color:#fbbf24;',
    'coordinador_general':        'background:rgba(139,92,246,.15);color:#8b5cf6;border-color:#8b5cf6;',
    'coordinador_primer_ciclo':   'background:rgba(99,102,241,.15);color:#818cf8;',
    'coordinador_segundo_ciclo':  'background:rgba(59,130,246,.15);color:#3b82f6;',
    'psicologa_primer_ciclo':     'background:rgba(236,72,153,.15);color:#ec4899;',
    'psicologa_segundo_ciclo':    'background:rgba(236,72,153,.15);color:#ec4899;',
    'coordinador':                'background:rgba(139,92,246,.15);color:#8b5cf6;',
    'profesor':                   'background:rgba(34,197,94,.15);color:#22c55e;',
    'secretaria':                 'background:rgba(251,146,60,.15);color:#fb923c;',
    'secretaria_docente':         'background:rgba(251,146,60,.15);color:#fb923c;',
    'digitador':                  'background:rgba(148,163,184,.15);color:#94a3b8;',
    'auxiliar_contabilidad':      'background:rgba(148,163,184,.15);color:#94a3b8;'
  };
  return cols[rol] || 'background:rgba(100,100,100,.1);color:#888;';
}

function cargarUsuarios() {
  var grid = document.getElementById('usuarios-grid');
  if (!grid) return;
  grid.innerHTML = '<div style="color:var(--muted);font-size:13px;">Cargando...</div>';
  fetch('/api/usuarios')
    .then(function(r) { return r.json(); })
    .then(function(usuarios) {
      if (!usuarios.length) {
        grid.innerHTML = '<div style="color:var(--muted);">No hay usuarios.</div>';
        return;
      }
      var html = '';
      usuarios.forEach(function(u) {
        var ini = u.nombre ? u.nombre[0].toUpperCase() : '?';
        html += '<div class="user-card">' +
          '<div class="uc-header">' +
            '<div class="uc-avatar">' + ini + '</div>' +
            '<div style="min-width:0;">' +
              '<div class="uc-name">' + escHtml(u.nombre) + '</div>' +
              '<div class="uc-user">@' + escHtml(u.username) + '</div>' +
              (u.email
                ? '<div style="font-size:10px;color:var(--muted);margin-top:1px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="' + escHtml(u.email) + '">' +
                  '✉ ' + escHtml(u.email) + '</div>'
                : '<div style="font-size:10px;color:#333;margin-top:1px;">Sin correo institucional</div>') +
            '</div>' +
          '</div>' +
          '<div class="uc-meta">' +
            '<span class="uc-tag" style="' + rolStyle(u.rol) + '">' + rolLabel(u.rol) + '</span>' +
            (u.grado   ? '<span class="uc-tag">' + escHtml(u.grado) + '</span>' : '') +
            (u.mencion ? '<span class="uc-tag">' + escHtml(u.mencion) + '</span>' : '') +
            '<span class="uc-tag" style="color:' + (u.activo ? 'var(--accent)' : '#ff6b6b') + ';">' +
              (u.activo ? '● activo' : '○ inactivo') + '</span>' +
          '</div>' +
          '<div class="uc-actions">' +
            '<button class="uc-btn" data-uid="' + u.id + '" onclick="editarUsuario(parseInt(this.dataset.uid))">✏ Editar</button>' +
            '<button class="uc-btn del" data-uid="' + u.id + '" data-uname="' + escHtml(u.username) + '" onclick="eliminarUsuario(parseInt(this.dataset.uid),this.dataset.uname)">🗑 Eliminar</button>' +
          '</div>' +
          '</div>';
      });
      grid.innerHTML = html;
    })
    .catch(function(e) {
      grid.innerHTML = '<div style="color:#ff6b6b;">Error: ' + e.message + '</div>';
    });
}

function abrirModalUsuario() {
  document.getElementById('modal-titulo').textContent = 'Nuevo usuario';
  document.getElementById('cu-id').value = '';
  document.getElementById('cu-nombre').value = '';
  document.getElementById('cu-username').value = '';
  document.getElementById('cu-email').value = '';
  document.getElementById('cu-password').value = '';
  document.getElementById('cu-asignaturas').value = '';
  document.getElementById('cu-rol').value = 'profesor';
  document.querySelectorAll('[name="cu-grado"]').forEach(function(r) { r.checked = false; });
  document.querySelectorAll('[name="cu-mencion"]').forEach(function(r) { r.checked = false; });
  toggleRolFields();
  document.getElementById('modal-usuario').classList.add('open');
}

function editarUsuario(uid) {
  fetch('/api/usuarios')
    .then(function(r) { return r.json(); })
    .then(function(usuarios) {
      var u = usuarios.find(function(x) { return x.id === uid; });
      if (!u) return;
      document.getElementById('modal-titulo').textContent = 'Editar usuario';
      document.getElementById('cu-id').value = uid;
      document.getElementById('cu-nombre').value = u.nombre || '';
      document.getElementById('cu-username').value = u.username || '';
      document.getElementById('cu-email').value = u.email || '';
      document.getElementById('cu-password').value = '';
      document.getElementById('cu-asignaturas').value = u.asignaturas || '';
      document.getElementById('cu-rol').value = u.rol || 'profesor';
      document.querySelectorAll('[name="cu-grado"]').forEach(function(r) {
        r.checked = r.value === (u.grado || '');
      });
      document.querySelectorAll('[name="cu-mencion"]').forEach(function(r) {
        r.checked = r.value === (u.mencion || '').toLowerCase();
      });
      toggleRolFields();
      document.getElementById('modal-usuario').classList.add('open');
    });
}

function cerrarModal() {
  document.getElementById('modal-usuario').classList.remove('open');
}

function toggleRolFields() {
  var rol = document.getElementById('cu-rol').value;
  // Solo el rol "profesor" necesita los campos de grado/mención/asignaturas
  var rolesProfesor = ['profesor'];
  var showProf = rolesProfesor.indexOf(rol) >= 0;
  document.getElementById('prof-fields').style.display = showProf ? 'block' : 'none';

  // Para roles de primer ciclo, ocultar campo mención
  var mencEl = document.getElementById('mencion-fields');
  if (mencEl) {
    var esPrimerCiclo = document.querySelector('[name="cu-grado"]:checked');
    var gradoVal = esPrimerCiclo ? esPrimerCiclo.value : '';
    var esPrimer = ['1ro','2do','3ro'].indexOf(gradoVal) >= 0;
    mencEl.style.display = esPrimer ? 'none' : 'block';
  }

  // Descripción de permisos del rol seleccionado
  var rolesDesc = {
    'directora':                  '👑 Acceso total al sistema',
    'coordinador_general':        '🏛 Gestiona ambos ciclos y todos los usuarios',
    'coordinador_primer_ciclo':   '📚 Gestiona 1ro–3ro únicamente',
    'coordinador_segundo_ciclo':  '🎓 Gestiona 4to–6to únicamente',
    'psicologa_primer_ciclo':     '🧠 Perfiles y cuaderno anecdótico — 1er ciclo',
    'psicologa_segundo_ciclo':    '🧠 Perfiles y cuaderno anecdótico — 2do ciclo',
    'profesor':                   '👨‍🏫 Sus estudiantes y materias asignadas',
    'secretaria':                 '📋 Acceso de lectura — registros generales',
    'secretaria_docente':         '📋 Acceso de lectura — registros docentes',
    'digitador':                  '💻 Carga de datos — sin acceso a reportes',
    'auxiliar_contabilidad':      '📊 Acceso de lectura — sin expedientes'
  };
  var lbl = document.getElementById('rol-label-hint');
  if (lbl) lbl.textContent = rolesDesc[rol] || '';
}

function cargarSugerenciasMaterias() {
  // When grado + mención is selected in modal, suggest subjects from the plan
  var gradoEl  = document.querySelector('[name="cu-grado"]:checked');
  var mencEl   = document.querySelector('[name="cu-mencion"]:checked');
  if (!gradoEl || !mencEl) return;

  var grado   = gradoEl.value;
  var mencion = mencEl.value.toUpperCase();
  var cont    = document.getElementById('sugerencias-materias');
  if (!cont) return;

  fetch('/api/plan-estudio?grado=' + grado + '&mencion=' + mencion)
    .then(r => r.json())
    .then(data => {
      if (!data.asignaturas) return;
      // Only show specialty subjects (non-common)
      var comunes = ['lengua española','inglés','matemática','ciencias sociales',
                     'ciencias de la naturaleza','formación integral','educación física',
                     'identidad, cultura'];
      var especificas = data.asignaturas.filter(a => {
        var n = a.nombre.toLowerCase();
        return !comunes.some(c => n.includes(c));
      });
      cont.innerHTML = especificas.map(a =>
        '<button style="padding:3px 8px;border-radius:6px;border:1px solid var(--border);' +
        'background:rgba(var(--accent-rgb),.08);color:var(--accent);font-size:10px;cursor:pointer;' +
        (a.horas_semana===0 ? "border-style:dashed;" : "") + '" ' +
        'onclick="agregarMateria(this)" data-mat="' + escHtml(a.nombre) + '">' +
        escHtml(a.nombre) + (a.horas_semana === 0 ? ' ★' : '') +
        '</button>'
      ).join('');
    })
    .catch(() => {});
}

function agregarMateria(btn) {
  var mat = btn.getAttribute('data-mat');
  var inp = document.getElementById('cu-asignaturas');
  var current = inp.value.split(',').map(s => s.trim()).filter(Boolean);
  if (!current.includes(mat)) current.push(mat);
  inp.value = current.join(', ');
  btn.style.background = 'rgba(var(--accent-rgb),.2)';
  btn.style.fontWeight = '700';
}

function guardarUsuario() {
  var uid      = document.getElementById('cu-id').value;
  var nombre   = document.getElementById('cu-nombre').value.trim();
  var username = document.getElementById('cu-username').value.trim();
  var email    = document.getElementById('cu-email').value.trim().toLowerCase();
  var password = document.getElementById('cu-password').value.trim();
  var rol      = document.getElementById('cu-rol').value;
  var asigs    = document.getElementById('cu-asignaturas').value.trim();
  var gradoEl  = document.querySelector('[name="cu-grado"]:checked');
  var mencEl   = document.querySelector('[name="cu-mencion"]:checked');
  var grado    = gradoEl ? gradoEl.value : '';
  var mencion  = mencEl  ? mencEl.value  : '';

  if (!nombre || !username) { toast('Nombre y usuario son requeridos', 'err'); return; }

  // Validar email si viene
  if (email && !email.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)) {
    toast('El formato del correo no es válido', 'err'); return;
  }
  if (email && !['educacion.edu.do','minerd.gob.do','minerd.edu.do']
        .some(function(d){ return email.endsWith('@'+d); })) {
    toast('Solo correos @educacion.edu.do o @minerd.gob.do', 'err'); return;
  }

  var body = { nombre:nombre, username:username, email:email||null,
               rol:rol, grado:grado, mencion:mencion, asignaturas:asigs };
  if (password) body.password = password;

  var url    = uid ? '/api/usuarios/' + uid : '/api/usuarios';
  var method = uid ? 'PATCH' : 'POST';
  if (!uid && !password) { toast('La contraseña es requerida para usuarios nuevos', 'err'); return; }

  fetch(url, {
    method: method,
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(body)
  })
  .then(function(r) { return r.json(); })
  .then(function(d) {
    if (d.ok) {
      toast(uid ? 'Usuario actualizado' : 'Usuario creado', 'ok');
      cerrarModal();
      cargarUsuarios();
    } else {
      toast(d.error || 'Error al guardar', 'err');
    }
  })
  .catch(function(e) { toast('Error: ' + e.message, 'err'); });
}

function eliminarUsuario(uid, uname) {
  if (!confirm('¿Eliminar usuario "' + uname + '"? Esta acción no se puede deshacer.')) return;
  fetch('/api/usuarios/' + uid, {method:'DELETE'})
    .then(function(r) { return r.json(); })
    .then(function(d) {
      if (d.ok) { toast('Usuario eliminado', 'ok'); cargarUsuarios(); }
      else       { toast(d.error || 'Error', 'err'); }
    });
}

// ── TOAST ──────────────────────────────────────────────────────
function toast(msg, tipo) {
  var cont = document.getElementById('toast');
  var el = document.createElement('div');
  el.className = 'toast-item ' + (tipo === 'ok' ? 'toast-ok' : 'toast-err');
  el.textContent = msg;
  cont.appendChild(el);
  setTimeout(function() { el.remove(); }, 3500);
}

// ── HELPERS ────────────────────────────────────────────────────
function escHtml(s) {
  return (s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// Cerrar modal al click en overlay
document.getElementById('modal-usuario').addEventListener('click', function(e) {
  if (e.target === this) cerrarModal();
});


// ══════════════════════════════════════════════════════
//   BASE DE DATOS — GESTIÓN Y PURGA
// ══════════════════════════════════════════════════════
var _dbConfirmVisible = false;

var DB_TABLAS = [
  { key: "estudiantes",             label: "Estudiantes",            icon: "👥", color: "#60b8f0" },
  { key: "registro_liceo",          label: "Listado del liceo",      icon: "📋", color: "#60b8f0" },
  { key: "materias_calificaciones", label: "Calificaciones",         icon: "📊", color: "var(--accent)" },
  { key: "asistencia",              label: "Asistencia",             icon: "✅", color: "var(--accent)" },
  { key: "calificaciones_periodo",  label: "Cal. por período",       icon: "📅", color: "var(--accent)" },
  { key: "plan_personalizado",      label: "Materias aprendidas",    icon: "🧠", color: "#ff9f60" },
  { key: "mapeos_excel",            label: "Mapeos Excel",           icon: "🗂",  color: "#ff9f60" },
  { key: "reportes",                label: "Reportes",               icon: "🚩", color: "#ff6b6b" },
  { key: "historial_planificaciones", label: "Planificaciones",      icon: "📝", color: "#c060f0" }
];

function abrirModalDB() {
  document.getElementById('modal-db').classList.add('open');
  cargarEstadoDB();
  renderCheckboxesDB();
}

function cerrarModalDB() {
  document.getElementById('modal-db').classList.remove('open');
}

function renderCheckboxesDB() {
  var cont = document.getElementById('db-checkboxes');
  var html = '';
  for (var i = 0; i < DB_TABLAS.length; i++) {
    var t = DB_TABLAS[i];
    html += '<label style="display:inline-flex;align-items:center;gap:5px;padding:4px 10px;' +
      'border-radius:8px;border:1px solid var(--border);background:var(--hover);' +
      'font-size:11px;cursor:pointer;">' +
      '<input type="checkbox" class="db-check" value="' + t.key + '" ' +
      'style="accent-color:' + t.color + ';"> ' +
      t.icon + ' ' + t.label + '</label>';
  }
  cont.innerHTML = html;
}

function cargarEstadoDB() {
  var grid = document.getElementById('db-estado-grid');
  grid.innerHTML = '<div style="color:var(--muted);font-size:12px;grid-column:1/-1;">Cargando...</div>';
  fetch('/api/db/estado')
    .then(function(r) { return r.json(); })
    .then(function(d) {
      var tablas = d.tablas || {};
      var html = '';
      Object.keys(tablas).forEach(function(key) {
        var info  = tablas[key];
        var meta  = DB_TABLAS.find(function(t) { return t.key === key; });
        var icon  = meta ? meta.icon : '🗄';
        var color = info.registros > 0 ? (meta ? meta.color : 'var(--accent)') : 'var(--muted)';
        html += '<div style="display:flex;align-items:center;justify-content:space-between;' +
          'padding:7px 10px;border-radius:8px;background:var(--hover);border:1px solid var(--border);">' +
          '<span style="font-size:11px;">' + icon + ' ' + escHtml(info.label) + '</span>' +
          '<span style="font-family:var(--font-mono,monospace);font-size:12px;font-weight:700;color:' + color + ';">' +
          info.registros.toLocaleString() + '</span></div>';
      });
      grid.innerHTML = html || '<div style="color:var(--muted);">Sin datos</div>';
    })
    .catch(function(e) {
      grid.innerHTML = '<div style="color:#ff6b6b;font-size:12px;">Error: ' + e.message + '</div>';
    });
}

function ejecutarPurgaSelectiva() {
  var checks = document.querySelectorAll('.db-check:checked');
  if (!checks.length) { toast('Selecciona al menos una tabla', 'err'); return; }
  var tablas = Array.from(checks).map(function(c) { return c.value; });
  var labels = tablas.map(function(k) {
    var m = DB_TABLAS.find(function(t) { return t.key === k; });
    return (m ? m.label : k);
  }).join(', ');
  if (!confirm('Purgar: ' + labels + '. Esta accion no se puede deshacer.')) return;
  fetch('/api/db/purgar', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ tablas: tablas, confirmar: 'CONFIRMAR' })
  })
  .then(function(r) { return r.json(); })
  .then(function(d) {
    if (d.ok) {
      toast('Purga completada', 'ok');
      cargarEstadoDB();
      clearCache(); cargarDatos(true);
      document.querySelectorAll('.db-check').forEach(function(c) { c.checked = false; });
    } else {
      toast((d.errores || [d.error || 'Error']).join(' | '), 'err');
    }
  })
  .catch(function(e) { toast('Error: ' + e.message, 'err'); });
}

function toggleConfirmTotal() {
  _dbConfirmVisible = !_dbConfirmVisible;
  document.getElementById('db-confirm-box').style.display = _dbConfirmVisible ? 'block' : 'none';
  document.getElementById('db-btn-ejecutar-total').style.display = _dbConfirmVisible ? 'inline-flex' : 'none';
  if (_dbConfirmVisible) document.getElementById('db-confirm-input').focus();
}

function ejecutarPurgaTotal() {
  var val = (document.getElementById('db-confirm-input').value || '').trim();
  if (val !== 'BORRAR TODO') { toast('Escribe exactamente: BORRAR TODO', 'err'); return; }
  if (!confirm('ULTIMO AVISO: se borrara todo excepto usuarios. Continuar?')) return;
  fetch('/api/db/purgar-todo', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ confirmar: 'BORRAR TODO', yo_entiendo: true })
  })
  .then(function(r) { return r.json(); })
  .then(function(d) {
    if (d.ok) {
      toast(d.mensaje || 'BD reseteada', 'ok');
      cargarEstadoDB();
      clearCache(); cargarDatos(true);
      toggleConfirmTotal();
      document.getElementById('db-confirm-input').value = '';
    } else {
      toast(d.error || 'Error', 'err');
    }
  })
  .catch(function(e) { toast('Error: ' + e.message, 'err'); });
}

document.getElementById('modal-db').addEventListener('click', function(e) {
  if (e.target === this) cerrarModalDB();
});

// ── CALENDARIO ESCOLAR ───────────────────────────────────────────────────────
function agregarDiaCalendario() {
  var fecha = document.getElementById('cal-fecha').value;
  var tipo  = document.getElementById('cal-tipo').value;
  var desc  = (document.getElementById('cal-desc').value || '').trim();
  var stEl  = document.getElementById('status-calendario');
  if (!fecha) { if(stEl) stEl.innerHTML='<span style="color:#ff6b6b;">Elige una fecha</span>'; return; }
  fetch('/api/calendario', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({fecha:fecha, tipo:tipo, descripcion:desc})
  })
  .then(function(r){ return r.json(); })
  .then(function(d){
    if (d.ok) {
      if(stEl) stEl.innerHTML='<span style="color:#4dffb4;">✓ Día registrado</span>';
      document.getElementById('cal-fecha').value='';
      document.getElementById('cal-desc').value='';
      cargarCalendarioReciente();
    } else {
      if(stEl) stEl.innerHTML='<span style="color:#ff6b6b;">'+(d.error||'Error')+'</span>';
    }
  });
}

function cargarCalendarioReciente() {
  var y = new Date().getFullYear();
  var anio = (new Date().getMonth()+1) >= 8 ? y+'-'+(y+1) : (y-1)+'-'+y;
  fetch('/api/calendario?anio_escolar='+anio)
    .then(function(r){ return r.json(); })
    .then(function(dias){
      var el = document.getElementById('cal-lista-reciente');
      if (!el) return;
      var TIPOS_LABELS = {
        feriado:'🔴',vacacion_navidad:'🎄',vacacion_semana_santa:'✝️',
        vacacion_verano:'☀️',incidente_climatico:'🌧️',no_docencia:'📌',otro:'⚪'
      };
      if (!dias || !dias.length) { el.innerHTML='<div style="color:var(--muted);font-size:11px;">Sin días registrados.</div>'; return; }
      // Show last 6
      var html = '';
      dias.slice(-6).reverse().forEach(function(d){
        html += '<div style="display:flex;align-items:center;gap:6px;padding:4px 0;border-bottom:1px solid var(--border);font-size:10px;">'
          + '<span>' + (TIPOS_LABELS[d.tipo]||'⚪') + '</span>'
          + '<span style="color:var(--text);">' + d.fecha + '</span>'
          + '<span style="color:var(--muted);flex:1;">' + (d.descripcion || d.tipo) + '</span>'
          + '<button class="btn-del-cal" data-fecha="' + d.fecha + '" style="background:none;border:none;color:#ff4d4d;cursor:pointer;font-size:10px;">✕</button>'
          + '</div>';
      });
      el.innerHTML = html;
      el.querySelectorAll('.btn-del-cal').forEach(function(btn){
        btn.addEventListener('click', function(){ eliminarDiaCalendario(this.dataset.fecha); });
      });
    });
}

function recalcularPromedios() {
  if (!confirm('¿Recalcular promedios de todos los estudiantes desde sus materias?')) return;
  toast('Recalculando...', '#60b8f0');
  fetch('/api/recalcular-promedios', {method:'POST'})
    .then(function(r){ return r.json(); })
    .then(function(d){
      if (d.ok || d.actualizados) {
        toast('✓ ' + (d.actualizados||0) + ' estudiantes actualizados', '#4dffb4');
        clearCache(); cargarDatos(true);
      } else { toast(d.error || 'Error', '#ff6b6b'); }
    }).catch(function(){ toast('Error de conexión', '#ff6b6b'); });
}

function limpiarDuplicados() {
  if (!confirm('Esto buscará y fusionará estudiantes con nombres muy similares. ¿Continuar?')) return;
  fetch('/api/dedup-estudiantes', {method:'POST'})
    .then(function(r){ return r.json(); })
    .then(function(d){
      if (d.ok) {
        toast('✓ ' + d.eliminados + ' duplicados fusionados', '#4dffb4');
        clearCache(); cargarDatos(true); cargarEstadoDB();
      } else { toast((d.error || 'Error'), '#ff6b6b'); }
    }).catch(function(){ toast('Error de conexión', '#ff6b6b'); });
}

function eliminarDiaCalendario(fecha) {
  if (!confirm('¿Eliminar '+fecha+' del calendario?')) return;
  fetch('/api/calendario/'+fecha, {method:'DELETE'})
    .then(function(r){ return r.json(); })
    .then(function(d){ if(d.ok) cargarCalendarioReciente(); });
}

// Cargar calendario al abrir panel de carga
document.addEventListener('DOMContentLoaded', function(){
  var cardCal = document.getElementById('card-calendario');
  if (cardCal) cargarCalendarioReciente();

  // Cargar badge de notificaciones en nav
  fetch('/api/notificaciones/count')
    .then(function(r){ return r.json(); })
    .then(function(d){
      var cnt = d.no_leidas || d.total || 0;
      var b = document.getElementById('nav-casos-badge');
      if (b) { 
        if (cnt > 0) { b.textContent = cnt; b.style.display = 'inline'; }
        else { b.style.display = 'none'; }
      }
    }).catch(function(){});
});

// ── SIDEBAR TOGGLE (tablet / móvil) ──────────────────────────────────────
function toggleSidebar() {
  var sb  = document.querySelector('.sidebar');
  var ovr = document.getElementById('sb-overlay');
  if (!sb) return;
  var isOpen = sb.classList.toggle('open');
  if (ovr) ovr.style.display = isOpen ? 'block' : 'none';
}

// Cerrar sidebar al hacer clic en el overlay
document.addEventListener('DOMContentLoaded', function() {
  var ovr = document.createElement('div');
  ovr.id = 'sb-overlay';
  ovr.style.cssText = 'display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:299;';
  ovr.addEventListener('click', function() {
    document.querySelector('.sidebar') && document.querySelector('.sidebar').classList.remove('open');
    ovr.style.display = 'none';
  });
  document.body.appendChild(ovr);

  // Cerrar sidebar al seleccionar un item en móvil
  document.querySelectorAll('.sb-item').forEach(function(item) {
    item.addEventListener('click', function() {
      if (window.innerWidth < 768) {
        document.querySelector('.sidebar').classList.remove('open');
        ovr.style.display = 'none';
      }
    });
  });
});


// ── Avatar dropdown ──────────────────────────────────────────────────────────
function toggleAvatarMenu() {
  var dd = document.getElementById('avatar-dropdown');
  if (!dd) return;
  var visible = dd.style.display === 'block';
  dd.style.display = visible ? 'none' : 'block';
}
document.addEventListener('click', function(e) {
  var wrap = document.getElementById('avatar-menu-wrap');
  if (wrap && !wrap.contains(e.target)) {
    var dd = document.getElementById('avatar-dropdown');
    if (dd) dd.style.display = 'none';
  }
});

// ── PANEL DE NOTIFICACIONES ───────────────────────────────────────────────
var _notifOpen = false;

function toggleNotifPanel(e) {
  e.stopPropagation();
  var panel = document.getElementById('notif-panel');
  if (!panel) return;
  _notifOpen = !_notifOpen;
  panel.style.display = _notifOpen ? 'block' : 'none';
  if (_notifOpen) cargarNotificaciones();
}

document.addEventListener('click', function(e) {
  if (_notifOpen) {
    var wrap = document.getElementById('notif-wrap');
    if (wrap && !wrap.contains(e.target)) {
      var panel = document.getElementById('notif-panel');
      if (panel) panel.style.display = 'none';
      _notifOpen = false;
    }
  }
});

function cargarNotificaciones() {
  var lista = document.getElementById('notif-lista');
  if (!lista) return;
  fetch('/api/notificaciones?no_leidas=0')
    .then(function(r){ return r.json(); })
    .then(function(data) {
      if (!data || !data.length) {
        lista.innerHTML = '<div style="text-align:center;padding:24px;color:#555;font-size:12px;">Sin notificaciones</div>';
        return;
      }
      lista.innerHTML = data.slice(0, 15).map(function(n) {
        var opacityStyle = n.leida ? 'opacity:.5;' : '';
        var dot = n.leida ? '' : '<span style="width:6px;height:6px;border-radius:50%;background:#ff4444;flex-shrink:0;margin-top:5px;display:inline-block;"></span>';
        var fecha = (n.creada_en || '').split('T')[0];
        var nombre = n.est_nombre ? escapeN(n.est_nombre + ' ' + (n.est_apellido || '')) : '';
        var titulo = escapeN(n.titulo || '');
        var url = encodeURIComponent('/perfil/' + (n.estudiante_id || ''));
        var fw = n.leida ? '400' : '600';
        var html = '<div';
        html += ' onclick="abrirNotif(' + n.id + ',decodeURIComponent(\'' + url + '\'))"';
        html += ' style="padding:10px 14px;border-bottom:1px solid rgba(255,255,255,.06);cursor:pointer;display:flex;gap:8px;align-items:flex-start;' + opacityStyle + '"';
        html += ' onmouseover="this.style.background=rgba(255,255,255,.04)"';
        html += ' onmouseout="this.style.background=">';
        html += dot;
        html += '<div style="flex:1;min-width:0;">';
        html += '<div style="font-size:12px;font-weight:' + fw + ';color:#f0f0f0;margin-bottom:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' + titulo + '</div>';
        html += '<div style="font-size:10px;color:#666;">' + (nombre ? nombre + ' &middot; ' : '') + fecha + '</div>';
        html += '</div></div>';
        return html;
      }).join('');
    })
    .catch(function() {
      lista.innerHTML = '<div style="text-align:center;padding:24px;color:#555;font-size:12px;">Error cargando notificaciones</div>';
    });
}

function abrirNotif(nid, dest) {
  fetch('/api/notificaciones/' + nid + '/leer', { method: 'POST' })
    .finally(function() {
      if (dest && dest !== '/perfil/' && dest !== '/perfil/undefined') {
        window.location.href = dest;
      }
      var panel = document.getElementById('notif-panel');
      if (panel) panel.style.display = 'none';
      _notifOpen = false;
    });
}

function marcarTodasLeidas() {
  fetch('/api/notificaciones/leer-todas', { method: 'POST' })
    .then(function() {
      var b = document.getElementById('nav-casos-badge');
      if (b) b.style.display = 'none';
      cargarNotificaciones();
    });
}

function escapeN(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}


function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}