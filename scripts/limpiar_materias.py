#!/usr/bin/env python3
"""
scripts/limpiar_materias.py
Limpia materias_calificaciones:
  1. Elimina materias de otra mención cargadas por error desde PDFs
  2. Deduplica entradas con el mismo nombre normalizado por estudiante

Uso:
  python3 scripts/limpiar_materias.py          # dry-run (solo muestra)
  python3 scripts/limpiar_materias.py --apply  # escribe en la BD
"""
import sqlite3, os, sys, unicodedata, re

_en_render = os.path.exists("/opt/render")
DATABASE = os.environ.get("DATABASE_PATH", "/data/database.db" if _en_render else "database.db")
apply = "--apply" in sys.argv

print(f"BD: {DATABASE}")
print(f"Modo: {'ESCRIBIR' if apply else 'DRY-RUN'}\n")


def norm(s):
    """Minúsculas + sin tildes + sin puntuación redundante."""
    s = (s or "").strip().lower()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    # Eliminar numeración romana al final (" i", " ii", " iii", " iv"…)
    s = re.sub(r'\s+(i{1,3}v?|iv|v?i{0,3}|ix|x)\s*$', '', s)
    s = s.rstrip('.,;')
    return s.strip()


def get_mencion(curso):
    c = (curso or "").upper()
    if 'MULTIMEDIA'           in c: return 'MULTIMEDIA'
    if 'TEATRO'               in c: return 'TEATRO'
    if 'MUSICA' in c or 'MÚSICA' in c: return 'MUSICA'
    if 'VISUAL'               in c: return 'ARTES_VISUALES'
    if 'DANZA'                in c: return 'DANZA'
    return None  # primer ciclo o sin mención → no filtrar


# ────────────────────────────────────────────────────────────────────────────
# Patrones PROHIBIDOS por mención del estudiante.
# Si el nombre normalizado de una materia contiene alguno de estos, se elimina.
# Los patrones académicos (lengua, ingles, matematica, etc.) nunca están aquí.
# ────────────────────────────────────────────────────────────────────────────
PROHIBIDOS = {
    'MULTIMEDIA': [
        # ── De TEATRO ──────────────────────────────────────────────────────
        'caracterizaci',            # Caracterización de Personaje
        'entrenamiento ritmico',    # Entrenamiento Rítmico Corporal y Vocal
        'corporal y vocal',
        'historia del artes y apreciacion',   # Historia del Artes y Apreciación del Teatro
        'historia del teatro',                # Historia del Teatro Universal y Dominicano
        'expresion corporal y tecnica actoral',
        'puesta en escena',
        'actuacion',                # Actuación I / II (Teatro específico)
        # ── De MÚSICA ──────────────────────────────────────────────────────
        'canto coral',
        'practica instrumental',
        'instrumental grupal',
        'lenguaje musical, teoria',  # "Lenguaje Musical, Teoría y Entrenamiento" ≠ MULTIMEDIA
        'lenguaje musical teoria',
        'teoria y solfeo',
        'instrumento principal',
        'coro y conjunto',
        # ── De ARTES VISUALES ──────────────────────────────────────────────
        'lenguaje plastico',
        'ceramica',
        'tecnicas mixtas',
        'pintura y tecnica',
        'dibujo tecnico y artistico',
        'grabado y serigrafia',
        'escultura',
        # ── De DANZA ───────────────────────────────────────────────────────
        'tecnica de danza',
        'coreografi',
        'danza clasica',
        'danza moderna',
        'danza folklorica',
        'composicion coreografica',
    ],
    'TEATRO': [
        # ── De MULTIMEDIA ──────────────────────────────────────────────────
        'diseno basico',
        'historia del arte universal y estetica',
        'diseno web', 'diseno grafico', 'publicidad y creatividad',
        'operacion de camara', 'guion', 'redes sociales', 'produccion audiovisual',
        'videoarte', 'animacion', 'edicion sonido',
        # ── De MÚSICA ──────────────────────────────────────────────────────
        'canto coral', 'practica instrumental', 'instrumental grupal',
        'lenguaje musical, teoria', 'teoria y solfeo', 'instrumento principal',
        'coro y conjunto',
        # ── De ARTES VISUALES ──────────────────────────────────────────────
        'lenguaje plastico', 'ceramica', 'tecnicas mixtas', 'grabado y serigrafia',
        # ── De DANZA ───────────────────────────────────────────────────────
        'tecnica de danza', 'coreografi', 'danza clasica', 'danza moderna',
    ],
    'MUSICA': [
        # ── De MULTIMEDIA ──────────────────────────────────────────────────
        'diseno basico', 'historia del arte universal y estetica',
        'lenguaje visual, dibujo', 'lenguaje visual y principios',
        'lenguaje visual y artesanal',
        # ── De TEATRO ──────────────────────────────────────────────────────
        'caracterizaci', 'entrenamiento ritmico', 'corporal y vocal',
        'historia del teatro', 'puesta en escena', 'expresion corporal y tecnica actoral',
        # ── De ARTES VISUALES ──────────────────────────────────────────────
        'lenguaje plastico', 'ceramica', 'tecnicas mixtas', 'grabado y serigrafia',
        # ── De DANZA ───────────────────────────────────────────────────────
        'tecnica de danza', 'coreografi',
    ],
    'ARTES_VISUALES': [
        # ── De MULTIMEDIA ──────────────────────────────────────────────────
        'diseno basico', 'historia del arte universal y estetica',
        # ── De TEATRO ──────────────────────────────────────────────────────
        'caracterizaci', 'entrenamiento ritmico', 'historia del teatro',
        'puesta en escena', 'expresion corporal y tecnica actoral',
        # ── De MÚSICA ──────────────────────────────────────────────────────
        'canto coral', 'practica instrumental', 'teoria y solfeo',
        'instrumento principal', 'coro y conjunto',
        # ── De DANZA ───────────────────────────────────────────────────────
        'tecnica de danza', 'coreografi',
    ],
    'DANZA': [
        # ── De MULTIMEDIA ──────────────────────────────────────────────────
        'diseno basico', 'historia del arte universal y estetica',
        # ── De TEATRO ──────────────────────────────────────────────────────
        'caracterizaci', 'entrenamiento ritmico', 'historia del teatro',
        'puesta en escena', 'expresion corporal y tecnica actoral',
        # ── De MÚSICA ──────────────────────────────────────────────────────
        'canto coral', 'practica instrumental', 'teoria y solfeo',
        'instrumento principal', 'coro y conjunto',
        # ── De ARTES VISUALES ──────────────────────────────────────────────
        'lenguaje plastico', 'ceramica', 'tecnicas mixtas', 'grabado y serigrafia',
    ],
}


def es_prohibida(mat_norm, mencion):
    prohbs = PROHIBIDOS.get(mencion, [])
    return any(p in mat_norm for p in prohbs)


with sqlite3.connect(DATABASE, timeout=15) as conn:
    conn.row_factory = sqlite3.Row

    estudiantes = {r['id']: r['curso'] for r in
                   conn.execute("SELECT id, curso FROM estudiantes").fetchall()}

    todas = conn.execute(
        "SELECT id, estudiante_id, materia, p1, p2, p3, p4, promedio "
        "FROM materias_calificaciones ORDER BY estudiante_id, materia"
    ).fetchall()

    ids_wrong_mencion = []
    ids_dupes = []

    # ── PASO 1: Materias de otra mención ─────────────────────────────────
    for row in todas:
        mencion = get_mencion(estudiantes.get(row['estudiante_id'], ''))
        if not mencion:
            continue
        mn = norm(row['materia'])
        if es_prohibida(mn, mencion):
            ids_wrong_mencion.append((row['id'], row['estudiante_id'], row['materia']))

    eliminados_set = {t[0] for t in ids_wrong_mencion}
    restantes = [r for r in todas if r['id'] not in eliminados_set]

    # ── PASO 2: Deduplicar (mismo nombre normalizado, mismo estudiante) ──
    grupos = {}
    for row in restantes:
        key = (row['estudiante_id'], norm(row['materia']))
        grupos.setdefault(key, []).append(row)

    for key, grupo in grupos.items():
        if len(grupo) <= 1:
            continue
        # Elegir cuál conservar: más datos primero, luego proper case sobre UPPERCASE
        def score(r):
            total = (r['p1'] or 0) + (r['p2'] or 0) + (r['p3'] or 0) + (r['p4'] or 0)
            all_upper = r['materia'] == r['materia'].upper()
            return (-total, all_upper, r['id'])
        grupo_ord = sorted(grupo, key=score)
        for dup in grupo_ord[1:]:
            ids_dupes.append((dup['id'], dup['estudiante_id'], dup['materia']))

    # ── REPORTE ──────────────────────────────────────────────────────────
    print(f"Materias de otra mención a eliminar: {len(ids_wrong_mencion)}")
    if ids_wrong_mencion:
        # Agrupar por estudiante para el log
        from collections import defaultdict
        por_est = defaultdict(list)
        for rid, eid, mat in ids_wrong_mencion:
            por_est[eid].append(mat)
        for eid, mats in list(por_est.items())[:5]:
            nombre = conn.execute("SELECT nombre, apellido, curso FROM estudiantes WHERE id=?", (eid,)).fetchone()
            if nombre:
                print(f"  [{eid}] {nombre['nombre']} {nombre['apellido']} ({nombre['curso']})")
            for m in mats:
                print(f"    ✗ {m}")
        if len(por_est) > 5:
            print(f"  ... y {len(por_est)-5} estudiantes más")

    print(f"\nDuplicados a eliminar:               {len(ids_dupes)}")
    if ids_dupes:
        for rid, eid, mat in ids_dupes[:8]:
            print(f"  ✗ [{eid}] {mat!r}")
        if len(ids_dupes) > 8:
            print(f"  ... y {len(ids_dupes)-8} más")

    total = len(ids_wrong_mencion) + len(ids_dupes)
    print(f"\nTotal a eliminar: {total}")

    if apply and total > 0:
        todos_ids = [t[0] for t in ids_wrong_mencion] + [t[0] for t in ids_dupes]
        ph = ','.join('?' * len(todos_ids))
        conn.execute(f"DELETE FROM materias_calificaciones WHERE id IN ({ph})", todos_ids)
        conn.commit()
        # Verificar resultado
        remaining = conn.execute("SELECT COUNT(*) FROM materias_calificaciones").fetchone()[0]
        print(f"\n✓ {total} filas eliminadas. Quedan {remaining} registros en MC.")
    elif total > 0:
        print("\nEjecuta con --apply para aplicar los cambios.")
    else:
        print("\nNada que limpiar.")
