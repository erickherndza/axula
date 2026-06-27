# -*- coding: utf-8 -*-
"""
Módulo OCR — Digitalización de documentos con Groq Vision.
Soporta: cédula, pasaporte, acta de nacimiento, factura, certificado y otros.
"""

import os
import json
import logging

logger = logging.getLogger("axula")

# Modelos Groq con capacidades de visión (se prueba en orden)
# Nota: llama-3.2-*-vision-preview y llava-* fueron decommissioned en 2025
_VISION_MODELS = [
    "meta-llama/llama-4-scout-17b-16e-instruct",
]

TIPOS_DOCUMENTO = {
    "cedula":          "Cédula de Identidad",
    "pasaporte":       "Pasaporte",
    "acta_nacimiento": "Acta de Nacimiento",
    "factura":         "Factura / Recibo",
    "estado_cuenta":   "Estado de Cuenta / Movimientos",
    "contrato":        "Contrato / Acuerdo",
    "certificado":     "Certificado",
    "otro":            "Documento General",
}

_PROMPT_OCR = """Eres un sistema experto en digitalización de documentos oficiales de República Dominicana.

Analiza la imagen del documento y realiza exactamente lo siguiente:

REGLA CRÍTICA: Solo extrae información que REALMENTE aparece visible en el documento.
NO inventes, NO asumas, NO completes datos que no puedas leer claramente.
Si un campo no está visible o no puedes leerlo con certeza, omítelo completamente.

1. IDENTIFICA el tipo de documento:
   - cedula          → Cédula de Identidad dominicana (JCE)
   - pasaporte       → Pasaporte dominicano o extranjero
   - acta_nacimiento → Acta de Nacimiento (Oficialía o Registro Civil)
   - factura         → Factura, recibo, nota de crédito, comprobante de pago comercial
   - estado_cuenta   → Estado de cuenta bancario, movimientos de cuenta, extracto bancario
   - contrato        → Contrato, acuerdo, convenio
   - certificado     → Certificado escolar, médico, policial, u oficial
   - otro            → Cualquier otro documento

2. EXTRAE todo el texto visible con la mayor fidelidad posible.

3. Extrae SOLO los campos que puedas leer claramente en el documento:
   - cedula:
       nombre, apellido, cedula (número con guiones), fecha_nacimiento,
       fecha_vencimiento, lugar_nacimiento, sexo
   - pasaporte:
       nombre, apellido, numero_pasaporte, nacionalidad,
       fecha_nacimiento, fecha_vencimiento, lugar_nacimiento, sexo
   - acta_nacimiento:
       nombre, apellido, fecha_nacimiento, lugar_nacimiento,
       nombre_padre, nombre_madre, nombre_abuelo_paterno,
       nombre_abuela_paterna, nombre_abuelo_materno, nombre_abuela_materna,
       numero_acta, tomo, folio, anio, oficalia
   - factura:
       numero_factura, fecha, ncf, vendedor, rnc_cedula_vendedor,
       comprador, rnc_cedula_comprador,
       items (lista: [{descripcion, cantidad, precio_unitario, subtotal}]),
       subtotal, itbis, descuento, total, forma_pago, moneda
   - estado_cuenta:
       banco, numero_cuenta, titular, tipo_cuenta,
       periodo_inicio, periodo_fin,
       saldo_inicial, saldo_final,
       movimientos (lista con UNA entrada por cada fila de la tabla de transacciones.
         Cada entrada DEBE tener todos los campos visibles de esa fila:
         {fecha, referencia, descripcion, tipo, debito, credito, saldo}.
         La "descripcion" debe ser el CONCEPTO o TIPO de transacción de esa fila,
         NO el nombre del titular de la cuenta.
         Si una celda está vacía en esa fila, usa null.
         Incluye TODAS las filas de la tabla, no solo algunas.)
   - contrato:
       partes, fecha, objeto, monto, duracion, condiciones_clave
   - certificado:
       nombre_beneficiario, tipo_certificado, fecha_emision,
       emitido_por, numero_registro, vigencia
   - otro:
       titulo_documento y solo los campos que puedas leer claramente como pares clave-valor

IMPORTANTE:
- Responde ÚNICAMENTE con JSON válido sin markdown ni explicaciones
- Si un valor no está claro en la imagen, NO lo incluyas en el JSON
- Para tablas (movimientos, items): lee fila por fila de arriba a abajo,
  extrae el valor de CADA columna de esa fila específica.
  NO repitas el mismo valor en todas las filas.
  NO uses el nombre del titular como descripción de transacciones.
- Incluye TODAS las filas visibles — no omitas ninguna
{
  "tipo": "tipo_identificado",
  "confianza": "alta|media|baja",
  "texto_completo": "todo el texto visible en el documento",
  "datos": { ... solo campos visibles ... }
}"""


def _get_groq_client():
    from groq import Groq
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY no configurado en .env")
    return Groq(api_key=api_key)


def _limpiar_json(raw: str) -> str:
    """Elimina bloques markdown si el modelo los devuelve."""
    raw = raw.strip()
    if raw.startswith("```"):
        partes = raw.split("```")
        # partes[1] puede ser "json\n{...}" o solo "{...}"
        raw = partes[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    if raw.endswith("```"):
        raw = raw[:-3].strip()
    return raw


def escanear_documento(imagen_base64: str, mime_type: str = "image/jpeg") -> dict:
    """
    Envía imagen a Groq Vision y devuelve texto + datos estructurados.

    Args:
        imagen_base64: imagen en base64 puro (sin prefijo data:)
        mime_type:     "image/jpeg" | "image/png" | "image/webp" | "image/gif"

    Returns:
        dict: {tipo, confianza, texto_completo, datos}

    Raises:
        RuntimeError si todos los modelos de visión fallan.
    """
    client = _get_groq_client()
    data_url = f"data:{mime_type};base64,{imagen_base64}"

    ultimo_error = None
    for model in _VISION_MODELS:
        try:
            logger.info(f"[OCR] Intentando con modelo: {model}")
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": data_url},
                            },
                            {
                                "type": "text",
                                "text": _PROMPT_OCR,
                            },
                        ],
                    }
                ],
                temperature=0.05,
                max_tokens=2048,
            )

            raw = response.choices[0].message.content or ""
            raw = _limpiar_json(raw)

            try:
                result = json.loads(raw)
            except json.JSONDecodeError:
                # El modelo respondió texto libre — devolver como texto_completo
                logger.warning(f"[OCR] Respuesta no-JSON de {model}, guardando como texto libre")
                return {
                    "tipo": "otro",
                    "confianza": "baja",
                    "texto_completo": raw,
                    "datos": {},
                }

            # Garantizar claves mínimas
            result.setdefault("tipo", "otro")
            result.setdefault("confianza", "media")
            result.setdefault("texto_completo", "")
            result.setdefault("datos", {})
            logger.info(f"[OCR] Éxito con {model} — tipo: {result['tipo']}")
            return result

        except Exception as exc:
            logger.warning(f"[OCR] {model} falló: {exc}")
            ultimo_error = exc
            continue

    raise RuntimeError(f"OCR falló en todos los modelos disponibles. Último error: {ultimo_error}")
