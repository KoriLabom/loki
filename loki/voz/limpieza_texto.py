"""Limpieza de texto no hablable antes de la síntesis de voz (D7).

Quita o reemplaza por una mención breve lo que no tiene sentido escuchar:
bloques de código, URLs, rutas de archivo largas y marcas de formato
markdown.
"""
from __future__ import annotations

import re

_MENCION_CODIGO = "el detalle está en el overlay"
_MENCION_ENLACE = "un enlace"
_MENCION_RUTA = "una ruta de archivo"

_BLOQUE_CODIGO = re.compile(r"```.*?```", re.DOTALL)
_URL = re.compile(r"https?://\S+|www\.\S+")
_RUTA_LARGA = re.compile(r"(?:[A-Za-z]:)?(?:[\\/][^\s\\/]+){2,}")
_ENCABEZADO = re.compile(r"^#{1,6}\s+", re.MULTILINE)
_VINETA = re.compile(r"^[ \t]*[-*]\s+", re.MULTILINE)
_NEGRITA = re.compile(r"\*\*([^*]+)\*\*|__([^_]+)__")
_CURSIVA = re.compile(r"\*([^*]+)\*|_([^_]+)_")
_CODIGO_INLINE = re.compile(r"`([^`]+)`")
_ESPACIOS = re.compile(r"[ \t]*\n[ \t]*|[ \t]{2,}")


def limpiar_para_voz(texto: str) -> str:
    """Devuelve `texto` listo para sintetizar: sin bloques de código, URLs,
    rutas largas ni marcas de markdown."""
    texto = _BLOQUE_CODIGO.sub(f" {_MENCION_CODIGO}. ", texto)
    texto = _URL.sub(_MENCION_ENLACE, texto)
    texto = _RUTA_LARGA.sub(_MENCION_RUTA, texto)
    texto = _ENCABEZADO.sub("", texto)
    texto = _VINETA.sub("", texto)
    texto = _NEGRITA.sub(lambda m: m.group(1) or m.group(2), texto)
    texto = _CURSIVA.sub(lambda m: m.group(1) or m.group(2), texto)
    texto = _CODIGO_INLINE.sub(lambda m: m.group(1), texto)
    texto = _ESPACIOS.sub(" ", texto)
    return texto.strip()
