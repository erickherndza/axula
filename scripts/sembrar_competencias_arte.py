#!/usr/bin/env python3
"""
Siembra Competencias Específicas (CEs) para todas las menciones de la
Modalidad de Artes del MINERD (Ord. 04-2023) y actualiza el perfil del
docente de MULTIMEDIA.

Uso:
    python3 scripts/sembrar_competencias_arte.py          # dry-run
    python3 scripts/sembrar_competencias_arte.py --commit # escribe en BD
"""
import sys
import sqlite3
import os

DRY_RUN = "--commit" not in sys.argv
DB_PATH = os.environ.get("DATABASE_URL", "").replace("sqlite:///", "") or \
          "/data/database.db" if os.path.exists("/data") else "database.db"

ANIO = "2025-2026"

# ── CEs por materia (4 por materia, uno por período) ─────────────────────────
# Fuente: Ord. 04-2023 / Diseño Curricular Modalidad Artes MINERD
CES = {

    # ── MULTIMEDIA ─────────────────────────────────────────────────────────
    "Fotografía": [
        ("CE1", "Aplica principios de composición y encuadre fotográfico en distintos géneros", 1),
        ("CE2", "Maneja los parámetros de exposición (apertura, velocidad, ISO) en cámara manual", 2),
        ("CE3", "Edita y retoca imágenes con herramientas digitales profesionales", 3),
        ("CE4", "Desarrolla un portafolio fotográfico con proyecto temático personal", 4),
    ],
    "Fotografía I": [
        ("CE1", "Identifica los fundamentos de la fotografía digital y el lenguaje visual", 1),
        ("CE2", "Aplica encuadre, luz natural y modos automáticos en la cámara", 2),
        ("CE3", "Edita imágenes básicas con herramientas de ajuste (brillo, contraste, color)", 3),
        ("CE4", "Construye un mini portafolio de 10 imágenes con propuesta estética propia", 4),
    ],
    "FOTOGRAFÍA": [
        ("CE1", "Aplica principios de composición y encuadre fotográfico en distintos géneros", 1),
        ("CE2", "Maneja los parámetros de exposición (apertura, velocidad, ISO) en cámara manual", 2),
        ("CE3", "Edita y retoca imágenes con herramientas digitales profesionales", 3),
        ("CE4", "Desarrolla un portafolio fotográfico con proyecto temático personal", 4),
    ],
    "Diseño Básico y Expresión Visual": [
        ("CE1", "Aplica los elementos del lenguaje visual (línea, forma, color, textura) con intención expresiva", 1),
        ("CE2", "Crea composiciones visuales usando principios de diseño (equilibrio, contraste, ritmo)", 2),
        ("CE3", "Utiliza técnicas manuales y digitales de representación visual", 3),
        ("CE4", "Desarrolla un proyecto de diseño con identidad visual coherente", 4),
    ],
    "DISEÑO BÁSICO Y EXPRESIÓN VISUAL": [
        ("CE1", "Aplica los elementos del lenguaje visual (línea, forma, color, textura) con intención expresiva", 1),
        ("CE2", "Crea composiciones visuales usando principios de diseño (equilibrio, contraste, ritmo)", 2),
        ("CE3", "Utiliza técnicas manuales y digitales de representación visual", 3),
        ("CE4", "Desarrolla un proyecto de diseño con identidad visual coherente", 4),
    ],
    "Diseño Web": [
        ("CE1", "Estructura páginas web con HTML semántico y CSS básico", 1),
        ("CE2", "Aplica principios de UI/UX en el diseño de interfaces web", 2),
        ("CE3", "Implementa diseño responsivo adaptado a dispositivos móviles", 3),
        ("CE4", "Desarrolla un sitio web funcional como proyecto integrador", 4),
    ],
    "Diseño Gráfico": [
        ("CE1", "Aplica teoría del color y tipografía en el diseño de piezas gráficas", 1),
        ("CE2", "Diseña materiales gráficos para medios impresos y digitales", 2),
        ("CE3", "Crea identidad visual básica (logo, paleta, manual de marca)", 3),
        ("CE4", "Desarrolla una campaña gráfica con coherencia visual y narrativa", 4),
    ],
    "Publicidad y Creatividad": [
        ("CE1", "Analiza estrategias publicitarias y su impacto en distintos públicos", 1),
        ("CE2", "Crea piezas publicitarias para distintos formatos y audiencias", 2),
        ("CE3", "Aplica técnicas creativas en el desarrollo de conceptos de campaña", 3),
        ("CE4", "Desarrolla una campaña publicitaria multimedia con propuesta creativa propia", 4),
    ],
    "Lenguaje Visual, Dibujo y Creación de Personajes": [
        ("CE1", "Aplica el lenguaje visual básico: línea, forma, proporción y perspectiva", 1),
        ("CE2", "Construye personajes originales con anatomía, actitud y expresión definidas", 2),
        ("CE3", "Desarrolla una hoja de modelo (model sheet) de personaje con variaciones", 3),
        ("CE4", "Crea una narrativa visual corta usando los personajes diseñados", 4),
    ],
    "LENGUAJE VISUAL, DIBUJO Y CREACIÓN DE PERSONAJES": [
        ("CE1", "Aplica el lenguaje visual básico: línea, forma, proporción y perspectiva", 1),
        ("CE2", "Construye personajes originales con anatomía, actitud y expresión definidas", 2),
        ("CE3", "Desarrolla una hoja de modelo (model sheet) de personaje con variaciones", 3),
        ("CE4", "Crea una narrativa visual corta usando los personajes diseñados", 4),
    ],

    # ── TEATRO ─────────────────────────────────────────────────────────────
    "Lenguaje Danzario y Teatral": [
        ("CE1", "Reconoce y aplica los elementos básicos del movimiento corporal expresivo", 1),
        ("CE2", "Integra secuencias de movimiento con texto dramático en improvisaciones", 2),
        ("CE3", "Desarrolla una partitura corporal-vocal con intención escénica", 3),
        ("CE4", "Presenta una pieza que integra danza y teatro con propuesta artística propia", 4),
    ],
    "LENGUAJE DANZARIO Y TEATRAL": [
        ("CE1", "Reconoce y aplica los elementos básicos del movimiento corporal expresivo", 1),
        ("CE2", "Integra secuencias de movimiento con texto dramático en improvisaciones", 2),
        ("CE3", "Desarrolla una partitura corporal-vocal con intención escénica", 3),
        ("CE4", "Presenta una pieza que integra danza y teatro con propuesta artística propia", 4),
    ],
    "Expresión Corporal y Técnica Actoral I": [
        ("CE1", "Explora las posibilidades expresivas del cuerpo como instrumento dramático", 1),
        ("CE2", "Aplica técnicas básicas de relajación, respiración y presencia escénica", 2),
        ("CE3", "Realiza improvisaciones estructuradas con conflicto y objetivo claro", 3),
        ("CE4", "Interpreta un personaje en una escena corta con motivación y acción física", 4),
    ],
    "Expresión Corporal y Técnica Actoral II": [
        ("CE1", "Profundiza en el análisis de texto dramático: circunstancias dadas y subtexto", 1),
        ("CE2", "Desarrolla la memoria emotiva y sensorial en escenas de mayor complejidad", 2),
        ("CE3", "Crea un solo teatral con estructura dramática completa", 3),
        ("CE4", "Codirige y actúa en una obra corta presentada ante público", 4),
    ],
    "Técnica Actoral III": [
        ("CE1", "Aplica técnicas de actuación realista y no realista en escenas de repertorio", 1),
        ("CE2", "Desarrolla un proceso de investigación sobre un personaje histórico o literario", 2),
        ("CE3", "Trabaja en un montaje colaborativo con dramaturgia y dirección compartidas", 3),
        ("CE4", "Participa en una producción teatral completa como actor principal o de reparto", 4),
    ],
    "Dramaturgia": [
        ("CE1", "Analiza textos dramáticos identificando estructura, conflicto y personajes", 1),
        ("CE2", "Escribe escenas cortas aplicando los principios de dramaturgia contemporánea", 2),
        ("CE3", "Desarrolla un guión teatral breve con estructura en tres actos", 3),
        ("CE4", "Presenta la lectura dramatizada de su obra ante el grupo", 4),
    ],
    "Puesta en Escena I": [
        ("CE1", "Identifica los elementos de la puesta en escena: espacio, luz, sonido, vestuario", 1),
        ("CE2", "Analiza una producción teatral aplicando criterios de puesta en escena", 2),
        ("CE3", "Diseña la propuesta visual y espacial de una escena corta", 3),
        ("CE4", "Coordina y presenta una puesta en escena básica con elementos integrados", 4),
    ],
    "Puesta en Escena III": [
        ("CE1", "Dirige ensayos con criterio artístico y organización de tiempo escénico", 1),
        ("CE2", "Integra todos los elementos escénicos en un montaje de mediana complejidad", 2),
        ("CE3", "Resuelve problemas de producción durante el proceso de montaje", 3),
        ("CE4", "Dirige y presenta una producción teatral completa ante público", 4),
    ],
    "Historia del Teatro Universal y Dominicano I": [
        ("CE1", "Identifica los períodos y estilos del teatro desde la Antigüedad al Barroco", 1),
        ("CE2", "Analiza obras representativas y su contexto histórico-cultural", 2),
        ("CE3", "Relaciona el teatro dominicano con las corrientes universales", 3),
        ("CE4", "Presenta un trabajo investigativo sobre un movimiento teatral o dramaturgo", 4),
    ],
    "Historia del Teatro Contemporáneo": [
        ("CE1", "Estudia los movimientos teatrales del siglo XX: Brecht, Grotowski, Artaud", 1),
        ("CE2", "Analiza tendencias del teatro latinoamericano y caribeño contemporáneo", 2),
        ("CE3", "Asiste y analiza críticamente una producción teatral contemporánea", 3),
        ("CE4", "Desarrolla un ensayo crítico sobre el teatro dominicano actual", 4),
    ],
    "Diseño de Escenografía y Vestuario": [
        ("CE1", "Aplica principios de diseño visual al espacio escénico y el vestuario", 1),
        ("CE2", "Crea bocetos de escenografía y vestuario para una obra específica", 2),
        ("CE3", "Construye maquetas o prototipos de los elementos diseñados", 3),
        ("CE4", "Diseña y ejecuta el vestuario y/o escenografía de una producción real", 4),
    ],
    "Dirección Teatral": [
        ("CE1", "Analiza el texto dramático desde la perspectiva del director", 1),
        ("CE2", "Desarrolla una propuesta de puesta en escena con concepto artístico claro", 2),
        ("CE3", "Dirige ensayos aplicando metodologías de trabajo con actores", 3),
        ("CE4", "Presenta una producción teatral dirigida con coherencia artística y técnica", 4),
    ],

    # ── MÚSICA ─────────────────────────────────────────────────────────────
    "Instrumento I": [
        ("CE1", "Desarrolla postura, digitación y lectura básica en el instrumento asignado", 1),
        ("CE2", "Interpreta piezas de nivel inicial con precisión rítmica y afinación", 2),
        ("CE3", "Aplica dinámica y fraseo en repertorio de nivel elemental", 3),
        ("CE4", "Ejecuta un recital de nivel I con repertorio variado y presentación escénica", 4),
    ],
    "Instrumento II": [
        ("CE1", "Amplía el rango técnico con escalas, arpegios y estudios de nivel intermedio", 1),
        ("CE2", "Interpreta obras de mayor complejidad con articulación y expresión musical", 2),
        ("CE3", "Trabaja repertorio de distintos estilos y períodos históricos", 3),
        ("CE4", "Presenta un recital de nivel II con conciencia interpretativa y escénica", 4),
    ],
    "Instrumento III": [
        ("CE1", "Domina técnicas avanzadas específicas del instrumento (virtuosismo, ornamentación)", 1),
        ("CE2", "Interpreta obras del repertorio académico con rigor estilístico", 2),
        ("CE3", "Desarrolla capacidad de acompañamiento y música de cámara", 3),
        ("CE4", "Ejecuta un recital de graduación con repertorio de nivel avanzado", 4),
    ],
    "INSTRUMENTO II": [
        ("CE1", "Amplía el rango técnico con escalas, arpegios y estudios de nivel intermedio", 1),
        ("CE2", "Interpreta obras de mayor complejidad con articulación y expresión musical", 2),
        ("CE3", "Trabaja repertorio de distintos estilos y períodos históricos", 3),
        ("CE4", "Presenta un recital de nivel II con conciencia interpretativa y escénica", 4),
    ],
    "INSTRUMENTO III": [
        ("CE1", "Domina técnicas avanzadas específicas del instrumento", 1),
        ("CE2", "Interpreta obras del repertorio académico con rigor estilístico", 2),
        ("CE3", "Desarrolla capacidad de acompañamiento y música de cámara", 3),
        ("CE4", "Ejecuta un recital de graduación con repertorio de nivel avanzado", 4),
    ],
    "Canto Coral I": [
        ("CE1", "Desarrolla técnica vocal básica: respiración, postura y emisión", 1),
        ("CE2", "Afina y blenda su voz dentro del conjunto coral", 2),
        ("CE3", "Interpreta repertorio coral a dos voces con dinámica y fraseo", 3),
        ("CE4", "Participa en un concierto coral con presentación y disciplina escénica", 4),
    ],
    "Canto Coral III": [
        ("CE1", "Interpreta repertorio coral a cuatro voces o más con independencia vocal", 1),
        ("CE2", "Aplica técnicas avanzadas de blend, afinación y balance coral", 2),
        ("CE3", "Trabaja repertorio de distintos períodos y géneros corales", 3),
        ("CE4", "Participa como sección líder en concierto final del año escolar", 4),
    ],
    "CANTO CORAL I": [
        ("CE1", "Desarrolla técnica vocal básica: respiración, postura y emisión", 1),
        ("CE2", "Afina y blenda su voz dentro del conjunto coral", 2),
        ("CE3", "Interpreta repertorio coral a dos voces con dinámica y fraseo", 3),
        ("CE4", "Participa en un concierto coral con presentación y disciplina escénica", 4),
    ],
    "CANTO CORAL II": [
        ("CE1", "Desarrolla la lectura a vista coral y el solfeo aplicado al canto", 1),
        ("CE2", "Interpreta repertorio coral a tres voces con control dinámico", 2),
        ("CE3", "Trabaja la expresión y fraseo en obras de distintos estilos", 3),
        ("CE4", "Actúa como guía de sección en la presentación coral del período", 4),
    ],
    "CANTO CORAL III": [
        ("CE1", "Interpreta repertorio coral a cuatro voces o más con independencia vocal", 1),
        ("CE2", "Aplica técnicas avanzadas de blend, afinación y balance coral", 2),
        ("CE3", "Trabaja repertorio de distintos períodos y géneros corales", 3),
        ("CE4", "Participa como sección líder en concierto final del año escolar", 4),
    ],
    "Práctica Instrumental Grupal I": [
        ("CE1", "Integra habilidades individuales al trabajo en conjunto instrumental", 1),
        ("CE2", "Aplica escucha activa, balance y blend en el ensamble", 2),
        ("CE3", "Interpreta repertorio grupal de nivel I con precisión rítmica y afinación", 3),
        ("CE4", "Participa en concierto de ensamble con presentación escénica profesional", 4),
    ],
    "Práctica Instrumental Grupal III": [
        ("CE1", "Lidera secciones del ensamble con criterio musical y cohesión grupal", 1),
        ("CE2", "Interpreta repertorio avanzado en distintos formatos (dúo, trío, cuarteto)", 2),
        ("CE3", "Adapta y arregla piezas para el ensamble disponible", 3),
        ("CE4", "Dirige y/o protagoniza el concierto grupal de final de año", 4),
    ],
    "PRÀCTICA INSTRUMENTAL GRUPAL II": [
        ("CE1", "Desarrolla la lectura conjunta y el seguimiento del director en el ensamble", 1),
        ("CE2", "Interpreta repertorio de nivel II con expresión y equilibrio grupal", 2),
        ("CE3", "Trabaja diferentes géneros musicales en formación de conjunto", 3),
        ("CE4", "Actúa en concierto de ensamble representando el trabajo del período", 4),
    ],
    "Lenguaje Musical": [
        ("CE1", "Lee y escribe notación musical: figuras, compases y alteraciones básicas", 1),
        ("CE2", "Desarrolla el dictado rítmico y melódico en tonalidades mayores y menores", 2),
        ("CE3", "Aplica escalas, intervalos y acordes básicos en el análisis musical", 3),
        ("CE4", "Realiza ejercicios de solfeo y dictado de nivel intermedio con precisión", 4),
    ],
    "LENGUAJE MUSICAL": [
        ("CE1", "Lee y escribe notación musical: figuras, compases y alteraciones básicas", 1),
        ("CE2", "Desarrolla el dictado rítmico y melódico en tonalidades mayores y menores", 2),
        ("CE3", "Aplica escalas, intervalos y acordes básicos en el análisis musical", 3),
        ("CE4", "Realiza ejercicios de solfeo y dictado de nivel intermedio con precisión", 4),
    ],
    "Armonía I": [
        ("CE1", "Construye acordes triadas y sus inversiones en tonalidades mayores y menores", 1),
        ("CE2", "Aplica los principios de enlace armónico (voz líder, movimiento contrario)", 2),
        ("CE3", "Analiza progresiones armónicas en obras del repertorio tonal", 3),
        ("CE4", "Compone una pieza breve aplicando los principios de armonía tonal básica", 4),
    ],
    "Armonía II": [
        ("CE1", "Trabaja acordes de séptima, dominante secundaria y modulación", 1),
        ("CE2", "Analiza armonía cromática en obras del período romántico y moderno", 2),
        ("CE3", "Armoniza melodías dadas con progresiones de mayor complejidad", 3),
        ("CE4", "Compone o arregla una pieza que incorpore recursos armónicos avanzados", 4),
    ],
    "ARMONIA I": [
        ("CE1", "Construye acordes triadas y sus inversiones en tonalidades mayores y menores", 1),
        ("CE2", "Aplica los principios de enlace armónico (voz líder, movimiento contrario)", 2),
        ("CE3", "Analiza progresiones armónicas en obras del repertorio tonal", 3),
        ("CE4", "Compone una pieza breve aplicando los principios de armonía tonal básica", 4),
    ],
    "ARMONIA II": [
        ("CE1", "Trabaja acordes de séptima, dominante secundaria y modulación", 1),
        ("CE2", "Analiza armonía cromática en obras del período romántico y moderno", 2),
        ("CE3", "Armoniza melodías dadas con progresiones de mayor complejidad", 3),
        ("CE4", "Compone o arregla una pieza que incorpore recursos armónicos avanzados", 4),
    ],
    "Historia de las Formas Musicales": [
        ("CE1", "Identifica y analiza las grandes formas musicales: sonata, fuga, suite, sinfonía", 1),
        ("CE2", "Estudia la evolución de las formas musicales desde el Barroco al Romanticismo", 2),
        ("CE3", "Analiza obras representativas de cada período con escucha activa guiada", 3),
        ("CE4", "Presenta un trabajo investigativo sobre una forma musical o compositor", 4),
    ],
    "Tecnología Musical": [
        ("CE1", "Maneja software de notación musical (MuseScore / Sibelius básico)", 1),
        ("CE2", "Produce y edita audio básico con herramientas DAW (GarageBand / Audacity)", 2),
        ("CE3", "Crea un arreglo o composición usando recursos digitales", 3),
        ("CE4", "Desarrolla un proyecto multimedia que integre música y tecnología", 4),
    ],
    "Dirección de Grupos Musicales": [
        ("CE1", "Aplica técnica de batuta: preparación, ictus, finales y cambios de tempo", 1),
        ("CE2", "Dirige ensambles pequeños con control de balance y expresión musical", 2),
        ("CE3", "Desarrolla el análisis de partituras desde la perspectiva del director", 3),
        ("CE4", "Dirige un ensayo y/o concierto del grupo como director principal", 4),
    ],
    "TEORIA Y ENTRENAMIENTO MUSICAL I": [
        ("CE1", "Domina lectura rítmica y melódica básica en clave de Sol y Fa", 1),
        ("CE2", "Desarrolla el oído relativo y el dictado melódico en escala mayor", 2),
        ("CE3", "Aplica los rudimentos de la armonía (triadas y funciones básicas)", 3),
        ("CE4", "Ejecuta ejercicios de solfeo y dictado con autonomía", 4),
    ],

    # ── ARTES VISUALES ─────────────────────────────────────────────────────
    "Lenguaje Visual y Principios del Diseño Artesanal": [
        ("CE1", "Aplica los elementos del lenguaje visual en composiciones bidimensionales", 1),
        ("CE2", "Desarrolla técnicas artesanales tradicionales y contemporáneas dominicanas", 2),
        ("CE3", "Crea piezas artesanales integrando diseño, función y estética", 3),
        ("CE4", "Desarrolla un proyecto artesanal con identidad cultural y propuesta estética", 4),
    ],
    "Lenguaje Visual y Principios del Diseño": [
        ("CE1", "Domina los principios del diseño: equilibrio, proporción, ritmo y énfasis", 1),
        ("CE2", "Crea composiciones visuales en distintos soportes y técnicas", 2),
        ("CE3", "Aplica teoría del color y psicología del color en sus producciones", 3),
        ("CE4", "Desarrolla un proyecto visual con concepto, proceso y presentación final", 4),
    ],
    "LENGUAJE VISUAL Y PRRINCIPIOS DEL DISEÑO ARTESANAL": [
        ("CE1", "Aplica los elementos del lenguaje visual en composiciones bidimensionales", 1),
        ("CE2", "Desarrolla técnicas artesanales tradicionales y contemporáneas dominicanas", 2),
        ("CE3", "Crea piezas artesanales integrando diseño, función y estética", 3),
        ("CE4", "Desarrolla un proyecto artesanal con identidad cultural y propuesta estética", 4),
    ],
    "Historia del Arte Universal y Dominicano": [
        ("CE1", "Estudia las manifestaciones artísticas desde la Prehistoria hasta el Renacimiento", 1),
        ("CE2", "Analiza el arte moderno y contemporáneo en contexto histórico-social", 2),
        ("CE3", "Identifica las corrientes y figuras del arte dominicano y caribeño", 3),
        ("CE4", "Desarrolla un ensayo crítico o proyecto visual inspirado en un movimiento estudiado", 4),
    ],
    "Introducción a la Historia del Arte universal y Dominicano": [
        ("CE1", "Reconoce las manifestaciones artísticas básicas de las civilizaciones antiguas", 1),
        ("CE2", "Estudia el arte medieval, renacentista y barroco con análisis de obras clave", 2),
        ("CE3", "Identifica los movimientos modernos: Impresionismo, Cubismo, Surrealismo", 3),
        ("CE4", "Analiza el arte dominicano contemporáneo y su relación con el arte universal", 4),
    ],
    "PRINCIPIOS DEL DIBUJO, PINTURA Y CREATIVIDAD": [
        ("CE1", "Aplica los fundamentos del dibujo: proporción, perspectiva y claroscuro", 1),
        ("CE2", "Explora técnicas de pintura básicas: acrílico, acuarela y témpera", 2),
        ("CE3", "Desarrolla la creatividad a través de procesos de experimentación visual", 3),
        ("CE4", "Crea una serie de obras con concepto artístico propio y presentación crítica", 4),
    ],
    "DIBUJO TÉCNICO": [
        ("CE1", "Aplica instrumentos de dibujo técnico: escuadra, compás, escalímetro", 1),
        ("CE2", "Realiza proyecciones ortogonales y vistas técnicas básicas", 2),
        ("CE3", "Desarrolla planos de objetos simples con acotación normalizada", 3),
        ("CE4", "Ejecuta un proyecto de diseño técnico aplicado a un objeto o espacio", 4),
    ],
}


def main():
    if not os.path.exists(DB_PATH):
        # Fallback para local
        alt = "database.db"
        if os.path.exists(alt):
            db = alt
        else:
            print(f"ERROR: No se encontró la base de datos en {DB_PATH}")
            sys.exit(1)
    else:
        db = DB_PATH

    conn = sqlite3.connect(db, timeout=15)
    conn.row_factory = sqlite3.Row
    total = 0

    # ── 1. Actualizar perfil de Erick (id=3) ─────────────────────────────
    materias_erick = (
        "Fotografía|Diseño Básico y Expresión Visual|"
        "Diseño Web|Diseño Gráfico|Publicidad y Creatividad"
    )
    erick = conn.execute(
        "SELECT id, username, grado, mencion, materia FROM usuarios WHERE nombre='Erick Hernandez' AND rol='profesor'"
    ).fetchone()
    if erick:
        print(f"Perfil encontrado: id={erick['id']} usuario={erick['username']}")
        print(f"  Antes → grado={erick['grado']} mencion={erick['mencion']}")
        if not DRY_RUN:
            conn.execute("""
                UPDATE usuarios SET
                    grado='4to,5to', mencion='MULTIMEDIA',
                    materia=?, tipo_docencia='tecnica'
                WHERE id=?
            """, (materias_erick, erick["id"]))
        print(f"  Después → grado=4to,5to mencion=MULTIMEDIA materia={materias_erick}")
    else:
        print("ADVERTENCIA: Usuario 'Erick Hernandez' profesor no encontrado")

    # ── 2. Sembrar competencias ───────────────────────────────────────────
    for materia, ces in CES.items():
        for numero, descripcion, periodo in ces:
            exists = conn.execute(
                "SELECT 1 FROM competencias_materia WHERE materia=? AND numero=? AND anio_escolar=?",
                (materia, numero, ANIO)
            ).fetchone()
            if exists:
                print(f"  SKIP  {materia[:45]:<45} {numero}")
                continue
            print(f"  {'DRY ' if DRY_RUN else 'INS '} {materia[:45]:<45} {numero} P{periodo}")
            if not DRY_RUN:
                conn.execute("""
                    INSERT INTO competencias_materia
                        (materia, numero, descripcion, periodo_eval, anio_escolar, activa)
                    VALUES (?, ?, ?, ?, ?, 1)
                """, (materia, numero, descripcion, periodo, ANIO))
            total += 1

    if not DRY_RUN:
        conn.commit()
        print(f"\n✓ {total} competencias insertadas. Perfil Erick actualizado.")
    else:
        print(f"\nDRY-RUN — {total} filas se insertarían. Agrega --commit para ejecutar.")

    conn.close()


if __name__ == "__main__":
    main()
