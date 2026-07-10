"""
Carga notas desde los PDFs de boletines (1ro-6to grado) a la BD Axula.
Uso: python3 scripts/cargar_notas_pdf.py [--dry-run]

Estructura PDF (detectada con pypdf):
  - Cada página física = 1 alumno
  - Parte superior: índice académico, No., tabla de notas por competencia, sección PC
  - Parte inferior: ALUMNO/A, MAESTRO/A, GRADO, SECCION, MENCIÓN (4-6), asistencia

Qué se extrae:
  - Índice académico (ya calculado por el centro)
  - Sección, Mención (4to-6to)
  - PC1, PC2, PC3, PC4, CF por materia (académico y técnico)
"""

import sqlite3
import re
import sys
import os
import unicodedata
from difflib import SequenceMatcher

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH  = os.path.join(BASE_DIR, "database.db")

DRY_RUN = "--dry-run" in sys.argv

# ── Definición de materias por ciclo ─────────────────────────────────────────
MATS_1_3 = [
    "Lengua Española",
    "Idioma Inglés",
    "Idioma Francés",
    "Matemática",
    "Ciencias Sociales",
    "Ciencias Naturales",
    "Educación Artística",
    "Educación Física",
    "FIHR",
]

MATS_ACAD_4_6 = [
    "Lengua Española",
    "Idioma Inglés",
    "Matemática",
    "Ciencias Sociales",
    "Ciencias Naturales",
    "Educación Física",
    "FIHR",
]

MATS_TECNICAS = {
    "MÚSICA": {
        "4TO": [
            "Identidad, Cultura y Emprendimiento",
            "Introducción a la Historia del Arte universal y Dominicano",
            "Lenguaje Visual y Principios del Diseño Artesanal",
            "Lenguaje Danzario y Teatral",
            "Lenguaje Musical, Teoría y Entrenamiento",
            "Instrumento I",
            "Práctica Instrumental Grupal I",
            "Canto Coral I",
        ],
        "5TO": [
            "Identidad, Cultura y Emprendimiento",
            "Historia del Arte Universal y Dominicano",
            "Lenguaje Visual y Principios del Diseño",
            "Lenguaje Danzario y Teatral",
            "Armonía I",
            "Instrumento II",
            "Práctica Instrumental Grupal II",
            "Canto Coral II",
        ],
        "6TO": [
            "Teoría y Entrenamiento Musical II",
            "Armonía II",
            "Historia de las Formas Musicales",
            "Instrumento III",
            "Práctica Instrumental Grupal III",
            "Canto Coral III",
            "Tecnología Musical",
            "Dirección de Grupos Musicales",
        ],
    },
    "TEATRO": {
        "4TO": [
            "Identidad, Cultura y Emprendimiento",
            "Introducción a la Historia del Arte universal y Dominicano",
            "Lenguaje Visual y Principios del Diseño Artesanal",
            "Lenguaje Musical, Teoría y Entrenamiento",
            "Expresión Corporal y Técnica Actoral I",
            "Historia del Teatro Universal y Dominicano I",
            "Lenguaje Danzario",
            "Puesta en Escena I",
        ],
        "5TO": [
            "Identidad, Cultura y Emprendimiento",
            "Historia del Arte Universal y Dominicano",
            "Lenguaje Visual y Principios del Diseño",
            "Lenguaje Musical",
            "Expresión Corporal y Técnica Actoral II",
            "Historia del Teatro Universal y Dominicano II",
            "Movimiento Escénico",
            "Puesta en Escena II",
        ],
        "6TO": [
            "Dramaturgia",
            "Historia del Teatro Contemporáneo",
            "Técnica Actoral III",
            "Diseño de Escenografía y Vestuario",
            "Puesta en Escena III",
            "Dirección Teatral",
        ],
    },
    "ARTES VISUALES": {
        "4TO": [
            "Identidad, Cultura y Emprendimiento",
            "Introducción a la Historia del Arte universal y Dominicano",
            "Lenguaje Visual y Principios del Diseño Artesanal",
            "Lenguaje Danzario y Teatral",
            "Lenguaje Musical, Teoría y Entrenamiento",
            "Dibujo Artístico I",
            "Pintura I",
            "Historia del Arte Universal y Dominicano",
        ],
        "5TO": [
            "Identidad, Cultura y Emprendimiento",
            "Historia del Arte Universal y Dominicano",
            "Lenguaje Visual y Principios del Diseño",
            "Lenguaje Danzario y Teatral",
            "Lenguaje Musical",
            "Dibujo Artístico II",
            "Pintura II",
            "Historia del Arte Dominicano",
        ],
        "6TO": [
            "Historia del Arte Contemporáneo",
            "Dibujo Artístico III",
            "Pintura III",
            "Escultura",
            "Grabado",
            "Gestión Cultural",
        ],
    },
    "MULTIMEDIA": {
        "4TO": [
            "Identidad, Cultura y Emprendimiento",
            "Introducción a la Historia del Arte universal y Dominicano",
            "Lenguaje Visual y Principios del Diseño Artesanal",
            "Lenguaje Danzario y Teatral",
            "Lenguaje Musical, Teoría y Entrenamiento",
            "Fotografía I",
            "Lenguaje Visual, Dibujo y Creación de Personajes",
            "Diseño Básico y Expresión Visual",
        ],
        "5TO": [
            "Identidad, Cultura y Emprendimiento",
            "Historia del Arte Universal y Dominicano",
            "Lenguaje Visual y Principios del Diseño",
            "Diseño Web",
            "Diseño Gráfico",
            "Publicidad y Creatividad",
            "Operación de Cámara de Video",
            "Guión",
            "Medios de Comunicación",
        ],
        "6TO": [
            "Redes Sociales",
            "Producción Audiovisual",
            "Videoarte",
            "Animación",
            "Edición, Sonido y Musicalización",
            "Producción de Proyecto Emprendedor",
        ],
    },
}

# ── Utilidades ─────────────────────────────────────────────────────────────────
def norm(s):
    s = s.lower().strip()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s)


def log(msg):
    print(msg)


# ── Parser por página ─────────────────────────────────────────────────────────
def extraer_indice(texto):
    """El índice académico es el primer entero de la página (antes de 'No.')"""
    m = re.match(r"\s*(\d+)\s*\n", texto)
    if m:
        v = int(m.group(1))
        if 0 <= v <= 100:
            return v
    return 0


def extraer_nombre(texto):
    """Busca el nombre del alumno en el texto de la página."""
    # Formato A (4-6 compact, pg 1+): "ALUMNO/A: Nombre ESTADO:"
    m = re.search(r"ALUMNO/A:\s+(.+?)\s+ESTADO:", texto)
    if m:
        n = re.sub(r"\s+", " ", m.group(1)).strip()
        if 2 <= len(n.split()) <= 6 and not n.isupper():
            return n

    # Formato B (1-3 pg0): después de "ESTADO:\nGRADO:"
    # [ \t]* en vez de \s* para no saltar la newline
    m = re.search(
        r"ESTADO:\s*\nGRADO:[ \t]*[^\n]*\n+([A-ZÁÉÍÓÚÑ][^\n]{3,50})\n",
        texto
    )
    if m:
        n = m.group(1).strip()
        if 2 <= len(n.split()) <= 6:
            return re.sub(r"\s+", " ", n)

    # Formato C (4-6 pg0): "ALUMNO/A:\nMAESTRO/A:\n[nombre]"
    m = re.search(
        r"ALUMNO/A:\s*\nMAESTRO/A:\s*\n([A-ZÁÉÍÓÚÑ][^\n]{3,50})\n",
        texto
    )
    if m:
        n = m.group(1).strip()
        if 2 <= len(n.split()) <= 6 and not n.isupper():
            return re.sub(r"\s+", " ", n)

    # Formato D (6TO pg0): "MAESTRO/A:\n[nombre alumno en título]\n[MAESTRO EN CAPS]"
    m = re.search(
        r"MAESTRO/A:\s*\n([A-ZÁÉÍÓÚÑ][^\n]{3,50})\n",
        texto
    )
    if m:
        n = m.group(1).strip()
        # El nombre del alumno tiene letras minúsculas; el maestro está en CAPS
        if 2 <= len(n.split()) <= 6 and not n.isupper():
            return re.sub(r"\s+", " ", n)

    return ""


def extraer_seccion(texto):
    # Formato compact: "SECCION: A" en la misma línea o separado solo por espacio
    m = re.search(r"SECCION:[ \t]*([A-E])\b", texto)
    if m:
        return m.group(1)
    # Formato multi-línea (1-3): letra de sección sola antes de "ALUMNO/A:"
    m = re.search(r"\n([A-E])\s*\nALUMNO/A:", texto)
    if m:
        return m.group(1)
    return ""


def extraer_grado_texto(texto):
    m = re.search(r"GRADO:\s*(\w+\.?)", texto)
    return m.group(1) if m else ""


def extraer_mencion(texto):
    """Extrae la mención artística. Solo acepta valores conocidos."""
    MENC = r"(MÚSICA|TEATRO|MULTIMEDIA|ARTES\s+VISUALES)"

    # Formato 1 (compact 6to pg1+): "MENCIÓN MÚSICA SECCION:"
    m = re.search(r"MENCIÓN\s+" + MENC + r"\s+SECCION:", texto)
    if m:
        return m.group(1).strip()

    # Formato 2 (4to-6to header): "MÚSICA SECCION:" sin etiqueta MENCIÓN
    m = re.search(MENC + r"\s+SECCION:", texto)
    if m:
        return m.group(1).strip()

    # Formato 3 (multi-línea): "MENCIÓN\nMÚSICA"
    m = re.search(r"MENCIÓN\s*\n\s*" + MENC, texto)
    if m:
        return m.group(1).strip()

    return ""


def pc_rows_para_materias(texto, materias):
    """
    Extrae PC1, PC2, PC3, PC4, CF para cada materia buscando por nombre.
    Retorna dict {materia: {p1,p2,p3,p4,promedio,tipo}}
    """
    resultado = {}
    # Valor numérico o placeholder ### (período incompleto)
    NUM = r"([\d.]+|###)"
    for mat in materias:
        pat = re.escape(mat) + r"\s+" + r"\s+".join([NUM] * 5)
        m = re.search(pat, texto)
        if m:
            vals = []
            for x in m.groups():
                vals.append(0.0 if x == "###" else float(x))
            resultado[mat] = {
                "p1":       vals[0],
                "p2":       vals[1],
                "p3":       vals[2],
                "p4":       vals[3],
                "promedio": vals[4],
                "tipo":     "académico",
            }
    return resultado


def pc_tecnico_desde_filas(texto, materias_tec):
    """
    Extrae las filas de PC del componente técnico.
    Las filas aparecen como: '[PC1] [PC2] [PC3] [PC4] [CF]  0' después del separador '0 0 0 0 0 0'
    """
    resultado = {}
    sep_idx = texto.find("0 0 0 0 0 0")
    if sep_idx == -1:
        return resultado

    tec_text = texto[sep_idx + len("0 0 0 0 0 0"):]

    # Extraer líneas con exactamente 5 o 6 números (PC1-PC4-CF [y posible 0 extra])
    filas = []
    for line in tec_text.split("\n"):
        line = line.strip()
        if not line:
            continue
        nums = re.findall(r"\d+(?:\.\d+)?", line)
        # Validar: 5-6 números todos en rango 0-100
        if 5 <= len(nums) <= 7 and all(0 <= float(n) <= 100 for n in nums[:5]):
            filas.append([float(n) for n in nums[:5]])
        if len(filas) >= len(materias_tec):
            break

    for i, mat in enumerate(materias_tec):
        if i < len(filas):
            f = filas[i]
            resultado[mat] = {
                "p1":       f[0],
                "p2":       f[1],
                "p3":       f[2],
                "p4":       f[3],
                "promedio": f[4],
                "tipo":     "técnico",
            }
    return resultado


def parsear_pagina(texto, grado):
    """Parsea el texto de UNA página y devuelve los datos del alumno."""
    datos = {
        "grado":    grado,
        "materias": {},
        "mencion":  "",
        "nombre":   "",
        "seccion":  "",
        "indice":   0,
    }

    datos["indice"]  = extraer_indice(texto)
    datos["nombre"]  = extraer_nombre(texto)
    datos["seccion"] = extraer_seccion(texto)
    datos["mencion"] = extraer_mencion(texto)

    primer_ciclo = grado in ("1ERO", "2DO", "3ERO")
    mats_acad = MATS_1_3 if primer_ciclo else MATS_ACAD_4_6

    # ── Sección PC: el área entre "PC1 PC2 PC3 PC4" y "(P1)" o "(P2)"
    pc_start = texto.find("PC1 PC2 PC3 PC4")
    pc_end   = texto.find("(P1)")
    if pc_start == -1:
        pc_start = texto.find("PC1")
    if pc_end == -1:
        pc_end = len(texto)

    pc_texto = texto[pc_start:pc_end] if pc_start != -1 else ""

    # Extraer materias académicas
    datos["materias"].update(pc_rows_para_materias(pc_texto, mats_acad))

    # Extraer materias técnicas (4to-6to)
    if not primer_ciclo:
        mencion_key = datos["mencion"].upper()
        mats_tec = MATS_TECNICAS.get(mencion_key, {}).get(grado, [])
        if mats_tec:
            tec = pc_tecnico_desde_filas(pc_texto, mats_tec)
            datos["materias"].update(tec)

    return datos


# ── Parsear PDF completo ───────────────────────────────────────────────────────
def parsear_pdf(ruta, grado):
    import pypdf

    log(f"\n{'='*60}")
    log(f"Procesando: {os.path.basename(ruta)} — Grado {grado}")
    log(f"{'='*60}")

    reader = pypdf.PdfReader(ruta)
    total_pgs = len(reader.pages)
    log(f"Páginas: {total_pgs}")

    resultados = []
    primer_ciclo = grado in ("1ERO", "2DO", "3ERO")

    for i, page in enumerate(reader.pages):
        try:
            texto = page.extract_text() or ""
            if not texto.strip():
                continue

            # Verificar que la página tiene datos de un alumno
            if "No." not in texto and "ALUMNO/A" not in texto:
                continue

            datos = parsear_pagina(texto, grado)

            if not datos["nombre"]:
                continue  # saltar páginas sin nombre

            resultados.append(datos)

        except Exception as e:
            log(f"  ⚠ Error en página {i}: {e}")

    log(f"Alumnos parseados: {len(resultados)}")
    return resultados


# ── Matching BD ────────────────────────────────────────────────────────────────
def construir_indice_bd(conn, grado):
    cur = conn.cursor()
    cur.execute(
        "SELECT id, nombre, apellido FROM estudiantes WHERE grado = ?",
        (grado,)
    )
    rows = cur.fetchall()
    indice = {}
    for est_id, nombre, apellido in rows:
        clave = norm(f"{nombre} {apellido}")
        indice.setdefault(clave, []).append(est_id)
    nombres_bd = {r[0]: f"{r[1]} {r[2]}" for r in rows}
    return indice, nombres_bd


def buscar_estudiante(nombre_pdf, indice):
    clave = norm(nombre_pdf)
    if clave in indice:
        return indice[clave][0], 1.0
    mejor = (None, 0.0)
    for k, ids in indice.items():
        s = SequenceMatcher(None, clave, k).ratio()
        if s > mejor[1]:
            mejor = (ids[0], s)
    if mejor[1] >= 0.82:
        return mejor
    return None, mejor[1]


# ── Carga a BD ────────────────────────────────────────────────────────────────
def agregar_columnas_si_faltan(conn):
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(materias_calificaciones)")
    existentes = {r[1] for r in cur.fetchall()}
    extra = {"anio_escolar": "TEXT DEFAULT '2025-2026'"}
    for col, defn in extra.items():
        if col not in existentes:
            cur.execute(f"ALTER TABLE materias_calificaciones ADD COLUMN {col} {defn}")
            log(f"  ✓ Columna añadida: {col}")


def cargar_a_bd(conn, datos, est_id, grado):
    cur = conn.cursor()
    anio = "2025-2026"

    cur.execute("""
        UPDATE estudiantes
        SET mencion = ?, seccion = ?, tiene_notas = 1, ind_academico = ?
        WHERE id = ?
    """, (datos.get("mencion",""), datos.get("seccion",""),
          datos.get("indice", 0), est_id))

    cur.execute(
        "DELETE FROM materias_calificaciones WHERE estudiante_id = ? AND grado = ?",
        (est_id, grado)
    )

    ciclo = "primer_ciclo" if grado in ("1ERO","2DO","3ERO") else "segundo_ciclo"

    for mat, vals in datos.get("materias", {}).items():
        prom = vals.get("promedio", 0)
        if prom == 0:
            ps = [vals.get(f"p{i}",0) for i in range(1,5)]
            ps_v = [p for p in ps if p > 0]
            prom = round(sum(ps_v)/len(ps_v), 1) if ps_v else 0

        cur.execute("""
            INSERT INTO materias_calificaciones
                (estudiante_id, materia, grado, p1, p2, p3, p4,
                 promedio, tipo, ciclo, anio_escolar)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (est_id, mat, grado,
              vals.get("p1",0), vals.get("p2",0),
              vals.get("p3",0), vals.get("p4",0),
              prom, vals.get("tipo","académico"), ciclo, anio))


# ── Main ──────────────────────────────────────────────────────────────────────
PDFS = [
    ("notas/Boletin de calificaciones AC 1er. Grado.pdf", "1ERO"),
    ("notas/Boletin de calificaciones AC 2do. Grado.pdf", "2DO"),
    ("notas/Boletin de calificaciones AC 3er. Grado.pdf", "3ERO"),
    ("notas/Boletin de calificaciones AC 4to. Grado.pdf", "4TO"),
    ("notas/Boletin de calificaciones AC 5to. Grado.pdf", "5TO"),
    ("notas/Boletin de calificaciones AC 6to. Grado.pdf", "6TO"),
]


def main():
    if DRY_RUN:
        log("⚠  MODO DRY-RUN — no se escribe nada en la BD\n")

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")

    if not DRY_RUN:
        agregar_columnas_si_faltan(conn)

    resumen = {
        "cargados":        0,
        "fuzzy":           0,
        "no_encontrados":  [],
        "sin_materias":    0,
        "errores":         [],
    }

    for pdf_rel, grado in PDFS:
        pdf_path = os.path.join(BASE_DIR, pdf_rel)
        if not os.path.exists(pdf_path):
            log(f"\n⚠ PDF no encontrado: {pdf_path}")
            continue

        resultados = parsear_pdf(pdf_path, grado)
        indice_bd, nombres_bd = construir_indice_bd(conn, grado)
        primer_ciclo = grado in ("1ERO","2DO","3ERO")
        n_mats_esperadas = len(MATS_1_3) if primer_ciclo else len(MATS_ACAD_4_6)

        log(f"\nMatching {len(resultados)} alumnos con {len(indice_bd)} en BD…")

        for datos in resultados:
            nombre = datos.get("nombre","").strip()
            if not nombre:
                continue

            est_id, score = buscar_estudiante(nombre, indice_bd)

            if est_id is None:
                resumen["no_encontrados"].append(
                    f"[{grado}] {nombre} (score={score:.2f})"
                )
                continue

            tipo = "exacto" if score == 1.0 else f"fuzzy {score:.2f}"
            if score < 1.0:
                resumen["fuzzy"] += 1
                log(f"  ~ Fuzzy [{tipo}]: '{nombre}' → '{nombres_bd[est_id]}'")

            n_mat = len(datos.get("materias",{}))
            if n_mat < n_mats_esperadas:
                resumen["sin_materias"] += 1
                log(f"  ⚠ Pocas materias ({n_mat}/{n_mats_esperadas}): {nombre}")

            if not DRY_RUN:
                try:
                    cargar_a_bd(conn, datos, est_id, grado)
                    resumen["cargados"] += 1
                except Exception as e:
                    resumen["errores"].append(f"[{grado}] {nombre}: {e}")
                    log(f"  ✗ Error BD: {nombre}: {e}")
            else:
                resumen["cargados"] += 1

        if not DRY_RUN:
            conn.commit()
            log(f"  ✓ Commit {grado}")

    conn.close()

    log("\n" + "="*60)
    log("RESUMEN FINAL")
    log("="*60)
    log(f"✓ Procesados:       {resumen['cargados']}")
    log(f"~ Fuzzy matches:    {resumen['fuzzy']}")
    log(f"⚠ Pocas materias:   {resumen['sin_materias']}")
    log(f"✗ No encontrados:   {len(resumen['no_encontrados'])}")
    log(f"✗ Errores BD:       {len(resumen['errores'])}")

    if resumen["no_encontrados"]:
        log("\nAlumnos sin match en BD:")
        for e in resumen["no_encontrados"]:
            log(f"  - {e}")

    if DRY_RUN:
        log("\n⚠ DRY-RUN — ningún dato fue escrito.")
    else:
        log("\n✅ Carga completada.")


if __name__ == "__main__":
    main()
