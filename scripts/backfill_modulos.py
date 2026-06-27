# -*- coding: utf-8 -*-
"""
backfill_modulos.py — Backfill de módulos técnicos desde materias_calificaciones.

Lee materias_calificaciones y rellena las columnas por período y promedio
en la tabla estudiantes para las menciones Música, Teatro y Artes Visuales.

Uso:
    cd /Users/erickhernandez/elearning
    python3 scripts/backfill_modulos.py
"""

import sqlite3
import sys
import os

# Ruta a la BD desde el directorio del proyecto
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'database.db')
DB_PATH = os.path.abspath(DB_PATH)

# ── Mapeo: término clave → (col_p1, col_p2, col_p3, col_p4, col_promedio)
# La clave es un fragmento que debe estar CONTENIDO en el nombre de la materia (lower)
MATERIA_A_COLUMNA = {
    # ── MÚSICA
    'práctica instrumental grupal':  ('instrumento_p1','instrumento_p2','instrumento_p3','instrumento_p4','p_instrumento'),
    'practica instrumental grupal':  ('instrumento_p1','instrumento_p2','instrumento_p3','instrumento_p4','p_instrumento'),
    'práctica instrumental':         ('instrumento_p1','instrumento_p2','instrumento_p3','instrumento_p4','p_instrumento'),
    'practica instrumental':         ('instrumento_p1','instrumento_p2','instrumento_p3','instrumento_p4','p_instrumento'),
    'instrumento principal':         ('instrumento_p1','instrumento_p2','instrumento_p3','instrumento_p4','p_instrumento'),
    'instrumento':                   ('instrumento_p1','instrumento_p2','instrumento_p3','instrumento_p4','p_instrumento'),
    'canto coral':                   ('canto_p1','canto_p2','canto_p3','canto_p4','p_canto'),
    'canto':                         ('canto_p1','canto_p2','canto_p3','canto_p4','p_canto'),
    'coral':                         ('canto_p1','canto_p2','canto_p3','canto_p4','p_canto'),
    'lenguaje musical':              ('lenguaje_musical_p1','lenguaje_musical_p2','lenguaje_musical_p3','lenguaje_musical_p4','p_lenguaje_musical'),
    'teoría musical':                ('lenguaje_musical_p1','lenguaje_musical_p2','lenguaje_musical_p3','lenguaje_musical_p4','p_lenguaje_musical'),
    'teoria musical':                ('lenguaje_musical_p1','lenguaje_musical_p2','lenguaje_musical_p3','lenguaje_musical_p4','p_lenguaje_musical'),
    'solfeo':                        ('lenguaje_musical_p1','lenguaje_musical_p2','lenguaje_musical_p3','lenguaje_musical_p4','p_lenguaje_musical'),
    # ── TEATRO
    'entrenamiento rítmico':         ('entrenamiento_p1','entrenamiento_p2','entrenamiento_p3','entrenamiento_p4','p_entrenamiento'),
    'entrenamiento ritmico':         ('entrenamiento_p1','entrenamiento_p2','entrenamiento_p3','entrenamiento_p4','p_entrenamiento'),
    'entrenamiento vocal':           ('entrenamiento_p1','entrenamiento_p2','entrenamiento_p3','entrenamiento_p4','p_entrenamiento'),
    'técnica vocal':                 ('entrenamiento_p1','entrenamiento_p2','entrenamiento_p3','entrenamiento_p4','p_entrenamiento'),
    'tecnica vocal':                 ('entrenamiento_p1','entrenamiento_p2','entrenamiento_p3','entrenamiento_p4','p_entrenamiento'),
    'lenguaje danzario':             ('expresion_p1','expresion_p2','expresion_p3','expresion_p4','p_expresion'),
    'expresión corporal':            ('expresion_p1','expresion_p2','expresion_p3','expresion_p4','p_expresion'),
    'expresion corporal':            ('expresion_p1','expresion_p2','expresion_p3','expresion_p4','p_expresion'),
    'actuación teatral':             ('expresion_p1','expresion_p2','expresion_p3','expresion_p4','p_expresion'),
    'actuacion teatral':             ('expresion_p1','expresion_p2','expresion_p3','expresion_p4','p_expresion'),
    'historia del arte y apreciaci': ('historia_teatro_p1','historia_teatro_p2','historia_teatro_p3','historia_teatro_p4','p_historia_teatro'),
    'historia del teatro':           ('historia_teatro_p1','historia_teatro_p2','historia_teatro_p3','historia_teatro_p4','p_historia_teatro'),
    'historia y apreciación teatral':('historia_teatro_p1','historia_teatro_p2','historia_teatro_p3','historia_teatro_p4','p_historia_teatro'),
    'historia y apreciacion teatral':('historia_teatro_p1','historia_teatro_p2','historia_teatro_p3','historia_teatro_p4','p_historia_teatro'),
    'apreciación teatral':           ('historia_teatro_p1','historia_teatro_p2','historia_teatro_p3','historia_teatro_p4','p_historia_teatro'),
    'apreciacion teatral':           ('historia_teatro_p1','historia_teatro_p2','historia_teatro_p3','historia_teatro_p4','p_historia_teatro'),
    # ── ARTES VISUALES
    'dibujo técnico':                ('dibujo_p1','dibujo_p2','dibujo_p3','dibujo_p4','p_dibujo'),
    'dibujo tecnico':                ('dibujo_p1','dibujo_p2','dibujo_p3','dibujo_p4','p_dibujo'),
    'principios de dibujo':          ('dibujo_p1','dibujo_p2','dibujo_p3','dibujo_p4','p_dibujo'),
    'dibujo':                        ('dibujo_p1','dibujo_p2','dibujo_p3','dibujo_p4','p_dibujo'),
    'pintura y técnicas mixtas':     ('pintura_p1','pintura_p2','pintura_p3','pintura_p4','p_pintura'),
    'pintura y tecnicas mixtas':     ('pintura_p1','pintura_p2','pintura_p3','pintura_p4','p_pintura'),
    'técnicas mixtas':               ('pintura_p1','pintura_p2','pintura_p3','pintura_p4','p_pintura'),
    'tecnicas mixtas':               ('pintura_p1','pintura_p2','pintura_p3','pintura_p4','p_pintura'),
    'pintura':                       ('pintura_p1','pintura_p2','pintura_p3','pintura_p4','p_pintura'),
    'cerámica':                      ('pintura_p1','pintura_p2','pintura_p3','pintura_p4','p_pintura'),
    'ceramica':                      ('pintura_p1','pintura_p2','pintura_p3','pintura_p4','p_pintura'),
    'historia del arte universal':   ('historia_arte_p1','historia_arte_p2','historia_arte_p3','historia_arte_p4','p_historia_arte'),
    'historia del arte':             ('historia_arte_p1','historia_arte_p2','historia_arte_p3','historia_arte_p4','p_historia_arte'),
    'apreciación artística':         ('historia_arte_p1','historia_arte_p2','historia_arte_p3','historia_arte_p4','p_historia_arte'),
    'apreciacion artistica':         ('historia_arte_p1','historia_arte_p2','historia_arte_p3','historia_arte_p4','p_historia_arte'),
}

# Ordenar por longitud de clave descendente (más específico primero)
MATERIA_A_COLUMNA_SORTED = sorted(MATERIA_A_COLUMNA.items(), key=lambda x: len(x[0]), reverse=True)


def detectar_columnas(nombre_materia):
    """Retorna la tupla de columnas para un nombre de materia o None si no mapea."""
    mn = nombre_materia.lower().strip()
    for clave, cols in MATERIA_A_COLUMNA_SORTED:
        if clave in mn:
            return cols
    return None


def main():
    print(f"Conectando a: {DB_PATH}")
    if not os.path.exists(DB_PATH):
        print(f"ERROR: No se encontró database.db en {DB_PATH}")
        sys.exit(1)

    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        conn.row_factory = sqlite3.Row

        # Verificar columnas disponibles en estudiantes
        cols_existentes = {row[1] for row in conn.execute("PRAGMA table_info(estudiantes)").fetchall()}
        columnas_requeridas = set()
        for _, cols in MATERIA_A_COLUMNA.items():
            columnas_requeridas.update(cols)
        faltantes = columnas_requeridas - cols_existentes
        if faltantes:
            print(f"ADVERTENCIA: Faltan {len(faltantes)} columnas en estudiantes: {sorted(faltantes)}")
            print("Ejecuta primero: python3 app.py (para aplicar la migración)")

        # Leer todas las materias_calificaciones
        rows = conn.execute("""
            SELECT estudiante_id, materia, p1, p2, p3, p4, promedio
            FROM materias_calificaciones
        """).fetchall()

        print(f"Registros en materias_calificaciones: {len(rows)}")

        actualizados = set()
        sin_mapeo   = set()
        errores     = 0

        for row in rows:
            est_id = row['estudiante_id']
            materia = row['materia'] or ''
            cols = detectar_columnas(materia)
            if not cols:
                sin_mapeo.add(materia.lower().strip())
                continue

            col_p1, col_p2, col_p3, col_p4, col_prom = cols

            # Solo actualizar si la columna existe
            sets = []
            vals = []
            for col, val in [(col_p1, row['p1']), (col_p2, row['p2']),
                             (col_p3, row['p3']), (col_p4, row['p4']),
                             (col_prom, row['promedio'])]:
                if col in cols_existentes and val is not None and float(val) > 0:
                    sets.append(f"{col} = ?")
                    vals.append(val)

            if not sets:
                continue

            vals.append(est_id)
            try:
                conn.execute(
                    f"UPDATE estudiantes SET {', '.join(sets)} WHERE id = ?",
                    vals
                )
                actualizados.add(est_id)
            except Exception as ex:
                print(f"  ERROR estudiante {est_id} materia '{materia}': {ex}")
                errores += 1

        conn.commit()

    print(f"\n{'='*50}")
    print(f"Estudiantes actualizados: {len(actualizados)}")
    print(f"Errores:                  {errores}")
    if sin_mapeo:
        print(f"\nMaterias sin mapeo ({len(sin_mapeo)}) — no son módulos técnicos de estas menciones:")
        for m in sorted(sin_mapeo)[:20]:
            print(f"  - {m}")
        if len(sin_mapeo) > 20:
            print(f"  ... y {len(sin_mapeo)-20} más")


if __name__ == '__main__':
    main()
