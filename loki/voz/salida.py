"""Orquesta síntesis + reproducción de una respuesta, con fallback (D7).

Si la síntesis de una oración falla, se muestra el texto completo de la
respuesta por `on_fallo_sintesis` (pensado para el overlay) y se registra
el error, sin perder el turno de conversación: no se relanza la
excepción, y Loki queda listo para el próximo turno.
"""
from __future__ import annotations

import logging
from typing import Awaitable, Callable

from loki.voz.reproductor import Reproductor
from loki.voz.tts import sintetizar_mp3

logger = logging.getLogger(__name__)

Sintetizador = Callable[[str, str], Awaitable[bytes]]


async def hablar_oraciones(
    oraciones: list[str],
    texto_completo: str,
    voz: str,
    reproductor: Reproductor,
    on_fallo_sintesis: Callable[[str], None] | None = None,
    sintetizador: Sintetizador = sintetizar_mp3,
) -> None:
    on_fallo_sintesis = on_fallo_sintesis or (lambda _texto: None)
    for oracion in oraciones:
        try:
            audio = await sintetizador(oracion, voz)
        except Exception:
            logger.exception("Fallo la sintesis de voz para: %s", oracion)
            on_fallo_sintesis(texto_completo)
            return
        reproductor.encolar(audio)
