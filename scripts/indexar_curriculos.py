#!/usr/bin/env python3
"""Registra e indexa los PDFs de currículum de modalidades artísticas en el RAG."""
import sys
import os
sys.path.insert(0, '/Users/erickhernandez/elearning')

import sqlite3
from datetime import date
from core.rag import procesar_normativa

DATABASE = '/Users/erickhernandez/elearning/database.db'

CURRICULOS = [
    {
        'ruta': '/Users/erickhernandez/elearning/uploads/archivos/Bachillerato-multimedia.pdf',
        'titulo': 'Currículum Bachillerato Modalidad Artes — Mención Multimedia',
        'tipo': 'curriculo',
        'descripcion': 'Currículum oficial MINERD para la mención Multimedia del Bachillerato en Artes',
    },
    {
        'ruta': '/Users/erickhernandez/elearning/uploads/archivos/Bachillerato-en-musicapdf.pdf',
        'titulo': 'Currículum Bachillerato Modalidad Artes — Mención Música',
        'tipo': 'curriculo',
        'descripcion': 'Currículum oficial MINERD para la mención Música del Bachillerato en Artes',
    },
    {
        'ruta': '/Users/erickhernandez/elearning/uploads/archivos/Bachillerato-en-teatro.pdf',
        'titulo': 'Currículum Bachillerato Modalidad Artes — Mención Teatro',
        'tipo': 'curriculo',
        'descripcion': 'Currículum oficial MINERD para la mención Teatro del Bachillerato en Artes',
    },
    {
        'ruta': '/Users/erickhernandez/elearning/uploads/archivos/Bachillerato-artes-visuales.pdf',
        'titulo': 'Currículum Bachillerato Modalidad Artes — Mención Artes Visuales',
        'tipo': 'curriculo',
        'descripcion': 'Currículum oficial MINERD para la mención Artes Visuales del Bachillerato en Artes',
    },
]

SUBIDO_POR = 2  # ID de la directora (usuario admin)
ANIO_ESCOLAR = '2025-2026'

def main():
    print("=== Indexador de Currículos MINERD — Axula RAG ===\n")

    with sqlite3.connect(DATABASE, timeout=30) as conn:
        conn.row_factory = sqlite3.Row

        for doc in CURRICULOS:
            ruta = doc['ruta']
            titulo = doc['titulo']
            tipo = doc['tipo']

            # Verificar que el archivo existe
            if not os.path.exists(ruta):
                print(f"[ERROR] Archivo no encontrado: {ruta}")
                continue

            tamanio_kb = os.path.getsize(ruta) // 1024
            nombre_archivo = os.path.basename(ruta)
            ruta_relativa = f"uploads/archivos/{nombre_archivo}"

            print(f"Procesando: {titulo}")
            print(f"  Archivo: {nombre_archivo} ({tamanio_kb} KB)")

            # Verificar si ya existe en la BD
            existente = conn.execute(
                "SELECT id, procesado, total_chunks FROM normativa_minerd WHERE titulo=?",
                (titulo,)
            ).fetchone()

            if existente:
                norm_id = existente['id']
                print(f"  Ya existe en BD (id={norm_id}). Re-procesando...")
                # Limpiar chunks anteriores
                conn.execute("DELETE FROM normativa_chunks WHERE normativa_id=?", (norm_id,))
                conn.execute(
                    "UPDATE normativa_minerd SET procesado=0, total_chunks=0 WHERE id=?",
                    (norm_id,)
                )
                conn.commit()
            else:
                # Insertar nuevo registro
                conn.execute("""
                    INSERT INTO normativa_minerd
                        (titulo, descripcion, tipo, anio_escolar, version,
                         ruta_archivo, tipo_archivo, tamanio_kb,
                         subido_por, procesado, total_chunks, fecha_subida, activo)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, ?, 1)
                """, (
                    titulo,
                    doc['descripcion'],
                    tipo,
                    ANIO_ESCOLAR,
                    '1.0',
                    ruta_relativa,
                    'pdf',
                    tamanio_kb,
                    SUBIDO_POR,
                    date.today().isoformat(),
                ))
                conn.commit()
                norm_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                print(f"  Registrado en BD con id={norm_id}")

            # Procesar con el motor RAG (extrae texto, chunkea, guarda chunks)
            ok = procesar_normativa(conn, norm_id, ruta)

            if ok:
                resultado = conn.execute(
                    "SELECT total_chunks FROM normativa_minerd WHERE id=?",
                    (norm_id,)
                ).fetchone()
                chunks = resultado['total_chunks'] if resultado else 0
                print(f"  OK — {chunks} chunks creados\n")
            else:
                print(f"  ERROR — No se pudo procesar (posiblemente PDF sin texto extraíble)\n")

    print("=== Indexación completada ===")
    print("\nResumen:")
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT titulo, procesado, total_chunks
            FROM normativa_minerd
            WHERE tipo='curriculo'
            ORDER BY id
        """).fetchall()
        for r in rows:
            estado = "OK" if r['procesado'] == 1 else ("SIN TEXTO" if r['procesado'] == 2 else "PENDIENTE")
            print(f"  [{estado}] {r['titulo'][:60]} — {r['total_chunks']} chunks")


if __name__ == '__main__':
    main()
