#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
diag_listado_vs_bd.py
=======================
Diagnóstico de solo lectura: para cada alumno del archivo
"Listado_Estudiantes_4TO_A_Multimedia.xlsx" (33 nombres/cédulas ya
conocidos, hardcodeados abajo), busca en `estudiantes` por cédula y por
nombre+apellido — SIN filtrar por grado/curso — y muestra exactamente qué
hay: no existe, existe con datos limpios, o existe con grado/curso corrupto.

No escribe nada en la BD.

Uso:
    python3 scripts/diag_listado_vs_bd.py
"""
import os
import sqlite3

_en_render = os.path.exists("/data")
DB_PATH = os.environ.get(
    "DATABASE_PATH",
    "/data/database.db" if _en_render
    else os.path.join(os.path.dirname(__file__), "..", "database.db"),
)

# (no, nombre, apellido, cedula) tal como está en el archivo oficial
ALUMNOS = [
    (1, "Leandro Alfredo", "Alayon Mercedes", "33414785"),
    (2, "Angel David", "Amparo Matos", "6592209"),
    (3, "Trino Sahino", "Arias Rosa", None),
    (4, "Haratza Lisbeth", "Batista", "32954358"),
    (5, "Ana Lia", "Beltran De La Cruz", None),
    (6, "Alianna Andreina", "Burgos Jiménez", "6912946"),
    (7, "Chainiel", "Cuevas", "27168107"),
    (8, "Brayan Isael", "Diaz Santana", "11993482"),
    (9, "Darickson Starlin", "Encarnación Hidalgo", "32831299"),
    (10, "Jordany Leonel", "Fajardo Martínez", "11841714"),
    (11, "Gabriel Alexander", "Feliz Jimenez", "7003225"),
    (12, "Erick Manuel", "Ferreras", "32847465"),
    (13, "José Alejandro", "Gómez Castillo", "27195117"),
    (14, "Jeury Samuel", "Guillen Medina", "32741571"),
    (15, "Charles Enrique", "Horacius Pierre", "6383694"),
    (16, "Kasandra", "Jean-Baptiste Bonas", "33454136"),
    (17, "Gabriela", "Lague Jean", "33198700"),
    (18, "Genesis", "Medina Portolatin", "33325199"),
    (19, "Alanjel", "Medina Sánchez", "11892251"),
    (20, "Axel Jose", "Mejia Guzman", "32786109"),
    (21, "José Eduardo", "Mena Almonte", "6955613"),
    (22, "Renata Oriett", "Meregildo Adames", "32558173"),
    (23, "Yelissa Alexandra", "Montero García", "27152843"),
    (24, "Richard Javier", "Olivero de la Cruz", "11882300"),
    (25, "Jefry", "Olizard", "32729770"),
    (26, "Yefernny Rafael", "Paniagua Florentino", "33934833"),
    (27, "Luisanny", "Peña Rojas", None),
    (28, "Jan Moyses", "Pérez Cordero", "11970921"),
    (29, "Danna", "Reyes Pichardo", "33039162"),
    (30, "Brinny Merjorie", "Salazar Cordero", "6799530"),
    (31, "Ambar Esther", "Santana Oguis", "6822225"),
    (32, "Yovanny Yadiel", "Serrano Sanchez", "32642300"),
    (33, "Reilyn", "Silfa Álvarez", "33502147"),
]


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    print(f"BD: {DB_PATH}\n")

    no_existe, existe_limpio, existe_corrupto = [], [], []

    for no, nombre, apellido, cedula in ALUMNOS:
        row = None
        if cedula:
            row = conn.execute(
                "SELECT id, nombre, apellido, cedula, grado, curso, mencion FROM estudiantes WHERE cedula=?",
                (cedula,)
            ).fetchone()
        if not row:
            row = conn.execute(
                """SELECT id, nombre, apellido, cedula, grado, curso, mencion FROM estudiantes
                   WHERE lower(nombre)=lower(?) AND lower(apellido)=lower(?)""",
                (nombre, apellido)
            ).fetchone()

        if not row:
            no_existe.append((no, nombre, apellido, cedula))
            print(f"#{no:>2} {nombre} {apellido:<25} → NO EXISTE en la BD")
        else:
            limpio = row["grado"] in ("4TO", "4to") and "MULTIMEDIA" in (row["curso"] or "")
            estado = "OK" if limpio else "CORRUPTO"
            (existe_limpio if limpio else existe_corrupto).append(row["id"])
            print(f"#{no:>2} {nombre} {apellido:<25} → id={row['id']:<5} [{estado}] "
                  f"grado={row['grado']!r} curso={row['curso']!r}")

    print(f"\nResumen: {len(no_existe)} no existen · {len(existe_limpio)} existen limpios · "
          f"{len(existe_corrupto)} existen con grado/curso corrupto")

    conn.close()


if __name__ == "__main__":
    main()
