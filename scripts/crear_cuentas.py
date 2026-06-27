# -*- coding: utf-8 -*-
"""
Script: crear_cuentas.py
Uso: python3 scripts/crear_cuentas.py

Edita la lista PERSONAL_REAL abajo con los datos del personal,
luego ejecuta el script. Genera contraseña inicial: Nombre2026!
(primera palabra del nombre + 2026!)
"""

import sqlite3
import sys
import os

# Asegura que corre desde el directorio raíz del proyecto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from werkzeug.security import generate_password_hash

DATABASE = "database.db"

# ─────────────────────────────────────────────────────────────────────────────
# EDITAR ESTA LISTA con los datos reales del personal
# Formato: (nombre_completo, rol, usuario)
#
# Roles disponibles:
#   profesor, coordinador_primer_ciclo, coordinador_segundo_ciclo,
#   psicologa_primer_ciclo, psicologa_segundo_ciclo,
#   secretaria, secretaria_docente, digitador,
#   auxiliar_contabilidad, suministros, asistente_directora
# ─────────────────────────────────────────────────────────────────────────────
PERSONAL_REAL = [
    # ("Nombre Apellido",     "rol",                        "usuario"),
    # ("María García",        "secretaria_docente",         "mgarcia"),
    # ("Juan Pérez",          "profesor",                   "jperez"),
    # ("Ana Rodríguez",       "psicologa_segundo_ciclo",    "arodriguez"),
]

def generar_password(nombre: str) -> str:
    """Contraseña inicial: PrimeraPalabra + 2026! (ej: María → Maria2026!)"""
    primera = nombre.strip().split()[0]
    # Normalizar: capitalizar, quitar acentos básicos
    primera = primera.capitalize()
    for a, b in [("á","a"),("é","e"),("í","i"),("ó","o"),("ú","u"),
                 ("Á","A"),("É","E"),("Í","I"),("Ó","O"),("Ú","U"),("ñ","n"),("Ñ","N")]:
        primera = primera.replace(a, b)
    return f"{primera}2026!"


def crear_cuentas():
    if not PERSONAL_REAL:
        print("⚠️  La lista PERSONAL_REAL está vacía. Edita el script antes de correr.")
        return

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    creadas   = []
    existentes = []
    errores    = []

    for nombre, rol, usuario in PERSONAL_REAL:
        # Verificar si ya existe
        existe = conn.execute(
            "SELECT id FROM usuarios WHERE username = ?", (usuario,)
        ).fetchone()

        if existe:
            existentes.append(usuario)
            continue

        pwd_plain = generar_password(nombre)
        pwd_hash  = generate_password_hash(pwd_plain, method="pbkdf2:sha256")

        try:
            conn.execute("""
                INSERT INTO usuarios (username, password, nombre, rol, activo)
                VALUES (?, ?, ?, ?, 1)
            """, (usuario, pwd_hash, nombre, rol))
            creadas.append((nombre, rol, usuario, pwd_plain))
        except Exception as e:
            errores.append((usuario, str(e)))

    conn.commit()
    conn.close()

    print("\n" + "═" * 60)
    print("  RESULTADO — CREACIÓN DE CUENTAS")
    print("═" * 60)

    if creadas:
        print(f"\n✅ CREADAS ({len(creadas)}):\n")
        print(f"  {'NOMBRE':<25} {'ROL':<30} {'USUARIO':<15} {'PASSWORD'}")
        print(f"  {'-'*25} {'-'*30} {'-'*15} {'-'*12}")
        for nombre, rol, usuario, pwd in creadas:
            print(f"  {nombre:<25} {rol:<30} {usuario:<15} {pwd}")

    if existentes:
        print(f"\n⚠️  YA EXISTÍAN ({len(existentes)}): {', '.join(existentes)}")

    if errores:
        print(f"\n❌ ERRORES ({len(errores)}):")
        for u, e in errores:
            print(f"  {u}: {e}")

    print("\n" + "═" * 60)
    print("  NOTA: Entregar esta lista al personal para primer acceso.")
    print("  Cada usuario puede cambiar su contraseña desde /perfil")
    print("═" * 60 + "\n")


if __name__ == "__main__":
    crear_cuentas()
