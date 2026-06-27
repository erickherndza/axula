// ============================================================================
// ============================================================================
// PLANIFICACION.JS — Versión corregida 2026
// Módulo: Planificación IA + Plantilla ABP MINERD
// ============================================================================

// Toast general
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

// ============================================================================
// GENERAR PLANIFICACIÓN CON IA (MATERIA NORMAL)
// ============================================================================
async function generarPlanificacion() {
    const materia = document.getElementById("plan-materia")?.value?.trim();
    const objetivo = document.getElementById("plan-objetivo")?.value?.trim();
    const cont = document.getElementById("plan-output");

    if (!materia || !objetivo) {
        tk("Completa todos los campos", "warn");
        return;
    }

    if (!cont) {
        tk("⚠ No se encontró el contenedor para mostrar la planificación", "error");
        return;
    }

    cont.innerHTML = `
        <div style="padding:20px;text-align:center;color:#777">
            <i class="fas fa-spinner fa-spin"></i> Generando planificación…
        </div>
    `;

    const btn = document.getElementById("btn-plan-generar");
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Generando…`;
    }

    try {
        const r = await fetch("/api/planificacion", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ materia, objetivo })
        });

        const data = await r.json();

        if (!data.ok || !data.texto) {
            tk("Error generando planificación", "error");
            cont.innerHTML = `<div style="color:#ff6b6b;padding:20px">Error al generar la planificación</div>`;
            return;
        }

        cont.innerHTML = `<div class="plan-block">${data.texto}</div>`;
        tk("Planificación generada ✅", "success");

    } catch (e) {
        tk("Error de conexión", "error");
        cont.innerHTML = `<div style="color:#ff6b6b;padding:20px">Error conectando con el servidor</div>`;
    }

    if (btn) {
        btn.disabled = false;
        btn.innerHTML = `Generar`;
    }
}

// ============================================================================
// GENERAR ABP (PLANTILLA MINERD) - CORREGIDO
// ============================================================================
async function generarABP() {
    const titulo = document.getElementById("abp-titulo")?.value?.trim();
    const problema = document.getElementById("abp-problema")?.value?.trim();
    const materia = document.getElementById("abp-materia")?.value?.trim();
    const grado = document.getElementById("abp-grado")?.value?.trim();

    const out =
        document.getElementById("abp-preview") ||
        document.querySelector("[data-abp-preview]");

    if (!out) {
        tk("⚠ No se encontró el contenedor ABP en este HTML", "error");
        return;
    }

    if (!titulo || !problema || !materia || !grado) {
        tk("Completa todos los campos del ABP", "warn");
        return;
    }

    out.innerHTML = `
        <div style="padding:20px;text-align:center;color:#777">
            <i class="fas fa-spinner fa-spin"></i> Generando ABP…
        </div>
    `;

    const btn = document.getElementById("btn-abp-generar");
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Generando…`;
    }

    try {
        const r = await fetch("/api/abp", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ titulo, problema, materia, grado })
        });

        const data = await r.json();

        if (!data.ok || !data.texto) {
            out.innerHTML = `<div style="color:#ff6b6b;padding:20px">Error al generar ABP</div>`;
            tk("Error generando ABP", "error");
            return;
        }

        out.innerHTML = `<div class="abp-block">${data.texto}</div>`;
        tk("ABP generado ✅", "success");

    } catch (e) {
        tk("Error de conexión con servidor", "error");
        out.innerHTML = `<div style="color:#ff6b6b;padding:20px">Error al conectar con el servidor</div>`;
    }

    if (btn) {
        btn.disabled = false;
        btn.innerHTML = `Generar ABP`;
    }
}

// ============================================================================
// EXPORTAR DOCUMENTO (DOCX / PDF)
// ============================================================================
async function exportarPlan(type) {
    const cont = document.getElementById("plan-output");
    if (!cont || !cont.innerText.trim()) {
        tk("Genera una planificación antes de exportar", "warn");
        return;
    }

    try {
        const r = await fetch(`/api/planificacion/export?type=${type}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ contenido: cont.innerHTML })
        });

        const blob = await r.blob();
        const url = URL.createObjectURL(blob);

        const a = document.createElement("a");
        a.href = url;
        a.download = `planificacion.${type}`;
        a.click();

        tk("Documento descargado ✅", "success");

    } catch (e) {
        tk("Error exportando documento", "error");
    }
}

document.addEventListener("DOMContentLoaded", () => {
    console.log("✅ planificacion.js cargado y listo");
});
