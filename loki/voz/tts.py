"""Segmentación en oraciones y síntesis de voz con edge-tts (D7).

`SegmentadorOraciones` corta el texto parcial del cerebro apenas hay una
oración completa, para que la voz de salida pueda empezar antes de que la
respuesta termine de generarse. `sintetizar_mp3` sintetiza una oración a
MP3 en memoria con la voz configurada, sin depender de una API key.
"""
from __future__ import annotations

import re
from typing import Awaitable, Callable, Protocol

import edge_tts

_LIMITE_ORACION = re.compile(r"[.?!]+\s|\n")


class SegmentadorOraciones:
    """Acumula texto parcial y entrega oraciones completas en orden."""

    def __init__(self) -> None:
        self._buffer = ""

    def agregar(self, fragmento: str) -> list[str]:
        self._buffer += fragmento
        oraciones: list[str] = []
        while True:
            m = _LIMITE_ORACION.search(self._buffer)
            if not m:
                break
            oracion = self._buffer[: m.end()].strip()
            self._buffer = self._buffer[m.end() :]
            if oracion:
                oraciones.append(oracion)
        return oraciones

    def flush(self) -> str | None:
        """Devuelve lo que quedó pendiente en el buffer (última oración sin
        puntuación final o sin espacio de cierre todavía), o None si no
        queda nada."""
        resto = self._buffer.strip()
        self._buffer = ""
        return resto or None


class Comunicador(Protocol):
    def stream(self) -> "AsyncIteratorAudio": ...


class AsyncIteratorAudio(Protocol):
    def __aiter__(self) -> "AsyncIteratorAudio": ...
    async def __anext__(self) -> dict: ...


FabricaComunicador = Callable[[str, str], Comunicador]


def _fabrica_por_defecto(texto: str, voz: str) -> Comunicador:
    return edge_tts.Communicate(texto, voz)


async def sintetizar_mp3(
    texto: str,
    voz: str,
    fabrica: FabricaComunicador = _fabrica_por_defecto,
) -> bytes:
    """Sintetiza `texto` con `voz` y devuelve el MP3 resultante en memoria."""
    comunicador = fabrica(texto, voz)
    partes: list[bytes] = []
    async for chunk in comunicador.stream():
        if chunk.get("type") == "audio":
            partes.append(chunk["data"])
    return b"".join(partes)
