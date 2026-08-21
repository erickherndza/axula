# -*- coding: utf-8 -*-
"""Blueprint: perfil — Perfil de estudiante, análisis IA, fotos, expediente, cuaderno."""

import sqlite3
import logging
import os
from datetime import date
from flask import (
    Blueprint, render_template, request, jsonify, session,
    redirect, send_file, abort,
)

from core.constants import *
from core.database import get_db, cache_get, cache_set, cache_bust
from core.auth import (
    _normalizar_rol, login_required, rate_limited, get_usuario,
)
from core.helpers import (
    _anonimizar_estudiante, _calcular_bienestar_emocional,
    _calcular_indice_conductual, _recalcular_indicadores,
    _validar_magic_imagen, _get_profesor,
    calcular_motor_conductual, _semaforo_color,
)
from core.ia import _get_groq_client, construir_prompt, generar_con_fallback
from core import rls as _rls

logger = logging.getLogger("axula")

perfil_bp = Blueprint("perfil_bp", __name__)


# ── PERFIL DEL ESTUDIANTE ────────────────────────────────────────────────────

@perfil_bp.route("/perfil/<int:id>")
@login_required
def perfil_estudiante(id):
    u = get_usuario()
    if u.get("rol") == "padre":
        with sqlite3.connect(DATABASE, timeout=10) as _vc:
            vinculo = _vc.execute(
                "SELECT id FROM vinculos_padre_estudiante WHERE padre_id=? AND estudiante_id=?",
                (u["id"], id)
            ).fetchone()
        if not vinculo:
            return redirect("/portal-padres")

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        estudiante = conn.execute(
            "SELECT * FROM estudiantes WHERE id = ?", (id,)
        ).fetchone()
    if estudiante:
        e = dict(estudiante)

        with sqlite3.connect(DATABASE, timeout=10) as conn2:
            conn2.row_factory = sqlite3.Row
            mats = conn2.execute("""
                SELECT materia, p1, p2, p3, p4, promedio, fecha_carga, profesor
                FROM materias_calificaciones
                WHERE estudiante_id = ?
            """, (id,)).fetchall()

        if mats:
            MODULO_MAP_PERFIL = {
                'fotografía':                       'fotografia',
                'fotografia':                       'fotografia',
                'foto':                             'fotografia',
                'fotografía digital':               'fotografia',
                'fotografia digital':               'fotografia',
                'introducción fotografía':          'fotografia',
                'introduccion fotografia':          'fotografia',
                'introducción fotografía digital':  'fotografia',
                'introduccion fotografia digital':  'fotografia',
                'introducción a la fotografía':     'fotografia',
                'introduccion a la fotografia':     'fotografia',
                'introducción a la fotografía digital': 'fotografia',
                'introduccion a la fotografia digital': 'fotografia',
                'fotografía artística':             'fotografia',
                'fotografia artistica':             'fotografia',
                'lenguaje visual':                                          'lv',
                'lenguaje visual, dibujo y creación de personajes':         'lv',
                'lenguaje visual dibujo y creacion de personajes':          'lv',
                'lenguaje visual, dibujo y creacion de personajes':         'lv',
                'lenguaje visual y principios de diseño':                   'lv',
                'lenguaje visual y principios de diseno':                   'lv',
                'lenguaje visual y principios del diseño':                  'lv',
                'lenguaje visual y principios del diseno':                  'lv',
                'lenguaje visual y principios del diseño artesanal':        'lv',
                'lenguaje visual y principios del diseno artesanal':        'lv',
                'lenguaje visual artesanal':                                'lv',
                'lenguaje plástico y visual':                               'lv',
                'lenguaje plastico y visual':                               'lv',
                'lv':                                                       'lv',
                'diseño básico y expresión visual':                  'diseno',
                'diseño basico y expresion visual':                  'diseno',
                'diseño básico y expresion visual':                  'diseno',
                'diseno basico y expresion visual':                  'diseno',
                'diseño básico':                                     'diseno',
                'diseño basico':                                     'diseno',
                'diseño':                                            'diseno',
                'diseno':                                            'diseno',
                'dibujo técnico':                                    'diseno',
                'dibujo tecnico':                                    'diseno',
                'dibujo técnico y artístico':                        'diseno',
                'dibujo tecnico y artistico':                        'diseno',
                'principios de dibujo, pintura y creatividad':       'diseno',
                'principios de dibujo pintura y creatividad':        'diseno',
                'pintura y técnicas mixtas':                         'diseno',
                'pintura y tecnicas mixtas':                         'diseno',
                'pintura':                                           'diseno',
                'lenguaje plástico':                                 'diseno',
                'lenguaje plastico':                                 'diseno',

                # ── MÚSICA ──────────────────────────────────────────────────────────
                'instrumento i':                                         'instrumento',
                'instrumento ii':                                        'instrumento',
                'instrumento iii':                                       'instrumento',
                'instrumento':                                           'instrumento',
                'instrumento principal':                                 'instrumento',
                'práctica instrumental':                                 'instrumento',
                'practica instrumental':                                 'instrumento',
                'práctica instrumental grupal i':                        'instrumento',
                'practica instrumental grupal i':                        'instrumento',
                'práctica instrumental grupal ii':                       'instrumento',
                'practica instrumental grupal ii':                       'instrumento',
                'práctica instrumental grupal iii':                      'instrumento',
                'practica instrumental grupal iii':                      'instrumento',
                'canto coral i':                                         'canto',
                'canto coral ii':                                        'canto',
                'canto coral iii':                                       'canto',
                'canto coral':                                           'canto',
                'canto':                                                 'canto',
                'coral':                                                 'canto',
                'lenguaje musical':                                      'lenguaje_musical',
                'lenguaje musical, teoría y entrenamiento':              'lenguaje_musical',
                'lenguaje musical, teoria y entrenamiento':              'lenguaje_musical',
                'lenguaje musical teoría y entrenamiento':               'lenguaje_musical',
                'lenguaje musical teoria y entrenamiento':               'lenguaje_musical',
                'teoría musical':                                        'lenguaje_musical',
                'teoria musical':                                        'lenguaje_musical',
                'solfeo':                                                'lenguaje_musical',
                'introducción a la historia del arte universal y dominicano': 'lenguaje_musical',
                'introduccion a la historia del arte universal y dominicano': 'lenguaje_musical',

                # ── TEATRO ──────────────────────────────────────────────────────────
                'entrenamiento rítmico, corporal y vocal i':             'entrenamiento',
                'entrenamiento ritmico, corporal y vocal i':             'entrenamiento',
                'entrenamiento rítmico corporal y vocal i':              'entrenamiento',
                'entrenamiento ritmico corporal y vocal i':              'entrenamiento',
                'entrenamiento rítmico, corporal y vocal ii':            'entrenamiento',
                'entrenamiento ritmico, corporal y vocal ii':            'entrenamiento',
                'entrenamiento rítmico, corporal y vocal iii':           'entrenamiento',
                'entrenamiento ritmico, corporal y vocal iii':           'entrenamiento',
                'entrenamiento vocal':                                   'entrenamiento',
                'técnica vocal':                                         'entrenamiento',
                'tecnica vocal':                                         'entrenamiento',
                'lenguaje danzario y teatral':                           'expresion',
                'lenguaje danzario teatral':                             'expresion',
                'lenguaje danzario':                                     'expresion',
                'expresión corporal':                                    'expresion',
                'expresion corporal':                                    'expresion',
                'actuación teatral':                                     'expresion',
                'actuacion teatral':                                     'expresion',
                'historia del arte y apreciación del teatro universal':  'historia_teatro',
                'historia del arte y apreciacion del teatro universal':  'historia_teatro',
                'historia del arte y apreciación del teatro':            'historia_teatro',
                'historia del teatro':                                   'historia_teatro',
                'historia y apreciación teatral':                        'historia_teatro',
                'historia y apreciacion teatral':                        'historia_teatro',
                'apreciación teatral':                                   'historia_teatro',
                'apreciacion teatral':                                   'historia_teatro',

                # ── ARTES VISUALES ──────────────────────────────────────────────────
                'dibujo técnico':                                        'dibujo',
                'dibujo tecnico':                                        'dibujo',
                'dibujo técnico y artístico':                            'dibujo',
                'dibujo tecnico y artistico':                            'dibujo',
                'principios de dibujo, pintura y creatividad':           'dibujo',
                'principios de dibujo pintura y creatividad':            'dibujo',
                'principios de dibujo':                                  'dibujo',
                'dibujo':                                                'dibujo',
                'pintura y técnicas mixtas':                             'pintura',
                'pintura y tecnicas mixtas':                             'pintura',
                'pintura':                                               'pintura',
                'técnicas mixtas':                                       'pintura',
                'tecnicas mixtas':                                       'pintura',
                'cerámica':                                              'pintura',
                'ceramica':                                              'pintura',
                'historia del arte universal y teoría de las artes visuales.': 'historia_arte',
                'historia del arte universal y teoria de las artes visuales.': 'historia_arte',
                'historia del arte universal y teoría de las artes visuales':  'historia_arte',
                'historia del arte universal y teoria de las artes visuales':  'historia_arte',
                'historia del arte universal y la estética digital':     'historia_arte',
                'historia del arte universal y la estetica digital':     'historia_arte',
                'historia del arte':                                     'historia_arte',
                'historia del arte universal':                           'historia_arte',
                'apreciación artística':                                 'historia_arte',
                'apreciacion artistica':                                 'historia_arte',
            }

            MATS_ACAD_STD = {
                'lengua española', 'lengua espanola', 'español', 'espanol',
                'lengua', 'lengua y literatura', 'castellano',
                'inglés', 'ingles', 'english', 'idioma extranjero',
                'idioma inglés', 'idioma ingles', 'idioma inglés',
                'matemática', 'matematica', 'matemáticas', 'matematicas', 'math',
                'matemática general', 'matematica general',
                'ciencias sociales', 'sociales', 'cs. sociales', 'cs sociales',
                'historia y geografía', 'historia y geografia',
                'ciencias de la naturaleza', 'ciencias naturales', 'naturales',
                'cs. naturales', 'cs naturales', 'ciencias nat.',
                'ciencias nat', 'biología', 'biologia',
                'formación integral humana y religiosa',
                'formacion integral humana y religiosa',
                'formación humana y religiosa',
                'formacion humana y religiosa',
                'formación religiosa', 'formacion religiosa',
                'religión', 'religion',
                'f.i.h.r.', 'fihr',
                'formacion integral', 'formación integral',
                'ed. religiosa', 'educacion religiosa', 'educación religiosa',
                'formación integral humana',
                'educación física', 'educacion fisica',
                'ed. física', 'ed fisica', 'ed. fis.',
                'educacion fiscia', 'educacion fis',
                'fisica', 'física',
            }

            materias_extras = {}
            promedios_acad  = []
            ASISTENCIA_KEYS = {'asistencia', 'asistencias', 'asist.', 'attendence'}

            for mat in mats:
                mn = mat['materia'].lower().strip()

                if any(a in mn for a in ASISTENCIA_KEYS):
                    for pi in [1,2,3,4]:
                        key = f'asistencia_p{pi}'
                        if not e.get(key):
                            e[key] = mat[f'p{pi}'] or 0
                    continue

                col = MODULO_MAP_PERFIL.get(mn)
                if not col:
                    for k, v in MODULO_MAP_PERFIL.items():
                        if k in mn or mn in k:
                            col = v
                            break

                if col:
                    P_COL_MAP = {
                        'fotografia':      'p_foto',
                        'lv':              'p_lv',
                        'diseno':          'p_diseno',
                        'instrumento':     'p_instrumento',
                        'canto':           'p_canto',
                        'lenguaje_musical':'p_lenguaje_musical',
                        'entrenamiento':   'p_entrenamiento',
                        'expresion':       'p_expresion',
                        'historia_teatro': 'p_historia_teatro',
                        'dibujo':          'p_dibujo',
                        'pintura':         'p_pintura',
                        'historia_arte':   'p_historia_arte',
                    }
                    p_col = P_COL_MAP.get(col, f'p_{col}')
                    for pi in [1,2,3,4]:
                        key = f'{col}_p{pi}'
                        if not e.get(key):
                            e[key] = mat[f'p{pi}'] or 0
                    if not e.get(p_col) and mat['promedio']:
                        e[p_col] = mat['promedio']
                    continue

                es_acad = any(a in mn or mn in a for a in MATS_ACAD_STD)
                if es_acad:
                    if mat['promedio'] and mat['promedio'] > 0:
                        promedios_acad.append(mat['promedio'])
                    for pi in [1,2,3,4]:
                        key = f'acad_p{pi}'
                        if not e.get(key) and mat[f'p{pi}']:
                            e[key] = mat[f'p{pi}']
                    continue

                nombre_mat = mat['materia'].strip()
                materias_extras[nombre_mat] = {
                    'p1': mat['p1'], 'p2': mat['p2'],
                    'p3': mat['p3'], 'p4': mat['p4'],
                    'promedio': mat['promedio'],
                }
                if mat['promedio'] and mat['promedio'] > 0:
                    promedios_acad.append(mat['promedio'])

            if materias_extras:
                e['materias_extras'] = materias_extras

            mencion_e = str(e.get('mencion') or '').upper()
            if 'MUSIC' in mencion_e or 'MÚSICA' in mencion_e:
                mod_keys = ['p_instrumento', 'p_canto', 'p_lenguaje_musical']
            elif 'TEATRO' in mencion_e:
                mod_keys = ['p_entrenamiento', 'p_expresion', 'p_historia_teatro']
            elif 'VISUAL' in mencion_e:
                mod_keys = ['p_dibujo', 'p_pintura', 'p_historia_arte']
            else:  # Multimedia y default
                mod_keys = ['p_foto', 'p_lv', 'p_diseno']
            mods = [e.get(k) or 0 for k in mod_keys if (e.get(k) or 0) > 0]
            if not mods and e.get('materias_extras'):
                mods = [v.get('promedio') or 0 for v in e['materias_extras'].values() if (v.get('promedio') or 0) > 0]
            if mods and not e.get('prom_modulos'):
                e['prom_modulos'] = round(sum(mods)/len(mods), 1)

            if not e.get('p_acad') and promedios_acad:
                e['p_acad'] = round(sum(promedios_acad)/len(promedios_acad), 1)

        texto_defaults = {
            'uso_celular': 'No', 'nivel_riesgo': 'N/D',
            'grado': '4to', 'condicion': 'ACTIVO',
            'tendencia': 'igual', 'categoria': '',
            'reporte': '', 'color': '', 'ia_analisis': None,
            'nombre': '', 'apellido': '', 'curso': '',
        }
        for k, v in texto_defaults.items():
            if e.get(k) is None:
                e[k] = v

        campos_numericos = [
            'p_acad','p_foto','p_lv','p_diseno','p_cond','p_auto',
            'p_emocional','prom_modulos','asistencia','proyeccion',
            'puntualidad','tareas','participacion','comprension','rendimiento',
            'interrupciones','conflictos','desafia_autoridad','distraccion',
            'falta_respeto','motivacion','estado_emocional','interes_futuro',
            'apoyo_familiar','indice_riesgo','edad','silencioso',
            'fotografia_p1','fotografia_p2','fotografia_p3','fotografia_p4',
            'lv_p1','lv_p2','lv_p3','lv_p4',
            'diseno_p1','diseno_p2','diseno_p3','diseno_p4',
            'asistencia_p1','asistencia_p2','asistencia_p3','asistencia_p4',
            'acad_p1','acad_p2','acad_p3','acad_p4',
            # Música
            'instrumento_p1','instrumento_p2','instrumento_p3','instrumento_p4','p_instrumento',
            'canto_p1','canto_p2','canto_p3','canto_p4','p_canto',
            'lenguaje_musical_p1','lenguaje_musical_p2','lenguaje_musical_p3','lenguaje_musical_p4','p_lenguaje_musical',
            # Teatro
            'entrenamiento_p1','entrenamiento_p2','entrenamiento_p3','entrenamiento_p4','p_entrenamiento',
            'expresion_p1','expresion_p2','expresion_p3','expresion_p4','p_expresion',
            'historia_teatro_p1','historia_teatro_p2','historia_teatro_p3','historia_teatro_p4','p_historia_teatro',
            # Artes Visuales
            'dibujo_p1','dibujo_p2','dibujo_p3','dibujo_p4','p_dibujo',
            'pintura_p1','pintura_p2','pintura_p3','pintura_p4','p_pintura',
            'historia_arte_p1','historia_arte_p2','historia_arte_p3','historia_arte_p4','p_historia_arte',
        ]
        for k in campos_numericos:
            if e.get(k) is None:
                e[k] = 0.0

        acad_p1 = e.get('acad_p1') or 0
        acad_p2 = e.get('acad_p2') or 0
        acad_p3 = e.get('acad_p3') or 0
        acad_p4 = e.get('acad_p4') or 0
        p_acad  = e.get('p_acad')  or 0

        periodos_con_nota = [p for p in [acad_p1,acad_p2,acad_p3,acad_p4] if p > 0]

        if len(periodos_con_nota) >= 2:
            ultimo    = periodos_con_nota[-1]
            penultimo = periodos_con_nota[-2]
            delta     = ultimo - penultimo
            amort     = 0.6 if len(periodos_con_nota) >= 3 else 0.8
            proyeccion_calc = round(min(max(ultimo + delta * amort, 0), 100), 1)
        elif len(periodos_con_nota) == 1:
            base = periodos_con_nota[0]
            p_cond  = e.get('p_cond') or 0
            p_auto  = e.get('p_auto') or 0
            boost = 0
            if p_cond  >= 75: boost += 1.5
            if p_auto  >= 70: boost += 1.0
            if p_cond  <  60: boost -= 2.0
            proyeccion_calc = round(min(max(base + boost, 0), 100), 1)
        elif p_acad > 0:
            proyeccion_calc = p_acad
        else:
            _mencion_proy = str(e.get('mencion') or '').upper()
            if 'MUSIC' in _mencion_proy or 'MÚSICA' in _mencion_proy:
                _mod_keys_proy = ['p_instrumento', 'p_canto', 'p_lenguaje_musical']
            elif 'TEATRO' in _mencion_proy:
                _mod_keys_proy = ['p_entrenamiento', 'p_expresion', 'p_historia_teatro']
            elif 'VISUAL' in _mencion_proy:
                _mod_keys_proy = ['p_dibujo', 'p_pintura', 'p_historia_arte']
            else:
                _mod_keys_proy = ['p_foto', 'p_lv', 'p_diseno']
            mods = [e.get(m) or 0 for m in _mod_keys_proy if (e.get(m) or 0) > 0]
            if not mods and e.get('materias_extras'):
                mods = [v.get('promedio') or 0 for v in e['materias_extras'].values() if (v.get('promedio') or 0) > 0]
            proyeccion_calc = round(sum(mods)/len(mods), 1) if mods else 0.0

        if not e.get('proyeccion') or e.get('proyeccion', 0) == 0:
            e['proyeccion'] = proyeccion_calc

        if len(periodos_con_nota) >= 2:
            if periodos_con_nota[-1] > periodos_con_nota[-2]:
                e['tendencia'] = 'subiendo'
            elif periodos_con_nota[-1] < periodos_con_nota[-2]:
                e['tendencia'] = 'bajando'
            else:
                e['tendencia'] = 'igual'

        e['tiene_notas'] = bool(e.get('p_acad', 0) > 0 or e.get('acad_p1', 0) > 0)

        with sqlite3.connect(DATABASE, timeout=10) as _conn:
            _conn.row_factory = sqlite3.Row
            ind_cond  = _calcular_indice_conductual(_conn, id)
            ind_psico = _calcular_bienestar_emocional(_conn, id)
        # Siempre usar el índice calculado del ecosistema — incorpora
        # indicadores directos (prof/psicóloga) + reportes + cuaderno + asistencia.
        e['p_cond'] = ind_cond
        e['p_auto'] = ind_psico

        viewer_rol = _normalizar_rol(u.get("rol", ""))
        _ROLES_COORD = {"coordinador_general", "coordinador_primer_ciclo", "coordinador_segundo_ciclo"}
        if viewer_rol in _ROLES_COORD:
            _CAMPOS_SENSIBLES = [
                "p_emocional", "p_auto", "motivacion", "estado_emocional",
                "silencioso", "indice_riesgo", "nivel_riesgo",
                "apoyo_familiar", "ind_conducta", "ind_psico",
                "interrupciones", "conflictos", "desafia_autoridad",
                "distraccion", "falta_respeto", "ia_analisis",
            ]
            for campo in _CAMPOS_SENSIBLES:
                e[campo] = None

        return render_template("perfil.html", e=e, current_user=get_usuario())
    return "Estudiante no encontrado", 404


# ── ANÁLISIS IA (Groq) ───────────────────────────────────────────────────────

@perfil_bp.route("/api/analisis-ia/<int:id>", methods=["POST"])
@login_required
@rate_limited(max_calls=20, window=60)
def generar_analisis_ia(id):
    _viewer = get_usuario()
    _vrol = _normalizar_rol(_viewer.get("rol", ""))
    if _vrol in {"coordinador_general", "coordinador_primer_ciclo", "coordinador_segundo_ciclo"}:
        return jsonify({"error": "Sin permisos para ver análisis psicopedagógico"}), 403
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        e = conn.execute(
            "SELECT * FROM estudiantes WHERE id = ?", (id,)
        ).fetchone()

    if not e:
        return jsonify({"error": "Estudiante no encontrado"}), 404

    e = dict(e)

    if e.get("ia_analisis"):
        return jsonify({"analisis": e["ia_analisis"], "cached": True})

    try:
        analisis = generar_con_fallback(
            construir_prompt(e),
            prompt_sistema=(
                "Eres un orientador pedagógico experto en la Modalidad de Artes "
                "del bachillerato dominicano. Respondes siempre en español, "
                "de forma estructurada y profesional."
            ),
            temperature=0.6,
            max_tokens=600,
        )

        with sqlite3.connect(DATABASE, timeout=10) as conn:
            conn.execute(
                "UPDATE estudiantes SET ia_analisis = ? WHERE id = ?",
                (analisis, id)
            )
            conn.commit()

        return jsonify({"analisis": analisis, "cached": False})

    except Exception as ex:
        logger.error(f"[IA] Error IA perfil: {ex}")
        return jsonify({"error": "Error al generar el análisis. Intenta de nuevo."}), 500


@perfil_bp.route("/api/analisis-ia/<int:id>", methods=["DELETE"])
@login_required
def limpiar_analisis_ia(id):
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.execute(
            "UPDATE estudiantes SET ia_analisis = NULL WHERE id = ?", (id,)
        )
        conn.commit()
    return jsonify({"status": "cleared"})


@perfil_bp.route("/api/competencias-ia/<int:id>", methods=["POST"])
@login_required
def evaluar_competencias_ia(id):
    """Genera evaluación por competencias usando datos reales de indicadores."""
    try:
        with sqlite3.connect(DATABASE, timeout=10) as conn:
            conn.row_factory = sqlite3.Row
            e = conn.execute("SELECT * FROM estudiantes WHERE id=?", (id,)).fetchone()

        if not e:
            return jsonify({"error": "Estudiante no encontrado"}), 404

        e = dict(e)

        def pv(campo):
            v = e.get(campo)
            return round(float(v), 1) if v and float(v) > 0 else None

        bloques = []

        f_vals = [(f"P{i+1}", pv(f"fotografia_p{i+1}")) for i in range(4)]
        f_con  = [(l,v) for l,v in f_vals if v]
        if f_con:
            bloques.append("FOTOGRAFÍA: " + " | ".join(f"{l}={v}" for l,v in f_con))

        lv_vals = [(f"P{i+1}", pv(f"lv_p{i+1}")) for i in range(4)]
        lv_con  = [(l,v) for l,v in lv_vals if v]
        if lv_con:
            bloques.append("LENGUAJE VISUAL: " + " | ".join(f"{l}={v}" for l,v in lv_con))

        d_vals = [(f"P{i+1}", pv(f"diseno_p{i+1}")) for i in range(4)]
        d_con  = [(l,v) for l,v in d_vals if v]
        if d_con:
            bloques.append("DISEÑO: " + " | ".join(f"{l}={v}" for l,v in d_con))

        a_vals = [(f"P{i+1}", pv(f"asistencia_p{i+1}")) for i in range(4)]
        a_con  = [(l,v) for l,v in a_vals if v]
        if a_con:
            bloques.append("ASISTENCIA: " + " | ".join(f"{l}={v}%" for l,v in a_con))

        ac_vals = [(f"P{i+1}", pv(f"acad_p{i+1}")) for i in range(4)]
        ac_con  = [(l,v) for l,v in ac_vals if v]
        if ac_con:
            bloques.append("PROM. ACADÉMICO: " + " | ".join(f"{l}={v}" for l,v in ac_con))

        comp_items = [
            ("Puntualidad", pv("puntualidad")), ("Tareas", pv("tareas")),
            ("Participación", pv("participacion")), ("Comprensión", pv("comprension")),
            ("Rendimiento", pv("rendimiento")),
        ]
        comp_con = [(l,v) for l,v in comp_items if v]
        if comp_con:
            bloques.append("COMPORTAMIENTO ACADÉMICO: " + " | ".join(f"{l}={v}" for l,v in comp_con))

        emoc_items = [
            ("Motivación", pv("motivacion")), ("Autoestima", pv("p_auto")),
            ("Estado Emocional", pv("estado_emocional")), ("Interés Futuro", pv("interes_futuro")),
            ("Apoyo Familiar", pv("apoyo_familiar")),
        ]
        emoc_con = [(l,v) for l,v in emoc_items if v]
        if emoc_con:
            bloques.append("INDICADORES EMOCIONALES: " + " | ".join(f"{l}={v}" for l,v in emoc_con))

        if not bloques:
            return jsonify({"error": "Este estudiante no tiene datos de calificaciones cargados aún."}), 400

        datos_txt = "\n".join(bloques)
        grado = e.get("grado", "4to")
        nombre_completo = _anonimizar_estudiante(e.get('id', 0))

        prompt = f"""Eres un especialista en evaluación por competencias del bachillerato dominicano,
Modalidad de Artes, mención Multimedia. Genera un informe de competencias basado en datos reales.

ESTUDIANTE: {nombre_completo}
GRADO: {grado} Multimedia
CATEGORÍA: {e.get('categoria','Estable')} | Riesgo: {e.get('nivel_riesgo','Bajo')}
PROMEDIO FINAL: {round(float(e.get('p_acad') or 0), 1)} | Conductual: {round(float(e.get('p_cond') or 0), 1)} | Emocional: {round(float(e.get('p_emocional') or 0), 1)}

CALIFICACIONES:
{datos_txt}

Genera un informe con EXACTAMENTE estas 4 secciones:

1. NIVEL DE COMPETENCIA ALCANZADO
Por cada materia presente, indica el nivel real: Inicial / En desarrollo / Competente / Destacado.
Basa el nivel en los promedios reales. Menciona los datos específicos.

2. PROGRESIÓN ENTRE PERÍODOS
Analiza la evolución P1→P2 (y P3/P4 si existen). ¿Qué mejoró? ¿Qué bajó?
¿La tendencia es positiva o negativa? Sé específico con los números.

3. INDICADORES CRÍTICOS
Lista los 2-3 aspectos con notas más bajas o mayor preocupación.
Para cada uno sugiere una acción concreta y práctica para el docente.

4. PROYECCIÓN P3 Y P4
Con base en la tendencia actual, ¿qué puede lograr al final del año?
¿Qué debe priorizar el docente en los próximos períodos?

Usa lenguaje técnico-pedagógico. Sé preciso con los datos. Máximo 380 palabras."""

        resultado = generar_con_fallback(
            prompt,
            prompt_sistema="Eres un evaluador pedagógico experto en la Modalidad de Artes del bachillerato dominicano. Respondes en español con análisis precisos basados en datos reales.",
            temperature=0.5,
            max_tokens=700,
        )
        return jsonify({"resultado": resultado})

    except Exception as ex:
        logger.error(f"[IA] Error generando análisis perfil: {ex}")
        return jsonify({"error": "Error al generar el análisis. Intenta de nuevo."}), 500


# ── FOTO DE PERFIL ───────────────────────────────────────────────────────────

@perfil_bp.route("/api/foto/<int:id>", methods=["GET"])
@login_required
def servir_foto(id):
    """
    Sirve la foto de perfil de forma autenticada.
    Protege datos de menores — la imagen nunca se expone desde /static directamente.
    Funciona tanto en local (static/fotos/) como en Render (/data/fotos/).
    """
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        _rls.verificar_acceso_estudiante(conn, id)
        row = conn.execute(
            "SELECT foto_path FROM estudiantes WHERE id=?", (id,)
        ).fetchone()

    if not row or not row[0]:
        abort(404)

    stored = row[0]
    # Soporta rutas antiguas (/static/fotos/est_1.jpg) y nuevas (/api/foto/<id>)
    filename = os.path.basename(stored)
    file_path = os.path.join(FOTOS_DIR, filename)

    if not os.path.isfile(file_path):
        abort(404)

    return send_file(file_path, max_age=3600)


@perfil_bp.route("/api/foto/<int:id>", methods=["POST"])
@login_required
def subir_foto_alias(id):
    """Alias de /api/estudiante/<id>/foto POST — compatibilidad con perfil.js."""
    return subir_foto(id)


@perfil_bp.route("/api/foto/<int:id>", methods=["DELETE"])
@login_required
def borrar_foto_alias(id):
    """Alias de /api/estudiante/<id>/foto DELETE — compatibilidad con perfil.js."""
    return borrar_foto(id)


@perfil_bp.route("/api/estudiante/<int:id>/foto", methods=["POST"])
@login_required
def subir_foto(id):
    """Sube foto de perfil de un estudiante."""
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        _rls.verificar_acceso_estudiante(conn, id)  # 403 si no tiene permiso
    f = request.files.get("foto")
    if not f or not f.filename:
        return jsonify({"error": "No se recibió archivo"}), 400
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in (".jpg", ".jpeg", ".png", ".webp"):
        return jsonify({"error": "Formato no válido. Usa JPG, PNG o WEBP"}), 400
    datos = f.read()
    if len(datos) > 5 * 1024 * 1024:
        return jsonify({"error": "La foto no puede superar 5 MB"}), 413
    if not _validar_magic_imagen(datos, ext):
        return jsonify({"error": "El archivo no es una imagen válida"}), 400
    filename = f"est_{id}{ext}"
    path     = os.path.join(FOTOS_DIR, filename)
    with open(path, "wb") as _fh:
        _fh.write(datos)
    # URL autenticada — funciona en Render (/data/fotos) y en local (static/fotos)
    url = f"/api/foto/{id}"
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.execute("UPDATE estudiantes SET foto_path=? WHERE id=?", (url, id))
        conn.commit()
    return jsonify({"ok": True, "url": url})


@perfil_bp.route("/api/estudiante/<int:id>/foto", methods=["DELETE"])
@login_required
def borrar_foto(id):
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        _rls.verificar_acceso_estudiante(conn, id)  # 403 si no tiene permiso
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT foto_path FROM estudiantes WHERE id=?", (id,)).fetchone()
        if row and row["foto_path"]:
            try:
                filename = os.path.basename(row["foto_path"])
                safe_path = os.path.abspath(os.path.join(FOTOS_DIR, filename))
                allowed_dir = os.path.abspath(FOTOS_DIR)
                if safe_path.startswith(allowed_dir + os.sep):
                    os.remove(safe_path)
            except Exception as _e:
                logger.warning(f"[perfil] Excepción silenciada")
        conn.execute("UPDATE estudiantes SET foto_path=NULL WHERE id=?", (id,))
        conn.commit()
    return jsonify({"ok": True})


# ── EXPEDIENTE, LOGROS ───────────────────────────────────────────────────────

@perfil_bp.route("/api/expediente/<int:est_id>", methods=["GET"])
@login_required
def get_expediente(est_id):
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        _recalcular_indicadores(conn, est_id)
        conn.commit()
        reportes = conn.execute("""
            SELECT id,'reporte' as fuente,tipo,subtipo,titulo,descripcion,
                   severidad,reportado_por,fecha,estado,seguimiento,fecha_cierre,
                   NULL as registrado_por, COALESCE(autor_id, 0) as autor_id
            FROM reportes WHERE estudiante_id=? ORDER BY fecha DESC
        """, (est_id,)).fetchall()
        logros = []
        try:
            logros = conn.execute("""
                SELECT id,'logro' as fuente,tipo,NULL as subtipo,titulo,descripcion,
                       NULL as severidad,NULL as reportado_por,fecha,'Activo' as estado,
                       NULL as seguimiento,NULL as fecha_cierre,registrado_por
                FROM logros WHERE estudiante_id=? ORDER BY fecha DESC
            """, (est_id,)).fetchall()
        except Exception as _e:
            logger.warning(f"[perfil] Excepción silenciada")
        try:
            indicadores = conn.execute(
                "SELECT ind_conducta,ind_psico,ind_academico,ind_logros FROM estudiantes WHERE id=?",
                (est_id,)).fetchone()
        except Exception:
            indicadores = None
    reportes_list = [dict(r) for r in reportes]
    logros_list   = [dict(r) for r in logros]

    # Profesores solo ven reportes que ellos crearon
    prof = _get_profesor()
    if prof and _normalizar_rol(prof.get("rol", "")) == "profesor":
        reportes_list = [r for r in reportes_list if r.get("autor_id") == prof["id"]]

    eventos = reportes_list + logros_list
    eventos.sort(key=lambda x: x.get('fecha','') or '', reverse=True)
    return jsonify({"eventos": eventos, "indicadores": dict(indicadores) if indicadores else {}})


@perfil_bp.route("/api/logros/<int:est_id>", methods=["GET"])
@login_required
def get_logros(est_id):
    try:
        with sqlite3.connect(DATABASE, timeout=10) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM logros WHERE estudiante_id=? ORDER BY fecha DESC", (est_id,)).fetchall()
        return jsonify([dict(r) for r in rows])
    except Exception:
        return jsonify([])


@perfil_bp.route("/api/logros", methods=["POST"])
@login_required
def crear_logro():
    d = request.get_json(silent=True) or {}
    est_id = d.get("estudiante_id")
    tipo   = d.get("tipo","reconocimiento")
    titulo = d.get("titulo","").strip()
    descripcion  = d.get("descripcion","").strip()
    fecha        = d.get("fecha","")
    registrado_por = d.get("registrado_por", session.get("nombre",""))
    if not est_id or not titulo:
        return jsonify({"error":"estudiante_id y titulo son requeridos"}), 400
    try:
        with sqlite3.connect(DATABASE, timeout=10) as conn:
            conn.execute("INSERT INTO logros(estudiante_id,tipo,titulo,descripcion,fecha,registrado_por) VALUES(?,?,?,?,?,?)",
                         (est_id, tipo, titulo, descripcion, fecha, registrado_por))
            conn.commit()
            _recalcular_indicadores(conn, est_id)
            conn.commit()
        cache_bust()
        return jsonify({"ok":True})
    except Exception as ex:
        logger.error(f"[PERFIL] Error registrando logro: {ex}")
        return jsonify({"error": "Error al registrar el logro. Intenta de nuevo."}), 500


@perfil_bp.route("/api/logros/<int:logro_id>", methods=["DELETE"])
@login_required
def eliminar_logro(logro_id):
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        logro = conn.execute("SELECT estudiante_id FROM logros WHERE id=?", (logro_id,)).fetchone()
        if logro:
            conn.execute("DELETE FROM logros WHERE id=?", (logro_id,))
            conn.commit()
            _recalcular_indicadores(conn, logro['estudiante_id'])
            conn.commit()
    cache_bust()
    return jsonify({"ok":True})


# ── CUADERNO ANECDÓTICO ──────────────────────────────────────────────────────

@perfil_bp.route("/api/cuaderno/<int:est_id>", methods=["GET"])
@login_required
def get_cuaderno(est_id):
    u = get_usuario()
    rol_n = _normalizar_rol(u.get("rol", ""))
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        est = conn.execute("SELECT ciclo FROM estudiantes WHERE id=?", (est_id,)).fetchone()
        if not est:
            return jsonify({"error": "Estudiante no encontrado"}), 404
        ciclo_est = est["ciclo"] or "segundo_ciclo"
        ciclo_acc = u.get("ciclo_acceso")
        if ciclo_acc and ciclo_acc != ciclo_est and not u.get("es_directora"):
            return jsonify({"error": "Sin acceso a este estudiante"}), 403

        puede_ver_privadas = (
            u.get("es_directora") or
            u.get("es_coord") or
            u.get("es_psicologa") or
            rol_n in ROLES_COORD or
            rol_n in ROLES_PSICOLOGA
        )

        if puede_ver_privadas:
            rows = conn.execute("""
                SELECT ca.*, u.nombre as autor_nombre, u.rol as autor_rol
                FROM cuaderno_anecdotico ca
                JOIN usuarios u ON ca.autor_id = u.id
                WHERE ca.estudiante_id = ?
                ORDER BY ca.fecha DESC, ca.creado_en DESC
            """, (est_id,)).fetchall()
        elif rol_n == "profesor":
            rows = conn.execute("""
                SELECT ca.*, u.nombre as autor_nombre, u.rol as autor_rol
                FROM cuaderno_anecdotico ca
                JOIN usuarios u ON ca.autor_id = u.id
                WHERE ca.estudiante_id = ?
                  AND (ca.autor_id = ? OR ca.privado = 0)
                ORDER BY ca.fecha DESC, ca.creado_en DESC
            """, (est_id, u["id"])).fetchall()
        else:
            rows = conn.execute("""
                SELECT ca.*, u.nombre as autor_nombre, u.rol as autor_rol
                FROM cuaderno_anecdotico ca
                JOIN usuarios u ON ca.autor_id = u.id
                WHERE ca.estudiante_id = ?
                  AND ca.privado = 0
                  AND ca.visible_en_perfil = 1
                ORDER BY ca.fecha DESC, ca.creado_en DESC
            """, (est_id,)).fetchall()

    return jsonify([dict(r) for r in rows])


@perfil_bp.route("/api/cuaderno", methods=["POST"])
@login_required
def crear_entrada_cuaderno():
    u = get_usuario()
    data = request.get_json() or {}
    est_id      = data.get("estudiante_id")
    tipo        = data.get("tipo", "conductual")
    descripcion = (data.get("descripcion") or "").strip()
    seguimiento = (data.get("seguimiento") or "").strip()
    fecha       = data.get("fecha") or date.today().isoformat()
    privado     = 1 if data.get("privado") else 0

    if not est_id or not descripcion:
        return jsonify({"error": "Faltan campos obligatorios"}), 400

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        est = conn.execute("SELECT ciclo FROM estudiantes WHERE id=?", (est_id,)).fetchone()
        if not est:
            return jsonify({"error": "Estudiante no encontrado"}), 404

        conn.execute("""
            INSERT INTO cuaderno_anecdotico
                (estudiante_id, autor_id, fecha, tipo, descripcion,
                 seguimiento, privado, visible_en_perfil)
            VALUES (?,?,?,?,?,?,?,1)
        """, (est_id, u["id"], fecha, tipo, descripcion, seguimiento, privado))
        conn.commit()
    cache_bust()
    return jsonify({"ok": True, "mensaje": "Entrada registrada en el cuaderno anecdótico"})


@perfil_bp.route("/api/cuaderno/<int:entrada_id>", methods=["PATCH"])
@login_required
def editar_entrada_cuaderno(entrada_id):
    u = get_usuario()
    data = request.get_json() or {}
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        entrada = conn.execute(
            "SELECT * FROM cuaderno_anecdotico WHERE id=?", (entrada_id,)
        ).fetchone()
        if not entrada:
            return jsonify({"error": "Entrada no encontrada"}), 404
        rol_n = _normalizar_rol(u.get("rol",""))
        if entrada["autor_id"] != u["id"] and rol_n not in {"directora","coordinador_general","coordinador_primer_ciclo","coordinador_segundo_ciclo"}:
            return jsonify({"error": "Solo el autor puede editar esta entrada"}), 403

        conn.execute("""
            UPDATE cuaderno_anecdotico
               SET descripcion=?, seguimiento=?, tipo=?, privado=?
             WHERE id=?
        """, (
            data.get("descripcion", entrada["descripcion"]),
            data.get("seguimiento", entrada["seguimiento"]),
            data.get("tipo", entrada["tipo"]),
            1 if data.get("privado") else 0,
            entrada_id
        ))
        conn.commit()
    return jsonify({"ok": True})


@perfil_bp.route("/api/cuaderno/<int:entrada_id>/convertir-reporte", methods=["POST"])
@login_required
def convertir_reporte_cuaderno(entrada_id):
    """Convierte una entrada del cuaderno en reporte formal."""
    u = get_usuario()
    rol_n = _normalizar_rol(u.get("rol", ""))

    puede_escalar = (
        u.get("es_directora") or
        u.get("es_coord") or
        u.get("es_psicologa") or
        rol_n in ROLES_COORD or
        rol_n in ROLES_PSICOLOGA
    )
    if not puede_escalar:
        return jsonify({"error": "Solo psicología o coordinación pueden escalar una entrada a reporte formal"}), 403

    d = request.get_json(silent=True) or {}
    severidad = d.get("severidad", "Media")
    notas_adicionales = (d.get("notas", "") or "").strip()

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        entrada = conn.execute(
            "SELECT * FROM cuaderno_anecdotico WHERE id=?", (entrada_id,)
        ).fetchone()
        if not entrada:
            return jsonify({"error": "Entrada no encontrada"}), 404
        if entrada["convertido_reporte"]:
            return jsonify({"error": "Esta entrada ya fue convertida a reporte", "ya_existe": True}), 409

        TIPO_MAP = {
            "conductual": "conducta",
            "emocional":  "psicologico",
            "académico":  "academico",
            "familiar":   "psicologico",
            "otro":       "conducta",
        }
        tipo_reporte = TIPO_MAP.get(entrada["tipo"], "conducta")

        descripcion_reporte = entrada["descripcion"]
        if notas_adicionales:
            descripcion_reporte += f"\n\n[Nota al escalar — {u['nombre']}]: {notas_adicionales}"
        if entrada["seguimiento"]:
            descripcion_reporte += f"\n\n[Seguimiento original]: {entrada['seguimiento']}"

        conn.execute("""
            INSERT INTO reportes
                (estudiante_id, tipo, titulo, descripcion,
                 severidad, reportado_por, estado, fecha)
            VALUES (?,?,?,?,?,?,?,?)
        """, (
            entrada["estudiante_id"],
            tipo_reporte,
            f"Escalado desde cuaderno — {entrada['tipo'].capitalize()}",
            descripcion_reporte,
            severidad,
            u["nombre"],
            "Abierto",
            entrada["fecha"]
        ))
        reporte_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        conn.execute("""
            UPDATE cuaderno_anecdotico
               SET convertido_reporte=1, visible_en_perfil=1
             WHERE id=?
        """, (entrada_id,))
        conn.commit()

        _recalcular_indicadores(conn, entrada["estudiante_id"])
        conn.commit()

    cache_bust()
    return jsonify({
        "ok": True,
        "reporte_id": reporte_id,
        "mensaje": f"Entrada escalada a reporte formal (ID #{reporte_id}). Los indicadores del estudiante han sido actualizados."
    })


@perfil_bp.route("/api/cuaderno/<int:entrada_id>", methods=["DELETE"])
@login_required
def eliminar_entrada_cuaderno(entrada_id):
    u = get_usuario()
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        entrada = conn.execute(
            "SELECT autor_id FROM cuaderno_anecdotico WHERE id=?", (entrada_id,)
        ).fetchone()
        if not entrada:
            return jsonify({"error": "No encontrada"}), 404
        rol_n = _normalizar_rol(u.get("rol",""))
        if entrada["autor_id"] != u["id"] and rol_n not in {"directora","coordinador_general"}:
            return jsonify({"error": "Sin permisos"}), 403
        conn.execute("DELETE FROM cuaderno_anecdotico WHERE id=?", (entrada_id,))
        conn.commit()
    return jsonify({"ok": True})


# ── MOTOR CONDUCTUAL ─────────────────────────────────────────────────────────

@perfil_bp.route("/api/conductual/<int:est_id>", methods=["GET"])
@login_required
def get_motor_conductual(est_id):
    """
    Retorna el semáforo conductual del estudiante.
    Accesible por coordinador, directora, profesor (solo sus alumnos), psicóloga.
    """
    u = get_usuario()
    rol = _normalizar_rol(u.get("rol", ""))

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        est = conn.execute(
            "SELECT id, nombre, apellido, grado FROM estudiantes WHERE id=?", (est_id,)
        ).fetchone()
        if not est:
            return jsonify({"error": "Estudiante no encontrado"}), 404

        if rol == "profesor":
            acceso = conn.execute(
                "SELECT 1 FROM calificaciones_periodo WHERE profesor_id=? AND estudiante_id=? LIMIT 1",
                (u["id"], est_id)
            ).fetchone()
            if not acceso:
                return jsonify({"error": "Sin acceso"}), 403

        resultado = calcular_motor_conductual(conn, est_id)
        resultado["color"] = _semaforo_color(resultado["semaforo"])
        resultado["nombre"] = f"{est['nombre']} {est['apellido']}"
        resultado["grado"] = est["grado"]
        return jsonify(resultado)


# ── PROGRESO DEL ESTUDIANTE ──────────────────────────────────────────────────

@perfil_bp.route("/api/progreso/<int:est_id>", methods=["GET"])
@login_required
def get_progreso_estudiante(est_id):
    """
    Retorna un resumen de progreso de un estudiante:
    notas por período, tendencia, asistencia mensual, cuaderno anecdótico (resumen).
    """
    u = get_usuario()
    anio_esc = request.args.get("anio_escolar", "2025-2026")
    rol = _normalizar_rol(u.get("rol", ""))

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row

        est = conn.execute(
            "SELECT * FROM estudiantes WHERE id=?", (est_id,)
        ).fetchone()
        if not est:
            return jsonify({"error": "Estudiante no encontrado"}), 404

        # RLS: profesor solo puede ver progreso de sus propios estudiantes
        if rol == "profesor":
            acceso = conn.execute(
                "SELECT 1 FROM calificaciones_periodo WHERE profesor_id=? AND estudiante_id=? LIMIT 1",
                (u["id"], est_id)
            ).fetchone()
            if not acceso:
                return jsonify({"error": "Sin acceso a este estudiante"}), 403

        materias = conn.execute("""
            SELECT materia, tipo, p1, p2, p3, p4, promedio, profesor
            FROM materias_calificaciones
            WHERE estudiante_id=?
            ORDER BY tipo, materia
        """, (est_id,)).fetchall()

        asistencia = conn.execute("""
            SELECT am.mes, am.anio, am.materia, am.porcentaje,
                   am.dias_asistio, am.dias_clase_impartidos, am.validado,
                   u.nombre as profesor_nombre
            FROM asistencia_mensual am
            JOIN usuarios u ON am.profesor_id = u.id
            WHERE am.estudiante_id=?
            ORDER BY am.anio DESC, am.mes DESC
        """, (est_id,)).fetchall()

        cuaderno_cnt = conn.execute(
            "SELECT COUNT(*) FROM cuaderno_anecdotico WHERE estudiante_id=?",
            (est_id,)
        ).fetchone()[0]
        cuaderno_reciente = conn.execute("""
            SELECT ca.fecha, ca.tipo, ca.descripcion, u.nombre as autor
            FROM cuaderno_anecdotico ca
            JOIN usuarios u ON ca.autor_id = u.id
            WHERE ca.estudiante_id=? AND ca.visible_en_perfil=1
            ORDER BY ca.fecha DESC LIMIT 3
        """, (est_id,)).fetchall()

        narrativas = conn.execute("""
            SELECT en.periodo, en.texto, u.nombre as profesor_nombre
            FROM evaluaciones_narrativas en
            JOIN usuarios u ON en.profesor_id = u.id
            WHERE en.estudiante_id=? AND en.anio_escolar=?
            ORDER BY en.periodo
        """, (est_id, anio_esc)).fetchall()

    from core import rls as _rls
    materias_filtradas = _rls.filtrar_materias_profesor([dict(m) for m in materias])

    return jsonify({
        "estudiante":  dict(est),
        "materias":    materias_filtradas,
        "asistencia":  [dict(a) for a in asistencia],
        "cuaderno": {
            "total_entradas": cuaderno_cnt,
            "recientes": [dict(c) for c in cuaderno_reciente]
        },
        "evaluaciones_narrativas": [dict(n) for n in narrativas]
    })
