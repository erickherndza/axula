# -*- coding: utf-8 -*-
"""
Blueprint: Motor de Promoción Estudiantil
Prefijo: /api/promocion
Auth:     coord_required (coordinador o directora)

Reglas MINERD implementadas en core/promocion_engine.py
"""
import logging
import traceback as _tb

from flask import Blueprint, jsonify, request, session

from core.database import get_db

log = logging.getLogger(__name__)
from core.helpers import _anio_escolar_actual, _audit
from core.auth import login_required, coord_required
from core.promocion_engine import (
    evaluar_estudiante,
    evaluar_grado,
    resumen_grado,
    ejecutar_promocion_lote,
    ejecutar_promocion_estudiante,
    evaluar_post_recuperacion,
    _norm_grado,
)

promocion_bp = Blueprint("promocion", __name__, url_prefix="/api/promocion")


# ── Helpers locales ───────────────────────────────────────────────────────────

def _anio_param() -> str:
    return (
        request.args.get("anio_escolar")
        or request.args.get("anio")
        or _anio_escolar_actual()
    )


def _uid() -> int:
    return session.get("uid") or session.get("user_id") or 0


# ── Rutas ─────────────────────────────────────────────────────────────────────

@promocion_bp.route("/preview")
@login_required
@coord_required
def preview():
    """
    GET /api/promocion/preview?grado=4TO&anio_escolar=2025-2026

    Vista previa sin escribir en BD.
    Retorna resumen + lista de estudiantes con su estado calculado.
    """
    grado = _norm_grado(request.args.get("grado", ""))
    anio  = _anio_param()

    if not grado:
        return jsonify({"ok": False, "error": "Parámetro 'grado' requerido"}), 400

    db = get_db()
    resultados = evaluar_grado(db, grado, anio)

    return jsonify({
        "ok":        True,
        "grado":     grado,
        "anio_escolar": anio,
        "resumen":   resumen_grado(resultados),
        "estudiantes": resultados,
    })


@promocion_bp.route("/estudiante/<int:est_id>")
@login_required
@coord_required
def preview_estudiante(est_id: int):
    """
    GET /api/promocion/estudiante/123?anio_escolar=2025-2026

    Evaluación individual sin escribir en BD.
    """
    try:
        anio = _anio_param()
        db   = get_db()
        res  = evaluar_estudiante(db, est_id, anio)

        if "error" in res:
            return jsonify({"ok": False, "error": res["error"]}), 404

        return jsonify({"ok": True, **res})
    except Exception as exc:
        log.exception("preview_estudiante est_id=%s", est_id)
        return jsonify({"ok": False, "error": str(exc), "traceback": _tb.format_exc()}), 500


@promocion_bp.route("/ejecutar", methods=["POST"])
@login_required
@coord_required
def ejecutar_lote():
    """
    POST /api/promocion/ejecutar
    Body JSON:
    {
      "grado": "5TO",
      "anio_escolar": "2025-2026",
      "estudiante_ids": [1, 2, 3],
      "observacion": "Cierre año escolar 2025-2026"
    }

    Ejecuta la promoción en una sola transacción.
    """
    d    = request.get_json(silent=True) or {}
    grado = _norm_grado(d.get("grado", ""))
    anio  = d.get("anio_escolar") or _anio_escolar_actual()
    ids   = d.get("estudiante_ids", [])
    obs   = d.get("observacion", "")

    if not grado:
        return jsonify({"ok": False, "error": "Campo 'grado' requerido"}), 400
    if not ids:
        return jsonify({"ok": False, "error": "Campo 'estudiante_ids' requerido"}), 400

    db  = get_db()
    res = ejecutar_promocion_lote(db, grado, anio, ids, _uid(), observacion=obs)

    _audit(db, _uid(), "promocion_lote",
           f"grado={grado} anio={anio} promovidos={res.get('promovidos',0)} "
           f"recuperacion={res.get('recuperacion',0)} no_promovidos={res.get('no_promovidos',0)}")
    db.commit()

    return jsonify(res), 200 if res["ok"] else 500


@promocion_bp.route("/ejecutar/<int:est_id>", methods=["POST"])
@login_required
@coord_required
def ejecutar_individual(est_id: int):
    """
    POST /api/promocion/ejecutar/123
    Body JSON:
    {
      "anio_escolar": "2025-2026",
      "forzar": false,
      "observacion": ""
    }
    """
    d     = request.get_json(silent=True) or {}
    anio  = d.get("anio_escolar") or _anio_escolar_actual()
    forzar = bool(d.get("forzar", False))
    obs   = d.get("observacion", "")

    db  = get_db()
    res = ejecutar_promocion_estudiante(
        db, est_id, anio, _uid(), forzar=forzar, observacion=obs
    )

    if res.get("ok"):
        _audit(db, _uid(), "promocion_individual",
               f"est_id={est_id} anio={anio} estado={res['estado']}")
        db.commit()
        return jsonify(res)

    # requiere_confirmacion → 409, error real → 500
    status = 409 if res.get("requiere_confirmacion") else 500
    return jsonify(res), status


@promocion_bp.route("/post-recuperacion/<int:est_id>", methods=["POST"])
@login_required
@coord_required
def post_recuperacion(est_id: int):
    """
    POST /api/promocion/post-recuperacion/123
    Body JSON: { "anio_escolar": "2025-2026", "observacion": "" }

    Re-evalúa y ejecuta la promoción luego de ingresar notas de recuperación de agosto.
    Las notas ya deben estar guardadas en recuperaciones_pedagogicas.nota_recuperacion.
    """
    d    = request.get_json(silent=True) or {}
    anio = d.get("anio_escolar") or _anio_escolar_actual()
    obs  = d.get("observacion", "Recuperación agosto")

    db  = get_db()
    res = ejecutar_promocion_estudiante(
        db, est_id, anio, _uid(),
        post_recuperacion=True,
        observacion=obs,
    )

    if res.get("ok"):
        _audit(db, _uid(), "promocion_post_recuperacion",
               f"est_id={est_id} anio={anio} estado={res['estado']}")
        db.commit()
        return jsonify(res)

    return jsonify(res), 500


@promocion_bp.route("/historial")
@login_required
@coord_required
def historial():
    """
    GET /api/promocion/historial?grado=5TO&anio_escolar=2025-2026&est_id=123

    Historial de promociones. Los tres parámetros son opcionales.
    """
    grado   = _norm_grado(request.args.get("grado", ""))
    anio    = request.args.get("anio_escolar") or request.args.get("anio") or ""
    est_id  = request.args.get("est_id", type=int)

    db = get_db()
    filtros = []
    params  = []

    if grado:
        filtros.append("UPPER(TRIM(e.grado)) = ?")
        params.append(grado)
    if anio:
        filtros.append("p.anio_escolar = ?")
        params.append(anio)
    if est_id:
        filtros.append("p.estudiante_id = ?")
        params.append(est_id)

    where = ("WHERE " + " AND ".join(filtros)) if filtros else ""

    rows = db.execute(
        f"""
        SELECT p.id, p.estudiante_id, e.nombre, e.apellido, e.seccion, e.mencion,
               p.grado_origen, p.grado_destino, p.anio_escolar, p.estado,
               p.mats_reprobadas, p.mats_total, p.mats_recuperacion,
               p.tiene_completiva, p.ciclo, p.fecha, p.observacion,
               u.nombre AS ejecutado_por_nombre
        FROM   promociones p
        JOIN   estudiantes e ON e.id = p.estudiante_id
        LEFT JOIN usuarios u ON u.id = p.ejecutado_por
        {where}
        ORDER  BY p.fecha DESC
        LIMIT  500
        """,
        params,
    ).fetchall()

    return jsonify({
        "ok":   True,
        "total": len(rows),
        "data": [dict(r) for r in rows],
    })


@promocion_bp.route("/detalle/<int:prom_id>")
@login_required
@coord_required
def detalle_promocion(prom_id: int):
    """
    GET /api/promocion/detalle/42

    Detalle por materia de una promoción específica.
    """
    db = get_db()

    encabezado = db.execute(
        """
        SELECT p.*, e.nombre, e.apellido, e.seccion, e.mencion
        FROM   promociones p
        JOIN   estudiantes e ON e.id = p.estudiante_id
        WHERE  p.id = ?
        """,
        (prom_id,),
    ).fetchone()

    if not encabezado:
        return jsonify({"ok": False, "error": "Promoción no encontrada"}), 404

    materias = db.execute(
        """
        SELECT materia, promedio_anual, nota_completiva, nota_final_efectiva,
               aprobada, reprobada_asistencia, pct_inasistencia, estado_materia, snapshot_en
        FROM   promocion_detalle_materias
        WHERE  promocion_id = ?
        ORDER  BY materia
        """,
        (prom_id,),
    ).fetchall()

    return jsonify({
        "ok":        True,
        "promocion": dict(encabezado),
        "materias":  [dict(m) for m in materias],
    })


@promocion_bp.route("/completiva/<int:est_id>", methods=["POST"])
@login_required
@coord_required
def guardar_completiva(est_id: int):
    """
    POST /api/promocion/completiva/123
    Body JSON:
    {
      "anio_escolar": "2025-2026",
      "notas": [
        {"materia": "Matemática", "nota_completiva": 82.5},
        {"materia": "Lengua Española", "nota_completiva": 75.0}
      ]
    }

    Guarda nota_completiva en recuperaciones_pedagogicas para cada materia.
    Usa INSERT OR REPLACE para ser idempotente.
    """
    d    = request.get_json(silent=True) or {}
    anio = d.get("anio_escolar") or _anio_escolar_actual()
    notas = d.get("notas", [])

    if not notas:
        return jsonify({"ok": False, "error": "Campo 'notas' requerido"}), 400

    db       = get_db()
    guardadas = 0

    for item in notas:
        materia        = (item.get("materia") or "").strip()
        nota_completiva = item.get("nota_completiva")
        if not materia or nota_completiva is None:
            continue
        try:
            nota_completiva = float(nota_completiva)
        except (TypeError, ValueError):
            continue
        if not (0 <= nota_completiva <= 100):
            continue

        # Calcular nota_final_completiva = promedio_anual × 0.80 + completiva × 0.20
        row = db.execute(
            "SELECT promedio FROM materias_calificaciones WHERE estudiante_id=? AND materia=? AND anio_escolar=?",
            (est_id, materia, anio),
        ).fetchone()
        promedio_anual     = row["promedio"] if row else None
        nota_final_comp    = None
        if promedio_anual is not None:
            nota_final_comp = round(promedio_anual * 0.80 + nota_completiva * 0.20, 2)

        db.execute(
            """
            INSERT INTO recuperaciones_pedagogicas
                (estudiante_id, materia, anio_escolar, nota_completiva,
                 nota_final_completiva, registrado_por, actualizado)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(estudiante_id, materia, anio_escolar) DO UPDATE SET
                nota_completiva       = excluded.nota_completiva,
                nota_final_completiva = excluded.nota_final_completiva,
                registrado_por        = excluded.registrado_por,
                actualizado           = datetime('now')
            """,
            (est_id, materia, anio, nota_completiva, nota_final_comp, _uid()),
        )
        guardadas += 1

    db.commit()
    _audit(db, _uid(), "completiva_guardada",
           f"est_id={est_id} anio={anio} materias={guardadas}")

    return jsonify({"ok": True, "guardadas": guardadas})


@promocion_bp.route("/recuperacion/<int:est_id>", methods=["POST"])
@login_required
@coord_required
def guardar_recuperacion(est_id: int):
    """
    POST /api/promocion/recuperacion/123
    Body JSON:
    {
      "anio_escolar": "2025-2026",
      "notas": [
        {"materia": "Matemática", "nota_recuperacion": 74.0}
      ]
    }

    Guarda nota_recuperacion en recuperaciones_pedagogicas.
    Idempotente — actualiza si ya existe.
    """
    d     = request.get_json(silent=True) or {}
    anio  = d.get("anio_escolar") or _anio_escolar_actual()
    notas = d.get("notas", [])

    if not notas:
        return jsonify({"ok": False, "error": "Campo 'notas' requerido"}), 400

    db        = get_db()
    guardadas = 0

    for item in notas:
        materia       = (item.get("materia") or "").strip()
        nota_rec      = item.get("nota_recuperacion")
        if not materia or nota_rec is None:
            continue
        try:
            nota_rec = float(nota_rec)
        except (TypeError, ValueError):
            continue
        if not (0 <= nota_rec <= 100):
            continue

        estado = "APROBADA" if nota_rec >= 70 else "REPROBADA"

        db.execute(
            """
            INSERT INTO recuperaciones_pedagogicas
                (estudiante_id, materia, anio_escolar,
                 nota_recuperacion, estado_recuperacion, registrado_por, actualizado)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(estudiante_id, materia, anio_escolar) DO UPDATE SET
                nota_recuperacion  = excluded.nota_recuperacion,
                estado_recuperacion = excluded.estado_recuperacion,
                registrado_por     = excluded.registrado_por,
                actualizado        = datetime('now')
            """,
            (est_id, materia, anio, nota_rec, estado, _uid()),
        )
        guardadas += 1

    db.commit()
    _audit(db, _uid(), "recuperacion_guardada",
           f"est_id={est_id} anio={anio} materias={guardadas}")

    return jsonify({"ok": True, "guardadas": guardadas})
