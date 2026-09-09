from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from loki.audio.recorder import GrabadorContinuo, _decimar, _factor_decimacion


def test_factor_decimacion_es_uno_cuando_la_tasa_nativa_es_la_objetivo():
    assert _factor_decimacion(16000, 16000) == 1


def test_factor_decimacion_reduce_tasas_mas_altas():
    assert _factor_decimacion(48000, 16000) == 3
    assert _factor_decimacion(44100, 16000) == 3


def test_decimar_con_factor_uno_no_cambia_el_bloque():
    bloque = np.arange(10, dtype="float32")
    assert np.array_equal(_decimar(bloque, 1), bloque)


def test_decimar_con_factor_tres_toma_una_de_cada_tres_muestras():
    bloque = np.arange(9, dtype="float32")
    resultado = _decimar(bloque, 3)
    assert np.array_equal(resultado, np.array([0, 3, 6], dtype="float32"))


@patch("loki.audio.recorder._tasa_nativa_dispositivo", return_value=16000)
def test_los_suscriptores_reciben_los_mismos_bloques(_mock_tasa):
    grabador = GrabadorContinuo()
    recibidos_a: list[np.ndarray] = []
    recibidos_b: list[np.ndarray] = []
    grabador.suscribir(recibidos_a.append)
    grabador.suscribir(recibidos_b.append)

    bloque = np.ones((256, 1), dtype="float32") * 0.3
    grabador._callback(bloque, 256, None, None)

    assert len(recibidos_a) == 1
    assert len(recibidos_b) == 1
    assert np.array_equal(recibidos_a[0], recibidos_b[0])
    assert np.array_equal(recibidos_a[0], bloque)


@patch("loki.audio.recorder._tasa_nativa_dispositivo", return_value=48000)
def test_los_suscriptores_reciben_el_bloque_ya_decimado(_mock_tasa):
    grabador = GrabadorContinuo(tasa_objetivo=16000)
    assert grabador.tasa_efectiva == 16000
    recibidos: list[np.ndarray] = []
    grabador.suscribir(recibidos.append)

    bloque = np.arange(9, dtype="float32").reshape(-1, 1)
    grabador._callback(bloque, 9, None, None)

    assert recibidos[0].shape[0] == 3


@patch("loki.audio.recorder._tasa_nativa_dispositivo", return_value=16000)
def test_iniciar_y_detener_manejan_el_stream(_mock_tasa):
    grabador = GrabadorContinuo()
    with patch("sounddevice.InputStream") as MockStream:
        instancia = MockStream.return_value
        instancia.start = MagicMock()
        instancia.stop = MagicMock()
        instancia.close = MagicMock()

        grabador.iniciar()
        instancia.start.assert_called_once()

        grabador.detener()
        instancia.stop.assert_called_once()
        instancia.close.assert_called_once()
