
// ======================================================================
//  perfil.js — PARTE 1/5 (versión corregida 2026)
// ======================================================================

// ----------------------------------------------------------------------
// PROTECCIÓN CSRF PARA TODAS LAS PETICIONES (Corregido)
// ----------------------------------------------------------------------
(function () {
    const _originalFetch = window.fetch;

    window.fetch = function (url, opts = {}) {
        const method = (opts.method || "GET").toUpperCase();

        if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
            opts.headers = opts.headers || {};

            // Soporta Headers o plain object
            if (opts.headers instanceof Headers) {
                opts.headers.set("X-CSRF-Token", CSRF_TOKEN);
            } else {
                opts.headers["X-CSRF-Token"] = CSRF_TOKEN;
            }
        }
        return _originalFetch(url, opts);
    };
})();


// ======================================================================
//  BLOQUE 1 — BOLETÍN DEL ESTUDIANTE (CORREGIDO)
// ======================================================================
(function loadBoletin() {

    // Colores para notas
    function notaColor(v) {
        if (v === null || v === undefined || v === "") return "#444";
        v = parseFloat(v);
        if (v >= 70) return "#4dffb4";
        if (v >= 50) return "#f0c060";
        return "#ff6b6b";
    }

    function notaBG(v) {
        if (v === null || v === undefined || v === "") return "transparent";
        v = parseFloat(v);
        if (v >= 70) return "rgba(77,255,180,.08)";
        if (v >= 50) return "rgba(240,192,96,.1)";
        return "rgba(255,77,77,.1)";
    }

    function fmt(v) {
        if (v === null || v === undefined || v === "") return "—";
        return (Math.round(v * 10) / 10) + "";
    }

    // Crea el texto del estado
    function estadoBadge(estado, pctInasist) {
        let badge = "";

        if (pctInasist !== null && pctInasist >= 20) {
            badge += "🚨 Asistencia · ";
        }

        if (estado === "aprobado") badge += "✓ Aprobado";
        else if (estado === "completiva") badge += "⚠ Completiva";
        else if (estado === "reprobado") badge += "✗ Reprobado";
        else badge += "— Sin nota";

        return badge;
    }

    // ------------------------------------------------------------------
    // CARGA PRINCIPAL DEL BOLETÍN
    // ------------------------------------------------------------------
    fetch("/api/calificaciones/boletin/" + estId)
        .then(r => r.json())
        .then(d => {

            document.getElementById("boletin-loading").style.display = "none";

            if (!d || !d.materias) {
                const err = document.getElementById("boletin-error");
                err.style.display = "block";
                err.innerHTML = "Sin calificaciones registradas aún para este estudiante.";
                return;
            }

            // Año escolar
            if (d.anio_escolar) {
                document.getElementById("boletin-anio").textContent =
                    "Año Escolar " + d.anio_escolar;
            }

            // ------------------------------------------------------------------
            // RESUMEN
            // ------------------------------------------------------------------
            const total   = d.materias.length;
            const aprob   = d.materias.filter(m => m.estado === "aprobado").length;
            const compl   = d.materias.filter(m => m.estado === "completiva").length;
            const repr    = d.materias.filter(m => m.estado === "reprobado").length;
            const riesgoA = d.materias.filter(m => (m.pct_inasistencia_injustificada ?? 0) >= 20).length;

            let summaryHTML = `<div class="boletin-summary-block">`;
            summaryHTML += `<div class="sum-ok">✓ Aprobadas: ${aprob}</div>`;
            if (compl > 0) summaryHTML += `<div class="sum-warn">⚠ Completivas: ${compl}</div>`;
            if (repr > 0)  summaryHTML += `<div class="sum-danger">✗ Reprobadas: ${repr}</div>`;
            if (riesgoA > 0) summaryHTML += `<div class="sum-risk">🚨 Riesgo asistencia: ${riesgoA}</div>`;
            summaryHTML += `</div>`;

            const summaryEl = document.getElementById("boletin-summary");
            summaryEl.innerHTML = summaryHTML;
            summaryEl.style.display = "block";

            // ------------------------------------------------------------------
            // TABLA DE MATERIAS
            // ------------------------------------------------------------------
            const tbody = document.getElementById("boletin-tbody");
            const rows = d.materias.map((m, i) => {

                const pct = m.pct_inasistencia_injustificada;
                const asistColor =
                    pct == null ? "#444"
                    : pct >= 20 ? "#ff6b6b"
                    : pct >= 15 ? "#f0c060"
                    : "#4dffb4";

                const asistTexto =
                    pct == null ? "—"
                    : (pct >= 20 ? "🚨 " : pct >= 15 ? "⚠️ " : "✓ ")
                        + (100 - pct).toFixed(0) + "%";

                const rowBg = i % 2 === 0 ? "rgba(255,255,255,.02)" : "transparent";

                return `
                    <tr style="background:${rowBg}">
                        <td>${m.materia}</td>
                        <td style="color:${notaColor(m.p1)}">${fmt(m.p1)}</td>
                        <td style="color:${notaColor(m.p2)}">${fmt(m.p2)}</td>
                        <td style="color:${notaColor(m.p3)}">${fmt(m.p3)}</td>
                        <td style="color:${notaColor(m.p4)}">${fmt(m.p4)}</td>
                        
                        <td>${fmt(m.promedio)}</td>
                        
                        <td style="color:${asistColor};font-weight:600">
                            ${asistTexto}
                        </td>

                        <td>${estadoBadge(m.estado, pct)}</td>
                    </tr>`;
            }).join("");

            tbody.innerHTML = rows;

            document.getElementById("boletin-tabla").style.display = "block";
            document.getElementById("boletin-leyenda").style.display = "flex";
        })
        .catch(() => {
            document.getElementById("boletin-loading").style.display = "none";
            const err = document.getElementById("boletin-error");
            err.style.display = "block";
            err.textContent = "No se pudo cargar el boletín.";
        });

})();

// ======================================================================
//  PARTE 2 — Indicadores IA del Estudiante (Corregido)
// ======================================================================

// Si hay análisis anterior, se muestra automáticamente
if (typeof PLAN_GUARDADO !== "undefined" && PLAN_GUARDADO) {
    mostrarPlan(PLAN_GUARDADO, true);
}

// ----------------------------------------------------------------------
// GENERAR ANÁLISIS IA DEL ESTUDIANTE
// ----------------------------------------------------------------------
async function generarPlan(forzar = false) {

    setEstadoIA("cargando");

    try {
        const res = await fetch(`/api/analisis-ia/${ESTUDIANTE_ID}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ forzar })
        });

        const data = await res.json();

        if (data.error) {
            return setEstadoIA("error", data.error);
        }

        mostrarPlan(data.analisis, data.cached);

    } catch (e) {
        setEstadoIA("error", "No se pudo conectar con el servidor.");
    }
}


// ----------------------------------------------------------------------
// RENDER DEL ANÁLISIS — FORMATO CORREGIDO 2026
// ----------------------------------------------------------------------
function mostrarPlan(texto, desdeCache) {

    if (!texto) texto = "";

    const out = document.getElementById("ia-texto");
    const badge = document.getElementById("cache-badge");

    if (out) out.innerHTML = formatearAnalisis(texto);
    if (badge) badge.innerHTML = desdeCache ? "Desde caché" : "Recién generado";

    setEstadoIA("resultado");
}


// ----------------------------------------------------------------------
// FORMATEO INTELIGENTE DEL ANÁLISIS
// ----------------------------------------------------------------------
function formatearAnalisis(texto) {

    if (!texto) return "";

    // Configuración de colores/íconos para secciones IA
    const secciones = {
        "DIAGNOSTICO":     { color: "#4bbfe8", icon: "🔍" },
        "DIAGNÓSTICO":     { color: "#4bbfe8", icon: "🔍" },
        "SENALES":         { color: "#e85b4b", icon: "⚠️" },
        "SEÑALES":         { color: "#e85b4b", icon: "⚠️" },
        "RECOMENDACIONES": { color: "#4be87a", icon: "💡" },
        "PLAN":            { color: "#e8b84b", icon: "🎯" },
        "SEGUIMIENTO":     { color: "#b44be8", icon: "📊" }
    };

    function detectarSeccion(titulo) {
        const t = titulo
            .toUpperCase()
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, ""); // eliminar acentos

        for (let k in secciones) {
            const kk = k
                .normalize("NFD")
                .replace(/[\u0300-\u036f]/g, "");

            if (t.startsWith(kk)) return secciones[k];
        }

        return { color: "var(--accent)", icon: "►" };
    }

    let html = "";
    let lineas = texto.split("\n");
    let enBloque = false;

    for (let linea of lineas) {

        // Detecta encabezados tipo “1. DIAGNÓSTICO”
        const m = linea.match(/^(\d+)\.\s+(.+)$/);
        if (m) {
            if (enBloque) html += `</div>`;

            const cfg = detectarSeccion(m[2]);

            html += `
                <div class="ia-section-block">
                    <div class="ia-section-title" style="color:${cfg.color}">
                        ${cfg.icon} ${m[1]}. ${m[2]}
                    </div>
            `;
            enBloque = true;
            continue;
        }

        // Viñetas tipo "- texto" o "• texto"
        if (/^[\-\u2022]\s+/.test(linea)) {
            html += `
                <div class="ia-bullet">► ${linea.replace(/^[\-\u2022]\s+/, "")}</div>
            `;
            continue;
        }

        // Línea vacía → salto
        if (linea.trim() === "") {
            html += `<div class="ia-gap"></div>`;
            continue;
        }

        // Texto normal
        html += `<div class="ia-line">${linea}</div>`;
    }

    if (enBloque) html += `</div>`;

    return html;
}


// ----------------------------------------------------------------------
// ESTADO DE LA INTERFAZ IA
// ----------------------------------------------------------------------
function setEstadoIA(estado, errorMsg = "") {

    const sin = document.getElementById("ia-sin-generar");
    const carg = document.getElementById("ia-cargando");
    const res = document.getElementById("ia-resultado");
    const err = document.getElementById("ia-error");

    if (sin) sin.style.display = (estado === "idle" ? "block" : "none");
    if (carg) carg.style.display = (estado === "cargando" ? "block" : "none");
    if (res) res.style.display = (estado === "resultado" ? "block" : "none");
    if (err) err.style.display = (estado === "error" ? "block" : "none");

    if (estado === "error") {
        const msg = document.getElementById("ia-error-msg");
        if (msg) msg.textContent = errorMsg;
    }
}

// ======================================================================
//  PARTE 3 — Indicadores por Materia + Tabs dinámicos (corregido)
// ======================================================================

let materiasDisponibles = [];
let materiaActiva = null;

// ----------------------------------------------------------------------
// CARGAR LISTA DE MATERIAS PARA INDICADORES
// ----------------------------------------------------------------------
async function cargarIndicadoresMaterias() {
    try {
        const res = await fetch('/api/indicadores/materias/' + EST_ID);
        if (!res.ok) {
            materiasDisponibles = [];
            return;
        }

        materiasDisponibles = await res.json();

        // Notificar que materias están listas
        window._materiasListas = materiasDisponibles;
        document.dispatchEvent(
            new CustomEvent("materiasListas", { detail: materiasDisponibles })
        );

        const tabsEl = document.getElementById("materia-tabs");
        if (!tabsEl) return;

        // No hay materias
        if (!materiasDisponibles.length) {
            const sd = document.getElementById("ind-sin-datos");
            if (sd) sd.style.display = "block";
            return;
        }

        const sd2 = document.getElementById("ind-sin-datos");
        if (sd2) sd2.style.display = "none";

        // Limpiar
        tabsEl.innerHTML = "";

        // Paleta opcional
        const colores = {
            "Fotografía": "#4bbfe8",
            "Lenguaje_Visual": "#b44be8",
            "Diseño": "#e8b84b"
        };

        // Crear botones de materias
        materiasDisponibles.forEach(m => {
            const c = colores[m.materia] || "var(--accent)";
            const label = m.materia.replace("_", " ");

            const btn = document.createElement("button");
            btn.id = "tab-" + m.materia;
            btn.textContent = label;
            btn.className = "materia-tab-btn";

            btn.addEventListener("mouseover", function () {
                if (materiaActiva !== m.materia)
                    this.style.borderColor = c;
            });

            btn.addEventListener("mouseout", function () {
                if (materiaActiva !== m.materia)
                    this.style.borderColor = "var(--border)";
            });

            btn.addEventListener("click", () => verMateria(m.materia));

            tabsEl.appendChild(btn);
        });

        // Abrir la primera materia por defecto
        verMateria(materiasDisponibles[0].materia);

    } catch (e) {
        console.error("Error cargando indicadores:", e);
    }
}


// ----------------------------------------------------------------------
// VER UNA MATERIA (Carga gráficos, barras, indicadores)
// ----------------------------------------------------------------------
async function verMateria(materia) {

    materiaActiva = materia;

    const colores = {
        "Fotografía": "#4bbfe8",
        "Lenguaje_Visual": "#b44be8",
        "Diseño": "#e8b84b"
    };

    const activoColor = colores[materia] || "var(--accent)";

    // Actualizar estilos de pestañas
    materiasDisponibles.forEach(m => {
        const btn = document.getElementById("tab-" + m.materia);
        if (!btn) return;

        if (m.materia === materia) {
            btn.style.borderColor = activoColor;
            btn.style.color = activoColor;
            btn.style.background = "rgba(75,191,232,.08)";
        } else {
            btn.style.borderColor = "var(--border)";
            btn.style.color = "var(--text-muted)";
            btn.style.background = "transparent";
        }
    });

    // Fetch de indicadores
    const res = await fetch('/api/indicadores/' + EST_ID +
        '?materia=' + encodeURIComponent(materia));

    const indicadores = await res.json();

    const cont = document.getElementById("ind-contenido");
    if (cont) cont.style.display = "block";

    // ------------------------------------------------------------------
    // Promedios por período (P1–P4)
    // ------------------------------------------------------------------
    function promPeriodo(p) {
        const vals = indicadores
            .map(ind => ind[p])
            .filter(v => v !== null && v !== undefined);

        return vals.length
            ? Math.round(vals.reduce((a, b) => a + b) / vals.length * 10) / 10
            : null;
    }

    const promedios = {
        p1: promPeriodo("p1"),
        p2: promPeriodo("p2"),
        p3: promPeriodo("p3"),
        p4: promPeriodo("p4")
    };

    // Colorear barras
    ["p1", "p2", "p3", "p4"].forEach(p => {
        const val = promedios[p];
        const bar = document.getElementById("bar-" + p);
        const lbl = document.getElementById("bar-" + p + "-label");

        if (!bar || !lbl) return;

        if (val !== null) {
            const pct = (val / 100) * 80; // altura máxima 80px
            setTimeout(() => {
                bar.style.height = pct + "px";
                bar.style.background =
                    val >= 80 ? "#4be87a" :
                    val >= 70 ? "#e8b84b" : "#e85b4b";
            }, 100);

            lbl.textContent = val + "%";
            lbl.style.color =
                val >= 80 ? "#4be87a" :
                val >= 70 ? "#e8b84b" : "#e85b4b";

        } else {
            bar.style.height = "0";
            lbl.textContent = "—";
            lbl.style.color = "#666";
        }
    });

    // ------------------------------------------------------------------
    // Asistencia P1–P4 (según backend)
    // ------------------------------------------------------------------
    const asist = indicadores[0];

    if (asist) {
        const asistVals = [
            asist.asistencia_p1 ? `P1: ${asist.asistencia_p1}%` : null,
            asist.asistencia_p2 ? `P2: ${asist.asistencia_p2}%` : null,
            asist.asistencia_p3 ? `P3: ${asist.asistencia_p3}%` : null,
            asist.asistencia_p4 ? `P4: ${asist.asistencia_p4}%` : null
        ].filter(Boolean);

        const asistEl = document.getElementById("asist-detalle");
        if (asistEl) asistEl.innerHTML = asistVals.join("<br>");

        const asistNums = [
            asist.asistencia_p1,
            asist.asistencia_p2,
            asist.asistencia_p3,
            asist.asistencia_p4
        ].filter(v => v !== null);

        const promAsist = asistNums.length
            ? Math.round(asistNums.reduce((a, b) => a + b) / asistNums.length)
            : null;

        const promAsistEl = document.getElementById("asist-promedio");
        if (promAsistEl)
            promAsistEl.textContent = promAsist ? `${promAsist}% prom.` : "—";
    }

    // ------------------------------------------------------------------
    // TABLA DETALLADA DE INDICADORES
    // ------------------------------------------------------------------
    const tbody = document.getElementById("ind-tabla-body");
    if (!tbody) return;

    tbody.innerHTML = indicadores.map((ind, i) => {

        function celda(val) {
            if (val === null || val === undefined) {
                return `<td class="ind-empty">—</td>`;
            }

            const bg =
                val >= 80 ? "rgba(75,232,122,.1)" :
                val >= 70 ? "rgba(232,184,75,.1)" :
                            "rgba(232,91,75,.1)";

            const col =
                val >= 80 ? "#4be87a" :
                val >= 70 ? "#e8b84b" : "#e85b4b";

            return `
                <td style="background:${bg};color:${col};font-weight:600">
                    ${val}
                </td>`;
        }

        // Tendencia P1→P2
        let tend = "—";
        if (ind.p1 != null && ind.p2 != null) {
            if (ind.p2 > ind.p1) tend = `↑ +${ind.p2 - ind.p1}`;
            else if (ind.p2 < ind.p1) tend = `↓ ${ind.p2 - ind.p1}`;
            else tend = "→ =";
        }

        return `
            <tr>
                <td>${ind.indicador_num}. ${ind.indicador_texto}</td>
                ${celda(ind.p1)}
                ${celda(ind.p2)}
                ${celda(ind.p3)}
                ${celda(ind.p4)}
                <td>${tend}</td>
            </tr>
        `;
    }).join("");
}

======================================================================
// PARTE 4 — CARGA DE MATERIAS DESDE EXCEL + MAPEOS IA CORREGIDOS
// ======================================================================

let _materiaFile = null;
let _materiaMapeo = null;
let _columnas = [];

// ----------------------------------------------------------------------
// 1. INVOCAR CARGA DE ARCHIVO
// ----------------------------------------------------------------------
function iniciarCargaMateria(input) {
    if (!input.files[0]) return;

    _materiaFile = input.files[0];
    input.value = "";

    let nombre = prompt(
        "Nombre de la materia (ej: Historia del Arte, Matemática, Emprendimiento):"
    );

    if (!nombre || !nombre.trim()) {
        _materiaFile = null;
        return;
    }

    const btn = document.querySelector('[onclick*="fm-perfil"]');
    if (btn) {
        btn.innerHTML = " Analizando...";
        btn.disabled = true;
    }

    const fd = new FormData();
    fd.append("file", _materiaFile);
    fd.append("materia", nombre.trim());

    fetch("/api/interpretar-excel", { method: "POST", body: fd })
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                alert("Error: " + data.error);
                return;
            }
            _materiaMapeo = data.mapeo;
            _columnas = data.columnas_disponibles || [];
            mostrarModal(data);
        })
        .catch(() => alert("Error de conexión con el servidor"))
        .finally(() => {
            if (btn) {
                btn.innerHTML = " Agregar materia";
                btn.disabled = false;
            }
        });
}


// ----------------------------------------------------------------------
// 2. MOSTRAR MODAL DE MAPEOS IA CORREGIDO
// ----------------------------------------------------------------------
function mostrarModal(data) {
    const mapeo = data.mapeo || {};

    document.getElementById("modal-materia").value = data.materia || "";

    const conf = data.confianza || "media";
    const confColor =
        conf === "alta" || conf === "guardado"
            ? "#4dffb4"
            : conf === "media"
            ? "#378ADD"
            : "#ff4d4d";

    document.getElementById("modal-confianza").innerHTML = `
        <span style="color:${confColor};font-weight:700">
            ${conf === "guardado" ? "💾 Mapeo recordado" : `🤖 Confianza: ${conf}`}
        </span>
        <br>
        <small style="opacity:.7">${data.archivo || ""}</small>
    `;

    // Campos disponibles
    const campos = [
        { id: "sel-nombre", label: "Columna Nombre", key: "col_nombre" },
        { id: "sel-apellido", label: "Columna Apellido", key: "col_apellido" },
        { id: "sel-nc", label: "Nombre Completo (una col)", key: "col_nombre_completo" },
        { id: "sel-p1", label: "Promedio P1", key: "col_p1" },
        { id: "sel-p2", label: "Promedio P2", key: "col_p2" },
        { id: "sel-p3", label: "Promedio P3", key: "col_p3" },
        { id: "sel-p4", label: "Promedio P4", key: "col_p4" },
    ];

    let html = "";

    campos.forEach(c => {
        const val = mapeo[c.key] || "";
        let opts = `<option value="">-- ninguna --</option>`;

        _columnas.forEach(col => {
            opts += `<option value="${col}" ${col === val ? "selected" : ""}>${col}</option>`;
        });

        // IA detectó columna no existente → se conserva como opción
        if (val && !_columnas.includes(val)) {
            opts += `<option value="${val}" selected>${val} (IA)</option>`;
        }

        html += `
            <div class="map-row">
                <label>${c.label}</label>
                <select id="${c.id}">${opts}</select>
            </div>
        `;
    });

    document.getElementById("modal-campos").innerHTML = html;

    const notas = mapeo.notas || data.mensaje || "";
    document.getElementById("modal-notas-ia").innerHTML = notas
        ? `<div class="modal-ai-msg">${notas}</div>`
        : "";

    document.getElementById("modal-mapeo").style.display = "flex";
}


// ----------------------------------------------------------------------
// 3. CERRAR MODAL
// ----------------------------------------------------------------------
function cerrarModal() {
    document.getElementById("modal-mapeo").style.display = "none";
    _materiaFile = null;
    _materiaMapeo = null;
}


// ----------------------------------------------------------------------
// 4. CONFIRMAR CARGA DE MATERIA CON MAPEO FINAL
// ----------------------------------------------------------------------
function confirmarCarga() {
    const materia = document.getElementById("modal-materia").value.trim();
    if (!materia) {
        alert("Escribe el nombre de la materia");
        return;
    }

    if (!_materiaFile) {
        cerrarModal();
        return;
    }

    // Construir JSON final de mapeo
    const mapeoFinal = {
        col_nombre: document.getElementById("sel-nombre").value || null,
        col_apellido: document.getElementById("sel-apellido").value || null,
        col_nombre_completo: document.getElementById("sel-nc").value || null,
        col_p1: document.getElementById("sel-p1").value || null,
        col_p2: document.getElementById("sel-p2").value || null,
        col_p3: document.getElementById("sel-p3").value || null,
        col_p4: document.getElementById("sel-p4").value || null,

        fila_inicio_datos: (_materiaMapeo && _materiaMapeo.fila_inicio_datos) || 1,

        // Valores IA necesarios
        modo: (_materiaMapeo && _materiaMapeo.modo) || "llama",
        hojas: (_materiaMapeo && _materiaMapeo.hojas) || [],
    };

    const btn = document.getElementById("btn-confirmar");
    btn.textContent = "Cargando...";
    btn.disabled = true;

    const fd = new FormData();
    fd.append("file", _materiaFile);
    fd.append("materia", materia);
    fd.append("mapeo", JSON.stringify(mapeoFinal));

    const profEl = document.getElementById("modal-profesor");
    if (profEl?.value.trim()) fd.append("profesor", profEl.value.trim());

    const grado = document.getElementById("modal-grado")?.value || "";
    const mencion = document.getElementById("modal-mencion")?.value || "";

    if (grado) fd.append("grado", grado);
    if (mencion) fd.append("mencion", mencion);

    fetch("/api/cargar-materia", { method: "POST", body: fd })
        .then(r => r.json())
        .then(data => {
            if (data.ok) {
                cerrarModal();

                // Popup de éxito
                const msg = document.createElement("div");
                msg.className = "toast-success";
                msg.textContent = data.mensaje;

                document.body.appendChild(msg);
                setTimeout(() => msg.remove(), 4000);

                cargarMaterias();
            } else {
                alert("Error: " + (data.error || "desconocido"));
            }
        })
        .catch(() => alert("Error de conexión"))
        .finally(() => {
            btn.textContent = "Confirmar y Cargar";
            btn.disabled = false;
        });
}


// ======================================================================
// PARTE 4B — MÓDULOS POR MENCIÓN (ARTES / NO MULTIMEDIA)
// ======================================================================
(function () {
    const container = document.getElementById("modulos-mencion-container");
    if (!container) return; // Para Multimedia no aplica esta sección

    function renderDesdeData(lista) {
        if (!lista || !lista.length) {
            container.innerHTML = `
                <div class="no-mods">
                    Sin módulos cargados aún<br>
                    Carga el Excel del profesor o usa Editar
                </div>
            `;
            return;
        }

        let html = `<div class="mods-grid">`;

        lista.forEach(m => {
            const label = (m.materia || "").replace(/_/g, " ");
            const prom = parseFloat(m.promedio) || 0;

            let color =
                prom >= 85 ? "#4be87a" :
                prom >= 70 ? "#e8b84b" :
                prom > 0 ? "#e85b4b" : "#555";

            // Ícono automático por mención
            const lower = label.toLowerCase();
            let icon = "📚";

            if (/teatro|dram|actuac|taller/.test(lower)) icon = "🎭";
            else if (/música|musica|solfeo|instrumento/.test(lower)) icon = "🎵";
            else if (/dibujo|pintura|escultura/.test(lower)) icon = "🎨";
            else if (/foto/.test(lower)) icon = "📸";
            else if (/diseñ|diseno/.test(lower)) icon = "🖥️";

            html += `
                <div class="mod-card">
                    <div class="mod-top">
                        <span class="mod-icon">${icon}</span>
                        <span class="mod-title">${label}</span>
                        <span class="mod-prom" style="color:${color}">
                            ${prom > 0 ? prom.toFixed(1) + "%" : "—"}
                        </span>
                    </div>
                </div>
            `;
        });

        html += `</div>`;
        container.innerHTML = html;
    }

    // Si ya estaban disponibles antes de que cargara este script
    if (window._materiasListas) {
        renderDesdeData(window._materiasListas);
    }

    // Event listener
    document.addEventListener("materiasListas", ev => {
        renderDesdeData(ev.detail);
    });
})();

// ======================================================================
// PARTE 5 — TIMELINE, LOGROS, CASOS, ACUERDOS, ASISTENCIA, REPORTES
// ======================================================================


// ----------------------------------------------------------------------
// EXPEDIENTE: HISTORIAL / TIMELINE
// ----------------------------------------------------------------------
async function cargarHistorial() {
    const container = document.getElementById('timeline-container');

    try {
        const res = await fetch('/api/expediente/' + EST_ID);
        const data = await res.json();

        if (data.indicadores)
            renderIndicadoresBadges(data.indicadores, data.eventos || []);

        renderTimeline(data.eventos || [], container);
        renderLogrosSection((data.eventos || []).filter(e => e.fuente === 'logro'));

    } catch (e) {
        container.innerHTML = `
            <div class="err">Error cargando historial</div>
        `;
    }
}


// ----------------------------------------------------------------------
// BADGES EN LA CABECERA DEL PERFIL (INDICADORES)
// ----------------------------------------------------------------------
function renderIndicadoresBadges(ind, eventos) {

    eventos = eventos || [];

    const containers = [
        document.getElementById('expediente-indicadores'),
        document.getElementById('expediente-indicadores-hero')
    ].filter(Boolean);

    if (!containers.length) return;

    const cfg = {
        ind_conducta:  { label: "Conducta", critico:"🔴 Crítico", alerta:"🟠 Alerta", observacion:"🟡 Obs", neutro:"✓" },
        ind_psico:     { label: "Psicológico", critico:"🔵 Crítico", alerta:"🔵 Alerta", observacion:"🔵 Obs", neutro:"✓" },
        ind_academico: { label: "Académico", critico:"🔴 Crítico", alerta:"🟠 Alerta", observacion:"🟡 Obs", neutro:"✓" },
        ind_logros:    { label: "Logros", destacado:"⭐⭐ Dest.", activo:"⭐ Activo", neutro:"—" }
    };

    let html = "";

    for (let key in cfg) {
        const val = ind[key] || "neutro";
        const txt = cfg[key][val] || val;
        html += `
            <div class="exp-badge">${cfg[key].label}: ${txt}</div>
        `;
    }

    containers.forEach(c => c.innerHTML = html);
}


// ----------------------------------------------------------------------
// RENDER CRONOLÓGICO DEL TIMELINE
// ----------------------------------------------------------------------
function renderTimeline(eventos, container) {

    if (!eventos || !eventos.length) {
        container.innerHTML = `
            <div class="timeline-empty">
                📭<br>
                Sin reportes registrados.<br>
                Usa "Nuevo reporte".
            </div>
        `;
        return;
    }

    const COLORS = {
        conducta: "#ffc44d",
        psicologico: "#60b8f0",
        academico: "#378ADD",
        incidente_grave: "#ff6b6b",
        reconocimiento: "#378ADD",
        olimpiada: "#ffd700",
        premio: "#ffd700",
        logro: "#378ADD"
    };

    const LABELS = {
        conducta: "⚡ Conducta",
        psicologico: "🧠 Psicológico",
        academico: "📚 Académico",
        incidente_grave: "🚨 Incidente",
        reconocimiento: "🏆 Reconocimiento",
        olimpiada: "🥇 Olimpiada",
        premio: "🎖️ Premio",
        logro: "⭐ Logro"
    };

    container.innerHTML = eventos.map((r, i) => {

        const col = COLORS[r.tipo] || "#999";
        const lab = LABELS[r.tipo] || r.tipo;

        return `
            <div class="timeline-item">
                <div class="timeline-dot" style="background:${col}"></div>

                <div class="timeline-content">
                    <div class="tl-head">
                        <span class="tl-type">${lab}</span>
                        <span class="tl-date">${(r.fecha || "").split("T")[0]}</span>
                    </div>

                    <div class="tl-title">${r.titulo || "Sin título"}</div>
                    <div class="tl-desc">${(r.descripcion || "").slice(0,200)}${r.descripcion?.length>200?"…":""}</div>

                    ${r.seguimiento ? `<div class="tl-seg">${r.seguimiento}</div>` : ""}
                    ${r.reportado_por ? `<div class="tl-by">Por: ${r.reportado_por}</div>` : ""}
                </div>
            </div>
        `;
    }).join("");
}


// ----------------------------------------------------------------------
// LOGROS DEL ESTUDIANTE
// ----------------------------------------------------------------------
function renderLogrosSection(logros) {
    const section = document.getElementById('logros-section');
    const list = document.getElementById('logros-list');

    if (!section || !list) return;

    if (!logros.length) {
        section.style.display = "none";
        return;
    }

    section.style.display = "block";

    const ICON = { reconocimiento:"🏆", olimpiada:"🥇", premio:"🎖️", logro:"⭐" };

    list.innerHTML = logros.map(l => `
        <div class="logro-item">
            <div class="logro-title">${ICON[l.tipo] || "⭐"} ${l.titulo}</div>
            ${l.descripcion ? `<div class="logro-desc">${l.descripcion}</div>` : ""}
            ${l.fecha ? `<div class="logro-date">${l.fecha}</div>` : ""}
        </div>
    `).join("");
}


// ----------------------------------------------------------------------
// NUEVO REPORTE (desde el perfil)
// ----------------------------------------------------------------------
function abrirModalReporte() {
    const m = document.getElementById('modal-reporte-perfil');
    m.style.display = "flex";

    document.getElementById("rp-titulo").value = "";
    document.getElementById("rp-descripcion").value = "";
    document.getElementById("rp-status").textContent = "";
}

function cerrarModalReporte() {
    document.getElementById('modal-reporte-perfil').style.display = 'none';
}


// GUARDAR REPORTE DIRECTO EN EL PERFIL
function guardarReportePerfil() {

    const titulo = document.getElementById("rp-titulo").value.trim();
    const desc   = document.getElementById("rp-descripcion").value.trim();
    const status = document.getElementById("rp-status");

    if (!desc) {
        status.innerHTML = "La descripción es requerida";
        return;
    }

    status.innerHTML = "Guardando...";

    fetch("/api/reportes", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            estudiante_id: EST_ID,
            tipo: document.getElementById("rp-tipo").value,
            severidad: document.getElementById("rp-severidad").value,
            titulo,
            descripcion: desc
        })
    })
    .then(r => r.json())
    .then(d => {
        if (d.ok) {
            status.innerHTML = "✓ Reporte creado";
            setTimeout(cerrarModalReporte, 800);
            cargarHistorial();
        } else {
            status.innerHTML = "✗ " + (d.error || "Error");
        }
    })
    .catch(() => status.innerHTML = "✗ Error de conexión");
}


// Cerrar clic fuera del modal
document.getElementById("modal-reporte-perfil")?.addEventListener("click", e => {
    if (e.target === e.currentTarget) cerrarModalReporte();
});


// ----------------------------------------------------------------------
// FOTO DE PERFIL
// ----------------------------------------------------------------------
function subirFoto(input) {

    const file = input.files[0];
    if (!file) return;

    if (file.size > 3 * 1024 * 1024) {
        alert("La imagen debe ser menor de 3 MB");
        return;
    }

    const fd = new FormData();
    fd.append("foto", file);

    const wrap = document.getElementById('avatar-wrap');
    wrap.style.opacity = ".4";

    fetch("/api/foto/" + EST_ID, { method: "POST", body: fd })
        .then(r => r.json())
        .then(d => {
            wrap.style.opacity = "1";
            if (d.ok) {
                let img = document.getElementById("avatar-img");
                const ini = document.getElementById("avatar-initials");

                if (!img) {
                    img = document.createElement("img");
                    img.id = "avatar-img";
                    img.style = "width:100%;height:100%;object-fit:cover;border-radius:inherit;";
                    wrap.insertBefore(img, wrap.firstChild);
                }

                img.src = d.url + "?t=" + Date.now();
                if (ini) ini.style.display = "none";
            } else {
                alert("Error: " + (d.error || "No se pudo subir"));
            }
        })
        .catch(() => {
            wrap.style.opacity = "1";
            alert("Error de conexión");
        });
}


function borrarFoto() {
    if (!confirm("¿Eliminar la foto de perfil?")) return;

    fetch("/api/foto/" + EST_ID, { method: "DELETE" })
        .then(r => r.json())
        .then(d => {
            if (d.ok) {
                const img = document.getElementById("avatar-img");
                const ini = document.getElementById("avatar-initials");
                if (img) img.remove();

                if (ini) ini.style.display = "";
                else {
                    const wrap = document.getElementById("avatar-wrap");
                    const span = document.createElement("span");
                    span.id = "avatar-initials";
                    wrap.insertBefore(span, wrap.firstChild);
                }
            }
        });
}


// ----------------------------------------------------------------------
// ASISTENCIA MENSUAL (GRID)
// ----------------------------------------------------------------------
function cargarAsistenciaMensualPerfil() {

    fetch("/api/asistencia-mensual/" + EST_ID)
    .then(r => r.json())
    .then(data => renderAsistenciaMensual(data))
    .catch(() => {
        document.getElementById("asistencia-mensual-grid").innerHTML =
            `<div class="err">Error cargando asistencia mensual</div>`;
    });
}

function renderAsistenciaMensual(meses) {

    const cont = document.getElementById("asistencia-mensual-grid");
    if (!cont) return;

    const MESES = ["","Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"];

    if (!meses || !meses.length) {
        cont.innerHTML = `
            <div class="no-asist">
                📅<br>
                Sin registros de asistencia mensual validados.
            </div>
        `;
        return;
    }

    // Agrupar por materia
    const porMateria = {};
    meses.forEach(m => {
        if (!porMateria[m.materia]) porMateria[m.materia] = [];
        porMateria[m.materia].push(m);
    });

    let html = "";

    for (let mat in porMateria) {
        const registros = porMateria[mat];

        const promedio = registros.reduce((s,r) => s + (r.porcentaje||0), 0) / registros.length;
        const colProm =
            promedio >= 85 ? "#4dffb4" :
            promedio >= 70 ? "#f7b731" : "#ff4d4d";

        html += `
            <div class="asist-card">
                <div class="asist-title">${mat} <span style="color:${colProm}">${promedio.toFixed(0)}% prom.</span></div>
        `;

        registros.forEach(r => {
            const col =
                r.porcentaje >= 85 ? "#22c55e" :
                r.porcentaje >= 70 ? "#f59e0b" : "#ef4444";

            html += `
                <div class="asist-item">
                    <div class="asist-pct" style="color:${col}">${r.porcentaje.toFixed(0)}%</div>
                    <div class="asist-fecha">${MESES[r.mes]} ${r.anio}</div>
                    <div class="asist-det">${r.dias_asistio}/${r.dias_clase_impartidos} días</div>
                    <div class="asist-valid">${r.validado ? "✓ Validado" : "Pendiente"}</div>
                </div>
            `;
        });

        html += `</div>`;
    }

    cont.innerHTML = html;
}


// ----------------------------------------------------------------------
// EVALUACIONES NARRATIVAS
// ----------------------------------------------------------------------
function cargarNarrativasPerfil() {
    const anio = _anioEscolarPerfil();

    fetch("/api/evaluacion-narrativa/" + EST_ID + "?anio_escolar=" + anio)
        .then(r => r.json())
        .then(renderNarrativasPerfil)
        .catch(() => {
            const cont = document.getElementById("narrativas-perfil-cont");
            if (cont) cont.innerHTML = `<div class="err">Error cargando evaluaciones</div>`;
        });
}

function renderNarrativasPerfil(narrs) {
    const cont = document.getElementById("narrativas-perfil-cont");
    if (!cont) return;

    if (!narrs || !narrs.length) {
        cont.innerHTML = `
            <div class="no-narr">
                ✍️<br>Sin evaluaciones narrativas registradas.
            </div>
        `;
        return;
    }

    cont.innerHTML = narrs.map(n => `
        <div class="narr-item">
            <div class="narr-head">Período ${n.periodo} — ${n.profesor_nombre}</div>
            <div class="narr-text">${n.texto}</div>
        </div>
    `).join("");
}


// ----------------------------------------------------------------------
// CASOS DEL ESTUDIANTE (RESUMEN)
// ----------------------------------------------------------------------
async function cargarCasosPerfil() {

    const cont = document.getElementById("perfil-casos-contenido");
    if (!cont) return;

    try {
        const r = await fetch('/api/casos/estudiante/' + EST_ID);
        const data = await r.json();

        if (!data.length) {
            cont.innerHTML = `
                <div class="no-casos">
                    🗂️<br>Sin casos registrados para este estudiante.
                </div>
            `;
            return;
        }

        const ICON = {
            asistencia: "📅",
            conducta: "⚠️",
            academico: "📚",
            familiar: "🏠",
            emocional: "💛",
        };

        const BGC = {
            "Abierto": "rgba(96,184,240,.15)",
            "En seguimiento": "rgba(255,196,77,.15)",
            "Escalado": "rgba(255,77,77,.15)",
            "Resuelto": "rgba(77,255,180,.15)",
            "Cerrado": "rgba(100,100,100,.15)"
        };

        const TC = {
            "Abierto": "var(--blue)",
            "En seguimiento": "var(--warn)",
            "Escalado": "#ff6b6b",
            "Resuelto": "var(--success)",
            "Cerrado": "var(--muted)"
        };

        cont.innerHTML = data.map(c => `
            <div class="caso-card" style="background:${BGC[c.estado] || "#eee"}">
                <div class="caso-top">
                    <span class="caso-icon">${ICON[c.tipo] || "📋"}</span>
                    <span class="caso-title">${c.titulo}</span>
                    <span class="caso-state" style="color:${TC[c.estado]}">${c.estado}</span>
                </div>

                <div class="caso-det">
                    Tipo: ${c.tipo} · 
                    Abierto: ${(c.creado_en || "").split("T")[0]}
                    ${c.nivel_escala > 1 ? ` · Nivel ${c.nivel_escala}` : ""}
                </div>

                <div class="caso-desc">${c.descripcion || ""}</div>

                <a class="caso-link" href="/casos">Ver caso completo →</a>
            </div>
        `).join("");

    } catch (e) {
        cont.innerHTML = `<div class="err">Error cargando casos</div>`;
    }
}


// ----------------------------------------------------------------------
// ACUERDO‑COMPROMISO
// ----------------------------------------------------------------------
let _acAbierto = false;

function abrirModalAcuerdo() {
    const m = document.getElementById("modal-acuerdo");
    if (!m) {
        alert("Error: modal-acuerdo no encontrado");
        return;
    }
    m.style.display = "flex";
    _acAbierto = true;
    cargarCasosParaAcuerdo();
}

function cerrarModalAcuerdo() {
    document.getElementById("modal-acuerdo").style.display = "none";
    _acAbierto = false;
}

function volverAConfigurar() {
    document.getElementById("ac-step1").style.display = "block";
    document.getElementById("ac-step2").style.display = "none";
    document.getElementById("ac-loading").style.display = "none";
    const err = document.getElementById("ac-error-msg");
    if (err) err.style.display = "none";
}

function cargarCasosParaAcuerdo() {
    const estId = EST_ID;

    fetch('/api/casos?estudiante_id=' + estId)
        .then(r => r.json())
        .then(casos => {
            const sel = document.getElementById("ac-caso-sel");
            if (!sel) return;

            sel.innerHTML = `<option value="">— Sin caso vinculado —</option>`;

            casos.forEach(c => {
                const opt = document.createElement("option");
                opt.value = c.id;
                opt.textContent = `[${c.tipo}] ${c.titulo || "Sin título"}`;
                sel.appendChild(opt);
            });
        });
}

async function generarAcuerdo() {

    const estId = EST_ID;
    const casoId = document.getElementById("ac-caso-sel").value;
    const contexto = document.getElementById("ac-contexto").value;

    document.getElementById("ac-step1").style.display = "none";
    document.getElementById("ac-step2").style.display = "none";
    document.getElementById("ac-loading").style.display = "block";

    try {
        const res = await fetch("/api/acuerdo-compromiso/generar", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                estudiante_id: estId,
                caso_id: casoId || null,
                contexto_adicional: contexto
            })
        });

        const d = await res.json();

        document.getElementById("ac-loading").style.display = "none";

        if (d.error) {
            document.getElementById("ac-step1").style.display = "block";

            let errDiv = document.getElementById("ac-error-msg");
            if (!errDiv) {
                errDiv = document.createElement("div");
                errDiv.id = "ac-error-msg";
                errDiv.className = "ac-error";
                document.getElementById("ac-step1").prepend(errDiv);
            }

            errDiv.textContent = "⚠ " + d.error;
            errDiv.style.display = "block";
            return;
        }

        document.getElementById("ac-numero").textContent = d.numero || "";
        document.getElementById("ac-contenido").textContent = d.contenido || "";

        document.getElementById("ac-step2").style.display = "block";

    } catch (err) {
        document.getElementById("ac-loading").style.display = "none";
        document.getElementById("ac-step1").style.display = "block";

        let errDiv = document.getElementById("ac-error-msg");
        if (!errDiv) {
            errDiv = document.createElement("div");
            errDiv.id = "ac-error-msg";
            errDiv.className = "ac-error";
            document.getElementById("ac-step1").prepend(errDiv);
        }

        errDiv.textContent = "⚠ Error de conexión: " + err;
        errDiv.style.display = "block";
    }
}


// IMPRIMIR ACUERDO
function imprimirAcuerdo() {
    const num = document.getElementById("ac-numero").textContent;
    const cuerpo = document.getElementById("ac-contenido").textContent;

    const printEl = document.getElementById("ac-print-area");

    document.getElementById("ac-print-num").textContent = num;
    document.getElementById("ac-print-body").textContent = cuerpo;

    printEl.style.display = "block";
    window.print();
    printEl.style.display = "none";
}


// ESCAPE de modal con ESC
document.addEventListener("keydown", e => {
    if (e.key === "Escape" && _acAbierto) cerrarModalAcuerdo();
});


// ----------------------------------------------------------------------
// INICIALIZACIÓN FINAL DEL PERFIL
// ----------------------------------------------------------------------
cargarHistorial();
cargarCuadernoPerfil();
cargarAsistenciaMensualPerfil();
cargarNarrativasPerfil();
cargarCasosPerfil();
