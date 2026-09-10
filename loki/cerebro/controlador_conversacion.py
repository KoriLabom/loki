"""Sincroniza el overlay con la sesión de relay activa (D9, spec
sesiones-de-agentes).

Todo el texto dictado va siempre al cerebro (ver design.md, hallazgo de
la tarea 9.2): mientras hay una sesión de relay activa, es el propio
cerebro quien decide, turno a turno, si reenvía lo dictado literalmente
a esa terminal con la herramienta MCP `enviar_a_terminal` o si lo
traduce a un comando de OpenSpec. Este controlador solo lleva el estado
de qué sesión está activa para mostrarlo en el overlay.
"""
from __future__ import annotations

from typing import Callable

from loki.cerebro.claude_headless import CerebroHeadless
from loki.cerebro.sesion import RegistroSesiones

MostrarSesionRelay = Callable[[str | None], None]


class ControladorConversacion:
    def __init__(
        self,
        registro: RegistroSesiones,
        cerebro: CerebroHeadless,
        mostrar_sesion_relay: MostrarSesionRelay,
    ) -> None:
        self._registro = registro
        self._cerebro = cerebro
        self._mostrar_sesion_relay = mostrar_sesion_relay

    @property
    def en_relay(self) -> bool:
        return self._registro.relay_activa is not None

    def activar_relay(self, handle: str) -> None:
        self._registro.activar_relay(handle)
        sesion = self._registro.obtener(handle)
        self._mostrar_sesion_relay(sesion.titulo if sesion else handle)

    def cambiar_sesion(self, handle: str) -> None:
        """Cambiar de sesión por voz es lo mismo que activar otra: la
        anterior sigue registrada, solo cambia cuál está activa."""
        self.activar_relay(handle)

    def salir_relay(self) -> None:
        """Vuelve a hablar con el cerebro sin cerrar la sesión de agente."""
        self._registro.salir_relay()
        self._mostrar_sesion_relay(None)

    async def procesar_dictado(self, texto: str) -> str:
        return await self._cerebro.enviar_turno(texto)
