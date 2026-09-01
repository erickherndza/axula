#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verificar_curriculo_ia.py
==========================
Diagnóstico de solo lectura: prueba que los 3 generadores de prompts de IA
(planificación, rúbrica, estrategia — core/ia.py) y el generador de
documentos de asignación (core/helpers.py::_construir_prompt_asignacion)
encuentren contenido curricular real para una materia de cada una de las
4 menciones (Multimedia, Artes Visuales, Música, Teatro).

Antes de la corrección de esta sesión (adecuación curricular MEJORAS/
RESUMEN_CAMBIOS.md), estas 4 funciones leían diccionarios cuyos nombres de
campo nunca coincidían con el esquema real de core/curriculo_*.py, así que
generaban el prompt SIN ningún contexto curricular oficial, sin importar
la mención — el bug era silencioso (no lanzaba error, solo devolvía
prompts vacíos de contexto).

No llama a ningún proveedor de IA (Groq/Claude) — solo construye el texto
del prompt y verifica que las líneas de contexto curricular no queden
vacías.

Uso:
    python3 scripts/verificar_curriculo_ia.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.helpers import _construir_prompt_asignacion  # noqa: E402
from core.ia import (  # noqa: E402
    construir_prompt_planificacion,
    construir_prompt_rubrica,
    construir_prompt_estrategia,
)

CASOS = [
    ("MULTIMEDIA", "Fotografía"),
    ("ARTES VISUALES", "Introducción a la Fotografía Digital"),
    ("MÚSICA", "Instrumento I"),
    ("TEATRO", "Maquillaje y Vestuario"),
]

MARCADORES_VACIO = (
    "Competencia oficial: \n",
    "Competencia curricular: \n",
    "Competencia: \n",
)


def main():
    fallos = []
    for mencion, materia in CASOS:
        print(f"=== {mencion} — {materia} ===")
        pruebas = {
            "planificacion": construir_prompt_planificacion(
                materia, "4to", "tema de prueba", 3, "grupo mixto", mencion=mencion),
            "rubrica": construir_prompt_rubrica(
                materia, "indicador de prueba", "4to", mencion=mencion),
            "estrategia": construir_prompt_estrategia(
                materia, "problema de prueba", "perfil de prueba", mencion=mencion),
            "asignacion": _construir_prompt_asignacion(
                "tarea", materia, "4to", mencion, ""),
        }
        for nombre, prompt in pruebas.items():
            vacio = any(m in prompt for m in MARCADORES_VACIO)
            estado = "⚠ VACÍO — sin contexto curricular" if vacio else "✓ OK — con contenido real"
            print(f"  {nombre:14s} {estado} ({len(prompt)} caracteres)")
            if vacio:
                fallos.append((mencion, materia, nombre))
        print()

    if fallos:
        print(f"⚠ {len(fallos)} generador(es) sin contexto curricular:")
        for f in fallos:
            print(f"  - {f}")
        sys.exit(1)
    else:
        print(f"✓ Los {len(CASOS)*4} generadores probados encontraron contenido curricular real.")


if __name__ == "__main__":
    main()
