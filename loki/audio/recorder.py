"""Captura de audio continua a 16 kHz mono, repartida a suscriptores (D6).

A diferencia del `Recorder` push-to-talk de voice-transcript, este abre un
stream continuo desde el arranque y entrega cada bloque a todos los
suscriptores (detector de wake word, grabador de frase, amplitud para el
overlay). Si el dispositivo no soporta 16 kHz nativamente, se resamplea
por decimación simple.
"""
from __future__ import annotations

from typing import Callable

import numpy as np
import sounddevice as sd

TASA_OBJETIVO = 16000


def _tasa_nativa_dispositivo() -> int:
    try:
        info = sd.query_devices(sd.default.device[0], "input")
        return int(info["default_samplerate"])
    except Exception:
        return TASA_OBJETIVO


def _factor_decimacion(tasa_nativa: int, tasa_objetivo: int) -> int:
    return max(1, round(tasa_nativa / tasa_objetivo))


def _decimar(bloque: np.ndarray, factor: int) -> np.ndarray:
    if factor <= 1:
        return bloque
    return bloque[::factor]


class GrabadorContinuo:
    """Stream continuo de micrófono que reparte cada bloque a N suscriptores."""

    CANALES = 1

    def __init__(self, tasa_objetivo: int = TASA_OBJETIVO) -> None:
        self.tasa_objetivo = tasa_objetivo
        self._tasa_nativa = _tasa_nativa_dispositivo()
        self._factor = _factor_decimacion(self._tasa_nativa, tasa_objetivo)
        self._suscriptores: list[Callable[[np.ndarray], None]] = []
        self._stream: sd.InputStream | None = None

    @property
    def tasa_efectiva(self) -> int:
        return self._tasa_nativa // self._factor

    def suscribir(self, callback: Callable[[np.ndarray], None]) -> None:
        self._suscriptores.append(callback)

    def iniciar(self) -> None:
        self._stream = sd.InputStream(
            samplerate=self._tasa_nativa,
            channels=self.CANALES,
            dtype="float32",
            callback=self._callback,
        )
        self._stream.start()

    def detener(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def _callback(self, indata: np.ndarray, frames: int, time, status) -> None:
        bloque = _decimar(indata.copy(), self._factor)
        for suscriptor in self._suscriptores:
            suscriptor(bloque)
