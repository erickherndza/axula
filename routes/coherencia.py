# -*- coding: utf-8 -*-
"""
Blueprint: coherencia — Coherencia Horizontal del Componente Especializado

Estructura tomada de la plantilla oficial que entregó el coordinador
("Coherencia Horizontal componente especializado.docx"):

  Encabezado institucional (header del .docx):
      CENTRO EDUCATIVO EN ARTES BENITO JUAREZ
      AÑO ESCOLAR <anio>
      COHERENCIA HORIZONTAL DEL COMPONENTE ESPECIALIZADO.

  Propósito (párrafo fijo)

  Tabla de identificación:  Docente | Asignatura · Mención · Grado

  4 períodos FIJOS del calendario escolar, cada uno con:
      - 1 Competencia Laboral (fila propia, ancho completo)
      - N filas de: RAE | Contenidos(Conceptos · Procedimientos ·
        Actitudes y valores) | Producto | Recursos

Los 4 períodos se crean automáticamente al crear la matriz — el docente no
los agrega, son del calendario MINERD.

La exportación a Word reutiliza el mismo mecanismo que el generador ABP
(routes/planificacion.py::exportar_planificacion_docx): subprocess a un
script Node con la librería `docx`, ver routes/generar_coherencia_docx.js.
"""

import json as _json
import logging
import os
import shutil
import subprocess
import tempfile

from flask import (
    Blueprint, render_template, request, redirect, url_for, flash,
    jsonify, send_file,
)

from core.constants import ROLES_COORD
from core.database import get_db
from core.auth import login_required, get_usuario, _csrf_check, _normalizar_rol
from core.helpers import _anio_escolar_actual, _get_config_centro

logger = logging.getLogger("axula")

coherencia_bp = Blueprint("coherencia_bp", __name__)

# Períodos fijos del calendario escolar — tal como vienen en la plantilla
PERIODOS = [
    (1, "Primer periodo: Agosto-Octubre"),
    (2, "Segundo periodo: Noviembre-Enero"),
    (3, "Tercer periodo: Febrero-Marzo"),
    (4, "Cuarto periodo: Abril-Junio"),
]
PERIODOS_MAP = dict(PERIODOS)

PROPOSITO = (
    "Promover una educación integral mediante la articulación horizontal de los "
    "diferentes componentes del área curricular, fomentando la integración de "
    "conocimientos, el desarrollo de competencias, para garantizar aprendizajes "
    "significativos y coherentes en los estudiantes."
)


def _es_admin(u):
    return _normalizar_rol(u.get("rol", "")) in ROLES_COORD


def _cargar_matriz(conn, matriz_id):
    """Devuelve (matriz, periodos_con_filas) o (None, None)."""
    matriz = conn.execute(
        """SELECT m.*, us.nombre AS docente_nombre
           FROM coherencia_horizontal m
           JOIN usuarios us ON us.id = m.docente_id
           WHERE m.id = ?""",
        (matriz_id,),
    ).fetchone()
    if not matriz:
        return None, None

    periodos = []
    for row in conn.execute(
        "SELECT * FROM coherencia_periodo WHERE matriz_id = ? ORDER BY numero",
        (matriz_id,),
    ).fetchall():
        p = dict(row)
        p["titulo"] = PERIODOS_MAP.get(p["numero"], f"Período {p['numero']}")
        p["filas"] = [
            dict(f) for f in conn.execute(
                "SELECT * FROM coherencia_rae WHERE periodo_id = ? ORDER BY orden, id",
                (p["id"],),
            ).fetchall()
        ]
        periodos.append(p)
    return matriz, periodos


@coherencia_bp.route("/coherencia")
@login_required
def coherencia_index():
    u = get_usuario()
    conn = get_db()
    admin = _es_admin(u)
    sql_cont = """(SELECT COUNT(*) FROM coherencia_rae r
                    JOIN coherencia_periodo p ON p.id = r.periodo_id
                    WHERE p.matriz_id = m.id) AS n_filas"""
    if admin:
        matrices = conn.execute(
            f"""SELECT m.*, us.nombre AS docente_nombre, {sql_cont}
                FROM coherencia_horizontal m
                JOIN usuarios us ON us.id = m.docente_id
                ORDER BY m.fecha_creacion DESC"""
        ).fetchall()
    else:
        matrices = conn.execute(
            f"""SELECT m.*, ? AS docente_nombre, {sql_cont}
                FROM coherencia_horizontal m
                WHERE m.docente_id = ?
                ORDER BY m.fecha_creacion DESC""",
            (u["nombre"], u["id"]),
        ).fetchall()
    return render_template("coherencia/index.html", matrices=matrices, es_admin=admin)


@coherencia_bp.route("/coherencia/nueva", methods=["GET", "POST"])
@login_required
def coherencia_nueva():
    u = get_usuario()
    anio = _anio_escolar_actual()
    centro_cfg = _get_config_centro()

    if request.method == "POST":
        if not _csrf_check():
            flash("Token de seguridad inválido.", "error")
            return redirect(url_for("coherencia_bp.coherencia_nueva"))

        asignatura = request.form.get("asignatura", "").strip()
        grado      = request.form.get("grado", "").strip()
        mencion    = request.form.get("mencion", "").strip()
        seccion    = request.form.get("seccion", "").strip()
        centro     = request.form.get("centro", "").strip() or centro_cfg.get("nombre", "")

        if not asignatura or not grado:
            flash("Asignatura y grado son obligatorios.", "error")
            return redirect(url_for("coherencia_bp.coherencia_nueva"))

        conn = get_db()
        cur = conn.execute(
            """INSERT INTO coherencia_horizontal
               (docente_id, anio_escolar, centro, grado, seccion, mencion, asignatura)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (u["id"], anio, centro, grado, seccion, mencion, asignatura),
        )
        matriz_id = cur.lastrowid
        # Los 4 períodos son del calendario escolar — se crean solos
        for numero, _titulo in PERIODOS:
            conn.execute(
                "INSERT INTO coherencia_periodo (matriz_id, numero) VALUES (?, ?)",
                (matriz_id, numero),
            )
        conn.commit()
        flash("Matriz creada. Completa cada período con sus RAE.", "success")
        return redirect(url_for("coherencia_bp.coherencia_editar", matriz_id=matriz_id))

    # Materias del profesor para prellenar el selector de asignatura
    materias_prof = [
        m.strip() for m in (u.get("materia", "") or "").split("|") if m.strip()
    ]
    return render_template(
        "coherencia/nueva.html",
        anio=anio,
        centro_nombre=centro_cfg.get("nombre", ""),
        grado_prof=(u.get("grado", "") or "").split(",")[0].strip(),
        mencion_prof=u.get("mencion", ""),
        materias_prof=materias_prof,
    )


@coherencia_bp.route("/coherencia/<int:matriz_id>/editar", methods=["GET", "POST"])
@login_required
def coherencia_editar(matriz_id):
    u = get_usuario()
    conn = get_db()
    admin = _es_admin(u)

    matriz, periodos = _cargar_matriz(conn, matriz_id)
    if not matriz:
        flash("Matriz no encontrada.", "error")
        return redirect(url_for("coherencia_bp.coherencia_index"))

    es_propietario = (matriz["docente_id"] == u["id"])
    if not es_propietario and not admin:
        flash("Sin permiso para ver esta matriz.", "error")
        return redirect(url_for("coherencia_bp.coherencia_index"))
    puede_editar = es_propietario

    if request.method == "POST":
        if not puede_editar:
            flash("Sin permiso para editar esta matriz.", "error")
            return redirect(url_for("coherencia_bp.coherencia_editar", matriz_id=matriz_id))
        if not _csrf_check():
            flash("Token de seguridad inválido.", "error")
            return redirect(url_for("coherencia_bp.coherencia_editar", matriz_id=matriz_id))

        accion = request.form.get("accion")

        if accion == "guardar_todo":
            # Un solo formulario cubre los 4 períodos: por cada uno, guarda
            # la Competencia Laboral y reemplaza sus filas de RAE completas
            # (arrays paralelos por índice — todas las filas se mandan juntas
            # desde el mismo <form>, sin recargar la página entre períodos).
            filas_guardadas = 0
            for numero, _titulo in PERIODOS:
                prow = conn.execute(
                    "SELECT id FROM coherencia_periodo WHERE matriz_id = ? AND numero = ?",
                    (matriz_id, numero),
                ).fetchone()
                if not prow:
                    continue
                pid = prow["id"]

                conn.execute(
                    "UPDATE coherencia_periodo SET competencia_laboral = ? WHERE id = ?",
                    (request.form.get(f"competencia_{numero}", "").strip(), pid),
                )

                raes      = request.form.getlist(f"rae_{numero}[]")
                conceptos = request.form.getlist(f"conceptos_{numero}[]")
                proced    = request.form.getlist(f"procedimientos_{numero}[]")
                actitudes = request.form.getlist(f"actitudes_{numero}[]")
                productos = request.form.getlist(f"producto_{numero}[]")
                recursos  = request.form.getlist(f"recursos_{numero}[]")

                conn.execute("DELETE FROM coherencia_rae WHERE periodo_id = ?", (pid,))
                orden = 0
                for i, rae_val in enumerate(raes):
                    rae_val = (rae_val or "").strip()
                    if not rae_val:
                        continue  # fila vacía (agregada y no llenada) — se ignora
                    conn.execute(
                        """INSERT INTO coherencia_rae
                           (periodo_id, rae, conceptos, procedimientos, actitudes,
                            producto, recursos, orden)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            pid, rae_val,
                            (conceptos[i] if i < len(conceptos) else "").strip(),
                            (proced[i]    if i < len(proced)    else "").strip(),
                            (actitudes[i] if i < len(actitudes) else "").strip(),
                            (productos[i] if i < len(productos) else "").strip(),
                            (recursos[i]  if i < len(recursos)  else "").strip(),
                            orden,
                        ),
                    )
                    orden += 1
                    filas_guardadas += 1

            conn.execute(
                "UPDATE coherencia_horizontal SET fecha_actualizacion = datetime('now') WHERE id = ?",
                (matriz_id,),
            )
            conn.commit()
            flash(f"Matriz guardada — {filas_guardadas} RAE en total. Descargando Word…", "success")
            return redirect(
                url_for("coherencia_bp.coherencia_editar", matriz_id=matriz_id) + "?generado=1"
            )

        return redirect(url_for("coherencia_bp.coherencia_editar", matriz_id=matriz_id))

    return render_template(
        "coherencia/editar.html",
        matriz=matriz,
        periodos=periodos,
        proposito=PROPOSITO,
        es_admin=admin,
        puede_editar=puede_editar,
    )


@coherencia_bp.route("/coherencia/<int:matriz_id>/eliminar", methods=["POST"])
@login_required
def coherencia_eliminar(matriz_id):
    u = get_usuario()
    conn = get_db()
    admin = _es_admin(u)

    matriz = conn.execute(
        "SELECT * FROM coherencia_horizontal WHERE id = ?", (matriz_id,)
    ).fetchone()
    if not matriz:
        flash("Matriz no encontrada.", "error")
        return redirect(url_for("coherencia_bp.coherencia_index"))
    if matriz["docente_id"] != u["id"] and not admin:
        flash("Sin permiso para eliminar esta matriz.", "error")
        return redirect(url_for("coherencia_bp.coherencia_index"))
    if not _csrf_check():
        flash("Token de seguridad inválido.", "error")
        return redirect(url_for("coherencia_bp.coherencia_index"))

    conn.execute(
        """DELETE FROM coherencia_rae WHERE periodo_id IN
           (SELECT id FROM coherencia_periodo WHERE matriz_id = ?)""",
        (matriz_id,),
    )
    conn.execute("DELETE FROM coherencia_periodo WHERE matriz_id = ?", (matriz_id,))
    conn.execute("DELETE FROM coherencia_horizontal WHERE id = ?", (matriz_id,))
    conn.commit()
    flash("Matriz eliminada.", "success")
    return redirect(url_for("coherencia_bp.coherencia_index"))


@coherencia_bp.route("/coherencia/<int:matriz_id>/imprimir")
@login_required
def coherencia_imprimir(matriz_id):
    u = get_usuario()
    conn = get_db()
    admin = _es_admin(u)

    matriz, periodos = _cargar_matriz(conn, matriz_id)
    if not matriz:
        return "Matriz no encontrada", 404
    if matriz["docente_id"] != u["id"] and not admin:
        return "Sin permiso para ver esta matriz.", 403

    return render_template(
        "coherencia/imprimir.html",
        matriz=matriz,
        periodos=periodos,
        proposito=PROPOSITO,
        centro=_get_config_centro(),
    )


@coherencia_bp.route("/coherencia/<int:matriz_id>/docx")
@login_required
def coherencia_docx(matriz_id):
    """Exporta la matriz al .docx con el formato exacto de la plantilla del
    coordinador. Mismo mecanismo que el generador ABP: subprocess a Node."""
    u = get_usuario()
    conn = get_db()
    admin = _es_admin(u)

    matriz, periodos = _cargar_matriz(conn, matriz_id)
    if not matriz:
        return jsonify({"error": "Matriz no encontrada"}), 404
    if matriz["docente_id"] != u["id"] and not admin:
        return jsonify({"error": "Sin permiso para exportar esta matriz."}), 403

    script_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "generar_coherencia_docx.js"
    )
    if not os.path.exists(script_path):
        return jsonify({"error": "Generador de documentos no encontrado"}), 500

    centro_cfg = _get_config_centro()
    payload = {
        "centro":       matriz["centro"] or centro_cfg.get("nombre", ""),
        "anio_escolar": matriz["anio_escolar"],
        "proposito":    PROPOSITO,
        "docente":      matriz["docente_nombre"],
        "asignatura":   matriz["asignatura"] or "",
        "mencion":      matriz["mencion"] or "",
        "grado":        matriz["grado"] or "",
        "periodos": [
            {
                "titulo":              p["titulo"],
                "competencia_laboral": p["competencia_laboral"] or "",
                "filas": [
                    {
                        "rae":            f["rae"] or "",
                        "conceptos":      f["conceptos"] or "",
                        "procedimientos": f["procedimientos"] or "",
                        "actitudes":      f["actitudes"] or "",
                        "producto":       f["producto"] or "",
                        "recursos":       f["recursos"] or "",
                    }
                    for f in p["filas"]
                ],
            }
            for p in periodos
        ],
    }

    tmp_in_path = tmp_out_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as tmp_in:
            _json.dump(payload, tmp_in, ensure_ascii=False)
            tmp_in_path = tmp_in.name

        tmp_out = tempfile.NamedTemporaryFile(suffix=".docx", delete=False)
        tmp_out_path = tmp_out.name
        tmp_out.close()

        node_bin = shutil.which("node") or "node"
        npm_bin  = shutil.which("npm") or "npm"
        proj_dir = os.path.dirname(os.path.abspath(__file__))
        node_mod = os.path.join(proj_dir, "node_modules", "docx")

        if not os.path.exists(node_mod):
            install = subprocess.run(
                [npm_bin, "install", "docx", "--prefix", proj_dir],
                capture_output=True, text=True, timeout=120,
            )
            if install.returncode != 0:
                return jsonify({
                    "error": f"No se pudo instalar el módulo docx: {install.stderr[:200]}"
                }), 500

        result = subprocess.run(
            [node_bin, script_path, tmp_in_path, tmp_out_path],
            capture_output=True, text=True, timeout=30, cwd=proj_dir,
        )
        if result.returncode != 0:
            logger.error(f"[coherencia] generador docx falló: {result.stderr[:400]}")
            return jsonify({"error": "Error generando el documento Word."}), 500

        nombre = (
            f"Coherencia_Horizontal_{(matriz['asignatura'] or 'Asignatura').replace(' ', '_')}"
            f"_{(matriz['grado'] or '').replace(' ', '_')}.docx"
        )
        return send_file(
            tmp_out_path,
            as_attachment=True,
            download_name=nombre,
            mimetype="application/vnd.openxmlformats-officedocument."
                     "wordprocessingml.document",
        )

    except subprocess.TimeoutExpired:
        return jsonify({"error": "Tiempo de generación agotado"}), 504
    except Exception as ex:
        logger.error(f"[coherencia] exportar docx: {ex}")
        return jsonify({"error": "Error al exportar el documento."}), 500
    finally:
        if tmp_in_path and os.path.exists(tmp_in_path):
            try:
                os.unlink(tmp_in_path)
            except OSError:
                pass
