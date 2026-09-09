import re
from pathlib import Path

import numpy as np
import pytest

from loki.audio.wake_word import DetectorWakeWord, ModeloWakeWordNoEncontrado


class _ModeloFalso:
    def __init__(self, score: float) -> None:
        self._score = score

    def predict(self, x: np.ndarray) -> dict[str, float]:
        return {"hey_jarvis": self._score}


def test_modelo_inexistente_levanta_error_claro_sin_cerrar_la_app(tmp_path):
    ruta_inexistente = tmp_path / "no_existe.onnx"

    with pytest.raises(ModeloWakeWordNoEncontrado, match=re.escape(str(ruta_inexistente))):
        DetectorWakeWord(ruta_modelo=ruta_inexistente)


def test_deteccion_dispara_callback_cuando_supera_el_umbral(tmp_path):
    ruta_modelo = tmp_path / "hey_jarvis.onnx"
    ruta_modelo.write_bytes(b"contenido falso")
    detectado = []

    detector = DetectorWakeWord(
        ruta_modelo=ruta_modelo,
        umbral=0.5,
        on_deteccion=lambda: detectado.append(True),
        fabrica_modelo=lambda rutas: _ModeloFalso(score=0.9),
    )
    score = detector.procesar_bloque(np.zeros(1280, dtype="int16"))

    assert score == 0.9
    assert detectado == [True]


def test_no_dispara_callback_bajo_el_umbral(tmp_path):
    ruta_modelo = tmp_path / "hey_jarvis.onnx"
    ruta_modelo.write_bytes(b"contenido falso")
    detectado = []

    detector = DetectorWakeWord(
        ruta_modelo=ruta_modelo,
        umbral=0.5,
        on_deteccion=lambda: detectado.append(True),
        fabrica_modelo=lambda rutas: _ModeloFalso(score=0.2),
    )
    score = detector.procesar_bloque(np.zeros(1280, dtype="int16"))

    assert score == 0.2
    assert detectado == []
