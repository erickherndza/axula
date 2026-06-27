
// ======================================================================
//  ASIGNACIONES.JS — CORREGIDO 2026
// ======================================================================

// Toast rápido
function tk(msg, tipo="info") {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.style.borderColor =
      tipo === "success" ? "rgba(77,255,180,.4)" :
      tipo === "error"   ? "rgba(255,77,77,.4)"  :
                           "rgba(255,196,77,.4)";
  t.style.color =
      tipo === "success" ? "#4dffb4" :
      tipo === "error"   ? "#ff6b6b" :
                           "#ffc44d";
  t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 3000);
}

// ------------------------------------------------------------
// CARGAR ASIGNACIONES
// ------------------------------------------------------------
async function cargarAsignaciones() {
  const cont = document.getElementById("asig-lista");
  cont.innerHTML = `<div style="padding:20px;text-align:center;color:#777">
      <i class="fas fa-spinner fa-spin"></i> Cargando…
  </div>`;

  try {
      const r = await fetch("/api/asignaciones");
      const data = await r.json();

      if (!data.length) {
          cont.innerHTML = `
              <div style="padding:20px;text-align:center;color:#777">
                  No hay asignaciones registradas.
              </div>`;
          return;
      }

      cont.innerHTML = data.map(a => renderAsignacion(a)).join("");

  } catch (err) {
      cont.innerHTML = `<div style="padding:20px;color:#ff6b6b;text-align:center">
          Error cargando asignaciones
      </div>`;
  }
}

// ------------------------------------------------------------
// RENDERIZAR TARJETA DE ASIGNACIÓN
// ------------------------------------------------------------
function renderAsignacion(a) {
  let criterios = [];

  try {
      criterios = JSON.parse(a.criterios || a.criterios_json || "[]");
  } catch (e) {
      criterios = [];
  }

  const critHtml = criterios.length
      ? criterios.map(c => `
          <li style="padding:4px 0;color:#ccc;font-size:12px">
              <strong>${c.criterio}</strong> — ${c.puntos} pts
          </li>`).join("")
      : `<li style="color:#777;font-size:12px">Sin criterios</li>`;

  return `
  <div class="asig-card">
      <div class="asig-title">${a.titulo}</div>
      <div class="asig-materia">${a.materia}</div>
      <div class="asig-desc">${a.descripcion || ""}</div>

      <ul class="asig-criterios">${critHtml}</ul>

      <div class="asig-actions">
          <button class="btn-edit" onclick="editarAsignacion(${a.id})">
              ✎ Editar
          </button>
          <button class="btn-del" onclick="eliminarAsignacion(${a.id})">
              ✕ Eliminar
          </button>
      </div>
  </div>`;
}

// ------------------------------------------------------------
// ABRIR MODAL PARA CREAR ASIGNACIÓN
// ------------------------------------------------------------
function nuevaAsignacion() {
  document.getElementById("asig-id").value = "";
  document.getElementById("asig-titulo").value = "";
  document.getElementById("asig-materia").value = "";
  document.getElementById("asig-descripcion").value = "";
  document.getElementById("asig-criterios").innerHTML = "";

  document.getElementById("asig-modal").style.display = "block";
}

// ------------------------------------------------------------
// AGREGAR CRITERIO AL FORMULARIO
// ------------------------------------------------------------
function agregarCriterio() {
  const lista = document.getElementById("asig-criterios");

  const item = document.createElement("div");
  item.classList.add("crit-item");

  item.innerHTML = `
      <input class="crit-nombre" placeholder="Criterio">
      <input class="crit-puntos" type="number" min="1" max="100" placeholder="pts">
      <button class="crit-del" onclick="this.parentNode.remove()">✕</button>
  `;

  lista.appendChild(item);
}

// ------------------------------------------------------------
// GUARDAR CREACIÓN / EDICIÓN
// ------------------------------------------------------------
async function guardarAsignacion() {
  const id = document.getElementById("asig-id").value;
  const titulo = document.getElementById("asig-titulo").value.trim();
  const materia = document.getElementById("asig-materia").value.trim();
  const descripcion = document.getElementById("asig-descripcion").value.trim();

  if (!titulo || !materia) {
      tk("Faltan campos obligatorios", "warn");
      return;
  }

  // ✅ Recoger criterios del formulario
  const critElems = document.querySelectorAll(".crit-item");
  let criterios = [];

  critElems.forEach(c => {
      const nom = c.querySelector(".crit-nombre").value.trim();
      const pts = parseInt(c.querySelector(".crit-puntos").value);
      if (nom && pts) criterios.push({ criterio: nom, puntos: pts });
  });

  const payload = {
      titulo,
      materia,
      descripcion,
      criterios: JSON.stringify(criterios)
  };

  const url = id ? `/api/asignaciones/${id}` : "/api/asignaciones";
  const method = id ? "PUT" : "POST";

  try {
      const r = await fetch(url, {
          method,
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
      });

      const d = await r.json();

      if (d.error) {
          tk(d.error, "error");
          return;
      }

      tk("Asignación guardada", "success");
      document.getElementById("asig-modal").style.display = "none";
      cargarAsignaciones();

  } catch (err) {
      tk("Error guardando asignación", "error");
  }
}

// ------------------------------------------------------------
// EDITAR ASIGNACIÓN EXISTENTE
// ------------------------------------------------------------
async function editarAsignacion(id) {
  try {
      const r = await fetch("/api/asignaciones");
      const data = await r.json();
      const a = data.find(x => x.id === id);
      if (!a) return;

      document.getElementById("asig-id").value = a.id;
      document.getElementById("asig-titulo").value = a.titulo;
      document.getElementById("asig-materia").value = a.materia;
      document.getElementById("asig-descripcion").value = a.descripcion || "";

      // ✅ Renderizar criterios actuales
      let criterios = [];
      try { criterios = JSON.parse(a.criterios || a.criterios_json || "[]"); } catch {}

      const cont = document.getElementById("asig-criterios");
      cont.innerHTML = "";

      criterios.forEach(c => {
          const el = document.createElement("div");
          el.classList.add("crit-item");
          el.innerHTML = `
              <input class="crit-nombre" value="${c.criterio}">
              <input class="crit-puntos" type="number" value="${c.puntos}">
              <button class="crit-del" onclick="this.parentNode.remove()">✕</button>
          `;
          cont.appendChild(el);
      });

      document.getElementById("asig-modal").style.display = "block";

  } catch (err) {
      tk("Error cargando asignación", "error");
  }
}

// ------------------------------------------------------------
// ELIMINAR ASIGNACIÓN
// ------------------------------------------------------------
async function eliminarAsignacion(id) {
  if (!confirm("¿Eliminar esta asignación?")) return;

  try {
      const r = await fetch(`/api/asignaciones/${id}`, { method: "DELETE" });
      const d = await r.json();

      if (d.ok) {
          tk("Eliminada", "success");
          cargarAsignaciones();
      } else tk("No se pudo eliminar", "error");

  } catch (err) {
      tk("Error eliminando", "error");
  }
}

// ------------------------------------------------------------
// CERRAR MODAL
// ------------------------------------------------------------
function cerrarAsignacion() {
  document.getElementById("asig-modal").style.display = "none";
}

// Cargar al abrir pestaña
document.addEventListener("DOMContentLoaded", () => {
  if (typeof cargarAsignaciones === "function") {
      cargarAsignaciones();
  }
});
