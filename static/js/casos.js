// ══════════════════════════════════════════════════════════════════════════════
// ESTADO GLOBAL
// ══════════════════════════════════════════════════════════════════════════════
var _casos = [];
var _filtroActual = 'todos';
var _casoActual = null;
var _acuerdoActual = null;

// ══════════════════════════════════════════════════════════════════════════════
// UTILIDADES
// ══════════════════════════════════════════════════════════════════════════════
function tk(msg, tipo) {
    var t = document.getElementById('toast-casos');
    t.textContent = msg;
    var colors = {ok:'#4dffb4', err:'#ff6b6b', warn:'#ffc44d'};
    t.style.color = colors[tipo] || '#e0e0e0';
    t.style.borderColor = (colors[tipo] || '#333') + '55';
    t.classList.add('show');
    clearTimeout(t._t);
    t._t = setTimeout(function(){ t.classList.remove('show'); }, 3000);
}

function esc(s) {
    return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function fmtFecha(s) {
    if (!s) return '—';
    return s.split('T')[0];
}

function cerrarModal(id) {
    document.getElementById(id).classList.remove('open');
}

// ══════════════════════════════════════════════════════════════════════════════
// CARGAR CASOS
// ══════════════════════════════════════════════════════════════════════════════
async function cargarCasos() {
    try {
        var r = await fetch('/api/casos');
        _casos = await r.json();
        renderLista();
        cargarNotifCount();
    } catch(e) {
        document.getElementById('casos-lista').innerHTML =
            '<div style="padding:20px;color:#ff6b6b;font-size:12px">Error cargando casos</div>';
    }
}

function renderLista() {
    var lista = _casos.filter(function(c) {
        if (_filtroActual === 'todos') return true;
        return c.estado === _filtroActual;
    });

    if (!lista.length) {
        document.getElementById('casos-lista').innerHTML =
            '<div style="padding:30px;text-align:center;color:var(--muted);font-size:12px">' +
            '<i class="fas fa-check-circle" style="font-size:24px;margin-bottom:8px;display:block;color:var(--success)"></i>' +
            'Sin casos en esta categoría</div>';
        return;
    }

    var TIPO_EMOJI = {asistencia:'📅',conducta:'⚠️',academico:'📚',familiar:'🏠',emocional:'💛'};
    var html = lista.map(function(c) {
        var activo = _casoActual && _casoActual.id === c.id ? ' active' : '';
        return '<div class="caso-item' + activo + '" onclick="verCaso(' + c.id + ')">' +
            '<div class="ci-header">' +
            '<span>' + (TIPO_EMOJI[c.tipo] || '📋') + '</span>' +
            '<span class="ci-nombre">' + esc(c.nombre_estudiante || '—') + '</span>' +
            '<span class="ci-fecha">' + fmtFecha(c.creado_en) + '</span>' +
            '</div>' +
            '<div class="ci-titulo">' + esc(c.titulo) + '</div>' +
            '<div class="ci-footer">' +
            '<span class="badge b-' + (c.estado||'').toLowerCase().replace(' ','-') + '">' + (c.estado||'—') + '</span>' +
            '<span class="badge b-' + c.tipo + '">' + (c.tipo||'') + '</span>' +
            (c.nivel_escala > 1 ? '<span class="badge" style="background:rgba(255,77,77,.1);color:#ff6b6b">Nivel ' + c.nivel_escala + '</span>' : '') +
            '</div></div>';
    }).join('');
    document.getElementById('casos-lista').innerHTML = html;
}

function filtrarCasos(estado, btn) {
    _filtroActual = estado;
    document.querySelectorAll('.filtro-btn').forEach(function(b){ b.classList.remove('active'); });
    btn.classList.add('active');
    renderLista();
}

// ══════════════════════════════════════════════════════════════════════════════
// VER CASO
// ══════════════════════════════════════════════════════════════════════════════
async function verCaso(id) {
    try {
        var r = await fetch('/api/casos/' + id);
        var data = await r.json();
        _casoActual = data;
        renderCasoDetalle(data);
        renderLista(); // refrescar highlight
    } catch(e) { tk('Error cargando caso', 'err'); }
}

function renderCasoDetalle(data) {
    var caso     = data.caso;
    var acciones = data.acciones || [];
    var est      = data.estudiante || {};
    var acuerdos = data.acuerdos  || [];

    var NIVEL_LABELS = ['','Psicóloga','Coordinación','Dirección'];
    var nivelActual  = caso.nivel_escala || 1;

    var TIPO_COLOR = {asistencia:'var(--warn)',conducta:'#ff6b6b',academico:'var(--blue)',familiar:'#f78337',emocional:'#b44be8'};
    var tc = TIPO_COLOR[caso.tipo] || 'var(--accent)';

    var html =
        // Header del caso
        '<div class="card" style="border-left:3px solid ' + tc + '">' +
        '<div style="display:flex;align-items:flex-start;gap:12px">' +
        '<div style="flex:1">' +
        '<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">' +
        '<span class="badge b-' + caso.tipo + '">' + caso.tipo + '</span>' +
        '<span class="badge b-' + (caso.estado||'').toLowerCase().replace(' ','-') + '">' + (caso.estado||'') + '</span>' +
        (nivelActual > 1 ? '<span class="badge" style="background:rgba(255,77,77,.1);color:#ff6b6b">Escala ' + NIVEL_LABELS[nivelActual] + '</span>' : '') +
        '</div>' +
        '<div style="font-family:\'Syne\',sans-serif;font-size:16px;font-weight:700;margin-bottom:4px">' + esc(caso.titulo) + '</div>' +
        '<div style="font-size:12px;color:var(--muted)">Estudiante: <a href="/perfil/' + est.id + '" style="color:var(--accent);text-decoration:none">' + esc(est.nombre + ' ' + est.apellido) + '</a> · ' +
        (est.grado||'') + ' ' + (est.curso||'') + '</div>' +
        '<div style="font-size:11px;color:var(--muted);margin-top:3px">Abierto: ' + fmtFecha(caso.creado_en) + ' · Por: ' + esc(caso.abierto_por_nombre||'sistema') + '</div>' +
        (caso.descripcion ? '<div style="font-size:12px;margin-top:8px;padding:10px;background:var(--surface2);border-radius:7px;line-height:1.6">' + esc(caso.descripcion) + '</div>' : '') +
        '</div>' +
        (caso.estado !== 'Resuelto' && caso.estado !== 'Cerrado' ?
        '<div style="display:flex;flex-direction:column;gap:6px">' +
        '<button class="btn-caso-accion" data-id="' + caso.id + '" data-tipo="escalar" style="background:rgba(255,77,77,.1);border:1px solid rgba(255,77,77,.3);color:#ff6b6b;padding:7px 12px;border-radius:8px;cursor:pointer;font-size:11px;font-weight:700;white-space:nowrap;"><i class="fas fa-level-up-alt"></i> Escalar</button>' +
        '<button onclick="cerrarModal2(' + caso.id + ')" style="background:rgba(77,255,180,.1);border:1px solid rgba(77,255,180,.3);color:var(--success);padding:7px 12px;border-radius:8px;cursor:pointer;font-size:11px;font-weight:700;white-space:nowrap;font-family:\'DM Sans\',sans-serif"><i class="fas fa-check"></i> Cerrar</button>' +
        '</div>' : '') +
        '</div></div>';

    // Escalera visual
    var pasos = [
        {label:'Psicóloga', icon:'🧠'},
        {label:'Coordinación', icon:'👤'},
        {label:'Dirección', icon:'🏛'}
    ];
    html += '<div class="card"><div class="card-title"><i class="fas fa-layer-group"></i>Nivel de Escalada</div>' +
        '<div style="display:flex;align-items:flex-start;gap:0">';
    pasos.forEach(function(p, i) {
        var n = i + 1;
        var cls = n < nivelActual ? 'done' : n === nivelActual ? 'current' : '';
        html += '<div style="text-align:center;flex:1">' +
            '<div class="step-dot ' + cls + '" style="margin:0 auto">' + p.icon + '</div>' +
            '<div class="step-label" style="color:' + (n===nivelActual?'var(--accent)':n<nivelActual?'var(--success)':'var(--muted)') + '">' + p.label + '</div>' +
            '</div>';
        if (i < pasos.length - 1) {
            html += '<div class="step-line' + (n < nivelActual ? ' done' : '') + '" style="margin-top:13px;flex-shrink:0;width:60px"></div>';
        }
    });
    html += '</div></div>';

    // Acciones disponibles
    if (caso.estado !== 'Resuelto' && caso.estado !== 'Cerrado') {
        html += '<div class="card"><div class="card-title"><i class="fas fa-bolt"></i>Acciones</div>' +
            '<div class="acciones-grid">' +
            _accionBtn(caso.id, 'nota',                  'fas fa-sticky-note',      'Nota / Observación') +
            _accionBtn(caso.id, 'cita',                  'fas fa-calendar-check',   'Cita con Estudiante') +
            _accionBtn(caso.id, 'reunion_profesor',       'fas fa-chalkboard-teacher','Reunión con Profesor') +
            _accionBtn(caso.id, 'reunion_coordinador',    'fas fa-user-tie',         'Reunión Coordinación') +
            _accionBtn(caso.id, 'reunion_padres',         'fas fa-people-roof',      'Reunión con Padres') +
            '<div class="accion-btn" onclick="abrirModalAcuerdo(' + caso.id + ',' + est.id + ')">' +
            '<i class="fas fa-file-signature"></i>Acuerdo-Compromiso</div>' +
            '</div></div>';
    }

    // Acuerdos existentes
    if (acuerdos.length) {
        html += '<div class="card"><div class="card-title"><i class="fas fa-file-signature"></i>Acuerdos-Compromiso</div>';
        acuerdos.forEach(function(ac) {
            html += '<div style="border:1px solid var(--border);border-radius:8px;padding:12px;margin-bottom:8px">' +
                '<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">' +
                '<span style="font-family:\'DM Mono\',monospace;font-size:11px;color:var(--accent)">' + esc(ac.numero_acuerdo||'') + '</span>' +
                '<span style="font-size:10px;color:var(--muted)">Generado: ' + fmtFecha(ac.fecha_acuerdo) + '</span>' +
                (ac.firmado ? '<span class="badge" style="background:rgba(77,255,180,.1);color:var(--success)">✓ Firmado</span>' : '<span class="badge" style="background:rgba(255,196,77,.1);color:var(--warn)">Pendiente firma</span>') +
                '</div>' +
                '<div style="font-size:11px;color:var(--muted);max-height:80px;overflow:hidden;line-height:1.6">' +
                esc((ac.contenido_completo||'').substring(0,200)) + '...</div>' +
                '<button onclick="verAcuerdo(' + ac.id + ')" style="margin-top:6px;background:transparent;border:1px solid var(--border);color:var(--muted);padding:4px 10px;border-radius:6px;cursor:pointer;font-size:11px;font-family:\'DM Sans\',sans-serif">Ver completo</button>' +
                '</div>';
        });
        html += '</div>';
    }

    // Timeline de acciones
    html += '<div class="card"><div class="card-title"><i class="fas fa-timeline"></i>Línea de Tiempo</div>';
    if (!acciones.length) {
        html += '<div style="color:var(--muted);font-size:12px;text-align:center;padding:16px">Sin acciones registradas aún.</div>';
    } else {
        html += '<div class="timeline">';
        acciones.forEach(function(a) {
            html += '<div class="tl-item">' +
                '<div class="tl-dot ' + (a.tipo_accion||'nota') + '"></div>' +
                '<div class="tl-meta">' +
                '<span>' + esc(a.actor_nombre||'') + '</span>' +
                '<span>·</span><span>' + fmtFecha(a.fecha_accion) + '</span>' +
                '<span class="badge b-' + (a.tipo_accion==='escalar'?'escalado':'abierto') + '" style="font-size:8px">' + esc(a.tipo_accion||'') + '</span>' +
                '</div>' +
                '<div class="tl-desc">' + esc(a.descripcion||'') + '</div>' +
                (a.resultado ? '<div class="tl-extra">Resultado: ' + esc(a.resultado) + '</div>' : '') +
                (a.fecha_programada ? '<div class="tl-extra">📅 Programado: ' + fmtFecha(a.fecha_programada) + '</div>' : '') +
                '</div>';
        });
        html += '</div>';
    }
    html += '</div>';

    document.getElementById('caso-main').innerHTML = html;
}

function _accionBtn(casoId, tipo, icon, label) {
    return '<div class="accion-btn btn-caso-accion" data-id="' + casoId + '" data-tipo="' + tipo + '">' +
        '<i class="' + icon + '"></i>' + label + '</div>';
}

// ══════════════════════════════════════════════════════════════════════════════
// NUEVO CASO
// ══════════════════════════════════════════════════════════════════════════════
function abrirModalNuevoCaso() {
    document.getElementById('nc-buscar').value   = '';
    document.getElementById('nc-est-id').value   = '';
    document.getElementById('nc-est-nombre').textContent = '';
    document.getElementById('nc-titulo').value   = '';
    document.getElementById('nc-desc').value     = '';
    document.getElementById('nc-resultados').style.display = 'none';
    document.getElementById('modal-nuevo-caso').classList.add('open');
}

var _buscarTimer = null;
function buscarEstudiante(q) {
    clearTimeout(_buscarTimer);
    if (q.length < 2) { document.getElementById('nc-resultados').style.display = 'none'; return; }
    _buscarTimer = setTimeout(async function() {
        var r = await fetch('/api/datos?q=' + encodeURIComponent(q));
        var data = await r.json();
        var box = document.getElementById('nc-resultados');
        if (!data.length) { box.style.display='none'; return; }
        box.innerHTML = data.slice(0,8).map(function(e) {
            return '<div class="est-search-item" data-id="' + e.id + '" data-nombre="' + esc(e.nombre+' '+e.apellido).replace(/"/g,'&quot;') + '" ' +
                'style="padding:8px 12px;cursor:pointer;border-bottom:1px solid var(--border);font-size:12px">' +
                '<strong>' + esc(e.apellido + ', ' + e.nombre) + '</strong> ' +
                '<span style="color:var(--muted)">' + esc(e.grado||'') + ' ' + esc(e.curso||'') + '</span></div>';
        }).join('');
        box.style.display = 'block';
    }, 300);
}

// Event delegation — handles dynamically generated buttons
document.addEventListener('click', function(ev) {
    // Caso action buttons (escalar, etc.)
    var accionBtn = ev.target.closest('.btn-caso-accion');
    if (accionBtn) {
        abrirModalAccion(parseInt(accionBtn.dataset.id), accionBtn.dataset.tipo);
        return;
    }
    // Student search results
    var estItem = ev.target.closest('.est-search-item');
    if (estItem) {
        selEstudiante(parseInt(estItem.dataset.id), estItem.dataset.nombre);
        return;
    }
});

function selEstudiante(id, nombre) {
    document.getElementById('nc-est-id').value = id;
    document.getElementById('nc-est-nombre').textContent = '✓ ' + nombre;
    document.getElementById('nc-buscar').value = nombre;
    document.getElementById('nc-resultados').style.display = 'none';
}

async function crearCaso() {
    var estId   = document.getElementById('nc-est-id').value;
    var titulo  = document.getElementById('nc-titulo').value.trim();
    var tipo    = document.getElementById('nc-tipo').value;
    var desc    = document.getElementById('nc-desc').value.trim();
    if (!estId) { tk('Selecciona un estudiante', 'err'); return; }
    if (!titulo){ tk('Escribe el título del caso', 'err'); return; }
    try {
        var r = await fetch('/api/casos', {
            method:'POST', headers:{'Content-Type':'application/json'},
            body: JSON.stringify({estudiante_id:parseInt(estId), tipo, titulo, descripcion:desc})
        });
        var d = await r.json();
        if (d.ok) {
            cerrarModal('modal-nuevo-caso');
            tk('Caso abierto correctamente', 'ok');
            await cargarCasos();
            verCaso(d.id);
        } else { tk(d.error||'Error', 'err'); }
    } catch(e) { tk('Error de conexión', 'err'); }
}

// ══════════════════════════════════════════════════════════════════════════════
// REGISTRAR ACCIÓN
// ══════════════════════════════════════════════════════════════════════════════
var ACCION_LABELS = {
    nota:               'Nota / Observación',
    cita:               'Cita con Estudiante',
    reunion_profesor:   'Reunión con Profesor',
    reunion_coordinador:'Reunión con Coordinación',
    reunion_padres:     'Reunión con Padres',
    escalar:            '⬆ Escalar Caso',
    resolucion:         'Resolución Final'
};

function abrirModalAccion(casoId, tipo) {
    document.getElementById('accion-caso-id').value = casoId;
    document.getElementById('accion-tipo-val').value = tipo;
    document.getElementById('accion-titulo').textContent = ACCION_LABELS[tipo] || tipo;
    document.getElementById('accion-sub').textContent =
        tipo === 'escalar' ? 'El caso subirá al siguiente nivel de atención' :
        tipo === 'cita'    ? 'Registra la cita y sus resultados' : 'Documenta la acción realizada';
    document.getElementById('accion-desc').value = '';
    document.getElementById('accion-fecha').value = '';
    document.getElementById('accion-partic').value = '';
    document.getElementById('accion-resultado').value = '';
    document.getElementById('modal-accion').classList.add('open');
}

async function guardarAccion() {
    var casoId = document.getElementById('accion-caso-id').value;
    var tipo   = document.getElementById('accion-tipo-val').value;
    var desc   = document.getElementById('accion-desc').value.trim();
    if (!desc) { tk('Escribe la descripción', 'err'); return; }
    try {
        var r = await fetch('/api/casos/' + casoId + '/accion', {
            method:'POST', headers:{'Content-Type':'application/json'},
            body: JSON.stringify({
                tipo_accion:      tipo,
                descripcion:      desc,
                fecha_programada: document.getElementById('accion-fecha').value || null,
                participantes:    document.getElementById('accion-partic').value.trim(),
                resultado:        document.getElementById('accion-resultado').value.trim()
            })
        });
        var d = await r.json();
        if (d.ok) {
            cerrarModal('modal-accion');
            tk('Acción registrada', 'ok');
            await cargarCasos();
            if (_casoActual) verCaso(_casoActual.id);
        } else { tk(d.error||'Error', 'err'); }
    } catch(e) { tk('Error de conexión', 'err'); }
}

// ══════════════════════════════════════════════════════════════════════════════
// ACUERDO-COMPROMISO
// ══════════════════════════════════════════════════════════════════════════════
function abrirModalAcuerdo(casoId, estId) {
    document.getElementById('acuerdo-caso-id').value = casoId;
    document.getElementById('acuerdo-est-id').value  = estId;
    document.getElementById('acuerdo-ctx').value     = '';
    document.getElementById('acuerdo-resultado').style.display  = 'none';
    document.getElementById('acuerdo-generando').style.display  = 'none';
    document.getElementById('btn-generar-acuerdo').style.display = 'inline-flex';
    _acuerdoActual = null;
    document.getElementById('modal-acuerdo').classList.add('open');
}

async function generarAcuerdo() {
    var casoId = document.getElementById('acuerdo-caso-id').value;
    var estId  = document.getElementById('acuerdo-est-id').value;
    var ctx    = document.getElementById('acuerdo-ctx').value.trim();
    document.getElementById('acuerdo-generando').style.display  = 'block';
    document.getElementById('btn-generar-acuerdo').style.display = 'none';
    document.getElementById('acuerdo-resultado').style.display  = 'none';
    try {
        var r = await fetch('/api/acuerdo-compromiso/generar', {
            method:'POST', headers:{'Content-Type':'application/json'},
            body: JSON.stringify({caso_id:parseInt(casoId), estudiante_id:parseInt(estId), contexto_adicional:ctx})
        });
        var d = await r.json();
        if (d.ok) {
            _acuerdoActual = d;
            document.getElementById('acuerdo-texto').textContent = d.contenido;
            document.getElementById('acuerdo-resultado').style.display = 'block';
            tk('Acuerdo generado: ' + d.numero, 'ok');
        } else { tk(d.error||'Error generando', 'err'); }
    } catch(e) { tk('Error: '+e.message, 'err'); }
    finally {
        document.getElementById('acuerdo-generando').style.display = 'none';
        document.getElementById('btn-generar-acuerdo').style.display = 'inline-flex';
    }
}

function copiarAcuerdo() {
    var txt = document.getElementById('acuerdo-texto').textContent;
    navigator.clipboard.writeText(txt).then(function(){ tk('Copiado al portapapeles', 'ok'); });
}

function guardarAcuerdo() {
    cerrarModal('modal-acuerdo');
    if (_casoActual) { cargarCasos(); verCaso(_casoActual.id); }
    tk('Acuerdo guardado en el expediente', 'ok');
}

async function verAcuerdo(acid) {
    var r    = await fetch('/api/acuerdo-compromiso/' + acid);
    var data = await r.json();
    document.getElementById('acuerdo-texto').textContent = data.contenido_completo || '';
    document.getElementById('acuerdo-resultado').style.display = 'block';
    document.getElementById('btn-generar-acuerdo').style.display = 'none';
    document.getElementById('modal-acuerdo').classList.add('open');
}

// ══════════════════════════════════════════════════════════════════════════════
// CERRAR CASO
// ══════════════════════════════════════════════════════════════════════════════
function cerrarModal2(casoId) {
    document.getElementById('cerrar-caso-id').value = casoId;
    document.getElementById('cerrar-desc').value    = '';
    document.getElementById('cerrar-sancion').value = '';
    document.getElementById('cerrar-seguimiento').value = 'ninguno';
    // Mostrar nivel del usuario que cierra
    var niveles = {1:'Orientación Psicológica', 2:'Coordinación', 3:'Dirección'};
    document.getElementById('cerrar-nivel-label').textContent = niveles[nivelUsuario] || 'Usuario';
    document.getElementById('modal-cerrar').classList.add('open');
}

async function cerrarCaso() {
    var casoId     = document.getElementById('cerrar-caso-id').value;
    var desc       = document.getElementById('cerrar-desc').value.trim();
    var sancion    = document.getElementById('cerrar-sancion').value;
    var seguimiento= document.getElementById('cerrar-seguimiento').value;
    if (!desc) { tk('Escribe la resolución final', 'err'); return; }
    try {
        var r = await fetch('/api/casos/' + casoId + '/cerrar', {
            method:'POST', headers:{'Content-Type':'application/json'},
            body: JSON.stringify({
                descripcion:  desc,
                sancion:      sancion,
                seguimiento:  seguimiento
            })
        });
        var d = await r.json();
        if (d.ok) {
            cerrarModal('modal-cerrar');
            tk('Caso cerrado y registrado en expediente', 'ok');
            await cargarCasos();
            if (_casoActual) verCaso(_casoActual.id);
        } else { tk(d.error || 'Error al cerrar', 'err'); }
    } catch(e) { tk('Error de conexión', 'err'); }
}

// ══════════════════════════════════════════════════════════════════════════════
// NOTIFICACIONES COUNT EN NAV
// ══════════════════════════════════════════════════════════════════════════════
async function cargarNotifCount() {
    try {
        var r = await fetch('/api/notificaciones/count');
        var d = await r.json();
        var badge = document.getElementById('nav-notif-count');
        if (d.total > 0) {
            badge.textContent = d.total;
            badge.style.display = 'inline';
        }
    } catch(e) {}
}

// Cerrar modales al click fuera
document.addEventListener('click', function(e) {
    ['modal-nuevo-caso','modal-accion','modal-acuerdo','modal-cerrar'].forEach(function(id) {
        var m = document.getElementById(id);
        if (e.target === m) m.classList.remove('open');
    });
});

// Init
document.addEventListener('DOMContentLoaded', function() {
    cargarCasos();
});