
// ======================================================================
//  profesor.js — PARTE 1/?? — versión corregida 2026
// ======================================================================

// Estado global
var ESTADOS = {};
var NOTAS_BUFFER = {};
var NOTAS_CARGADAS = {};
var _periodosEstado = { P1:false, P2:false, P3:false, P4:false };

// Toast elegante
function tk(msg, tipo = "info") {
    const t = document.getElementById("toast");
    if (!t) return alert(msg);

    t.textContent = msg;
    t.style.borderColor =
        tipo === "success" ? "rgba(77,255,180,.4)" :
        tipo === "error"   ? "rgba(255,77,77,.4)" :
                             "rgba(255,196,77,.4)";

    t.style.color =
        tipo === "success" ? "#4dffb4" :
        tipo === "error"   ? "#ff6b6b" :
                             "#ffc44d";

    t.classList.add("show");
    setTimeout(() => t.classList.remove("show"), 3000);
}



// ======================================================================
//  Sistema de Pestañas del Panel del Profesor
// ======================================================================

function showTab(name) {

    const tabs = ["pase", "historial", "resumen", "notas",
                  "plan", "cuaderno", "progreso", "estadisticas", "asignaciones"];

    tabs.forEach(t => {
        const el = document.getElementById("tab-" + t);
        if (el) el.style.display = (t === name ? "block" : "none");
    });

    document.querySelectorAll(".tab-btn").forEach(b => {
        b.classList.remove("active");
        if (b.textContent.toLowerCase().includes(name)) {
            b.classList.add("active");
        }
    });

    if (name === "historial") cargarHistorial();
    if (name === "notas") inicializarNotas();
    if (name === "cuaderno") initCuaderno();
    if (name === "progreso") initProgreso();
    if (name === "estadisticas") setTimeout(cargarEstadisticas, 50);
    if (name === "asignaciones") {
        if (typeof cargarAsignaciones === "function") cargarAsignaciones();
        if (typeof actualizarSugerencia === "function") actualizarSugerencia();
    }
}



// ======================================================================
//  PASE DE LISTA
// ======================================================================

function setEstado(btn, estado) {
    const row = btn.closest(".est-row");
    const id = parseInt(row.dataset.id);
    const obs = row.querySelector(".obs-inp").value;

    row.querySelectorAll(".asist-btn").forEach(b => b.classList.remove("sel"));
    btn.classList.add("sel");

    ESTADOS[id] = { estado, observacion: obs };
    actualizarContadores();
}

function marcarTodos(estado) {
    document.querySelectorAll(".est-row").forEach(row => {
        const btn = row.querySelector(".asist-btn." + estado[0]);
        if (btn) setEstado(btn, estado);
    });
}

function actualizarContadores() {
    const counts = { presente:0, tardanza:0, ausente:0, justificado:0 };
    const total = ESTUDIANTES.length;
    const marcados = Object.keys(ESTADOS).length;

    Object.values(ESTADOS).forEach(e => {
        if (counts[e.estado] !== undefined) counts[e.estado]++;
    });

    document.getElementById("cnt-p").textContent = "✔ " + counts.presente + " presentes";
    document.getElementById("cnt-t").textContent = "⏱ " + counts.tardanza + " tardanzas";
    document.getElementById("cnt-a").textContent = "✗ " + counts.ausente + " ausentes";
    document.getElementById("cnt-j").textContent = "📋 " + counts.justificado + " justificados";
    document.getElementById("cnt-sin-n").textContent = (total - marcados);
}



// ======================================================================
//  Guardar Asistencia — con manejo seguro de errores
// ======================================================================

async function guardarAsistencia() {

    const fecha = document.getElementById("lista-fecha").value;
    const materia = document.getElementById("lista-materia").value;
    const horas = parseInt(document.getElementById("lista-horas").value);
    const periodoStr = document.getElementById("lista-periodo").value;
    const periodo = parseInt(periodoStr.replace("P", ""));

    if (!fecha || !materia) {
        tk("Selecciona fecha y materia", "warn");
        return;
    }

    if (Object.keys(ESTADOS).length === 0) {
        tk("Marca al menos un estudiante", "warn");
        return;
    }

    const btn = document.getElementById("btn-guardar");
    btn.textContent = "Guardando…";
    btn.disabled = true;

    const registros = Object.entries(ESTADOS).map(([id, e]) => ({
        estudiante_id: parseInt(id),
        estado: e.estado,
        observacion: e.observacion
    }));

    try {

        const res = await fetch("/api/asistencia", {
            method: "POST",
            headers: { "Content-Type":"application/json" },
            body: JSON.stringify({
                fecha,
                materia,
                horas_clase: horas,
                periodo,
                registros
            })
        });

        const d = await res.json();

        if (d.ok) {
            tk("Asistencia guardada ✓", "success");
            ESTADOS = {};
            actualizarContadores();
            document.querySelectorAll(".asist-btn.sel").forEach(b => b.classList.remove("sel"));
        } else {
            tk(d.error || "Error al guardar", "error");
        }

    } catch (e) {
        tk("Error de conexión", "error");
    }

    btn.innerHTML = `<i class="fas fa-save"></i> Guardar lista`;
    btn.disabled = false;
}



// ======================================================================
//  Cargar Historial
// ======================================================================

async function cargarHistorial() {

    const materia = document.getElementById("hist-materia").value;
    const periodo = document.getElementById("hist-periodo").value;
    const desde = document.getElementById("hist-desde").value;
    const hasta = document.getElementById("hist-hasta").value;

    let url = `/api/asistencia?limit=200&`;

    if (materia) url += "materia=" + encodeURIComponent(materia) + "&";
    if (periodo) url += "periodo=" + periodo + "&";
    if (desde) url += "fecha_ini=" + desde + "&";
    if (hasta) url += "fecha_fin=" + hasta + "&";

    const tbody = document.getElementById("hist-body");
    tbody.innerHTML = `<tr>
        <td colspan="7" style="padding:20px;text-align:center;color:#777">
            Cargando…
        </td>
    </tr>`;

    try {
        const r = await fetch(url);
        const data = await r.json();

        if (!data.length) {
            tbody.innerHTML = `<tr>
                <td colspan="7" style="padding:20px;text-align:center;color:#777">
                    Sin registros
                </td>
            </tr>`;
            return;
        }

        tbody.innerHTML = data.map(r => `
            <tr>
                <td>${r.fecha}</td>
                <td><strong>${r.apellido}, ${r.nombre}</strong></td>
                <td>${r.materia}</td>
                <td><span class="est-tag ${r.estado}">${r.estado}</span></td>
                <td>${r.horas_clase} h</td>
                <td>P${r.periodo}</td>
                <td>${r.observacion || ""}</td>
            </tr>
        `).join("");

    } catch (e) {
        tbody.innerHTML = `<tr>
            <td colspan="7" style="color:#ff6b6b;padding:20px;text-align:center">
                Error cargando historial
            </td>
        </tr>`;
    }
}


// ======================================================================
//  INICIALIZACIÓN DE NOTAS
// ======================================================================

// Año escolar dinámico
function _anioEscolarActual() {
    const m = new Date().getMonth() + 1;
    const y = new Date().getFullYear();
    return m >= 8 ? `${y}-${y+1}` : `${y-1}-${y}`;
}

// Período actual automático
function _periodoActual() {
    const m = new Date().getMonth() + 1;
    if ([8,9,10].includes(m)) return "P1";
    if ([11,12,1].includes(m)) return "P2";
    if ([2,3,4].includes(m)) return "P3";
    return "P4";
}

// Colores para notas
function _colorNota(n) {
    if (n === null || n === "") return "#555";
    n = parseFloat(n);
    if (n >= 70) return "#4dffb4";
    if (n >= 50) return "#f7b731";
    return "#ff4d4d";
}

function _estadoNota(n) {
    if (n === null || n === "") return "";
    n = parseFloat(n);
    if (n >= 70) return "✓ Aprobado";
    if (n >= 50) return "⚡ Completiva";
    return "✗ Reprobado";
}


function inicializarNotas() {
    const anio = _anioEscolarActual();
    const prev = (parseInt(anio.split("-")[0]) - 1) + "-" + anio.split("-")[0];

    const sel = document.getElementById("notas-anio");
    sel.innerHTML = `
        <option value="${anio}">${anio} (actual)</option>
        <option value="${prev}">${prev}</option>
    `;

    document.getElementById("notas-periodo").value = _periodoActual();
    cargarTablaNotas();
}



// ======================================================================
//  CARGAR TABLA DE NOTAS — CON CORRECCIONES
// ======================================================================

async function cargarTablaNotas() {

    const materia = document.getElementById("notas-materia").value;
    const periodo = document.getElementById("notas-periodo").value;
    const anio = document.getElementById("notas-anio").value;

    const cont = document.getElementById("notas-table-container");
    const stats = document.getElementById("notas-stats");

    if (!materia || !periodo || !anio) return;

    NOTAS_BUFFER = {};
    NOTAS_CARGADAS = {};

    cont.innerHTML = `
        <div style="text-align:center;padding:20px;color:#777;font-size:12px;">
            <i class="fas fa-spinner fa-spin"></i> Cargando…
        </div>
    `;

    try {
        const url = `/api/calificaciones?materia=${encodeURIComponent(materia)}&periodo=${periodo}&anio=${anio}`;
        const res = await fetch(url);

        let notasArr;
        try {
            notasArr = await res.json();
        } catch (e) {
            cont.innerHTML = `<div style="color:#ff6b6b;padding:20px;">Error: respuesta inválida</div>`;
            return;
        }

        const notasMap = {};
        notasArr.forEach(n => {
            notasMap[n.estudiante_id] = n.calificacion;
        });

        NOTAS_CARGADAS = { ...notasMap };

        let aprobados = 0, completivas = 0, reprobados = 0, sinNota = 0;

        let html = `
            <table style="width:100%;border-collapse:collapse;font-size:12px;">
            <thead>
                <tr style="border-bottom:1px solid #222;">
                    <th>#</th>
                    <th>Estudiante</th>
                    <th>Grado</th>
                    <th>Nota ${periodo}</th>
                    <th>Estado</th>
                </tr>
            </thead>
            <tbody id="notas-tbody">
        `;

        ESTUDIANTES.forEach((est, i) => {

            let nota = notasMap[est.id] ?? "";
            if (nota !== "") {
                nota = parseFloat(nota);
                if (nota >= 70) aprobados++;
                else if (nota >= 50) completivas++;
                else reprobados++;
            } else sinNota++;

            const color = _colorNota(nota !== "" ? nota : null);
            const estado = _estadoNota(nota !== "" ? nota : null);

            html += `
                <tr style="border-bottom:1px solid #111;">
                    <td>${i+1}</td>
                    <td><strong>${est.apellido}, ${est.nombre}</strong></td>
                    <td style="text-align:center;">${est.grado}</td>

                    <td style="text-align:center;">
                        <input type="number" 
                               min="0" max="100" step="0.5"
                               data-est-id="${est.id}"
                               class="nota-input"
                               value="${nota !== "" ? nota : ""}"
                               oninput="onNotaInput(this)"
                               style="width:70px;text-align:center;color:${color};
                                      font-family:var(--font-mono);">
                    </td>

                    <td id="est-estado-${est.id}" 
                        style="text-align:center;color:${color}">
                        ${estado}
                    </td>
                </tr>
            `;
        });

        html += `</tbody></table>`;
        cont.innerHTML = html;

        stats.innerHTML = `
            <span class="badge green">✓ ${aprobados} aprobados</span>
            <span class="badge yellow">⚡ ${completivas} completivas</span>
            <span class="badge red">✗ ${reprobados} reprobados</span>
            <span class="badge gray">— ${sinNota} sin nota</span>
        `;

    } catch (e) {
        cont.innerHTML = `<div style="color:#ff6b6b;padding:20px;">Error cargando notas: ${e.message}</div>`;
    }
}



// ======================================================================
//  INPUT DE NOTA (actualiza estado visual)
// ======================================================================

function onNotaInput(input) {
    const id = parseInt(input.dataset.estId);
    let val = input.value.trim();

    if (val === "") {
        delete NOTAS_BUFFER[id];
        input.style.color = "#555";
        document.getElementById("est-estado-" + id).textContent = "";
        return;
    }

    let nota = parseFloat(val);

    if (isNaN(nota) || nota < 0 || nota > 100) {
        input.style.borderColor = "#ff4d4d";
        return;
    }

    input.style.borderColor = "#2a2a2a";
    input.style.color = _colorNota(nota);

    const estado = _estadoNota(nota);
    const estadoEl = document.getElementById("est-estado-" + id);

    estadoEl.textContent = estado;
    estadoEl.style.color = _colorNota(nota);

    NOTAS_BUFFER[id] = nota;
}
``

// ======================================================================
//  GUARDAR TODAS LAS NOTAS — CORREGIDO (antes CAUSABA BLOQUEOS)
// ======================================================================

async function guardarTodasNotas() {

    const materia = document.getElementById("notas-materia").value;
    const periodo = document.getElementById("notas-periodo").value;
    const anio = document.getElementById("notas-anio").value;
    const btn = document.getElementById("btn-guardar-notas");

    // Recoger TODOS los inputs válidos
    let batch = [];
    document.querySelectorAll(".nota-input").forEach(inp => {
        if (inp.value.trim() === "") return;

        const nota = parseFloat(inp.value);
        if (isNaN(nota) || nota < 0 || nota > 100) return;

        batch.push({
            estudiante_id: parseInt(inp.dataset.estId),
            materia,
            periodo,
            calificacion: nota,
            anio_escolar: anio
        });
    });

    if (batch.length === 0) {
        tk("No hay notas para guardar", "warn");
        return;
    }

    // Bloquear botón
    btn.disabled = true;
    btn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Guardando…`;

    try {
        const res = await fetch("/api/calificaciones", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(batch)
        });

        // ✅ Manejo seguro de respuesta JSON
        let d;
        try {
            d = await res.json();
        } catch (err) {
            tk("Error: respuesta inválida del servidor", "error");
            console.error("Respuesta:", await res.text());
            return;
        }

        // ✅ Si guardó correctamente
        if (d.ok || d.guardados > 0) {
            tk(`Guardadas ${d.guardados} notas de ${materia} (${periodo})`, "success");

            // Mostrar footer informativo
            const footer = document.getElementById("notas-footer");
            const msg = document.getElementById("notas-footer-msg");
            if (footer && msg) {
                footer.style.display = "flex";
                msg.textContent = `${d.guardados} notas guardadas — ${materia} ${periodo} ${anio}`;
                setTimeout(() => { footer.style.display = "none"; }, 6000);
            }

            NOTAS_BUFFER = {};

            // ✅ Recargar tabla correctamente
            await cargarTablaNotas();

        } else {
            // ✅ Evita congelamiento por stringify de objetos complejos
            if (Array.isArray(d.errores)) {
                d.errores.forEach(err => {
                    tk(err.mensaje || err || "Error al guardar notas", "error");
                });
            } else {
                tk("No se pudieron guardar las notas", "error");
            }
        }

    } catch (e) {
        tk("Error de conexión: " + e.message, "error");
    }

    // ✅ Siempre reactivar botón
    btn.disabled = false;
    btn.innerHTML = `<i class="fas fa-save"></i> Guardar Notas`;
}

/ ======================================================================
//  RESUMEN GLOBAL DE NOTAS POR ESTUDIANTE
// ======================================================================

async function cargarResumenNotas() {
    const estId = document.getElementById("notas-est-global").value;
    const cont = document.getElementById("notas-global-container");

    if (!estId) {
        cont.innerHTML = "";
        return;
    }

    cont.innerHTML = `
        <div style="text-align:center;padding:20px;color:#777;">
            <i class="fas fa-spinner fa-spin"></i> Cargando boletín…
        </div>
    `;

    try {
        const res = await fetch(`/api/calificaciones/boletin/${estId}`);
        const d = await res.json();

        if (!d.materias) throw new Error("Sin datos");

        const resumen = d.resumen;

        let html = `
            <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px;">
                <span class="badge green">✓ ${resumen.aprobadas} aprobadas</span>
                <span class="badge yellow">⚡ ${resumen.completivas} completivas</span>
                <span class="badge red">✗ ${resumen.reprobadas} reprobadas</span>
                ${
                    resumen.promueve
                    ? `<span class="badge green strong">📋 Promovido</span>`
                    : `<span class="badge red strong">⛔ Repite grado</span>`
                }
            </div>
        `;

        html += `
            <table class="tabla-boletin">
                <thead>
                    <tr>
                        <th>Materia</th>
                        <th>P1</th><th>P2</th><th>P3</th><th>P4</th>
                        <th>Final</th><th>Estado</th><th>Inasist.</th>
                    </tr>
                </thead>
                <tbody>
        `;

        d.materias.forEach(m => {
            const cFinal = _colorNota(m.nota_final);
            html += `
                <tr>
                    <td>${m.materia}</td>
                    <td style="color:${_colorNota(m.P1)}">${m.P1 ?? "—"}</td>
                    <td style="color:${_colorNota(m.P2)}">${m.P2 ?? "—"}</td>
                    <td style="color:${_colorNota(m.P3)}">${m.P3 ?? "—"}</td>
                    <td style="color:${_colorNota(m.P4)}">${m.P4 ?? "—"}</td>

                    <td style="color:${cFinal};font-weight:700;">${m.nota_final ?? "—"}</td>
                    <td style="color:${cFinal}">${_estadoNota(m.nota_final)}</td>

                    <td style="font-weight:700;color:${
                        m.reprueba_asistencia ? "#ff4d4d" :
                        m.alerta_asistencia   ? "#f7b731" :
                                                 "#777"
                    }">
                        ${m.pct_inasistencia}% ${
                            m.reprueba_asistencia ? "🚨" :
                            m.alerta_asistencia   ? "⚠️" : ""
                        }
                    </td>
                </tr>
            `;
        });

        html += `</tbody></table>`;
        cont.innerHTML = html;

    } catch (e) {
        cont.innerHTML = `
            <div style="color:#ff6b6b;padding:20px;">
                Error: ${e.message}
            </div>
        `;
    }
}



// ======================================================================
//  CUADERNO ANECDÓTICO
// ======================================================================

let CA_EST_ID = null;

function initCuaderno() {
    const d = new Date();
    const hoy = `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`;
    document.getElementById("ca-fecha").value = hoy;
}

function cargarCuaderno() {
    CA_EST_ID = document.getElementById("ca-estudiante").value;
    const cont = document.getElementById("ca-entradas");

    if (!CA_EST_ID) {
        document.getElementById("ca-lista").style.display = "none";
        return;
    }

    fetch(`/api/cuaderno/${CA_EST_ID}`)
        .then(r => r.json())
        .then(data => renderEntradas(data))
        .catch(() => tk("Error cargando entradas", "error"));
}

const TIPO_COLORES = {
    conductual: "#ef4444",
    emocional:  "#f59e0b",
    académico:  "#3b82f6",
    familiar:   "#f97316",
    otro:       "#6b7280"
};

const TIPO_EMOJIS = {
    conductual: "🔴",
    emocional:  "🟡",
    académico:  "🔵",
    familiar:   "🟠",
    otro:       "⚪"
};

function renderEntradas(entradas) {
    const lista = document.getElementById("ca-lista");
    const cont = document.getElementById("ca-entradas");

    lista.style.display = entradas.length ? "block" : "none";

    if (!entradas.length) {
        cont.innerHTML = `<div style="color:var(--muted);font-size:12px;">Sin entradas para este estudiante.</div>`;
        return;
    }

    cont.innerHTML = entradas.map(e => {
        const col = TIPO_COLORES[e.tipo] ?? "#6b7280";
        const emo = TIPO_EMOJIS[e.tipo] ?? "⚪";

        return `
        <div class="cuad-item" style="border-left:3px solid ${col}">
            <div class="cuad-top">
                <span class="cuad-tipo" style="color:${col}">
                    ${emo} ${e.tipo.toUpperCase()}
                </span>
                <span class="cuad-fecha">${e.fecha}</span>
                ${
                    e.convertido_reporte
                    ? `<span class="cuad-badge">📋 En perfil</span>`
                    : `<button class="cuad-btn"
                               onclick="convertirReporte(${e.id})">→ Convertir en reporte</button>`
                }
            </div>

            <div class="cuad-desc">${e.descripcion}</div>

            ${
                e.seguimiento
                ? `<div class="cuad-seg"><b>Seguimiento:</b> ${e.seguimiento}</div>`
                : ""
            }

            <div class="cuad-autor">Por: ${e.autor_nombre}</div>
        </div>`;
    }).join("");
}

async function guardarEntradaCuaderno() {
    const estId = document.getElementById("ca-estudiante").value;
    const desc  = document.getElementById("ca-descripcion").value.trim();

    if (!estId)  return tk("Selecciona un estudiante", "error");
    if (!desc)   return tk("La descripción es requerida", "warn");

    try {
        const res = await fetch("/api/cuaderno", {
            method: "POST",
            headers: { "Content-Type":"application/json" },
            body: JSON.stringify({
                estudiante_id: parseInt(estId),
                tipo: document.getElementById("ca-tipo").value,
                fecha: document.getElementById("ca-fecha").value,
                descripcion: desc,
                seguimiento: document.getElementById("ca-seguimiento").value.trim(),
                privado: document.getElementById("ca-privado").checked ? 1 : 0
            })
        });

        const d = await res.json();

        if (d.ok) {
            tk("Entrada guardada ✓", "success");
            document.getElementById("ca-descripcion").value = "";
            document.getElementById("ca-seguimiento").value = "";
            document.getElementById("ca-privado").checked = false;
            cargarCuaderno();
        } else {
            tk(d.error || "Error al guardar", "error");
        }

    } catch (e) {
        tk("Error de conexión", "error");
    }
}

async function convertirReporte(id) {
    if (!confirm("¿Convertir esta entrada en reporte?")) return;

    try {
        const r = await fetch(`/api/cuaderno/${id}/convertir-reporte`, {
            method: "POST"
        });

        const d = await r.json();

        if (d.ok) {
            tk("Convertido en reporte ✓", "success");
            cargarCuaderno();
        } else {
            tk(d.error || "No se pudo convertir", "error");
        }

    } catch (e) {
        tk("Error de conexión", "error");
    }
}

// ======================================================================
//  PROGRESO ESTUDIANTIL (KPIs + Materias + Asistencia + Narrativas)
// ======================================================================

let PG_EST_ID = null;

function initProgreso() {
    /* se activa al seleccionar estudiante */
}

function cargarProgreso() {
    PG_EST_ID = document.getElementById("pg-estudiante").value;
    const cont = document.getElementById("pg-contenido");

    if (!PG_EST_ID) {
        cont.style.display = "none";
        return;
    }

    fetch(`/api/progreso/${PG_EST_ID}`)
        .then(r => r.json())
        .then(d => { renderProgreso(d); cont.style.display = "block"; })
        .catch(() => tk("Error cargando progreso", "error"));
}

function bc2(v) {
    const dark = document.documentElement.getAttribute("data-theme") !== "light";
    if (!v && v !== 0) return "var(--muted)";
    if (dark) return v >= 85 ? "#4dffb4" : v >= 70 ? "#378ADD" : "#ff4d4d";
    return v >= 85 ? "#2563EB" : v >= 70 ? "#0284C7" : "#EF4444";
}

function renderProgreso(d) {

    const est = d.estudiante;
    const mats = d.materias || [];
    const acad = mats.filter(m => m.tipo === "académico" && m.promedio > 0);
    const tecn = mats.filter(m => m.tipo === "técnico" && m.promedio > 0);

    const promAcad = acad.length ? (acad.reduce((s,m)=>s+m.promedio,0)/acad.length).toFixed(1) : "—";
    const promTecn = tecn.length ? (tecn.reduce((s,m)=>s+m.promedio,0)/tecn.length).toFixed(1) : "—";

    const asist = d.asistencia || [];
    const promAsist = asist.length
        ? (asist.reduce((s,a)=>s+(a.porcentaje||0),0) / asist.length).toFixed(1) + "%"
        : "—";

    const cuadCnt = (d.cuaderno || {}).total_entradas || 0;

    document.getElementById("pg-kpis").innerHTML = [
        {lbl:"Prom. Académico", val: promAcad, col: bc2(parseFloat(promAcad))},
        {lbl:"Prom. Técnico", val: promTecn, col: bc2(parseFloat(promTecn))},
        {lbl:"Asistencia", val: promAsist, col: "#3b82f6"},
        {lbl:"Observaciones", val: cuadCnt, col: "#f59e0b"},
    ].map(k => `
        <div class="pg-kpi">
            <div class="pg-kpi-val" style="color:${k.col}">${k.val}</div>
            <div class="pg-kpi-label">${k.lbl}</div>
        </div>
    `).join("");

    // Tabla de materias
    let html = `
        <table class="pg-table">
            <thead>
                <tr>
                    <th>Materia</th><th>Tipo</th>
                    <th>P1</th><th>P2</th><th>P3</th><th>P4</th>
                    <th>Prom.</th>
                </tr>
            </thead>
            <tbody>
    `;

    mats.forEach(m => {
        html += `
            <tr>
                <td>${m.materia}</td>
                <td><span class="pg-tag">${m.tipo}</span></td>
                <td style="color:${bc2(m.p1)}">${m.p1 || "—"}</td>
                <td style="color:${bc2(m.p2)}">${m.p2 || "—"}</td>
                <td style="color:${bc2(m.p3)}">${m.p3 || "—"}</td>
                <td style="color:${bc2(m.p4)}">${m.p4 || "—"}</td>
                <td style="color:${bc2(m.promedio)};font-weight:700">${m.promedio || "—"}</td>
            </tr>
        `;
    });

    html += "</tbody></table>";

    document.getElementById("pg-materias").innerHTML = mats.length ? html :
        `<div class="pg-empty">Sin calificaciones registradas.</div>`;

    // Asistencia mensual
    const MESES = ["","Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"];

    const aHtml = asist.length ? asist.map(a => `
        <div class="pg-asist-item">
            <div class="pg-asist-pct" style="color:${
                a.porcentaje >= 85 ? "#22c55e" :
                a.porcentaje >= 70 ? "#f59e0b" : "#ef4444"
            }">${a.porcentaje.toFixed(0)}%</div>
            <div class="pg-asist-mes">${MESES[a.mes]} ${a.anio}</div>
            <div class="pg-asist-det">${a.dias_asistio}/${a.dias_clase_impartidos} días</div>
            ${a.validado ? `<div class="pg-asist-valid">✓ Validado</div>` : ""}
        </div>
    `).join("") : `<div class="pg-empty">Sin registros de asistencia mensual.</div>`;

    document.getElementById("pg-asistencia").innerHTML = aHtml;

    // Narrativas previas
    const narr = d.evaluaciones_narrativas || [];
    document.getElementById("pg-narrativas-prev").innerHTML = narr.length
        ? narr.map(n => `
            <div class="pg-narr-item">
                <div class="pg-narr-top">Período ${n.periodo} — ${n.profesor_nombre}</div>
                <div class="pg-narr-text">${n.texto}</div>
            </div>
        `).join("")
        : "";

    // Cuaderno reciente
    const cuad = (d.cuaderno || {}).recientes || [];
    document.getElementById("pg-cuaderno-prev").innerHTML = cuad.length
        ? cuad.map(c => `
            <div class="pg-cuad-item" style="border-left-color:${TIPO_COLORES[c.tipo] || "#6b7280"}">
                <div class="pg-cuad-head">${c.fecha} · ${c.autor}</div>
                <div class="pg-cuad-text">${c.descripcion}</div>
            </div>
        `).join("")
        : `<div class="pg-empty">Sin observaciones anecdóticas.</div>`;
}

function guardarNarrativa() {
    if (!PG_EST_ID) return tk("Selecciona un estudiante", "error");

    const texto = document.getElementById("pg-narrativa").value.trim();
    if (!texto) return tk("Escribe la evaluación", "warn");

    fetch("/api/evaluacion-narrativa", {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({
            estudiante_id: parseInt(PG_EST_ID),
            periodo: parseInt(document.getElementById("pg-periodo").value),
            texto
        })
    })
    .then(r => r.json())
    .then(d => {
        if (d.ok) {
            tk("Evaluación guardada ✓", "success");
            cargarProgreso();
        } else tk(d.error || "No se pudo guardar", "error");
    });
}



// ======================================================================
//  ESTADÍSTICAS DEL PROFESOR
// ======================================================================

let _estPeriod = "semana";

function setEstPeriod(p) {
    _estPeriod = p;

    document.querySelectorAll(".est-period-btn").forEach(btn => {
        const active = btn.textContent.toLowerCase().includes(
            p === "semana" ? "semana" :
            p === "mes"    ? "mes" :
            p === "periodo"? "per" : "año"
        );

        btn.classList.toggle("active", active);
        btn.style.color = active ? "var(--accent)" : "var(--muted)";
    });

    const wrap = document.getElementById("est-fecha-wrap");
    if (wrap) wrap.style.display = (p === "anio" ? "none" : "block");

    cargarEstadisticas();
}

function cargarEstadisticas() {

    const materia = document.getElementById("est-materia").value;
    const fecha = document.getElementById("est-fecha")?.value || "";

    const loading = document.getElementById("est-loading");
    const empty = document.getElementById("est-empty");
    const tabla = document.getElementById("est-tabla");
    const kpis = document.getElementById("est-kpis");

    if (loading) loading.style.display = "block";
    if (empty) empty.style.display = "none";
    if (tabla) tabla.style.display = "none";
    if (kpis) kpis.innerHTML = "";

    const params = new URLSearchParams({
        periodo: _estPeriod,
        fecha,
        materia
    });

    fetch(`/api/profesor/estadisticas-asistencia?${params}`)
        .then(r => r.json())
        .then(d => {
            if (loading) loading.style.display = "none";

            if (!d.estudiantes || d.estudiantes.length === 0) {
                if (empty) empty.style.display = "block";
                return;
            }

            // KPIs
            const arr = [
                {label:"Total días", val:d.resumen.total_dias, icon:"📅", color:"var(--accent)"},
                {label:"Prom. asist.", val:d.resumen.pct_promedio+"%", icon:"✅", color:"#4dffb4"},
                {label:"Estudiantes", val:d.resumen.total_est, icon:"👥", color:"var(--muted)"},
                {label:"≥ 80% asist.", val:d.resumen.sobre_80, icon:"⭐", color:"#4dffb4"},
                {label:"Con alerta", val:d.resumen.con_alerta, icon:"⚠️", color:"#ffc44d"},
                {label:"En riesgo", val:d.resumen.en_riesgo, icon:"🚨", color:"#ff6b6b"}
            ];

            if (kpis) {
                kpis.innerHTML = arr.map(k => `
                    <div class="est-kpi">
                        <div class="est-kpi-icon">${k.icon}</div>
                        <div class="est-kpi-val" style="color:${k.color}">${k.val}</div>
                        <div class="est-kpi-label">${k.label}</div>
                    </div>
                `).join("");
            }

            // Tabla
            const tbody = document.getElementById("est-tbody");
            tbody.innerHTML = d.estudiantes.map(e => {
                const pct = e.pct_asistencia || 0;
                const pctColor = pct >= 80 ? "#4dffb4" : pct >= 70 ? "#ffc44d" : "#ff6b6b";

                return `
                    <tr class="est-stat-row" data-id="${e.id}">
                        <td>
                            <div class="est-avatar">${(e.nombre||"?")[0].toUpperCase()}${(e.apellido||"?")[0].toUpperCase()}</div>
                            <div class="est-info">
                                <div class="est-name">${e.apellido}, ${e.nombre}</div>
                                <div class="est-grade">${e.grado}${e.seccion ? " · Sec. "+e.seccion : ""}</div>
                            </div>
                        </td>
                        <td class="est-num green">${e.presentes || 0}</td>
                        <td class="est-num red">${e.ausentes || 0}</td>
                        <td class="est-num yellow">${e.tardanzas || 0}</td>

                        <td class="est-bar-cell">
                            <div class="est-pct" style="color:${pctColor}">${pct}%</div>
                            <div class="est-bar">
                                <div class="est-bar-fill" style="width:${pct}%;background:${pctColor}"></div>
                            </div>
                        </td>

                        <td class="est-status">
                            ${
                                pct >= 80
                                ? `<span class="est-tag green2">✓ Regular</span>`
                                : pct >= 70
                                ? `<span class="est-tag yellow2">⚠ Observación</span>`
                                : `<span class="est-tag red2">🚨 En riesgo</span>`
                            }
                        </td>

                        <td>
                            <a href="/perfil/${e.id}" onclick="event.stopPropagation()" class="est-btn">
                                👤
                            </a>
                        </td>
                    </tr>
                `;
            }).join("");

            if (tabla) tabla.style.display = "table";

        })
        .catch(err => {
            if (loading) loading.style.display = "none";
            if (empty) {
                empty.style.display = "block";
                empty.innerHTML = `
                    <div style="font-size:32px;margin-bottom:10px;">⚠️</div>
                    Error cargando datos<br>
                    <span style="color:#ff6b6b;font-size:11px">${err}</span>
                `;
            }
        });
}



// ======================================================================
//  PERÍODOS P1–P4 (Bloqueo/Desbloqueo) — CORREGIDO
// ======================================================================

function cargarEstadoPeriodos() {
    fetch("/api/periodos/estado")
        .then(r => r.json())
        .then(d => {
            if (d.periodos) {
                _periodosEstado = d.periodos;
                verificarBloqueoNotas();
                actualizarBadgesPeriodos();
            }
        })
        .catch(() => {});
}

function verificarBloqueoNotas() {
    const periodoSel = document.getElementById("notas-periodo");
    const periodo = periodoSel ? periodoSel.value : "P1";

    const bloqueado = _periodosEstado[periodo] === true;

    const strip = document.getElementById("notas-lock-strip");
    const btnSave = document.getElementById("btn-guardar-notas");

    if (strip) strip.classList.toggle("visible", bloqueado);

    if (btnSave) {
        btnSave.disabled = bloqueado;
        btnSave.title = bloqueado ? "Período bloqueado" : "Guardar notas";
        btnSave.style.opacity = bloqueado ? "0.4" : "1";
    }

    document.querySelectorAll('#notas-tbody input[type="number"]').forEach(inp => {
        inp.disabled = bloqueado;
    });
}

function actualizarBadgesPeriodos() {
    const sel = document.getElementById("notas-periodo");
    if (!sel) return;

    Array.from(sel.options).forEach(opt => {
        const val = opt.value;
        const pk = val.toUpperCase();
        const locked = _periodosEstado[pk];

        opt.text = opt.text.replace(" 🔒", "").replace(" ✓", "");
        if (locked) opt.text += " 🔒";
    });
}



// ======================================================================
//  EVENTOS DELEGADOS
// ======================================================================

// Click en convertir cuaderno → reporte
document.addEventListener("click", ev => {
    const btn = ev.target.closest(".btn-convertir-rep");
    if (btn && btn.dataset.id) {
        ev.stopPropagation();
        convertirReporte(parseInt(btn.dataset.id));
    }
});

// Click en estadística → ir al perfil
document.addEventListener("click", ev => {
    const row = ev.target.closest(".est-stat-row");
    if (row && row.dataset.id) {
        window.location.href = `/perfil/${row.dataset.id}`;
    }
});



// ======================================================================
//  CARGA INICIAL
// ======================================================================

document.addEventListener("DOMContentLoaded", () => {
    cargarEstadoPeriodos();
});

// ======================================================================
//  AUTO-HORAS POR MATERIA (completa horas según la materia seleccionada)
// ======================================================================

function onMateriaChange() {
    const sel = document.getElementById("lista-materia");
    if (!sel) return;

    const opt = sel.options[sel.selectedIndex];
    const horas = opt ? opt.getAttribute("data-horas") : null;

    if (horas) {
        const horasSel = document.getElementById("lista-horas");
        if (horasSel) horasSel.value = horas;
    }

    verificarListaHoy();
}

// ======================================================================
//  VERIFICAR SI YA SE PASÓ LISTA HOY — CORREGIDO
// ======================================================================

async function verificarListaHoy() {
    const materia = document.getElementById("lista-materia");
    if (!materia) return;

    const hoy = new Date().toISOString().split("T")[0];

    try {
        const r = await fetch(`/api/asistencia?fecha_ini=${hoy}&fecha_fin=${hoy}&materia=${encodeURIComponent(materia.value)}`);
        const data = await r.json();

        const indicator = document.getElementById("lista-hoy-indicator");
        if (!indicator) return;

        if (data && data.length > 0) {
            indicator.innerHTML = `
                <span class="badge green2">
                    <i class="fas fa-circle-check"></i> Lista ya registrada hoy — puedes editarla
                </span>
            `;
        } else {
            indicator.innerHTML = `
                <span class="badge yellow2">
                    <i class="fas fa-clock"></i> Lista pendiente para hoy
                </span>
            `;
        }

    } catch (e) {
        // Silencioso para no interferir
    }
}

// ======================================================================
//  AUTO-SETEAR FECHA DE HOY PARA PASAR LISTA
// ======================================================================

document.getElementById("lista-fecha").value =
    new Date().toISOString().split("T")[0];

// ======================================================================
//  INICIALIZACIÓN FINAL DEL MÓDULO
// ======================================================================

document.addEventListener("DOMContentLoaded", () => {

    // Corrección de período por defecto (P1–P4)
    const periodoSel = document.getElementById("lista-periodo");
    if (periodoSel) {
        const pActual = _periodoActual();
        periodoSel.innerHTML = `
            <option value="P1" ${pActual === "P1" ? "selected" : ""}>P1 — Primer Período</option>
            <option value="P2" ${pActual === "P2" ? "selected" : ""}>P2 — Segundo Período</option>
            <option value="P3" ${pActual === "P3" ? "selected" : ""}>P3 — Tercer Período</option>
            <option value="P4" ${pActual === "P4" ? "selected" : ""}>P4 — Cuarto Período</option>
        `;
    }

    // Verifica si ya hay una lista registrada hoy
    verificarListaHoy();

    // Cargar estado de períodos bloqueados (notas)
    cargarEstadoPeriodos();
});


// ✅ FIN DEL ARCHIVO — profesor.js COMPLETO Y CORREGIDO
// ======================================================================
