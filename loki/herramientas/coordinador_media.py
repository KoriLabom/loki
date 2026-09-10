"""Conecta el control de media con la máquina de estados (D8, D11).

Pausa al detectar la palabra de activación si hay reproducción, reanuda
al volver a dormido sin confirmación pendiente, y expone la secuencia de
aviso no solicitado (pausar, hablar, esperar una activación, reanudar).
"""
from __future__ import annotations

import asyncio
import concurrent.futures
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
        loop: asyncio.AbstractEventLoop | None = None,
    ) -> None:
        self._maquina = maquina
        self._control_media = control_media
        self._hay_confirmacion_pendiente = hay_confirmacion_pendiente
        self._segundos_espera_aviso = segundos_espera_aviso
        self._loop = loop
        self._tareas_pendientes: set = set()
        maquina.observar(self._on_transicion)

    def establecer_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """La máquina de estados puede disparar transiciones desde
        cualquier hilo (por ejemplo el callback de audio); sin un loop
        explícito no hay forma segura de lanzar una corrutina desde ahí."""
        self._loop = loop

    def _on_transicion(self, anterior: Estado, nuevo: Estado) -> None:
        if nuevo == Estado.ESCUCHANDO:
            self._lanzar(self._control_media.pausar_si_hay_reproduccion())
        elif nuevo == Estado.DORMIDO and not self._hay_confirmacion_pendiente():
            self._lanzar(self._control_media.reanudar())

    def _lanzar(self, coro: Awaitable[None]) -> None:
        if self._loop is not None:
            futuro = asyncio.run_coroutine_threadsafe(coro, self._loop)
            self._tareas_pendientes.add(futuro)
            futuro.add_done_callback(self._tareas_pendientes.discard)
        else:
            tarea = asyncio.ensure_future(coro)
            self._tareas_pendientes.add(tarea)
            tarea.add_done_callback(self._tareas_pendientes.discard)

    async def esperar_tareas_pendientes(self) -> None:
        """Espera a que terminen las pausas/reanudaciones ya disparadas."""
        while self._tareas_pendientes:
            pendientes = list(self._tareas_pendientes)
            esperables = [
                asyncio.wrap_future(t) if isinstance(t, concurrent.futures.Future) else t
                for t in pendientes
            ]
            await asyncio.gather(*esperables)

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
