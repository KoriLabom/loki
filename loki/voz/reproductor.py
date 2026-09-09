"""Reproducción en cola de las oraciones sintetizadas (D7).

Un hilo consume una cola ordenada de audio MP3, lo decodifica con
miniaudio y lo reproduce con sounddevice en bloques pequeños para poder
cortar la reproducción a mitad de una oración cuando el usuario interrumpe.
"""
from __future__ import annotations

import queue
import threading
from typing import Callable, ContextManager, Protocol

import miniaudio
import numpy as np
import sounddevice as sd


class _EscritorAudio(Protocol):
    def write(self, bloque: np.ndarray) -> None: ...


FabricaStream = Callable[[int, int], ContextManager[_EscritorAudio]]
Decodificador = Callable[[bytes], "miniaudio.DecodedSoundFile"]


def _decodificar_por_defecto(mp3: bytes) -> "miniaudio.DecodedSoundFile":
    return miniaudio.decode(mp3)


def _fabrica_stream_por_defecto(samplerate: int, canales: int) -> ContextManager[_EscritorAudio]:
    return sd.OutputStream(samplerate=samplerate, channels=canales, dtype="int16")


class Reproductor:
    """Cola ordenada de audio con interrupción inmediata."""

    _FIN = object()

    def __init__(
        self,
        decodificador: Decodificador = _decodificar_por_defecto,
        fabrica_stream: FabricaStream = _fabrica_stream_por_defecto,
        tam_bloque: int = 2048,
    ) -> None:
        self._cola: "queue.Queue[object]" = queue.Queue()
        self._evento_interrumpir = threading.Event()
        self._decodificador = decodificador
        self._fabrica_stream = fabrica_stream
        self._tam_bloque = tam_bloque
        self._hilo = threading.Thread(target=self._bucle, daemon=True)

    def iniciar(self) -> None:
        self._hilo.start()

    def encolar(self, mp3: bytes) -> None:
        self._cola.put(mp3)

    def interrumpir(self) -> None:
        """Vacía lo pendiente en la cola y corta la reproducción en curso."""
        self._evento_interrumpir.set()
        while True:
            try:
                self._cola.get_nowait()
            except queue.Empty:
                break

    def detener(self) -> None:
        self._cola.put(self._FIN)
        self._hilo.join()

    def _bucle(self) -> None:
        while True:
            item = self._cola.get()
            if item is self._FIN:
                return
            self._evento_interrumpir.clear()
            self._reproducir(item)  # type: ignore[arg-type]

    def _reproducir(self, mp3: bytes) -> None:
        decodificado = self._decodificador(mp3)
        muestras = np.array(decodificado.samples, dtype=np.int16).reshape(
            -1, decodificado.nchannels
        )
        with self._fabrica_stream(decodificado.sample_rate, decodificado.nchannels) as stream:
            for inicio in range(0, len(muestras), self._tam_bloque):
                if self._evento_interrumpir.is_set():
                    return
                stream.write(muestras[inicio : inicio + self._tam_bloque])
