/**
 * generar_coherencia_docx.js
 * Genera el .docx de "Coherencia Horizontal del Componente Especializado"
 * C.E. Benito Juárez — Modalidad en Artes
 *
 * USO: node generar_coherencia_docx.js <json_data_file> <output_file>
 *
 * Réplica de la plantilla oficial entregada por el coordinador
 * ("Coherencia Horizontal componente especializado.docx"). Valores extraídos
 * del XML del documento original:
 *   - Landscape, ancho de contenido 14,668 DXA
 *   - Sombreado de encabezados: C1E4F5 (celeste claro)
 *   - Tabla identificación: 6 cols [2105, 6456, 1073, 2267, 994, 1773]
 *   - Tablas de período:    6 cols [2916, 2270, 3740, 2268, 1447, 2027]
 *   - Fila "Contenidos" abarca 3 columnas; RAE/Producto/Recursos usan
 *     vMerge vertical sobre las 2 filas de encabezado
 *
 * Sigue las mismas convenciones que generar_planificacion_abp.js (mismo
 * mecanismo de invocación desde Flask, ShadingType.CLEAR, helpers análogos).
 */

const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, PageOrientation, BorderStyle, WidthType, ShadingType,
  VerticalAlign, VerticalMergeType,
} = require('docx');
const fs = require('fs');

// ── PALETA (tomada del .docx original) ─────────────────────────────────────
const C = {
  HEADER:  'C1E4F5',   // Sombreado de encabezados de la plantilla
  WHITE:   'FFFFFF',
  BLACK:   '000000',
  BORDER:  '000000',
};

// ── ANCHOS (DXA) — exactos del documento original ──────────────────────────
const W = {
  TOTAL: 14668,
  // Identificación: Docente | (valor) ; Asignatura | val | Mención | val | Grado | val
  ID: [2105, 6456, 1073, 2267, 994, 1773],
  // Período: RAE | Conceptos | Procedimientos | Actitudes | Producto | Recursos
  PE: [2916, 2270, 3740, 2268, 1447, 2027],
};

// ── HELPERS ────────────────────────────────────────────────────────────────
const borde  = { style: BorderStyle.SINGLE, size: 4, color: C.BORDER };
const bordes = { top: borde, bottom: borde, left: borde, right: borde };

function run(text, opts = {}) {
  return new TextRun({
    text: String(text == null ? '' : text),
    font: 'Arial',
    size: opts.size || 18,          // 9pt = 18 half-points
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

/** Convierte texto multilínea en varios párrafos (respeta saltos de línea). */
function parasDeTexto(texto, opts = {}) {
  const t = String(texto == null ? '' : texto);
  const lineas = t.split('\n');
  if (lineas.length === 1 && lineas[0] === '') return [para(run(''), opts)];
  return lineas.map(l => para(run(l, { size: opts.size || 17 }), opts));
}

function celda(children, bgColor, widthDxa, opts = {}) {
  const cfg = {
    borders: bordes,
    width: { size: widthDxa, type: WidthType.DXA },
    shading: { fill: bgColor, type: ShadingType.CLEAR },
    verticalAlign: opts.vAlign || VerticalAlign.CENTER,
    columnSpan: opts.span || 1,
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: Array.isArray(children) ? children : [children],
  };
  if (opts.vMerge) cfg.verticalMerge = opts.vMerge;
  return new TableCell(cfg);
}

/** Celda de encabezado (sombreada, negrita, centrada). */
function celdaHdr(texto, widthDxa, opts = {}) {
  return celda(
    para(run(texto, { bold: true, size: opts.size || 17 }), { align: AlignmentType.CENTER }),
    C.HEADER, widthDxa, opts
  );
}

/** Celda de valor (blanca, texto normal). */
function celdaVal(texto, widthDxa, opts = {}) {
  return celda(parasDeTexto(texto), C.WHITE, widthDxa, opts);
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

function espacio(before = 120) {
  return new Paragraph({ children: [], spacing: { before } });
}

// ── ENCABEZADO INSTITUCIONAL (header del .docx original) ───────────────────
function encabezado(d) {
  return [
    para(run('CENTRO EDUCATIVO EN ARTES BENITO JUAREZ', { bold: true, size: 24 }),
         { align: AlignmentType.CENTER, before: 0, after: 40 }),
    para(run(`AÑO ESCOLAR ${d.anio_escolar || ''}`, { bold: true, size: 20 }),
         { align: AlignmentType.CENTER, before: 0, after: 40 }),
    para(run('COHERENCIA HORIZONTAL DEL COMPONENTE ESPECIALIZADO.', { bold: true, size: 20 }),
         { align: AlignmentType.CENTER, before: 0, after: 120 }),
  ];
}

// ── PROPÓSITO ──────────────────────────────────────────────────────────────
function proposito(d) {
  return para([
    run('Propósito: ', { bold: true, size: 18 }),
    run(d.proposito || '', { size: 18 }),
  ], { align: AlignmentType.JUSTIFIED, before: 60, after: 140 });
}

// ── TABLA DE IDENTIFICACIÓN ────────────────────────────────────────────────
function identificacion(d) {
  return tabla(W.ID, [
    fila(
      celdaHdr('Docente', W.ID[0]),
      celdaVal(d.docente || '', W.ID[1], { span: 5 }),
    ),
    fila(
      celdaHdr('Asignatura', W.ID[0]),
      celdaVal(d.asignatura || '', W.ID[1]),
      celdaHdr('Mención', W.ID[2]),
      celdaVal(d.mencion || '', W.ID[3]),
      celdaHdr('Grado', W.ID[4]),
      celdaVal(d.grado || '', W.ID[5]),
    ),
  ]);
}

// ── TABLA DE UN PERÍODO ────────────────────────────────────────────────────
function tablaPeriodo(p) {
  const rows = [
    // Título del período — ancho completo
    fila(celda(
      para(run(p.titulo || '', { bold: true, size: 18 }), { align: AlignmentType.CENTER }),
      C.HEADER, W.TOTAL, { span: 6 }
    )),
    // Competencia Laboral — label + valor a 5 columnas
    fila(
      celdaHdr('Competencia Laboral', W.PE[0]),
      celdaVal(p.competencia_laboral || '', W.PE[1], { span: 5, vAlign: VerticalAlign.TOP }),
    ),
    // Encabezado fila 1: RAE (vMerge) | Contenidos (span 3) | Producto (vMerge) | Recursos (vMerge)
    fila(
      celdaHdr('Resultados de aprendizaje esperados (RAE)', W.PE[0],
               { vMerge: VerticalMergeType.RESTART }),
      celdaHdr('Contenidos', W.PE[1], { span: 3 }),
      celdaHdr('Producto', W.PE[4], { vMerge: VerticalMergeType.RESTART }),
      celdaHdr('Recursos', W.PE[5], { vMerge: VerticalMergeType.RESTART }),
    ),
    // Encabezado fila 2: los 3 sub-tipos de contenido
    fila(
      celda([], C.HEADER, W.PE[0], { vMerge: VerticalMergeType.CONTINUE }),
      celdaHdr('Conceptos', W.PE[1]),
      celdaHdr('Procedimientos', W.PE[2]),
      celdaHdr('Actitudes y valores', W.PE[3]),
      celda([], C.HEADER, W.PE[4], { vMerge: VerticalMergeType.CONTINUE }),
      celda([], C.HEADER, W.PE[5], { vMerge: VerticalMergeType.CONTINUE }),
    ),
  ];

  const filas = Array.isArray(p.filas) ? p.filas : [];
  if (filas.length === 0) {
    // Fila vacía — igual que la plantilla en blanco del coordinador
    rows.push(fila(
      celdaVal('', W.PE[0], { vAlign: VerticalAlign.TOP }),
      celdaVal('', W.PE[1], { vAlign: VerticalAlign.TOP }),
      celdaVal('', W.PE[2], { vAlign: VerticalAlign.TOP }),
      celdaVal('', W.PE[3], { vAlign: VerticalAlign.TOP }),
      celdaVal('', W.PE[4], { vAlign: VerticalAlign.TOP }),
      celdaVal('', W.PE[5], { vAlign: VerticalAlign.TOP }),
    ));
  } else {
    filas.forEach(f => {
      rows.push(fila(
        celdaVal(f.rae,            W.PE[0], { vAlign: VerticalAlign.TOP }),
        celdaVal(f.conceptos,      W.PE[1], { vAlign: VerticalAlign.TOP }),
        celdaVal(f.procedimientos, W.PE[2], { vAlign: VerticalAlign.TOP }),
        celdaVal(f.actitudes,      W.PE[3], { vAlign: VerticalAlign.TOP }),
        celdaVal(f.producto,       W.PE[4], { vAlign: VerticalAlign.TOP }),
        celdaVal(f.recursos,       W.PE[5], { vAlign: VerticalAlign.TOP }),
      ));
    });
  }

  return tabla(W.PE, rows);
}

// ── DOCUMENTO ──────────────────────────────────────────────────────────────
async function generarDocx(data, outputPath) {
  const bloquesPeriodos = [];
  (data.periodos || []).forEach(p => {
    bloquesPeriodos.push(tablaPeriodo(p));
    bloquesPeriodos.push(espacio(160));
  });

  const doc = new Document({
    // Metadatos reales del documento. El .docx NO lleva ninguna protección
    // (sin documentProtection / readOnly / "marcar como final") — es
    // plenamente editable. Si Word lo abre en "Vista protegida" es por el
    // Mark-of-the-Web que el navegador pone a todo archivo descargado:
    // se resuelve con "Habilitar edición" o guardándolo antes de abrirlo.
    creator: data.docente || 'Axula',
    lastModifiedBy: data.docente || 'Axula',
    title: `Coherencia Horizontal — ${data.asignatura || ''} ${data.grado || ''}`.trim(),
    description: 'Coherencia Horizontal del Componente Especializado — '
               + `${data.centro || ''} — Año escolar ${data.anio_escolar || ''}`,
    styles: {
      default: { document: { run: { font: 'Arial', size: 18 } } },
    },
    sections: [{
      properties: {
        page: {
          size: {
            width: 12240,      // 8.5" → docx-js lo intercambia en landscape
            height: 15840,     // 11"
            orientation: PageOrientation.LANDSCAPE,
          },
          margin: { top: 720, right: 720, bottom: 720, left: 720 },
        },
      },
      children: [
        ...encabezado(data),
        proposito(data),
        identificacion(data),
        espacio(200),
        ...bloquesPeriodos,
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
  console.error('USO: node generar_coherencia_docx.js <data.json> <output.docx>');
  process.exit(1);
}
try {
  const data = JSON.parse(fs.readFileSync(args[0], 'utf8'));
  generarDocx(data, args[1])
    .then(() => process.exit(0))
    .catch(e => { console.error('ERROR:', e.message); process.exit(2); });
} catch (e) {
  console.error('ERROR leyendo JSON:', e.message);
  process.exit(3);
}
