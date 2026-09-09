"""Conecta el control de media con la máquina de estados (D8, D11).

Pausa al detectar la palabra de activación si hay reproducción, reanuda
al volver a dormido sin confirmación pendiente, y expone la secuencia de
aviso no solicitado (pausar, hablar, esperar una activación, reanudar).
"""
from __future__ import annotations

import asyncio
from typing import Awaitable, Callable

from loki.estados import Estado, MaquinaEstados
from loki.herramientas.media import ControlMedia


class CoordinadorMedia:
    def __init__(
        self,
        maquina: MaquinaEstados,
        control_media: ControlMedia,
        hay_confirmacion_pendiente: Callable[[], bool] = lambda: False,
        segundos_espera_aviso: float = 4.0,
    ) -> None:
        self._maquina = maquina
        self._control_media = control_media
        self._hay_confirmacion_pendiente = hay_confirmacion_pendiente
        self._segundos_espera_aviso = segundos_espera_aviso
        self._tareas_pendientes: set[asyncio.Task] = set()
        maquina.observar(self._on_transicion)

    def _on_transicion(self, anterior: Estado, nuevo: Estado) -> None:
        if nuevo == Estado.ESCUCHANDO:
            self._lanzar(self._control_media.pausar_si_hay_reproduccion())
        elif nuevo == Estado.DORMIDO and not self._hay_confirmacion_pendiente():
            self._lanzar(self._control_media.reanudar())

    def _lanzar(self, coro: Awaitable[None]) -> asyncio.Task:
        tarea = asyncio.ensure_future(coro)
        self._tareas_pendientes.add(tarea)
        tarea.add_done_callback(self._tareas_pendientes.discard)
        return tarea

    async def esperar_tareas_pendientes(self) -> None:
        """Espera a que terminen las pausas/reanudaciones ya disparadas."""
        while self._tareas_pendientes:
            await asyncio.gather(*list(self._tareas_pendientes))

    async def dar_aviso(self, hablar: Callable[[], Awaitable[None]]) -> None:
        """Secuencia de aviso no solicitado: pausa, habla, espera una
        activación hasta `segundos_espera_aviso` y, si no llega, reanuda."""
        await self._control_media.pausar_si_hay_reproduccion()
        await hablar()
        try:
            await asyncio.wait_for(self._espera_activacion(), timeout=self._segundos_espera_aviso)
        except asyncio.TimeoutError:
            await self._control_media.reanudar()

    async def _espera_activacion(self) -> None:
        while self._maquina.estado != Estado.ESCUCHANDO:
            await asyncio.sleep(0.02)
