import numpy as np

from loki.audio.fin_de_frase import DetectorFinDeFrase, ResultadoBloque

_BLOQUE_S = 0.1  # 100 ms por bloque, simplifica los cálculos de los tests


def _bloque(rms_deseado: float) -> np.ndarray:
    if rms_deseado == 0.0:
        return np.zeros(160, dtype="float32")
    return np.full(160, rms_deseado, dtype="float32")


def test_fin_por_silencio_tras_hablar():
    detector = DetectorFinDeFrase(umbral_rms=0.02, silencio_s=0.3, sin_voz_s=5.0, maximo_s=30.0)

    # El usuario habla dos bloques.
    assert detector.procesar_bloque(_bloque(0.5), _BLOQUE_S) == ResultadoBloque.CONTINUAR
    assert detector.procesar_bloque(_bloque(0.5), _BLOQUE_S) == ResultadoBloque.CONTINUAR

    # Silencio: con silencio_s=0.3 y bloques de 0.1s, hacen falta 3 bloques
    # silenciosos para acumular 0.3s.
    assert detector.procesar_bloque(_bloque(0.0), _BLOQUE_S) == ResultadoBloque.CONTINUAR
    assert detector.procesar_bloque(_bloque(0.0), _BLOQUE_S) == ResultadoBloque.CONTINUAR
    assert detector.procesar_bloque(_bloque(0.0), _BLOQUE_S) == ResultadoBloque.FIN_POR_SILENCIO


def test_silencio_breve_no_corta_la_frase():
    detector = DetectorFinDeFrase(umbral_rms=0.02, silencio_s=0.3, sin_voz_s=5.0, maximo_s=30.0)

    detector.procesar_bloque(_bloque(0.5), _BLOQUE_S)
    # Silencio breve (menos que silencio_s) y el usuario retoma.
    assert detector.procesar_bloque(_bloque(0.0), _BLOQUE_S) == ResultadoBloque.CONTINUAR
    assert detector.procesar_bloque(_bloque(0.5), _BLOQUE_S) == ResultadoBloque.CONTINUAR


def test_sin_voz_tras_activacion():
    detector = DetectorFinDeFrase(umbral_rms=0.02, silencio_s=1.2, sin_voz_s=0.5, maximo_s=30.0)

    # 4 bloques de silencio (0.4s) todavía no llegan a los 0.5s configurados.
    for _ in range(4):
        assert detector.procesar_bloque(_bloque(0.0), _BLOQUE_S) == ResultadoBloque.CONTINUAR
    # El quinto bloque cruza el umbral de sin_voz_s sin que se haya hablado.
    assert detector.procesar_bloque(_bloque(0.0), _BLOQUE_S) == ResultadoBloque.SIN_VOZ


def test_frase_demasiado_larga_corta_en_el_maximo():
    detector = DetectorFinDeFrase(umbral_rms=0.02, silencio_s=1.2, sin_voz_s=5.0, maximo_s=0.5)

    # El usuario habla sin parar, nunca hay silencio suficiente para cortar antes.
    for _ in range(4):
        assert detector.procesar_bloque(_bloque(0.5), _BLOQUE_S) == ResultadoBloque.CONTINUAR
    assert detector.procesar_bloque(_bloque(0.5), _BLOQUE_S) == ResultadoBloque.MAXIMO_ALCANZADO


def test_reiniciar_limpia_el_estado_entre_frases():
    detector = DetectorFinDeFrase(umbral_rms=0.02, silencio_s=0.2, sin_voz_s=5.0, maximo_s=30.0)
    detector.procesar_bloque(_bloque(0.5), _BLOQUE_S)
    detector.procesar_bloque(_bloque(0.0), _BLOQUE_S)
    detector.procesar_bloque(_bloque(0.0), _BLOQUE_S)  # FIN_POR_SILENCIO

    detector.reiniciar()
    # Después de reiniciar, un solo bloque de habla no debería disparar nada.
    assert detector.procesar_bloque(_bloque(0.5), _BLOQUE_S) == ResultadoBloque.CONTINUAR
