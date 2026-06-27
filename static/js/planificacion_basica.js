/**
 * planificacion_basica.js
 * Lógica para el módulo de Planificación Secuencial (Materias Básicas)
 */

"use strict";

/* ═══════════════════════════════════════════════════════════════════
   HELPERS
═══════════════════════════════════════════════════════════════════ */

function apiHeaders() {
  return {
    "Content-Type": "application/json",
    "X-CSRF-Token": (typeof CSRF_TOKEN !== "undefined" ? CSRF_TOKEN : ""),
  };
}

function toast(msg, tipo = "success") {
  const el = document.createElement("div");
  const color = tipo === "success" ? "#185FA5" : tipo === "error" ? "#ef4444" : "#f59e0b";
  Object.assign(el.style, {
    position: "fixed", bottom: "20px", right: "20px", zIndex: 9999,
    background: color, color: "#fff",
    padding: "10px 18px", borderRadius: "8px",
    fontSize: ".88rem", fontWeight: "600",
    boxShadow: "0 4px 12px rgba(0,0,0,.2)",
    maxWidth: "320px", lineHeight: "1.4",
  });
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

/* ═══════════════════════════════════════════════════════════════════
   VISTA LISTA — Modal nueva planificación
═══════════════════════════════════════════════════════════════════ */

function abrirModalNuevo() {
  const m = document.getElementById("modalNuevo");
  if (m) m.classList.add("open");
}

function cerrarModalNuevo() {
  const m = document.getElementById("modalNuevo");
  if (m) m.classList.remove("open");
}

// Cerrar al hacer click fuera
document.addEventListener("click", (e) => {
  const m = document.getElementById("modalNuevo");
  if (m && e.target === m) cerrarModalNuevo();
});

const formNuevo = document.getElementById("formNuevo");
if (formNuevo) {
  formNuevo.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(formNuevo);
    const resp = await fetch("/planificacion-basica/nueva", {
      method: "POST",
      headers: { "X-CSRF-Token": CSRF_TOKEN },
      body: fd,
    });
    const data = await resp.json();
    if (data.ok) {
      window.location = "/planificacion-basica/" + data.id;
    } else if (data.id) {
      // Ya existe → ir a ella
      toast("Ya existe ese plan. Redirigiendo...", "warn");
      setTimeout(() => { window.location = "/planificacion-basica/" + data.id; }, 1200);
    } else {
      toast(data.error || "Error al crear", "error");
    }
  });
}

/* ═══════════════════════════════════════════════════════════════════
   VISTA EDITOR
═══════════════════════════════════════════════════════════════════ */

if (typeof PLAN_ID !== "undefined" && PLAN_ID) {

  /* ── Unidades en memoria (cargadas desde el DOM) ── */
  let _unidades = {};

  // Poblar desde el HTML inicial (server-side render)
  document.querySelectorAll(".pb-unit-item").forEach((el) => {
    const uid = parseInt(el.dataset.id);
    _unidades[uid] = { id: uid }; // datos mínimos; se cargan al seleccionar
  });

  /* ── Cargar unidad en formulario ── */
  async function cargarUnidad(uid) {
    // Marcar activo en sidebar
    document.querySelectorAll(".pb-unit-item").forEach((el) => {
      el.classList.toggle("active", parseInt(el.dataset.id) === uid);
    });

    // Cargar datos desde la API
    let und;
    try {
      const resp = await fetch(`/api/planificacion-basica/${PLAN_ID}/unidades`, {
        headers: apiHeaders(),
      });
      const lista = await resp.json();
      und = lista.find((u) => u.id === uid);
    } catch (err) {
      toast("Error al cargar la unidad", "error");
      return;
    }
    if (!und) return;

    // Rellenar formulario
    document.getElementById("unidadId").value          = und.id;
    document.getElementById("fNumero").value           = und.numero_unidad;
    document.getElementById("fSemanas").value          = und.semanas;
    document.getElementById("fTitulo").value           = und.titulo || "";
    document.getElementById("fObjetivos").value        = und.objetivos || "";
    document.getElementById("fIndicadores").value      = und.indicadores || "";
    document.getElementById("fConceptuales").value     = und.contenidos_conceptuales || "";
    document.getElementById("fProcedimentales").value  = und.contenidos_procedimentales || "";
    document.getElementById("fActitudinales").value    = und.contenidos_actitudinales || "";
    document.getElementById("fEstrategias").value      = und.estrategias || "";
    document.getElementById("fRecursos").value         = und.recursos || "";
    document.getElementById("fTipoEval").value         = und.tipo_evaluacion || "formativa";
    document.getElementById("fPorcentaje").value       = und.porcentaje_calificacion || "";
    document.getElementById("fInstrumentos").value     = und.instrumentos || "";
    document.getElementById("fCriterios").value        = und.criterios || "";
    document.getElementById("fObservaciones").value    = und.observaciones || "";

    // Nuevos campos MINERD
    const elSit = document.getElementById("fSituacion");
    if (elSit) elSit.value = und.situacion_aprendizaje || "";
    const elPg = document.getElementById("fPreguntasGeneradoras");
    if (elPg) elPg.value = und.preguntas_generadoras || "";
    const elComp = document.getElementById("fCompetencias");
    if (elComp) elComp.value = und.competencias_especificas || "";
    const elBib = document.getElementById("fBibliografia");
    if (elBib) elBib.value = und.bibliografia || "";

    // Transversalidades
    let trans = {};
    try { trans = JSON.parse(und.transversalidades || "{}"); } catch (_) {}
    ["ambiental", "genero", "tics", "riesgo"].forEach((k) => {
      const cb = document.getElementById("t" + k.charAt(0).toUpperCase() + k.slice(1));
      if (cb) cb.checked = !!trans[k];
    });

    document.getElementById("editorTitulo").textContent = `Unidad ${und.numero_unidad}: ${und.titulo}`;
    document.getElementById("editorPanel").style.display = "";
    document.getElementById("emptyPanel").style.display  = "none";
    document.getElementById("btnEliminar").style.display = "";
  }

  /* ── Nueva unidad (limpiar formulario) ── */
  function nuevaUnidad() {
    document.querySelectorAll(".pb-unit-item").forEach((el) => el.classList.remove("active"));
    document.getElementById("unidadId").value          = "";
    document.getElementById("fNumero").value           = calcNextNumero();
    document.getElementById("fSemanas").value          = "4";
    document.getElementById("fTitulo").value           = "";
    document.getElementById("fObjetivos").value        = "";
    document.getElementById("fIndicadores").value      = "";
    document.getElementById("fConceptuales").value     = "";
    document.getElementById("fProcedimentales").value  = "";
    document.getElementById("fActitudinales").value    = "";
    document.getElementById("fEstrategias").value      = "";
    document.getElementById("fRecursos").value         = "";
    document.getElementById("fTipoEval").value         = "formativa";
    document.getElementById("fPorcentaje").value       = "";
    document.getElementById("fInstrumentos").value     = "";
    document.getElementById("fCriterios").value        = "";
    document.getElementById("fObservaciones").value    = "";
    ["fSituacion", "fPreguntasGeneradoras", "fCompetencias", "fBibliografia"].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.value = "";
    });
    ["Ambiental", "Genero", "Tics", "Riesgo"].forEach((k) => {
      const cb = document.getElementById("t" + k);
      if (cb) cb.checked = false;
    });
    document.getElementById("editorTitulo").textContent = "Nueva Unidad";
    document.getElementById("editorPanel").style.display = "";
    document.getElementById("emptyPanel").style.display  = "none";
    document.getElementById("btnEliminar").style.display = "none";
    document.getElementById("fTitulo").focus();
  }

  function calcNextNumero() {
    const nums = Array.from(document.querySelectorAll(".pb-unit-num")).map((el) => parseInt(el.textContent) || 0);
    return nums.length ? Math.max(...nums) + 1 : 1;
  }

  /* ── Guardar unidad ── */
  async function guardarUnidad() {
      const trans = {
        ambiental: document.getElementById("tAmbiental")?.checked || false,
        genero:    document.getElementById("tGenero")?.checked    || false,
        tics:      document.getElementById("tTics")?.checked      || false,
        riesgo:    document.getElementById("tRiesgo")?.checked    || false,
      };

      const uid = document.getElementById("unidadId").value;
      const titulo = document.getElementById("fTitulo").value.trim();
      if (!titulo) { toast("Escribe un título para la unidad", "warn"); return; }

      const body = {
        id:                         uid ? parseInt(uid) : null,
        numero_unidad:              parseInt(document.getElementById("fNumero").value),
        titulo,
        semanas:                    parseInt(document.getElementById("fSemanas").value),
        objetivos:                  document.getElementById("fObjetivos").value.trim(),
        indicadores:                document.getElementById("fIndicadores").value.trim(),
        contenidos_conceptuales:    document.getElementById("fConceptuales").value.trim(),
        contenidos_procedimentales: document.getElementById("fProcedimentales").value.trim(),
        contenidos_actitudinales:   document.getElementById("fActitudinales").value.trim(),
        estrategias:                document.getElementById("fEstrategias").value.trim(),
        recursos:                   document.getElementById("fRecursos").value.trim(),
        tipo_evaluacion:            document.getElementById("fTipoEval").value,
        instrumentos:               document.getElementById("fInstrumentos").value.trim(),
        criterios:                  document.getElementById("fCriterios").value.trim(),
        porcentaje_calificacion:    parseFloat(document.getElementById("fPorcentaje").value) || null,
        transversalidades:          trans,
        observaciones:              document.getElementById("fObservaciones").value.trim(),
        situacion_aprendizaje:      document.getElementById("fSituacion")?.value.trim()       || "",
        preguntas_generadoras:      document.getElementById("fPreguntasGeneradoras")?.value.trim() || "",
        competencias_especificas:   document.getElementById("fCompetencias")?.value.trim()    || "",
        bibliografia:               document.getElementById("fBibliografia")?.value.trim()    || "",
      };

      const resp = await fetch(`/planificacion-basica/${PLAN_ID}/unidad`, {
        method: "POST",
        headers: apiHeaders(),
        body: JSON.stringify(body),
      });
      const data = await resp.json();

      if (data.ok) {
        toast("Unidad guardada correctamente");
        document.getElementById("unidadId").value = data.id;
        document.getElementById("btnEliminar").style.display = "";
        document.getElementById("editorTitulo").textContent =
          `Unidad ${body.numero_unidad}: ${titulo}`;
        refreshSidebar();
      } else {
        toast(data.error || "Error al guardar", "error");
      }
  }


  /* ── Eliminar unidad ── */
  async function eliminarUnidad() {
    const uid = document.getElementById("unidadId").value;
    if (!uid) return;
    if (!confirm("¿Eliminar esta unidad? Esta acción no se puede deshacer.")) return;

    const resp = await fetch(`/planificacion-basica/${PLAN_ID}/unidad/${uid}`, {
      method: "DELETE",
      headers: apiHeaders(),
    });
    const data = await resp.json();

    if (data.ok) {
      toast("Unidad eliminada");
      window.location.reload();
    } else {
      toast(data.error || "Error al eliminar", "error");
    }
  }

  /* ── Cambiar estado del plan ── */
  async function cambiarEstado(estado) {
    const resp = await fetch(`/planificacion-basica/${PLAN_ID}/estado`, {
      method: "POST",
      headers: apiHeaders(),
      body: JSON.stringify({ estado }),
    });
    const data = await resp.json();
    if (data.ok) {
      toast(`Estado actualizado: ${estado}`);
    } else {
      toast(data.error || "Error", "error");
    }
  }

  /* ── Exportar DOCX ── */
  function exportarDocx() {
    window.location.href = `/planificacion-basica/${PLAN_ID}/exportar-docx`;
  }

  /* ── Generar con IA ── */
  async function generarConIA() {
    const titulo  = document.getElementById("fTitulo").value.trim();
    const numero  = parseInt(document.getElementById("fNumero").value) || 1;
    const semanas = parseInt(document.getElementById("fSemanas").value) || 4;

    if (!titulo) {
      toast("Escribe un título para la unidad antes de generar con IA", "warn");
      document.getElementById("fTitulo").focus();
      return;
    }

    const spinner = document.getElementById("iaSpinner");
    spinner.classList.add("active");

    try {
      const resp = await fetch(`/planificacion-basica/${PLAN_ID}/generar-ia`, {
        method: "POST",
        headers: apiHeaders(),
        body: JSON.stringify({ titulo, numero_unidad: numero, semanas }),
      });
      const data = await resp.json();

      if (!data.ok) {
        toast(data.error || "Error en la IA", "error");
        return;
      }

      const d = data.data;

      // Rellenar campos con el resultado de la IA
      if (d.objetivos)
        document.getElementById("fObjetivos").value = Array.isArray(d.objetivos)
          ? d.objetivos.map((o) => "• " + o).join("\n")
          : d.objetivos;

      if (d.indicadores)
        document.getElementById("fIndicadores").value = Array.isArray(d.indicadores)
          ? d.indicadores.map((i) => "• " + i).join("\n")
          : d.indicadores;

      if (d.conceptuales)
        document.getElementById("fConceptuales").value = Array.isArray(d.conceptuales)
          ? d.conceptuales.map((c) => "• " + c).join("\n")
          : d.conceptuales;

      if (d.procedimentales)
        document.getElementById("fProcedimentales").value = Array.isArray(d.procedimentales)
          ? d.procedimentales.map((p) => "• " + p).join("\n")
          : d.procedimentales;

      if (d.actitudinales)
        document.getElementById("fActitudinales").value = Array.isArray(d.actitudinales)
          ? d.actitudinales.map((a) => "• " + a).join("\n")
          : d.actitudinales;

      if (d.estrategias)   document.getElementById("fEstrategias").value   = d.estrategias;
      if (d.recursos)      document.getElementById("fRecursos").value      = d.recursos;
      if (d.tipo_evaluacion) document.getElementById("fTipoEval").value   = d.tipo_evaluacion;
      if (d.instrumentos)  document.getElementById("fInstrumentos").value  = d.instrumentos;
      if (d.criterios)     document.getElementById("fCriterios").value     = d.criterios;

      // Nuevos campos MINERD
      if (d.situacion_aprendizaje) {
        const el = document.getElementById("fSituacion");
        if (el) el.value = d.situacion_aprendizaje;
      }
      if (d.preguntas_generadoras) {
        const el = document.getElementById("fPreguntasGeneradoras");
        if (el) el.value = Array.isArray(d.preguntas_generadoras)
          ? d.preguntas_generadoras.join("\n")
          : d.preguntas_generadoras;
      }
      if (d.competencias_especificas) {
        const el = document.getElementById("fCompetencias");
        if (el) el.value = d.competencias_especificas;
      }
      if (d.bibliografia) {
        const el = document.getElementById("fBibliografia");
        if (el) el.value = d.bibliografia;
      }

      // Transversalidades
      if (d.transversalidades) {
        ["ambiental", "genero", "tics", "riesgo"].forEach((k) => {
          const cb = document.getElementById("t" + k.charAt(0).toUpperCase() + k.slice(1));
          if (cb) cb.checked = !!d.transversalidades[k];
        });
      }

      toast("Borrador generado con IA. Revisa y guarda.");
    } catch (err) {
      toast("Error al conectar con la IA", "error");
      console.error(err);
    } finally {
      spinner.classList.remove("active");
    }
  }

  /* ── Actualizar sidebar sin reload completo ── */
  async function refreshSidebar() {
    const resp  = await fetch(`/api/planificacion-basica/${PLAN_ID}/unidades`, {
      headers: apiHeaders(),
    });
    if (!resp.ok) return;
    const unidades = await resp.json();

    const list = document.getElementById("unidadesList");
    const currentId = parseInt(document.getElementById("unidadId").value);
    list.innerHTML = "";

    unidades.forEach((u) => {
      const div = document.createElement("div");
      div.className = "pb-unit-item" + (u.id === currentId ? " active" : "");
      div.dataset.id = u.id;
      div.onclick    = () => cargarUnidad(u.id);
      div.innerHTML  = `
        <div class="pb-unit-num">${u.numero_unidad}</div>
        <div class="pb-unit-title">${u.titulo}</div>
        <div class="pb-unit-weeks">${u.semanas}sem</div>
      `;
      list.appendChild(div);
    });
  }

  /* ── Eliminar planificación completa ── */
  async function eliminarPlan() {
    if (!confirm("¿Eliminar esta planificación y todas sus unidades? Esta acción no se puede deshacer.")) return;
    const resp = await fetch(`/planificacion-basica/${PLAN_ID}/eliminar`, {
      method: "DELETE",
      headers: apiHeaders(),
    });
    const data = await resp.json();
    if (data.ok) {
      toast("Planificación eliminada");
      setTimeout(() => { window.location.href = "/planificacion-basica"; }, 800);
    } else {
      toast(data.error || "Error al eliminar", "error");
    }
  }

  // Exponer globalmente para onclick en HTML
  window.cargarUnidad   = cargarUnidad;
  window.nuevaUnidad    = nuevaUnidad;
  window.guardarUnidad  = guardarUnidad;
  window.eliminarUnidad = eliminarUnidad;
  window.cambiarEstado  = cambiarEstado;
  window.exportarDocx   = exportarDocx;
  window.generarConIA   = generarConIA;
  window.eliminarPlan   = eliminarPlan;
}

/* ═══════════════════════════════════════════════════════════════════
   LISTA — exponer globales
═══════════════════════════════════════════════════════════════════ */
window.abrirModalNuevo  = abrirModalNuevo;
window.cerrarModalNuevo = cerrarModalNuevo;

/* ── Duplicar plantilla como plan propio ── */
async function duplicarPlantilla(plantillaId) {
  if (!confirm("¿Usar esta plantilla como base para un nuevo plan? Podrás editarla libremente.")) return;
  const resp = await fetch(`/planificacion-basica/${plantillaId}/duplicar`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": CSRF_TOKEN },
    body: JSON.stringify({}),
  });
  const data = await resp.json();
  if (data.ok) {
    toast("Plan creado desde plantilla. Redirigiendo...");
    setTimeout(() => { window.location.href = "/planificacion-basica/" + data.id; }, 800);
  } else {
    toast(data.error || "Error al duplicar", "error");
  }
}
window.duplicarPlantilla = duplicarPlantilla;
