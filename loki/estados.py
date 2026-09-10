"""Máquina de estados central de Loki (D11).

Estados: dormido, escuchando, pensando, hablando. El estado "agente
trabajando" es paralelo (uno o más monitores de terminal en segundo
plano) y no reemplaza al estado principal.
"""
from __future__ import annotations

from enum import Enum, auto
from typing import Callable

Observador = Callable[["Estado", "Estado"], None]


class Estado(Enum):
    DORMIDO = auto()
    ESCUCHANDO = auto()
    PENSANDO = auto()
    HABLANDO = auto()


class MaquinaEstados:
    """Dueña del estado principal y de las transiciones de D11."""

    def __init__(self, estado_inicial: Estado = Estado.DORMIDO) -> None:
        self._estado = estado_inicial
        self._agentes_trabajando: set[str] = set()
        self._observadores: list[Observador] = []

    @property
    def estado(self) -> Estado:
        return self._estado

    def observar(self, callback: Observador) -> None:
        self._observadores.append(callback)

    def _transicionar(self, nuevo: Estado) -> None:
        anterior = self._estado
        if anterior == nuevo:
            return
        self._estado = nuevo
        for observador in self._observadores:
            observador(anterior, nuevo)

    def wake_word_detectada(self) -> None:
        """Dormido -> escuchando (activación normal). Hablando -> escuchando
        (interrupción: corta la voz en curso)."""
        if self._estado in (Estado.DORMIDO, Estado.HABLANDO):
            self._transicionar(Estado.ESCUCHANDO)

    def fin_de_voz(self) -> None:
        if self._estado == Estado.ESCUCHANDO:
            self._transicionar(Estado.PENSANDO)

    def sin_voz_tras_activacion(self) -> None:
        if self._estado == Estado.ESCUCHANDO:
            self._transicionar(Estado.DORMIDO)

    def primera_oracion_lista(self) -> None:
        if self._estado == Estado.PENSANDO:
            self._transicionar(Estado.HABLANDO)

    def fin_de_reproduccion(self) -> None:
        if self._estado == Estado.HABLANDO:
            self._transicionar(Estado.DORMIDO)

    # Estado paralelo: agente trabajando.
    def agente_empezo_a_trabajar(self, id_terminal: str) -> None:
        self._agentes_trabajando.add(id_terminal)

    def agente_termino_de_trabajar(self, id_terminal: str) -> None:
        self._agentes_trabajando.discard(id_terminal)

    @property
    def hay_agentes_trabajando(self) -> bool:
        return bool(self._agentes_trabajando)
