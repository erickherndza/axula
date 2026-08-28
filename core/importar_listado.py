# -*- coding: utf-8 -*-
"""
core/importar_listado.py
=========================
Lógica compartida para leer y aplicar CUALQUIER "Listado de Estudiantes"
oficial (una hoja por archivo, encabezado "GRADO:"/"ÁREA:" + tabla de
alumnos) contra la tabla `estudiantes`.

Usada por:
  - scripts/cargar_listado_estudiantes.py (CLI, para Render Shell)
  - routes/profesor.py (subida desde el navegador en /profesor → Cargar Excel)

Una sola implementación — evita el patrón "una copia evoluciona, la otra
fosiliza" que ya causó bugs reales en este proyecto (ver CLAUDE.md sesión 8).
"""
import unicodedata
from difflib import SequenceMatcher

import openpyxl

GRADOS_VALIDOS = ["1ro", "2do", "3ro", "4to", "5to", "6to"]
_GRADO_ALIAS = {"1ero": "1ro", "1er": "1ro", "2er": "2do", "3er": "3ro"}

# nombre normalizado de encabezado → clave interna. Cubre las variantes más
# comunes; agregar aquí si aparece un listado con un nombre de columna nuevo.
HEADER_MAP = {
    "NO": "no", "NO.": "no", "NUM": "no", "NUMERO": "no", "N": "no", "#": "no",
    "NOMBRE": "nombre", "NOMBRES": "nombre",
    "APELLIDO": "apellido", "APELLIDOS": "apellido",
    "EDAD": "edad",
    "ID": "cedula", "CEDULA": "cedula", "IDENTIFICACION": "cedula", "NO IDENTIFICACION": "cedula",
    "SEXO": "sexo", "GENERO": "sexo",
    "FECHA DE NACIMIENTO": "nacimiento", "FECHA NACIMIENTO": "nacimiento", "NACIMIENTO": "nacimiento",
    "TELEFONO": "telefono", "TELEFONO CONTACTO": "telefono", "CONTACTO": "telefono", "TEL": "telefono",
}
COLUMNAS_REQUERIDAS = {"no", "nombre", "apellido"}


def norm(s):
    s = (s or "").strip().lower()
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")


def _norm_header(s):
    s = str(s or "").strip().upper()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return s.rstrip(".").strip()


def _parsear_grado_seccion(valor):
    """'4TO' → ('4to', None) · '4TO B' → ('4to', 'B') · '1er.' → ('1ro', None)"""
    grado, seccion = None, None
    resto = []
    for tok in str(valor or "").split():
        t = tok.strip().lower().rstrip(".")
        t = _GRADO_ALIAS.get(t, t)
        if t in GRADOS_VALIDOS:
            grado = t
        else:
            resto.append(tok.strip())
    if resto:
        cand = resto[0].strip().upper().rstrip(".")
        if cand and len(cand) <= 2 and cand.isalpha():
            seccion = cand
    return grado, seccion


def _extraer_etiqueta(ws, etiquetas, max_row=15):
    """
    Busca cualquiera de `etiquetas` (ej. "GRADO:") en las primeras filas.
    Soporta 'ETIQUETA: valor' en una sola celda o etiqueta y valor en
    celdas separadas (valor a la derecha). Devuelve el string del valor o ''.
    """
    for row in ws.iter_rows(min_row=1, max_row=min(max_row, ws.max_row)):
        for cell in row:
            texto = str(cell.value or "").strip()
            if not texto:
                continue
            texto_up = _norm_header(texto)
            for etq in etiquetas:
                etq_n = _norm_header(etq)
                if texto_up == etq_n:
                    # etiqueta sola → el valor está en la celda de al lado
                    vecino = ws.cell(row=cell.row, column=cell.column + 1).value
                    return str(vecino or "").strip()
                if texto_up.startswith(etq_n + ":") or texto_up.startswith(etq_n):
                    resto = texto[len(etq):].lstrip(":").strip()
                    if resto:
                        return resto
    return ""


def _detectar_fila_encabezado(ws, max_row=20):
    """
    Busca la fila que tiene los encabezados de la tabla de alumnos y arma
    {clave_interna: numero_de_columna}. No asume columnas fijas — cada
    listado puede traer las columnas en el orden/posición que sea.
    """
    mejor_fila, mejor_cols = None, {}
    for row in ws.iter_rows(min_row=1, max_row=min(max_row, ws.max_row)):
        cols = {}
        for cell in row:
            clave = HEADER_MAP.get(_norm_header(cell.value))
            if clave and clave not in cols:
                cols[clave] = cell.column
        if COLUMNAS_REQUERIDAS.issubset(cols.keys()) and len(cols) > len(mejor_cols):
            mejor_fila, mejor_cols = row[0].row, cols
    if not mejor_fila:
        raise ValueError(
            "No se encontró una fila de encabezados con las columnas mínimas "
            f"{sorted(COLUMNAS_REQUERIDAS)}. Revisa que el archivo tenga "
            "No./Nombre/Apellido como títulos de columna en alguna fila."
        )
    return mejor_fila, mejor_cols


def leer_listado_workbook(wb):
    """Recibe un Workbook de openpyxl ya cargado (desde archivo o BytesIO)."""
    ws = wb.worksheets[0]

    grado_raw   = _extraer_etiqueta(ws, ["GRADO:", "GRADO"])
    mencion_raw = _extraer_etiqueta(ws, ["ÁREA:", "AREA:", "MENCIÓN:", "MENCION:", "ÁREA", "MENCIÓN"])

    grado, seccion = _parsear_grado_seccion(grado_raw)
    if not grado:
        raise ValueError(
            f"No se pudo determinar el grado a partir de 'GRADO: {grado_raw!r}'. "
            "Verifica que el encabezado del archivo tenga 'GRADO:' seguido de "
            "1ro/2do/3ro/4to/5to/6to."
        )
    mencion = mencion_raw.strip().upper() or None

    fila_header, cols = _detectar_fila_encabezado(ws)

    def _val(row, clave):
        col = cols.get(clave)
        return row[col - 1].value if col else None

    alumnos = []
    for row in ws.iter_rows(min_row=fila_header + 1, max_row=ws.max_row):
        no = _val(row, "no")
        if not isinstance(no, (int, float)) or not (1 <= no <= 999):
            continue
        nombre   = str(_val(row, "nombre") or "").strip()
        apellido = str(_val(row, "apellido") or "").strip()
        if not nombre or not apellido:
            continue

        edad_raw = _val(row, "edad")
        try:
            edad = int(edad_raw) if edad_raw not in (None, "") else None
        except (TypeError, ValueError):
            edad = None

        cedula_raw = str(_val(row, "cedula") or "").strip()
        cedula_raw = cedula_raw.replace(".0", "").replace(",", "").replace("-", "").strip()
        cedula = cedula_raw if cedula_raw.isdigit() else None

        alumnos.append({
            "no": int(no), "nombre": nombre, "apellido": apellido,
            "edad": edad, "cedula": cedula,
        })
    return grado, seccion, mencion, alumnos


def leer_listado(path):
    """Variante para CLI: recibe una ruta de archivo."""
    wb = openpyxl.load_workbook(path, data_only=True)
    return leer_listado_workbook(wb)


def buscar_existente(conn, alumno, grado, mencion):
    """cédula exacta → nombre+apellido exacto → fuzzy dentro del mismo grado+mención."""
    if alumno["cedula"]:
        row = conn.execute(
            "SELECT id, nombre, apellido, cedula, grado, curso, condicion FROM estudiantes WHERE cedula=?",
            (alumno["cedula"],)
        ).fetchone()
        if row:
            return row

    row = conn.execute(
        """SELECT id, nombre, apellido, cedula, grado, curso, condicion FROM estudiantes
           WHERE lower(nombre)=lower(?) AND lower(apellido)=lower(?)""",
        (alumno["nombre"], alumno["apellido"])
    ).fetchone()
    if row:
        return row

    clave = norm(alumno["nombre"] + " " + alumno["apellido"])
    if mencion:
        candidatos = conn.execute(
            """SELECT id, nombre, apellido, cedula, grado, curso, condicion FROM estudiantes
               WHERE grado=? AND (mencion=? OR mencion IS NULL OR mencion='')""",
            (grado, mencion)
        ).fetchall()
    else:
        candidatos = conn.execute(
            "SELECT id, nombre, apellido, cedula, grado, curso, condicion FROM estudiantes WHERE grado=?",
            (grado,)
        ).fetchall()
    mejor, mejor_score = None, 0.0
    for c in candidatos:
        score = SequenceMatcher(None, clave, norm(c["nombre"] + " " + c["apellido"])).ratio()
        if score > mejor_score:
            mejor, mejor_score = c, score
    if mejor and mejor_score >= 0.82:
        return mejor
    return None


def construir_plan(conn, grado, seccion, mencion, alumnos):
    """
    Calcula, SIN escribir en BD, qué haría la carga por cada alumno.
    Devuelve (curso, ciclo, plan) donde plan es una lista de dicts:
      {no, nombre, apellido, cedula, accion: 'nuevo'|'actualiza',
       cambios: [...], advertencia: str|None, estudiante_id: int|None}
    """
    curso = f"{grado} {mencion}".strip() if mencion else grado
    ciclo = "primer_ciclo" if grado in ("1ro", "2do", "3ro") else "segundo_ciclo"

    plan = []
    for alumno in alumnos:
        existente = buscar_existente(conn, alumno, grado, mencion)
        item = {
            "no": alumno["no"], "nombre": alumno["nombre"], "apellido": alumno["apellido"],
            "cedula": alumno["cedula"], "edad": alumno["edad"],
            "advertencia": None, "estudiante_id": None,
        }
        if existente:
            cambios = []
            if existente["grado"] != grado: cambios.append(f"grado {existente['grado']!r}→{grado!r}")
            if existente["curso"] != curso: cambios.append(f"curso {existente['curso']!r}→{curso!r}")
            if not existente["cedula"] and alumno["cedula"]:
                cambios.append(f"cédula → {alumno['cedula']}")
            item.update(accion="actualiza", cambios=cambios, estudiante_id=existente["id"])
            if existente["condicion"] in ("RETIRADO", "TRANSFERIDO"):
                item["advertencia"] = (
                    f"Ya existe con condición {existente['condicion']} — "
                    "no se reactiva automáticamente, revisar a mano"
                )
        else:
            item.update(accion="nuevo", cambios=[])
            if not alumno["cedula"]:
                item["advertencia"] = "Sin cédula/ID en el archivo — queda con ID provisional"
        plan.append(item)
    return curso, ciclo, plan


def aplicar_carga(conn, grado, seccion, mencion, alumnos):
    """Escribe en BD. Devuelve (nuevos, actualizados)."""
    curso, ciclo, plan = construir_plan(conn, grado, seccion, mencion, alumnos)
    nuevos = actualizados = 0

    for alumno, item in zip(alumnos, plan):
        if item["accion"] == "actualiza":
            actualizados += 1
            # No se toca 'condicion' en un UPDATE — si el alumno ya existía
            # como RETIRADO/TRANSFERIDO, reactivarlo es una decisión humana.
            conn.execute(
                """UPDATE estudiantes
                      SET nombre=?, apellido=?, grado=?, curso=?, mencion=?, ciclo=?,
                          seccion=COALESCE(?, seccion),
                          cedula=COALESCE(NULLIF(cedula,''), ?),
                          edad=COALESCE(?, edad)
                    WHERE id=?""",
                (alumno["nombre"], alumno["apellido"], grado, curso, mencion, ciclo,
                 seccion, alumno["cedula"] or "", alumno["edad"], item["estudiante_id"])
            )
        else:
            nuevos += 1
            conn.execute(
                """INSERT INTO estudiantes
                       (id_evaluacion, cedula, nombre, apellido, curso, grado,
                        mencion, ciclo, seccion, condicion, edad)
                   VALUES (?,?,?,?,?,?,?,?,COALESCE(?,'A'),'ACTIVO',?)""",
                (alumno["cedula"] or f"PROV_{alumno['nombre'].split()[0]}_{alumno['apellido'].split()[0]}",
                 alumno["cedula"] or "", alumno["nombre"], alumno["apellido"],
                 curso, grado, mencion, ciclo, seccion, alumno["edad"])
            )
    conn.commit()
    return nuevos, actualizados
