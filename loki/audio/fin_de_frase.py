"""Fin de frase por energía, sin VAD neuronal (D5).

Se considera que el usuario empezó a hablar cuando el RMS de un bloque
supera un umbral configurable, y que terminó cuando el silencio se
mantiene por `silencio_s`. Si nunca empieza a hablar dentro de
`sin_voz_s`, se informa `SIN_VOZ`. Corte duro a los `maximo_s`.
"""
from __future__ import annotations

from enum import Enum, auto

import numpy as np


class ResultadoBloque(Enum):
    CONTINUAR = auto()
    FIN_POR_SILENCIO = auto()
    SIN_VOZ = auto()
    MAXIMO_ALCANZADO = auto()


def _rms(bloque: np.ndarray) -> float:
    if bloque.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(bloque, dtype=np.float64))))


class DetectorFinDeFrase:
    """Recibe bloques de audio consecutivos y decide cuándo cortar la frase."""

    def __init__(
        self,
        umbral_rms: float = 0.02,
        silencio_s: float = 1.2,
        sin_voz_s: float = 5.0,
        maximo_s: float = 30.0,
    ) -> None:
        self._umbral_rms = umbral_rms
        self._silencio_s = silencio_s
        self._sin_voz_s = sin_voz_s
        self._maximo_s = maximo_s
        self.reiniciar()

    def reiniciar(self) -> None:
        self._tiempo_total = 0.0
        self._tiempo_silencio_continuo = 0.0
        self._empezo_a_hablar = False

    def procesar_bloque(self, bloque: np.ndarray, duracion_s: float) -> ResultadoBloque:
        self._tiempo_total += duracion_s
        hay_voz = _rms(bloque) >= self._umbral_rms

        if hay_voz:
            self._empezo_a_hablar = True
            self._tiempo_silencio_continuo = 0.0
        else:
            self._tiempo_silencio_continuo += duracion_s

        if self._tiempo_total >= self._maximo_s:
            return ResultadoBloque.MAXIMO_ALCANZADO

        if not self._empezo_a_hablar and self._tiempo_total >= self._sin_voz_s:
            return ResultadoBloque.SIN_VOZ

        if self._empezo_a_hablar and self._tiempo_silencio_continuo >= self._silencio_s:
            return ResultadoBloque.FIN_POR_SILENCIO

        return ResultadoBloque.CONTINUAR
