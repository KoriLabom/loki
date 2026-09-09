"""Detección de la palabra de activación con openWakeWord (D4).

El detector sigue activo mientras Loki habla, para permitir interrupción
(ver D11). La ruta del modelo y el umbral vienen de la configuración, así
que se puede reemplazar `hey_jarvis` por un modelo propio sin tocar código.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Protocol

import numpy as np


class ModeloWakeWordNoEncontrado(Exception):
    """El archivo del modelo de wake word no existe en la ruta configurada."""


class ModeloPrediccion(Protocol):
    def predict(self, x: np.ndarray) -> dict[str, float]: ...


FabricaModelo = Callable[[list[str]], ModeloPrediccion]


def _fabrica_modelo_por_defecto(rutas: list[str]) -> ModeloPrediccion:
    from openwakeword.model import Model

    return Model(wakeword_models=rutas, inference_framework="onnx")


class DetectorWakeWord:
    """Envuelve un modelo de openWakeWord y dispara un callback al detectar."""

    def __init__(
        self,
        ruta_modelo: Path,
        umbral: float = 0.5,
        on_deteccion: Callable[[], None] | None = None,
        fabrica_modelo: FabricaModelo = _fabrica_modelo_por_defecto,
    ) -> None:
        if not ruta_modelo.exists():
            raise ModeloWakeWordNoEncontrado(
                f"No se encontró el modelo de wake word en '{ruta_modelo}'. "
                "Revisá audio.wake_word.modelo en config.yaml."
            )
        self._umbral = umbral
        self._on_deteccion = on_deteccion or (lambda: None)
        self._modelo = fabrica_modelo([str(ruta_modelo)])

    def procesar_bloque(self, bloque: np.ndarray) -> float:
        """Alimenta un bloque de audio al modelo; si algún score supera el
        umbral, dispara el callback de detección. Devuelve el score máximo
        de la predicción."""
        predicciones = self._modelo.predict(bloque)
        score_maximo = max(predicciones.values(), default=0.0)
        if score_maximo >= self._umbral:
            self._on_deteccion()
        return score_maximo
