#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
auditar_materias_profesores.py
================================
Diagnóstico de solo lectura: para CADA usuario con rol profesor, revisa
cada materia de su perfil (`asignaturas` o `materia`, separadas por `|`)
contra el catálogo interno PLAN_ARTES (para su/sus mención(es) y grado(s),
resueltos con la misma lógica que portal_profesor()/_resolver_alcance_profesor())
y reporta:

  - OK (substring)  → coincide exacto/por substring, como siempre funcionó
  - OK (difuso)      → coincide solo por SequenceMatcher >= 0.75 (típico:
                        una coma o palabra de más/menos frente al catálogo)
  - HUÉRFANA         → no coincide con nada del catálogo para su mención/
                        grado — esa materia NO aparece en su Pase de Lista
                        ni Plan de Estudio hasta que alguien decida si el
                        catálogo le falta esa materia o el perfil debe usar
                        el nombre exacto del catálogo. Se muestra el mejor
                        candidato aunque esté bajo el umbral, para ayudar a
                        decidir.

No escribe nada en la BD.

Uso:
    python3 scripts/auditar_materias_profesores.py
"""
import os
import sys
import unicodedata as _ud
import sqlite3
from difflib import SequenceMatcher

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

_en_render = os.path.exists("/data")
DB_PATH = os.environ.get(
    "DATABASE_PATH",
    "/data/database.db" if _en_render
    else os.path.join(os.path.dirname(__file__), "..", "database.db"),
)

UMBRAL_DIFUSO = 0.75


def _norm_asig(s):
    s = (s or "").strip().lower()
    return _ud.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")


def main():
    from core.helpers import _resolver_alcance_profesor
    from core.constants import PLAN_ARTES, PLAN_MULTIMEDIA

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    print(f"BD: {DB_PATH}\n")

    profesores = conn.execute("""
        SELECT id, nombre, username, rol, tipo_docencia, grado, mencion,
               ciclo, asignaturas, materia
        FROM usuarios
        WHERE rol='profesor' AND activo=1
        ORDER BY nombre
    """).fetchall()

    print(f"Profesores activos encontrados: {len(profesores)}\n")
    print("=" * 78)

    total_huerfanas = 0
    perfiles_con_huerfanas = 0

    for prof in profesores:
        prof_d = dict(prof)
        asigs_raw = (prof_d.get("asignaturas") or prof_d.get("materia") or "").strip()
        materias = [a.strip() for a in asigs_raw.split("|") if a.strip()]
        if not materias:
            continue

        alcance = _resolver_alcance_profesor(prof_d)
        grados_prof = alcance["grados"] or ["4to"]
        menciones_prof = (alcance["menciones"] if alcance["filtro_mencion"] else None) or ["MULTIMEDIA"]

        # Catálogo combinado de todos sus grados x menciones
        catalogo = {}  # nombre_normalizado -> nombre_original
        for gk in grados_prof:
            for mk in menciones_prof:
                plan_mencion = PLAN_ARTES.get(mk.upper(), PLAN_MULTIMEDIA)
                for asig, _horas in plan_mencion.get(gk.lower(), []):
                    catalogo[_norm_asig(asig)] = asig

        print(f"{prof_d['nombre']} ({prof_d['username']}) — grados={grados_prof} "
              f"menciones={menciones_prof if alcance['filtro_mencion'] else 'todas'}")

        huerfanas_de_este = []
        for mat in materias:
            n = _norm_asig(mat)
            estado = None
            if any(n in c or c in n for c in catalogo):
                estado = "OK (substring)"
            else:
                mejor_ratio, mejor_nombre = 0.0, None
                for c_norm, c_orig in catalogo.items():
                    r = SequenceMatcher(None, n, c_norm).ratio()
                    if r > mejor_ratio:
                        mejor_ratio, mejor_nombre = r, c_orig
                if mejor_ratio >= UMBRAL_DIFUSO:
                    estado = f"OK (difuso {mejor_ratio:.2f} con {mejor_nombre!r})"
                else:
                    estado = f"HUÉRFANA — mejor candidato: {mejor_nombre!r} (similitud {mejor_ratio:.2f})"
                    huerfanas_de_este.append(mat)

            marca = "✓" if estado.startswith("OK") else "✗"
            print(f"  [{marca}] {mat}")
            print(f"       {estado}")

        if huerfanas_de_este:
            perfiles_con_huerfanas += 1
            total_huerfanas += len(huerfanas_de_este)
            print(f"  ⚠ {len(huerfanas_de_este)} materia(s) huérfana(s) de {len(materias)} totales")
        print("=" * 78)

    print(f"\nResumen: {perfiles_con_huerfanas} perfil(es) con materias huérfanas, "
          f"{total_huerfanas} materia(s) huérfana(s) en total.")

    conn.close()


if __name__ == "__main__":
    main()
