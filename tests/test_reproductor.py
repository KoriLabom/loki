import threading
import time
from types import SimpleNamespace

import numpy as np

from loki.voz.reproductor import Reproductor


def _decodificado_falso(n_muestras: int, canales: int = 1) -> SimpleNamespace:
    return SimpleNamespace(
        samples=list(range(n_muestras * canales)),
        nchannels=canales,
        sample_rate=16000,
    )


class _StreamFalso:
    def __init__(self, bloques_escritos: list, evento_primer_bloque: threading.Event | None = None):
        self._bloques = bloques_escritos
        self._evento_primer_bloque = evento_primer_bloque

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def write(self, bloque) -> None:
        self._bloques.append(bloque)
        if self._evento_primer_bloque is not None:
            self._evento_primer_bloque.set()
        time.sleep(0.005)  # da tiempo a que el hilo de test llame a interrumpir()


def test_interrumpir_descarta_los_audios_pendientes_en_la_cola():
    bloques: list = []
    evento_primer_bloque = threading.Event()

    def decodificador(mp3: bytes):
        # Cada mp3 falso tiene muchas muestras para dar tiempo a interrumpir
        # antes de que termine de "reproducirse".
        return _decodificado_falso(n_muestras=100)

    def fabrica_stream(samplerate, canales):
        return _StreamFalso(bloques, evento_primer_bloque)

    reproductor = Reproductor(decodificador=decodificador, fabrica_stream=fabrica_stream, tam_bloque=1)
    reproductor.iniciar()

    reproductor.encolar(b"audio-1")
    reproductor.encolar(b"audio-2")
    reproductor.encolar(b"audio-3")

    assert evento_primer_bloque.wait(timeout=2), "el primer bloque no se reprodujo a tiempo"
    reproductor.interrumpir()

    reproductor.detener()

    # Como mucho se alcanzaron a escribir algunos bloques del primer audio;
    # los otros dos audios nunca llegaron a reproducirse.
    assert len(bloques) < 100
    assert reproductor._cola.empty()


def test_sin_interrupcion_reproduce_todos_los_bloques_en_orden():
    bloques: list = []

    def decodificador(mp3: bytes):
        return _decodificado_falso(n_muestras=4)

    def fabrica_stream(samplerate, canales):
        return _StreamFalso(bloques)

    reproductor = Reproductor(decodificador=decodificador, fabrica_stream=fabrica_stream, tam_bloque=4)
    reproductor.iniciar()
    reproductor.encolar(b"audio-1")
    reproductor.detener()

    assert len(bloques) == 1
    assert list(bloques[0]) == [0, 1, 2, 3]
