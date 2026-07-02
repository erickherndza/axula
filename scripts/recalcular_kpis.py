#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
recalcular_kpis.py
==================
Corrige 3 bugs de datos en la BD:

  Fix 1 — p_acad = 0 en listado aunque hay notas en materias_calificaciones
           Recalcula p_acad, acad_p1-p4 y columnas de módulos para todos los
           estudiantes afectados.

  Fix 2 — promedio = 0 en materias_calificaciones aunque p1/p2 tienen valores
           Recalcula el promedio desde los períodos disponibles.

  Fix 3 — prom_modulos = 0 para estudiantes de Música/Teatro/Artes Visuales
           aunque p_instrumento/p_canto/etc. ya están cargados.

Uso:
    python3 scripts/recalcular_kpis.py            # dry-run (solo muestra)
    python3 scripts/recalcular_kpis.py --commit   # aplica cambios en BD
"""

import sqlite3
import sys
import os

# Detecta si corre en Render (igual que constants.py)
_en_render = os.path.exists('/data')
DB_PATH = os.environ.get(
    "DATABASE_PATH",
    "/data/database.db" if _en_render else os.path.join(os.path.dirname(__file__), '..', 'database.db')
)

# ── Mapa de módulos artísticos (igual que en perfil.py) ─────────────────────
MODULO_MAP = {
    'fotografía': 'fotografia', 'fotografia': 'fotografia', 'foto': 'fotografia',
    'fotografía digital': 'fotografia', 'fotografia digital': 'fotografia',
    'introducción fotografía': 'fotografia', 'introduccion fotografia': 'fotografia',
    'introducción fotografía digital': 'fotografia',
    'introduccion fotografia digital': 'fotografia',
    'introducción a la fotografía': 'fotografia',
    'introduccion a la fotografia': 'fotografia',
    'introducción a la fotografía digital': 'fotografia',
    'introduccion a la fotografia digital': 'fotografia',
    'fotografía artística': 'fotografia', 'fotografia artistica': 'fotografia',
    'lenguaje visual': 'lv',
    'lenguaje visual, dibujo y creación de personajes': 'lv',
    'lenguaje visual dibujo y creacion de personajes': 'lv',
    'lenguaje visual, dibujo y creacion de personajes': 'lv',
    'lenguaje visual y principios de diseño': 'lv',
    'lenguaje visual y principios de diseno': 'lv',
    'lenguaje visual y principios del diseño': 'lv',
    'lenguaje visual y principios del diseno': 'lv',
    'lenguaje visual y principios del diseño artesanal': 'lv',
    'lenguaje visual y principios del diseno artesanal': 'lv',
    'lenguaje visual artesanal': 'lv',
    'lenguaje plástico y visual': 'lv', 'lenguaje plastico y visual': 'lv', 'lv': 'lv',
    'diseño básico y expresión visual': 'diseno',
    'diseño basico y expresion visual': 'diseno',
    'diseño básico y expresion visual': 'diseno',
    'diseno basico y expresion visual': 'diseno',
    'diseño básico': 'diseno', 'diseño basico': 'diseno',
    'diseño': 'diseno', 'diseno': 'diseno',
    'dibujo técnico': 'diseno', 'dibujo tecnico': 'diseno',
    'dibujo técnico y artístico': 'diseno', 'dibujo tecnico y artistico': 'diseno',
    'principios de dibujo, pintura y creatividad': 'diseno',
    'principios de dibujo pintura y creatividad': 'diseno',
    'pintura y técnicas mixtas': 'diseno', 'pintura y tecnicas mixtas': 'diseno',
    'pintura': 'diseno', 'lenguaje plástico': 'diseno', 'lenguaje plastico': 'diseno',
    # Música
    'instrumento i': 'instrumento', 'instrumento ii': 'instrumento',
    'instrumento iii': 'instrumento', 'instrumento': 'instrumento',
    'instrumento principal': 'instrumento',
    'práctica instrumental': 'instrumento', 'practica instrumental': 'instrumento',
    'práctica instrumental grupal i': 'instrumento',
    'practica instrumental grupal i': 'instrumento',
    'práctica instrumental grupal ii': 'instrumento',
    'practica instrumental grupal ii': 'instrumento',
    'práctica instrumental grupal iii': 'instrumento',
    'practica instrumental grupal iii': 'instrumento',
    'canto coral i': 'canto', 'canto coral ii': 'canto', 'canto coral iii': 'canto',
    'canto coral': 'canto', 'canto': 'canto', 'coral': 'canto',
    'lenguaje musical': 'lenguaje_musical',
    'lenguaje musical, teoría y entrenamiento': 'lenguaje_musical',
    'lenguaje musical, teoria y entrenamiento': 'lenguaje_musical',
    'lenguaje musical teoría y entrenamiento': 'lenguaje_musical',
    'lenguaje musical teoria y entrenamiento': 'lenguaje_musical',
    'teoría musical': 'lenguaje_musical', 'teoria musical': 'lenguaje_musical',
    'solfeo': 'lenguaje_musical',
    'introducción a la historia del arte universal y dominicano': 'lenguaje_musical',
    'introduccion a la historia del arte universal y dominicano': 'lenguaje_musical',
    # Teatro
    'entrenamiento rítmico, corporal y vocal i': 'entrenamiento',
    'entrenamiento ritmico, corporal y vocal i': 'entrenamiento',
    'entrenamiento rítmico corporal y vocal i': 'entrenamiento',
    'entrenamiento ritmico corporal y vocal i': 'entrenamiento',
    'entrenamiento rítmico, corporal y vocal ii': 'entrenamiento',
    'entrenamiento ritmico, corporal y vocal ii': 'entrenamiento',
    'entrenamiento rítmico, corporal y vocal iii': 'entrenamiento',
    'entrenamiento ritmico, corporal y vocal iii': 'entrenamiento',
    'entrenamiento vocal': 'entrenamiento',
    'técnica vocal': 'entrenamiento', 'tecnica vocal': 'entrenamiento',
    'lenguaje danzario y teatral': 'expresion',
    'lenguaje danzario teatral': 'expresion',
    'lenguaje danzario': 'expresion',
    'expresión corporal': 'expresion', 'expresion corporal': 'expresion',
    'actuación teatral': 'expresion', 'actuacion teatral': 'expresion',
    'historia del arte y apreciación del teatro universal': 'historia_teatro',
    'historia del arte y apreciacion del teatro universal': 'historia_teatro',
    'historia del arte y apreciación del teatro': 'historia_teatro',
    'historia del teatro': 'historia_teatro',
    'historia y apreciación teatral': 'historia_teatro',
    'historia y apreciacion teatral': 'historia_teatro',
    'apreciación teatral': 'historia_teatro', 'apreciacion teatral': 'historia_teatro',
    # Artes Visuales
    'dibujo técnico': 'dibujo', 'dibujo tecnico': 'dibujo',
    'dibujo técnico y artístico': 'dibujo', 'dibujo tecnico y artistico': 'dibujo',
    'principios de dibujo, pintura y creatividad': 'dibujo',
    'principios de dibujo pintura y creatividad': 'dibujo',
    'principios de dibujo': 'dibujo', 'dibujo': 'dibujo',
    'pintura y técnicas mixtas': 'pintura', 'pintura y tecnicas mixtas': 'pintura',
    'pintura': 'pintura', 'técnicas mixtas': 'pintura', 'tecnicas mixtas': 'pintura',
    'cerámica': 'pintura', 'ceramica': 'pintura',
    'historia del arte universal y teoría de las artes visuales.': 'historia_arte',
    'historia del arte universal y teoria de las artes visuales.': 'historia_arte',
    'historia del arte universal y teoría de las artes visuales': 'historia_arte',
    'historia del arte universal y teoria de las artes visuales': 'historia_arte',
    'historia del arte universal y la estética digital': 'historia_arte',
    'historia del arte universal y la estetica digital': 'historia_arte',
    'historia del arte': 'historia_arte',
    'historia del arte universal': 'historia_arte',
    'apreciación artística': 'historia_arte', 'apreciacion artistica': 'historia_arte',
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

ASISTENCIA_KEYS = {'asistencia', 'asistencias', 'asist.', 'attendence'}


def calcular_kpis(mats):
    """
    Dado un listado de filas de materias_calificaciones para un estudiante,
    devuelve un dict con los KPIs calculados (igual lógica que perfil.py).
    """
    modulos = {}   # col -> [p1,p2,p3,p4, promedio]
    promedios_acad = []
    acad_periodos = {1: None, 2: None, 3: None, 4: None}

    for mat in mats:
        mn = mat['materia'].lower().strip()

        # Asistencia → skip
        if any(a in mn for a in ASISTENCIA_KEYS):
            continue

        # Intentar mapear a módulo artístico
        col = MODULO_MAP.get(mn)
        if not col:
            for k, v in MODULO_MAP.items():
                if k in mn or mn in k:
                    col = v
                    break

        if col:
            if col not in modulos:
                modulos[col] = {'p1': None, 'p2': None, 'p3': None, 'p4': None, 'prom': None}
            for pi in [1, 2, 3, 4]:
                if modulos[col].get(f'p{pi}') is None and mat[f'p{pi}']:
                    modulos[col][f'p{pi}'] = mat[f'p{pi}']
            if modulos[col]['prom'] is None and mat['promedio']:
                modulos[col]['prom'] = mat['promedio']
            continue

        # Determinar si es académica
        es_acad = any(a in mn or mn in a for a in MATS_ACAD_STD)

        if es_acad:
            if mat['promedio'] and mat['promedio'] > 0:
                promedios_acad.append(mat['promedio'])
            for pi in [1, 2, 3, 4]:
                if acad_periodos[pi] is None and mat[f'p{pi}']:
                    acad_periodos[pi] = mat[f'p{pi}']
        else:
            # materias_extras — también contribuyen a promedio académico
            if mat['promedio'] and mat['promedio'] > 0:
                promedios_acad.append(mat['promedio'])
            for pi in [1, 2, 3, 4]:
                if acad_periodos[pi] is None and mat[f'p{pi}']:
                    acad_periodos[pi] = mat[f'p{pi}']

    # Calcular promedios de módulos multimedia (foto/lv/diseno)
    def prom_mod(col):
        if col not in modulos:
            return None
        ps = [modulos[col][f'p{i}'] for i in [1,2,3,4] if modulos[col].get(f'p{i}')]
        if ps:
            return round(sum(ps) / len(ps), 1)
        return modulos[col].get('prom')

    p_foto   = prom_mod('fotografia')
    p_lv     = prom_mod('lv')
    p_diseno = prom_mod('diseno')

    # Módulos de otras menciones
    p_instrumento     = prom_mod('instrumento')
    p_canto           = prom_mod('canto')
    p_lenguaje_musical= prom_mod('lenguaje_musical')
    p_entrenamiento   = prom_mod('entrenamiento')
    p_expresion       = prom_mod('expresion')
    p_historia_teatro = prom_mod('historia_teatro')
    p_dibujo          = prom_mod('dibujo')
    p_pintura         = prom_mod('pintura')
    p_historia_arte   = prom_mod('historia_arte')

    # prom_modulos = promedio de los módulos artísticos presentes
    mods_vals = [v for v in [p_foto, p_lv, p_diseno,
                              p_instrumento, p_canto, p_lenguaje_musical,
                              p_entrenamiento, p_expresion, p_historia_teatro,
                              p_dibujo, p_pintura, p_historia_arte] if v]
    prom_modulos = round(sum(mods_vals) / len(mods_vals), 1) if mods_vals else None

    # p_acad desde promedios académicos; si no hay, desde módulos
    p_acad = None
    if promedios_acad:
        p_acad = round(sum(promedios_acad) / len(promedios_acad), 1)
    elif prom_modulos:
        p_acad = prom_modulos

    return {
        'p_acad':    p_acad,
        'acad_p1':   acad_periodos[1],
        'acad_p2':   acad_periodos[2],
        'acad_p3':   acad_periodos[3],
        'acad_p4':   acad_periodos[4],
        'p_foto':    p_foto,
        'p_lv':      p_lv,
        'p_diseno':  p_diseno,
        'prom_modulos': prom_modulos,
    }


def main():
    commit = '--commit' in sys.argv
    print(f"Modo: {'APLICAR CAMBIOS' if commit else 'DRY-RUN (sin cambios)'}")
    print()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Estudiantes con materias pero p_acad = 0
    ids_problema = [
        r[0] for r in conn.execute('''
            SELECT DISTINCT mc.estudiante_id
            FROM materias_calificaciones mc
            JOIN estudiantes e ON e.id = mc.estudiante_id
            WHERE (e.p_acad IS NULL OR e.p_acad = 0)
        ''').fetchall()
    ]

    print(f"Estudiantes con notas en materias_calificaciones pero p_acad=0: {len(ids_problema)}")
    print()

    actualizados = 0
    sin_cambio   = 0
    errores      = []

    for est_id in ids_problema:
        mats = conn.execute('''
            SELECT materia, p1, p2, p3, p4, promedio
            FROM materias_calificaciones
            WHERE estudiante_id = ?
        ''', (est_id,)).fetchall()

        mats_list = [dict(m) for m in mats]
        kpis = calcular_kpis(mats_list)

        if not kpis.get('p_acad'):
            # Verificar si solo tiene módulos (sin academicas clásicas)
            sin_cambio += 1
            continue

        # Mostrar resumen
        est = conn.execute(
            'SELECT nombre, apellido, grado FROM estudiantes WHERE id=?', (est_id,)
        ).fetchone()
        nombre = f"{est['nombre']} {est['apellido']}" if est else f"ID {est_id}"
        grado  = est['grado'] if est else '?'

        if not commit:
            print(f"  [{est_id}] {nombre} ({grado}): p_acad={kpis['p_acad']} "
                  f"P1={kpis['acad_p1']} P2={kpis['acad_p2']} "
                  f"P3={kpis['acad_p3']} P4={kpis['acad_p4']}")

        if commit:
            try:
                conn.execute('''
                    UPDATE estudiantes SET
                        p_acad     = CASE WHEN (p_acad IS NULL OR p_acad=0)      THEN ? ELSE p_acad END,
                        acad_p1    = CASE WHEN (acad_p1 IS NULL OR acad_p1=0)    THEN ? ELSE acad_p1 END,
                        acad_p2    = CASE WHEN (acad_p2 IS NULL OR acad_p2=0)    THEN ? ELSE acad_p2 END,
                        acad_p3    = CASE WHEN (acad_p3 IS NULL OR acad_p3=0)    THEN ? ELSE acad_p3 END,
                        acad_p4    = CASE WHEN (acad_p4 IS NULL OR acad_p4=0)    THEN ? ELSE acad_p4 END,
                        p_foto     = CASE WHEN (p_foto IS NULL OR p_foto=0)      THEN ? ELSE p_foto END,
                        p_lv       = CASE WHEN (p_lv IS NULL OR p_lv=0)         THEN ? ELSE p_lv END,
                        p_diseno   = CASE WHEN (p_diseno IS NULL OR p_diseno=0)  THEN ? ELSE p_diseno END,
                        prom_modulos = CASE WHEN (prom_modulos IS NULL OR prom_modulos=0)
                                       THEN ? ELSE prom_modulos END,
                        tiene_notas = 1
                    WHERE id = ?
                ''', (
                    kpis['p_acad'],
                    kpis['acad_p1'], kpis['acad_p2'],
                    kpis['acad_p3'], kpis['acad_p4'],
                    kpis['p_foto'],  kpis['p_lv'],
                    kpis['p_diseno'], kpis['prom_modulos'],
                    est_id
                ))
                actualizados += 1
            except Exception as ex:
                errores.append((est_id, str(ex)))
        else:
            actualizados += 1

    if commit:
        conn.commit()

    print()
    print("=" * 60)
    if commit:
        print(f"  [Fix 1] Actualizados: {actualizados}")
        print(f"  [Fix 1] Sin datos suficientes (skip): {sin_cambio}")
        if errores:
            print(f"  [Fix 1] Errores: {len(errores)}")
            for eid, err in errores[:10]:
                print(f"    ID {eid}: {err}")
    else:
        print(f"  [Fix 1] Previsualización: {actualizados} estudiantes serían actualizados")
        print(f"  [Fix 1] Sin datos suficientes (skip): {sin_cambio}")
        print(f"  Ejecuta con --commit para aplicar los cambios")
        conn.close()
        return

    # ── FIX 2: promedio=0 en materias_calificaciones ─────────────────────────
    print()
    print("Fix 2 — promedio=0 en materias_calificaciones con períodos válidos...")
    conn.execute('''
        UPDATE materias_calificaciones
        SET promedio = ROUND(
            (
                COALESCE(CASE WHEN p1 > 0 THEN p1 END, 0) +
                COALESCE(CASE WHEN p2 > 0 THEN p2 END, 0) +
                COALESCE(CASE WHEN p3 > 0 THEN p3 END, 0) +
                COALESCE(CASE WHEN p4 > 0 THEN p4 END, 0)
            ) / (
                (CASE WHEN p1 > 0 THEN 1 ELSE 0 END) +
                (CASE WHEN p2 > 0 THEN 1 ELSE 0 END) +
                (CASE WHEN p3 > 0 THEN 1 ELSE 0 END) +
                (CASE WHEN p4 > 0 THEN 1 ELSE 0 END)
            ), 1)
        WHERE p1 > 0 AND (promedio IS NULL OR promedio = 0)
        AND (
            (CASE WHEN p1 > 0 THEN 1 ELSE 0 END) +
            (CASE WHEN p2 > 0 THEN 1 ELSE 0 END) +
            (CASE WHEN p3 > 0 THEN 1 ELSE 0 END) +
            (CASE WHEN p4 > 0 THEN 1 ELSE 0 END)
        ) > 0
    ''')
    r2 = conn.execute('SELECT changes()').fetchone()[0]
    conn.commit()
    print(f"  {r2} filas corregidas en materias_calificaciones")

    # ── FIX 3: prom_modulos=0 para menciones artísticas ─────────────────────
    print()
    print("Fix 3 — prom_modulos=0 para Música/Teatro/Artes Visuales/Multimedia...")

    # Música — SQLite no normaliza acentos, hay que buscar con y sin acento
    conn.execute('''
        UPDATE estudiantes
        SET prom_modulos = ROUND(
            (COALESCE(CASE WHEN p_instrumento > 0 THEN p_instrumento END, 0) +
             COALESCE(CASE WHEN p_canto > 0 THEN p_canto END, 0) +
             COALESCE(CASE WHEN p_lenguaje_musical > 0 THEN p_lenguaje_musical END, 0)) /
            NULLIF(
                (CASE WHEN p_instrumento > 0 THEN 1 ELSE 0 END) +
                (CASE WHEN p_canto > 0 THEN 1 ELSE 0 END) +
                (CASE WHEN p_lenguaje_musical > 0 THEN 1 ELSE 0 END), 0),
        1)
        WHERE (mencion LIKE '%USIC%' OR mencion LIKE '%ÚSIC%')
        AND (p_instrumento > 0 OR p_canto > 0 OR p_lenguaje_musical > 0)
        AND (prom_modulos IS NULL OR prom_modulos = 0)
    ''')
    r3a = conn.execute('SELECT changes()').fetchone()[0]

    # Teatro
    conn.execute('''
        UPDATE estudiantes
        SET prom_modulos = ROUND(
            (COALESCE(CASE WHEN p_entrenamiento > 0 THEN p_entrenamiento END, 0) +
             COALESCE(CASE WHEN p_expresion > 0 THEN p_expresion END, 0) +
             COALESCE(CASE WHEN p_historia_teatro > 0 THEN p_historia_teatro END, 0)) /
            NULLIF(
                (CASE WHEN p_entrenamiento > 0 THEN 1 ELSE 0 END) +
                (CASE WHEN p_expresion > 0 THEN 1 ELSE 0 END) +
                (CASE WHEN p_historia_teatro > 0 THEN 1 ELSE 0 END), 0),
        1)
        WHERE mencion LIKE '%ATRO%'
        AND (p_entrenamiento > 0 OR p_expresion > 0 OR p_historia_teatro > 0)
        AND (prom_modulos IS NULL OR prom_modulos = 0)
    ''')
    r3b = conn.execute('SELECT changes()').fetchone()[0]

    # Artes Visuales
    conn.execute('''
        UPDATE estudiantes
        SET prom_modulos = ROUND(
            (COALESCE(CASE WHEN p_dibujo > 0 THEN p_dibujo END, 0) +
             COALESCE(CASE WHEN p_pintura > 0 THEN p_pintura END, 0) +
             COALESCE(CASE WHEN p_historia_arte > 0 THEN p_historia_arte END, 0)) /
            NULLIF(
                (CASE WHEN p_dibujo > 0 THEN 1 ELSE 0 END) +
                (CASE WHEN p_pintura > 0 THEN 1 ELSE 0 END) +
                (CASE WHEN p_historia_arte > 0 THEN 1 ELSE 0 END), 0),
        1)
        WHERE mencion LIKE '%ISUAL%'
        AND (p_dibujo > 0 OR p_pintura > 0 OR p_historia_arte > 0)
        AND (prom_modulos IS NULL OR prom_modulos = 0)
    ''')
    r3c = conn.execute('SELECT changes()').fetchone()[0]

    # Multimedia
    conn.execute('''
        UPDATE estudiantes
        SET prom_modulos = ROUND(
            (COALESCE(CASE WHEN p_foto > 0 THEN p_foto END, 0) +
             COALESCE(CASE WHEN p_lv > 0 THEN p_lv END, 0) +
             COALESCE(CASE WHEN p_diseno > 0 THEN p_diseno END, 0)) /
            NULLIF(
                (CASE WHEN p_foto > 0 THEN 1 ELSE 0 END) +
                (CASE WHEN p_lv > 0 THEN 1 ELSE 0 END) +
                (CASE WHEN p_diseno > 0 THEN 1 ELSE 0 END), 0),
        1)
        WHERE (mencion LIKE '%EDIA%' OR mencion IS NULL OR mencion = '')
        AND (p_foto > 0 OR p_lv > 0 OR p_diseno > 0)
        AND (prom_modulos IS NULL OR prom_modulos = 0)
    ''')
    r3d = conn.execute('SELECT changes()').fetchone()[0]

    conn.commit()
    print(f"  Música: {r3a}  Teatro: {r3b}  Artes Visuales: {r3c}  Multimedia: {r3d}")

    conn.close()
    print()
    print("Todos los fixes aplicados. Reinicia la app para limpiar el caché en memoria.")


if __name__ == '__main__':
    main()
