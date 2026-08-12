/**
 * generar_planificacion_abp.js
 * Genera el .docx oficial MINERD para planificaciones ABP
 * C.E. Benito Juárez — Modalidad en Artes
 *
 * USO: node generar_planificacion_abp.js <json_data_file> <output_file>
 *
 * Referencia: Guía Técnica MINERD/DEMA v1.0 — Marzo 2026
 * Especificaciones:
 *   - Landscape US Letter (11×8.5")
 *   - Márgenes 0.5" = 720 DXA
 *   - Ancho contenido = 14,400 DXA
 *   - Fuente: Arial 9pt
 *   - ShadingType.CLEAR siempre (nunca SOLID)
 */

const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, PageOrientation, BorderStyle, WidthType, ShadingType,
  VerticalAlign, HeadingLevel
} = require('docx');
const fs = require('fs');

// ── PALETA OFICIAL ─────────────────────────────────────────────────────────
const C = {
  DARK_BLUE:  '1F4E79',   // Títulos de sección — texto blanco
  MID_BLUE:   '2E75B6',   // Títulos de instrumentos
  LIGHT_BLUE: 'BDD7EE',   // Headers de columna
  PHASE_BLUE: 'D6E4F0',   // Columna Fases ABP
  WHITE:      'FFFFFF',   // Celdas de contenido
  GRAY:       'F2F2F2',   // Fondo alternativo
  AMBER:      'BF8F00',   // Label Inicio fase 1
  BLACK:      '000000',
};

// ── ANCHOS POR BLOQUE (DXA) — suman 14,400 ────────────────────────────────
const W = {
  // Bloque 1 — IDENTIFICACIÓN: 8 cols
  ID: [1500, 2800, 900, 1200, 1200, 2200, 1200, 3400],
  // Bloque 2 — ELEMENTOS: 6 cols (CF va en fila fusionada aparte)
  EL: [2400, 2400, 2400, 3000, 2100, 2100],
  // Bloque 3 — FASES ABP: 8 cols (sin Competencias Fundamentales)
  FA: [2000, 1100, 3400, 2000, 1800, 1800, 1200, 1100],
  // Total
  TOTAL: 14400,
};

// ── HELPERS ────────────────────────────────────────────────────────────────
const borde = { style: BorderStyle.SINGLE, size: 4, color: C.DARK_BLUE };
const bordes = { top: borde, bottom: borde, left: borde, right: borde };
const bordeFino = { style: BorderStyle.SINGLE, size: 2, color: 'AAAAAA' };
const bordesFinos = { top: bordeFino, bottom: bordeFino, left: bordeFino, right: bordeFino };

function run(text, opts = {}) {
  return new TextRun({
    text: String(text || ''),
    font: 'Arial',
    size: opts.size || 18,         // 9pt = 18 half-points
    bold: opts.bold || false,
    color: opts.color || C.BLACK,
    italics: opts.italics || false,
  });
}

function para(children, opts = {}) {
  return new Paragraph({
    alignment: opts.align || AlignmentType.LEFT,
    spacing: { before: opts.before || 20, after: opts.after || 20 },
    children: Array.isArray(children) ? children : [children],
  });
}

function celda(children, bgColor, widthDxa, opts = {}) {
  return new TableCell({
    borders: opts.fino ? bordesFinos : bordes,
    width: { size: widthDxa, type: WidthType.DXA },
    shading: { fill: bgColor, type: ShadingType.CLEAR },
    verticalAlign: opts.vAlign || VerticalAlign.TOP,
    columnSpan: opts.span || 1,
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: Array.isArray(children) ? children : [children],
  });
}

function celdaHdr(texto, widthDxa, bgColor = C.DARK_BLUE, txtColor = C.WHITE) {
  return celda(
    para(run(texto, { bold: true, size: 16, color: txtColor }), { align: AlignmentType.CENTER }),
    bgColor, widthDxa
  );
}

function celdaLbl(texto, widthDxa) {
  return celda(
    para(run(texto, { bold: true, size: 16, color: C.BLACK })),
    C.LIGHT_BLUE, widthDxa
  );
}

function celdaVal(texto, widthDxa, opts = {}) {
  const lines = Array.isArray(texto) ? texto : [texto];
  return celda(
    lines.map((l, i) => para(run(l, { size: 17 }), {
      before: i === 0 ? 30 : 0, after: i === lines.length - 1 ? 30 : 0
    })),
    C.WHITE, widthDxa, opts
  );
}

function fila(...celdas) {
  return new TableRow({ children: celdas });
}

function tabla(columnWidths, rows) {
  return new Table({
    width: { size: W.TOTAL, type: WidthType.DXA },
    columnWidths,
    rows,
    margins: { top: 0, bottom: 0 },
  });
}

// Lista con viñeta simple
function listaItem(texto, nivel = 0) {
  const indent = nivel * 200;
  return para([
    run(`• ${texto}`, { size: 16 })
  ], { before: 10, after: 10 });
}

// ── BLOQUE 0 — ENCABEZADO INSTITUCIONAL ──────────────────────────────────
function bloque0() {
  return tabla([W.TOTAL], [
    fila(
      celda([
        para(run(
          'ESQUEMA DE PLANIFICACIÓN MODALIDAD EN ARTES / METODOLOGÍAS: ABP/ABPR/STEAM',
          { bold: true, size: 20, color: C.WHITE }
        ), { align: AlignmentType.CENTER }),
      ], C.DARK_BLUE, W.TOTAL)
    ),
    fila(
      celda([
        para([
          run('Viceministerio de Servicios Técnicos Pedagógicos', { size: 15, bold: true }),
        ], { align: AlignmentType.CENTER, before: 30, after: 10 }),
        para([
          run('Dirección de Educación Secundaria / Departamento de Educación Secundaria Modalidad en Artes', { size: 14 }),
        ], { align: AlignmentType.CENTER, before: 0, after: 30 }),
      ], C.WHITE, W.TOTAL)
    ),
  ]);
}

// ── BLOQUE 1 — IDENTIFICACIÓN ──────────────────────────────────────────────
function bloque1(d) {
  const prof = d.docente;
  const proy = d.proyecto;

  return tabla(W.ID, [
    // Título sección
    fila(celda(
      para(run('IDENTIFICACIÓN', { bold: true, size: 17, color: C.WHITE })),
      C.DARK_BLUE, W.TOTAL, { span: W.ID.length }
    )),
    // Fila 1: Centro | val | Mención | val | Asignatura | val | Docente | val
    fila(
      celdaLbl('Centro Educativo:', W.ID[0]),
      celdaVal(prof.centro || 'Centro Educativo en Artes Benito Juárez', W.ID[1]),
      celdaLbl('Mención:', W.ID[2]),
      celdaVal(prof.mencion || 'Multimedia', W.ID[3]),
      celdaLbl('Asignatura:', W.ID[4]),
      celdaVal(prof.asignatura || '', W.ID[5]),
      celdaLbl('Docente:', W.ID[6]),
      celdaVal(prof.nombre_completo || '', W.ID[7]),
    ),
    // Fila 2: Grado | val | Período/Fechas | val | Metodología | val | Duración | val
    fila(
      celdaLbl('Grado:', W.ID[0]),
      celdaVal(prof.grado || '4to Multimedia', W.ID[1]),
      celdaLbl('Inicio:', W.ID[2]),
      celdaVal(proy.fecha_inicio || '', W.ID[3]),
      celdaLbl('Cierre:', W.ID[4]),
      celdaVal(proy.fecha_cierre || '', W.ID[5]),
      celdaLbl('Metodología:', W.ID[6]),
      celdaVal('ABP', W.ID[7]),
    ),
    // Fila 3: Título del proyecto | val (span 5) | Duración | val
    fila(
      celdaLbl('Título del proyecto:', W.ID[0]),
      celda(
        para([run(`"${proy.titulo || ''}"`, { bold: true, size: 17 })]),
        C.WHITE, W.ID[1] + W.ID[2] + W.ID[3] + W.ID[4] + W.ID[5], { span: 5 }
      ),
      celdaLbl('Duración:', W.ID[6]),
      celdaVal(proy.duracion || '', W.ID[7]),
    ),
    // Fila 4: Producto final | val (span 7)
    fila(
      celdaLbl('Producto final:', W.ID[0]),
      celda(
        para(run(proy.producto_final || '', { size: 16 })),
        C.WHITE, W.ID.slice(1).reduce((a,b)=>a+b,0), { span: 7 }
      ),
    ),
  ]);
}

// ── BLOQUE 2 — ELEMENTOS DE LA UNIDAD ──────────────────────────────────────
function bloque2(d) {
  const cur = d.curriculo;

  // Competencias Fundamentales — fila fusionada ancho completo
  const competenciasUnicas = [...new Set(cur.competencias_fundamentales || [])];
  const competencias = competenciasUnicas.map(c =>
    para(run(`✓  ${c}`, { size: 16 }), { before: 15, after: 10 })
  );

  // Contenidos con sub-tipos
  const contenidos = [
    para(run('Conceptuales:', { bold: true, size: 16 }), { before: 20 }),
    ...(cur.contenidos?.conceptuales || []).map(c => listaItem(c)),
    para(run('Procedimentales:', { bold: true, size: 16 }), { before: 15 }),
    ...(cur.contenidos?.procedimentales || []).map(c => listaItem(c)),
    para(run('Actitudinales:', { bold: true, size: 16 }), { before: 15 }),
    ...(cur.contenidos?.actitudinales || []).map(c => listaItem(c)),
  ];

  // RAE
  const raeItems = Array.isArray(cur.rae) ? cur.rae : [];
  const rae = raeItems.length
    ? raeItems.map((r, i) => para(run(`${i+1}. ${r}`, { size: 16 }), { before: 15, after: 10 }))
    : [
        para(run(cur.rae_codigo || '', { bold: true, size: 16, color: C.MID_BLUE })),
        para(run(cur.rae_nombre || '', { bold: true, size: 16 })),
        para(run(cur.rae_descripcion || '', { size: 16 }), { before: 20 }),
      ];

  // Elemento de la competencia
  const elementos = (cur.elementos_competencia || []).map(e => listaItem(e));
  if (!elementos.length && cur.rae_descripcion) {
    elementos.push(para(run(cur.rae_descripcion, { size: 16 })));
  }

  // Competencias específicas (Laborales profesionales)
  const compEsp = (cur.competencias_especificas || cur.competencias_laborales || []).map(c => listaItem(c));
  if (!compEsp.length) {
    // fallback: reutilizar elementos_competencia si no hay campo específico
    (cur.elementos_competencia || []).forEach(e => compEsp.push(listaItem(e)));
  }

  return tabla(W.EL, [
    // Título sección
    fila(celda(
      para(run('ELEMENTOS DE LA UNIDAD', { bold: true, size: 17, color: C.WHITE })),
      C.DARK_BLUE, W.TOTAL, { span: 6 }
    )),
    // Fila fusionada: Competencias Fundamentales (header + contenido)
    fila(celda(
      para(run('Competencias Fundamentales', { bold: true, size: 16, color: C.BLACK }), { align: AlignmentType.CENTER }),
      C.LIGHT_BLUE, W.TOTAL, { span: 6 }
    )),
    fila(celda(
      competencias.length ? competencias : [para(run('—'))],
      C.WHITE, W.TOTAL, { span: 6 }
    )),
    // Encabezados 6 columnas
    fila(
      celdaHdr('Competencias específicas\n(Laborales profesionales)', W.EL[0], C.LIGHT_BLUE, C.BLACK),
      celdaHdr('Elemento de la\ncompetencia', W.EL[1], C.LIGHT_BLUE, C.BLACK),
      celdaHdr('RAE\n(Resultado de Aprendizaje Esperado)', W.EL[2], C.LIGHT_BLUE, C.BLACK),
      celdaHdr('Contenidos\n(Conceptuales, procedimentales, actitudinales)', W.EL[3], C.LIGHT_BLUE, C.BLACK),
      celdaHdr('Problema a resolver', W.EL[4], C.LIGHT_BLUE, C.BLACK),
      celdaHdr('Pregunta desafiante', W.EL[5], C.LIGHT_BLUE, C.BLACK),
    ),
    // Datos
    fila(
      celda(compEsp.length ? compEsp : [para(run('—'))], C.WHITE, W.EL[0]),
      celda(elementos.length ? elementos : [para(run('—'))], C.WHITE, W.EL[1]),
      celda(rae, C.WHITE, W.EL[2]),
      celda(contenidos, C.WHITE, W.EL[3]),
      celda([para(run(cur.problema || '', { size: 16, italics: true }), { before: 20, after: 20 })], C.WHITE, W.EL[4]),
      celda([para(run(cur.pregunta || '', { size: 16, italics: true, color: C.MID_BLUE }), { before: 20 })], C.WHITE, W.EL[5]),
    ),
  ]);
}

// ── BLOQUE 3 — FASES ABP ──────────────────────────────────────────────────
function bloque3(d) {
  const fases = d.fases || [];
  const nombres = [
    '1. Exploración e\nInvestigación',
    '2. Diseño y\nPlanificación',
    '3. Desarrollo y\nConstrucción',
    '4. Presentación\ny Evaluación',
  ];

  const filaHdr = fila(
    celdaHdr('*Fases del ABP/ABPr', W.FA[0], C.DARK_BLUE),
    celdaHdr('Tiempo\naproximado', W.FA[1], C.LIGHT_BLUE, C.BLACK),
    celdaHdr('Actividades', W.FA[2], C.LIGHT_BLUE, C.BLACK),
    celdaHdr('Integración STEAM\n(Ciencia, Tecnología, Ingeniería, Artes, Matemática)', W.FA[3], C.LIGHT_BLUE, C.BLACK),
    celdaHdr('Rol del\nDocente', W.FA[4], C.LIGHT_BLUE, C.BLACK),
    celdaHdr('Rol del\nestudiante', W.FA[5], C.LIGHT_BLUE, C.BLACK),
    celdaHdr('Recursos', W.FA[6], C.LIGHT_BLUE, C.BLACK),
    celdaHdr('Técnicas e Instrumentos\nde Evaluación', W.FA[7], C.LIGHT_BLUE, C.BLACK),
  );

  const filasData = fases.map((f, i) => {
    const nom = nombres[i] || `Fase ${i+1}`;

    // Actividades: soporta formato nuevo (inicio/desarrollo/cierre) y legacy (actividades plano)
    const activ = [];
    if (f.actividades_inicio && f.actividades_inicio.length) {
      activ.push(para(run('Inicio:', { bold: true, size: 16, color: C.AMBER }), { before: 10 }));
      f.actividades_inicio.forEach(a => activ.push(listaItem(a)));
    }
    if (f.actividades_desarrollo && f.actividades_desarrollo.length) {
      activ.push(para(run('Desarrollo:', { bold: true, size: 16, color: C.AMBER }), { before: 10 }));
      f.actividades_desarrollo.forEach(a => activ.push(listaItem(a)));
    }
    if (f.actividades_cierre && f.actividades_cierre.length) {
      activ.push(para(run('Cierre:', { bold: true, size: 16, color: C.AMBER }), { before: 10 }));
      f.actividades_cierre.forEach(a => activ.push(listaItem(a)));
    }
    // Fallback a formato legacy
    if (!activ.length && f.actividades) {
      f.actividades.forEach(a => activ.push(listaItem(a)));
    }

    // STEAM: soporta formato objeto nuevo {ciencia, tecnologia, ingenieria, arte, matematica}
    // y formato legacy (array de strings)
    const steam = [];
    if (f.steam && typeof f.steam === 'object' && !Array.isArray(f.steam)) {
      const steamMap = [
        ['Ciencia', f.steam.ciencia],
        ['Tecnología', f.steam.tecnologia],
        ['Ingeniería', f.steam.ingenieria],
        ['Arte', f.steam.arte],
        ['Matemática', f.steam.matematica],
      ];
      steamMap.forEach(([label, val]) => {
        if (val) {
          steam.push(para([
            run(`${label}: `, { bold: true, size: 16, color: C.MID_BLUE }),
            run(val, { size: 16 })
          ], { before: 10, after: 6 }));
        }
      });
    } else if (Array.isArray(f.steam)) {
      f.steam.forEach(s => steam.push(listaItem(s)));
    }

    const docente = (f.rol_docente || []).map(r => listaItem(r));
    const estud = (f.rol_estudiante || []).map(r => listaItem(r));
    const recur = (f.recursos || []).map(r => listaItem(r));

    // Evaluación: soporta instrumentos_evaluacion (nuevo) y evaluacion (legacy)
    const evaluaItems = f.instrumentos_evaluacion || f.evaluacion || [];
    const evalua = evaluaItems.map(e => listaItem(e));

    return fila(
      celda([
        para(run(nom, { bold: true, size: 16, color: C.DARK_BLUE }), { align: AlignmentType.CENTER }),
        para(run(`Tiempo: ${f.tiempo || ''}`, { size: 15, color: '555555' }), { align: AlignmentType.CENTER }),
      ], C.PHASE_BLUE, W.FA[0]),
      celda([para(run(f.tiempo || '', { size: 16 }))], C.WHITE, W.FA[1]),
      celda(activ.length ? activ : [para(run(f.actividad_central || ''))], C.WHITE, W.FA[2]),
      celda(steam.length ? steam : [para(run('—'))], C.WHITE, W.FA[3]),
      celda(docente.length ? docente : [para(run('—'))], C.WHITE, W.FA[4]),
      celda(estud.length ? estud : [para(run('—'))], C.WHITE, W.FA[5]),
      celda(recur.length ? recur : [para(run('—'))], C.WHITE, W.FA[6]),
      celda(evalua.length ? evalua : [para(run('—'))], C.WHITE, W.FA[7]),
    );
  });

  // Completar hasta 4 fases si faltan
  while (filasData.length < 4) {
    const i = filasData.length;
    filasData.push(fila(
      celda([para(run(nombres[i], { bold: true, size: 16 }))], C.PHASE_BLUE, W.FA[0]),
      ...W.FA.slice(1).map(w => celda([para(run(''))], C.WHITE, w))
    ));
  }

  return tabla(W.FA, [
    fila(celda(
      para(run('FASES ABP (Aprendizaje Basado en Proyectos)', { bold: true, size: 17, color: C.WHITE })),
      C.DARK_BLUE, W.TOTAL, { span: 8 }
    )),
    filaHdr,
    ...filasData,
  ]);
}

// ── BLOQUE 4 — INSTRUMENTOS DE EVALUACIÓN ────────────────────────────────
function bloque4(d) {
  const inst = d.instrumentos || {};
  const bordesInst = { top: bordeFino, bottom: bordeFino, left: bordeFino, right: bordeFino };

  function tituloInstr(texto) {
    return new Paragraph({
      children: [run(texto, { bold: true, size: 17, color: C.WHITE })],
      spacing: { before: 60, after: 60 },
      shading: { fill: C.MID_BLUE, type: ShadingType.CLEAR },
    });
  }

  // Lista de Cotejo
  const cotejo = inst.lista_cotejo || [];
  const tablaCotejo = tabla([8000, 1700, 1700], [
    fila(
      celdaHdr('Criterio / Indicador', 8000, C.LIGHT_BLUE, C.BLACK),
      celdaHdr('Sí', 1700, C.LIGHT_BLUE, C.BLACK),
      celdaHdr('No', 1700, C.LIGHT_BLUE, C.BLACK),
    ),
    ...(cotejo.length ? cotejo : ['—','—','—','—']).map(c => fila(
      celda([para(run(c, { size: 16 }))], C.WHITE, 8000, { fino: true }),
      celda([para(run('□', { size: 18 }), { align: AlignmentType.CENTER })], C.WHITE, 1700, { fino: true }),
      celda([para(run('□', { size: 18 }), { align: AlignmentType.CENTER })], C.WHITE, 1700, { fino: true }),
    )),
  ]);

  // Rúbrica de Proceso
  const rProc = inst.rubrica_proceso || [];
  const tablaRProc = tabla([3600, 2700, 2700, 2700, 2700], [
    fila(
      celdaHdr('Nivel / Criterio', 3600, C.LIGHT_BLUE, C.BLACK),
      celdaHdr('Excelente (4)', 2700, C.DARK_BLUE),
      celdaHdr('Bueno (3)', 2700, C.DARK_BLUE),
      celdaHdr('Básico (2)', 2700, C.DARK_BLUE),
      celdaHdr('Bajo (1)', 2700, C.DARK_BLUE),
    ),
    ...(rProc.length ? rProc : [{ nivel: '—', excelente:'', bueno:'', basico:'', bajo:'' }]).map(r => fila(
      celda([para(run(r.criterio || r.nivel || '', { bold: true, size: 16 }))], C.GRAY, 3600, { fino: true }),
      celda([para(run(r.destacado || r.excelente || '', { size: 16 }))], C.WHITE, 2700, { fino: true }),
      celda([para(run(r.satisfactorio || r.bueno || '', { size: 16 }))], C.WHITE, 2700, { fino: true }),
      celda([para(run(r.basico || r.básico || '', { size: 16 }))], C.WHITE, 2700, { fino: true }),
      celda([para(run(r.en_proceso || r.bajo || '', { size: 16 }))], C.WHITE, 2700, { fino: true }),
    )),
  ]);

  // Rúbrica Final
  const rFinal = inst.rubrica_final || [];
  const tablaRFinal = tabla([3600, 2700, 2700, 2700, 2700], [
    fila(
      celdaHdr('Criterio', 3600, C.LIGHT_BLUE, C.BLACK),
      celdaHdr('Excelente (20%)', 2700, C.DARK_BLUE),
      celdaHdr('Bueno (15%)', 2700, C.DARK_BLUE),
      celdaHdr('Básico (10%)', 2700, C.DARK_BLUE),
      celdaHdr('Bajo (5%)', 2700, C.DARK_BLUE),
    ),
    ...(rFinal.length ? rFinal : [
      { criterio: '—', excelente_20:'', bueno_15:'', basico_10:'', bajo_5:'' }
    ]).map(r => fila(
      celda([para(run(r.criterio || '', { bold: true, size: 16 }))], C.GRAY, 3600, { fino: true }),
      celda([para(run(r.excelente_20 || r.excelente || '', { size: 16 }))], C.WHITE, 2700, { fino: true }),
      celda([para(run(r.bueno_15 || r.bueno || '', { size: 16 }))], C.WHITE, 2700, { fino: true }),
      celda([para(run(r.basico_10 || r.basico || r.básico || '', { size: 16 }))], C.WHITE, 2700, { fino: true }),
      celda([para(run(r.bajo_5 || r.bajo || '', { size: 16 }))], C.WHITE, 2700, { fino: true }),
    )),
  ]);

  return [
    // Título bloque 4
    tabla([W.TOTAL], [
      fila(celda(
        para(run('INSTRUMENTOS DE EVALUACIÓN', { bold: true, size: 17, color: C.WHITE })),
        C.DARK_BLUE, W.TOTAL
      )),
    ]),
    // Lista de cotejo
    tituloInstr('1. Lista de Cotejo — Fase 1: Exploración e Investigación'),
    tablaCotejo,
    // Rúbrica proceso
    new Paragraph({ children: [], spacing: { before: 120 } }),
    tituloInstr('2. Rúbrica de Proceso — Fase 2: Diseño y Planificación'),
    tablaRProc,
    // Rúbrica final
    new Paragraph({ children: [], spacing: { before: 120 } }),
    tituloInstr('3. Rúbrica Final — Fase 4: Presentación y Evaluación'),
    tablaRFinal,
    // Firma
    new Paragraph({ children: [], spacing: { before: 200 } }),
    new Paragraph({
      children: [run(`Docente: ${d.docente?.nombre_completo || ''}          Fecha: ${d.proyecto?.fecha_cierre || ''}`, { size: 17 })],
      spacing: { before: 60 },
      border: { top: { style: BorderStyle.SINGLE, size: 4, color: C.DARK_BLUE, space: 6 } },
    }),
  ];
}

// ── GENERADOR PRINCIPAL ────────────────────────────────────────────────────
async function generarDocx(data, outputPath) {
  const b4 = bloque4(data);

  const doc = new Document({
    styles: {
      default: {
        document: { run: { font: 'Arial', size: 18 } },
      },
    },
    sections: [{
      properties: {
        page: {
          size: {
            width: 12240,      // 8.5" → docx-js swaps to landscape
            height: 15840,     // 11"  → docx-js swaps to landscape
            orientation: PageOrientation.LANDSCAPE,
          },
          margin: { top: 720, right: 720, bottom: 720, left: 720 },
        },
      },
      children: [
        // Bloque 0: Encabezado
        bloque0(),
        new Paragraph({ children: [], spacing: { before: 80 } }),
        // Bloque 1: Identificación
        bloque1(data),
        new Paragraph({ children: [], spacing: { before: 80 } }),
        // Bloque 2: Elementos de la Unidad
        bloque2(data),
        new Paragraph({ children: [], spacing: { before: 80 } }),
        // Bloque 3: Fases ABP
        bloque3(data),
        new Paragraph({ children: [], spacing: { before: 80 } }),
        // Bloque 4: Instrumentos (múltiples elementos)
        ...b4,
        // Nota al pie
        new Paragraph({
          children: [run('- Anexar los instrumentos de evaluación de cada fase.', { size: 16, italics: true })],
          spacing: { before: 120, after: 60 },
        }),
      ],
    }],
  });

  const buffer = await Packer.toBuffer(doc);
  fs.writeFileSync(outputPath, buffer);
  console.log(`OK:${outputPath}`);
}

// ── ENTRY POINT ────────────────────────────────────────────────────────────
const args = process.argv.slice(2);
if (args.length < 2) {
  console.error('USO: node generar_planificacion_abp.js <data.json> <output.docx>');
  process.exit(1);
}
try {
  const data = JSON.parse(fs.readFileSync(args[0], 'utf8'));
  generarDocx(data, args[1])
    .then(() => process.exit(0))
    .catch(e => { console.error('ERROR:', e.message); process.exit(2); });
} catch(e) {
  console.error('ERROR leyendo JSON:', e.message);
  process.exit(3);
}
