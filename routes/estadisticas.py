# -*- coding: utf-8 -*-
"""Blueprint: estadisticas — ML clustering, indicadores, comparativas por mención."""

import sqlite3
import logging
from flask import Blueprint, render_template, request, jsonify, session

from core.constants import *
from core.database import get_db, cache_get, cache_set, cache_bust
from core.auth import _normalizar_rol, login_required, get_usuario
from core.helpers import _features_para_clustering

logger = logging.getLogger("axula")

estadisticas_bp = Blueprint("estadisticas_bp", __name__)


# ── INDICADORES POR MATERIA ──────────────────────────────────────────────────

@estadisticas_bp.route("/api/indicadores/materias/<int:estudiante_id>")
@login_required
def get_indicadores_materias(estudiante_id):
    """Lista de materias disponibles para el estudiante con promedio."""
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT materia,
                   COALESCE(p1,0) p1, COALESCE(p2,0) p2,
                   COALESCE(p3,0) p3, COALESCE(p4,0) p4,
                   COALESCE(promedio,0) promedio, fecha_carga
            FROM materias_calificaciones
            WHERE estudiante_id = ?
            ORDER BY materia
        """, (estudiante_id,)).fetchall()
    return jsonify([dict(r) for r in rows])


@estadisticas_bp.route("/api/indicadores/<int:estudiante_id>")
@login_required
def get_indicadores(estudiante_id):
    """Indicadores de una materia específica por período."""
    materia = request.args.get("materia", "")
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("""
            SELECT materia, p1, p2, p3, p4, promedio, fecha_carga
            FROM materias_calificaciones
            WHERE estudiante_id=? AND materia=?
        """, (estudiante_id, materia)).fetchone()
    if not row:
        return jsonify({"indicadores": [], "materia": materia, "promedio": 0})
    r = dict(row)
    periodos = []
    for i, (p, label) in enumerate([("p1","P1"),("p2","P2"),("p3","P3"),("p4","P4")], 1):
        val = r.get(p)
        if val and val > 0:
            periodos.append({
                "periodo": label,
                "indicador_texto": f"Período {i}",
                "p1": val if i==1 else None,
                "p2": val if i==2 else None,
                "p3": val if i==3 else None,
                "p4": val if i==4 else None,
            })
    return jsonify({
        "materia":    r["materia"],
        "promedio":   r["promedio"] or 0,
        "indicadores": periodos,
        "p1": r["p1"], "p2": r["p2"], "p3": r["p3"], "p4": r["p4"],
    })


# ── CLUSTERING ML ────────────────────────────────────────────────────────────

@estadisticas_bp.route("/api/ml/calcular", methods=["POST"])
@login_required
def calcular_clusters():
    """K-Means puro con numpy — compatible con cualquier Python."""
    try:
        import numpy as np

        def kmeans_numpy(X, k, max_iter=300, n_init=10, seed=42):
            """K-Means implementado con numpy puro."""
            rng = np.random.RandomState(seed)
            best_inertia = float('inf')
            best_labels  = None
            best_centers = None

            for _ in range(n_init):
                idx = [rng.randint(0, len(X))]
                for _ in range(k - 1):
                    dists = np.array([min(np.sum((x - X[i])**2) for i in idx) for x in X])
                    probs = dists / dists.sum()
                    idx.append(rng.choice(len(X), p=probs))
                centers = X[idx].copy()

                labels = np.zeros(len(X), dtype=int)
                for iteration in range(max_iter):
                    dists  = np.array([[np.sum((x - c)**2) for c in centers] for x in X])
                    new_labels = np.argmin(dists, axis=1)
                    if np.all(new_labels == labels):
                        break
                    labels = new_labels
                    for ci in range(k):
                        mask = labels == ci
                        if mask.sum() > 0:
                            centers[ci] = X[mask].mean(axis=0)

                inertia = sum(np.sum((X[labels == ci] - centers[ci])**2)
                              for ci in range(k) if (labels == ci).sum() > 0)
                if inertia < best_inertia:
                    best_inertia  = inertia
                    best_labels   = labels.copy()
                    best_centers  = centers.copy()

            return best_labels, best_centers, best_inertia

        def silhouette(X, labels):
            """Silhouette score simplificado."""
            n = len(X)
            if n < 4:
                return 0.0
            scores = []
            unique = list(set(labels))
            if len(unique) < 2:
                return 0.0
            for i in range(n):
                same  = X[labels == labels[i]]
                a     = np.mean([np.sqrt(np.sum((X[i]-x)**2)) for x in same if not np.all(x==X[i])]) if len(same) > 1 else 0
                other_means = []
                for c in unique:
                    if c != labels[i]:
                        grp = X[labels == c]
                        if len(grp) > 0:
                            other_means.append(np.mean([np.sqrt(np.sum((X[i]-x)**2)) for x in grp]))
                b = min(other_means) if other_means else 0
                m = max(a, b)
                scores.append((b - a) / m if m > 0 else 0)
            return float(np.mean(scores))

        with sqlite3.connect(DATABASE, timeout=10) as conn:
            conn.row_factory = sqlite3.Row
            rows = _features_para_clustering(conn)

        if len(rows) < 10:
            return jsonify({"error": f"Solo {len(rows)} estudiantes con datos. "
                                      "Se necesitan al menos 10 para clustering."}), 400

        ids   = [r[0] for r in rows]
        X_raw = np.array([[r[1],r[2],r[3],r[4],r[5],r[6],r[7],r[8],r[9],r[10],r[11],r[12]]
                           for r in rows], dtype=float)

        mean = X_raw.mean(axis=0)
        std  = X_raw.std(axis=0)
        std[std == 0] = 1
        Xs = (X_raw - mean) / std

        max_k  = min(5, len(rows) // 5)
        max_k  = max(2, max_k)
        best_k = 2
        best_s = -1
        best_labels = None
        best_centers = None

        for k in range(2, max_k + 1):
            lbs, ctrs, _ = kmeans_numpy(Xs, k)
            if len(set(lbs.tolist())) > 1:
                s = silhouette(Xs, lbs)
                if s > best_s:
                    best_s = s; best_k = k
                    best_labels  = lbs
                    best_centers = ctrs

        if best_labels is None:
            best_labels, best_centers, _ = kmeans_numpy(Xs, 2)
            best_k = 2

        cluster_risk = {}
        for ci in range(best_k):
            mask = best_labels == ci
            if mask.sum() == 0:
                cluster_risk[ci] = 0
                continue
            avg_riesgo = float(X_raw[mask, 6].mean())
            avg_acad   = float(X_raw[mask, 0].mean())
            avg_auto   = float(X_raw[mask, 2].mean())
            cluster_risk[ci] = avg_riesgo - avg_acad * 0.3 - avg_auto * 0.2

        sorted_clusters = sorted(cluster_risk.keys(), key=lambda c: cluster_risk[c])
        cluster_map     = {orig: pos for pos, orig in enumerate(sorted_clusters)}

        distances = np.array([[np.sqrt(np.sum((Xs[i] - best_centers[ci])**2))
                                for ci in range(best_k)]
                               for i in range(len(Xs))])

        meta_map = {}
        for orig_ci in range(best_k):
            mask = best_labels == orig_ci
            if mask.sum() == 0:
                continue
            avg_acad   = float(X_raw[mask, 0].mean())
            avg_cond   = float(X_raw[mask, 1].mean())
            avg_auto   = float(X_raw[mask, 2].mean())
            avg_riesgo = float(X_raw[mask, 6].mean())
            avg_conflic= float(X_raw[mask, 8].mean())

            if avg_acad >= 75 and avg_auto >= 70 and avg_riesgo < 25:
                meta_idx = 0
            elif avg_acad >= 75 and avg_auto < 60:
                meta_idx = 3
            elif avg_riesgo >= 45 or avg_conflic >= 50:
                meta_idx = 4
            elif avg_conflic >= 35 or avg_cond < 55:
                meta_idx = 2
            else:
                meta_idx = 1

            meta = CLUSTER_META[min(meta_idx, len(CLUSTER_META) - 1)]
            meta_map[orig_ci] = {
                "label":       meta["label"],
                "color":       meta["color"],
                "icon":        meta["icon"],
                "accion":      meta["accion"],
                "desc":        meta["desc"],
                "n":           int(mask.sum()),
                "avg_acad":    round(avg_acad, 1),
                "avg_cond":    round(avg_cond, 1),
                "avg_auto":    round(avg_auto, 1),
                "avg_riesgo":  round(avg_riesgo, 1),
            }

        with sqlite3.connect(DATABASE, timeout=10) as conn:
            for i, (est_id, orig_ci) in enumerate(zip(ids, best_labels.tolist())):
                meta      = meta_map.get(int(orig_ci), {})
                dist_min  = float(distances[i][orig_ci])
                score     = round(max(0, 100 - dist_min * 10), 1)
                conn.execute("""
                    UPDATE estudiantes
                    SET cluster_id=?, cluster_label=?, cluster_color=?, cluster_score=?
                    WHERE id=?
                """, (int(cluster_map[int(orig_ci)]), meta.get("label",""),
                      meta.get("color","#888"), score, est_id))
            conn.execute("""
                INSERT INTO ml_clusters (n_clusters, features_usadas, resumen)
                VALUES (?,?,?)
            """, (best_k,
                  "p_acad,p_cond,p_auto,p_emocional,motivacion,apoyo_familiar,"
                  "indice_riesgo,interrupciones,conflictos,falta_respeto,distraccion,prom_modulos",
                  str({v["label"]: v["n"] for v in meta_map.values()})))
            conn.commit()

        return jsonify({
            "ok":    True,
            "k":     best_k,
            "silhouette": round(best_s, 3),
            "estudiantes_analizados": len(ids),
            "clusters": [meta_map[ci] for ci in sorted(meta_map.keys(),
                          key=lambda c: cluster_risk[c])]
        })

    except Exception as ex:
        logger.error(f"[ML] Error clustering: {ex}", exc_info=True)
        return jsonify({"error": "Error al calcular métricas. Intenta de nuevo."}), 500


@estadisticas_bp.route("/api/ml/patrones")
@login_required
def get_patrones():
    """Devuelve resumen de clusters + estudiantes por cluster."""
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        clusters = conn.execute("""
            SELECT cluster_id, cluster_label, cluster_color,
                   COUNT(*) n,
                   ROUND(AVG(p_acad),1)       avg_acad,
                   ROUND(AVG(p_cond),1)       avg_cond,
                   ROUND(AVG(p_auto),1)       avg_auto,
                   ROUND(AVG(indice_riesgo),1) avg_riesgo,
                   ROUND(AVG(cluster_score),1) avg_score
            FROM estudiantes
            WHERE cluster_id IS NOT NULL
            GROUP BY cluster_id
            ORDER BY cluster_id
        """).fetchall()

        estudiantes = conn.execute("""
            SELECT id, nombre, apellido, grado, curso,
                   cluster_id, cluster_label, cluster_color, cluster_score,
                   p_acad, p_cond, indice_riesgo
            FROM estudiantes
            WHERE cluster_id IS NOT NULL
            ORDER BY cluster_id, indice_riesgo DESC
        """).fetchall()

        ultimo = conn.execute("""
            SELECT fecha_calculo, n_clusters FROM ml_clusters
            ORDER BY id DESC LIMIT 1
        """).fetchone()

    label_to_meta = {m["label"]: m for m in CLUSTER_META}

    clusters_out = []
    for c in clusters:
        d = dict(c)
        meta = label_to_meta.get(d["cluster_label"], {})
        d["icon"]   = meta.get("icon",  "📌")
        d["accion"] = meta.get("accion","")
        d["desc"]   = meta.get("desc",  "")
        clusters_out.append(d)

    return jsonify({
        "clusters":     clusters_out,
        "estudiantes":  [dict(e) for e in estudiantes],
        "ultimo_calculo": dict(ultimo) if ultimo else None
    })


@estadisticas_bp.route("/api/ml/similar/<int:est_id>")
@login_required
def estudiantes_similares(est_id):
    """Devuelve los 5 estudiantes más similares al perfil dado."""
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        target = conn.execute(
            "SELECT * FROM estudiantes WHERE id=?", (est_id,)
        ).fetchone()
        if not target:
            return jsonify([])
        t = dict(target)

        same_cluster = conn.execute("""
            SELECT id, nombre, apellido, grado, curso,
                   p_acad, p_cond, indice_riesgo, cluster_label, cluster_score
            FROM estudiantes
            WHERE cluster_id=? AND id!=?
            ORDER BY ABS(COALESCE(p_acad,0) - ?)
                   + ABS(COALESCE(indice_riesgo,0) - ?)
            LIMIT 5
        """, (t.get("cluster_id"), est_id,
              t.get("p_acad") or 0, t.get("indice_riesgo") or 0)).fetchall()

    return jsonify([dict(e) for e in same_cluster])


@estadisticas_bp.route("/patrones")
@login_required
def vista_patrones():
    return render_template("patrones.html", current_user=get_usuario())


# ── COMPARATIVA POR MENCIÓN ──────────────────────────────────────────────────

@estadisticas_bp.route("/api/comparativa-mencion")
@login_required
def comparativa_mencion():
    """Devuelve promedios académicos, conductuales y de riesgo agrupados por mención."""
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT
                curso,
                AVG(CASE WHEN p_acad  > 0 THEN p_acad  END) as avg_acad,
                AVG(CASE WHEN p_cond  > 0 THEN p_cond  END) as avg_cond,
                AVG(CASE WHEN p_auto  > 0 THEN p_auto  END) as avg_auto,
                AVG(CASE WHEN indice_riesgo > 0 THEN indice_riesgo END) as avg_riesgo,
                AVG(CASE WHEN prom_modulos  > 0 THEN prom_modulos  END) as avg_modulos,
                COUNT(*) as total,
                SUM(CASE WHEN p_acad > 0 THEN 1 ELSE 0 END) as con_notas,
                SUM(CASE WHEN indice_riesgo >= 50 THEN 1 ELSE 0 END) as riesgo_alto,
                SUM(CASE WHEN categoria = 'ALERTA DE REPROBACIÓN' THEN 1 ELSE 0 END) as alertas
            FROM estudiantes
            WHERE condicion IS NULL OR condicion != 'RETIRADO'
            GROUP BY curso
            ORDER BY curso
        """).fetchall()

    MENCION_LABEL = {
        'multimedia': 'Multimedia',
        'teatro':     'Teatro',
        'musica':     'Música',
        'visual':     'Artes Visuales',
    }
    MENCION_COLOR = {
        'multimedia': '#c8f060',
        'teatro':     '#60b8f0',
        'musica':     '#ff9f60',
        'visual':     '#c060f0',
    }

    result = []
    for r in rows:
        curso = (r['curso'] or '').lower()
        mencion_key = next((k for k in MENCION_LABEL if k in curso), None)
        if not mencion_key:
            continue
        result.append({
            'curso':       r['curso'],
            'mencion':     MENCION_LABEL[mencion_key],
            'color':       MENCION_COLOR[mencion_key],
            'total':       r['total'],
            'con_notas':   r['con_notas'],
            'riesgo_alto': r['riesgo_alto'],
            'alertas':     r['alertas'],
            'avg_acad':    round(r['avg_acad'] or 0, 1),
            'avg_cond':    round(r['avg_cond'] or 0, 1),
            'avg_auto':    round(r['avg_auto'] or 0, 1),
            'avg_riesgo':  round(r['avg_riesgo'] or 0, 1),
            'avg_modulos': round(r['avg_modulos'] or 0, 1),
        })

    merged = {}
    for r in result:
        m = r['mencion']
        if m not in merged:
            merged[m] = {**r, '_cnt': 1}
        else:
            ex = merged[m]
            ex['total']       += r['total']
            ex['con_notas']   += r['con_notas']
            ex['riesgo_alto'] += r['riesgo_alto']
            ex['alertas']     += r['alertas']
            n = ex['_cnt']
            for k in ('avg_acad','avg_cond','avg_auto','avg_riesgo','avg_modulos'):
                ex[k] = round((ex[k] * n + r[k]) / (n + 1), 1)
            ex['_cnt'] += 1

    final = []
    for m, d in merged.items():
        d.pop('_cnt', None)
        final.append(d)

    return jsonify(final)
