"""Control de media con la sesión de Windows (D8).

Usa `GlobalSystemMediaTransportControlsSessionManager` (WinRT) para
pausar y reanudar explícitamente la sesión que Loki pausó, sin tocar un
media que ya estaba pausado. Si el paquete WinRT no carga, cae a la tecla
multimedia play/pause (alterna, se acepta el riesgo).
"""
from __future__ import annotations

import logging
from typing import Awaitable, Callable, Protocol

logger = logging.getLogger(__name__)


class InfoReproduccion(Protocol):
    playback_status: int


class SesionMedia(Protocol):
    source_app_user_model_id: str

    def get_playback_info(self) -> InfoReproduccion: ...
    async def try_pause_async(self) -> bool: ...
    async def try_play_async(self) -> bool: ...


class GestorSesiones(Protocol):
    def get_current_session(self) -> SesionMedia | None: ...


FabricaManager = Callable[[], Awaitable[GestorSesiones]]


async def _fabrica_manager_por_defecto() -> GestorSesiones:
    from winrt.windows.media.control import (
        GlobalSystemMediaTransportControlsSessionManager as Manager,
    )

    return await Manager.request_async()


def _esta_reproduciendo(info: InfoReproduccion) -> bool:
    from winrt.windows.media.control import (
        GlobalSystemMediaTransportControlsSessionPlaybackStatus as Estado,
    )

    return info.playback_status == Estado.PLAYING


def _tecla_multimedia() -> None:
    import pyautogui

    pyautogui.press("playpause")


def _winrt_disponible() -> bool:
    try:
        import winrt.windows.media.control  # noqa: F401

        return True
    except ImportError:
        return False


class ControlMedia:
    """Pausa/reanuda con memoria de qué sesión fue la que Loki pausó."""

    def __init__(
        self,
        fabrica_manager: FabricaManager | None = None,
        forzar_fallback: bool | None = None,
        tecla_multimedia: Callable[[], None] = _tecla_multimedia,
    ) -> None:
        usar_fallback = forzar_fallback if forzar_fallback is not None else not _winrt_disponible()
        self._modo_fallback = usar_fallback
        self._fabrica_manager = fabrica_manager or _fabrica_manager_por_defecto
        self._tecla_multimedia = tecla_multimedia
        self._id_sesion_pausada: str | None = None
        self._fallback_pendiente_de_reanudar = False

    async def _sesion_actual(self) -> SesionMedia | None:
        try:
            manager = await self._fabrica_manager()
            return manager.get_current_session()
        except Exception:
            logger.exception("No se pudo consultar la sesión de media")
            return None

    async def pausar_si_hay_reproduccion(self) -> None:
        if self._modo_fallback:
            self._tecla_multimedia()
            self._fallback_pendiente_de_reanudar = True
            return

        sesion = await self._sesion_actual()
        if sesion is None:
            return
        try:
            if not _esta_reproduciendo(sesion.get_playback_info()):
                return
            await sesion.try_pause_async()
            self._id_sesion_pausada = sesion.source_app_user_model_id
        except Exception:
            logger.exception("No se pudo pausar la sesión de media")

    async def reanudar(self) -> None:
        if self._modo_fallback:
            if self._fallback_pendiente_de_reanudar:
                self._tecla_multimedia()
                self._fallback_pendiente_de_reanudar = False
            return

        if self._id_sesion_pausada is None:
            return
        id_a_reanudar = self._id_sesion_pausada
        self._id_sesion_pausada = None
        sesion = await self._sesion_actual()
        if sesion is None or sesion.source_app_user_model_id != id_a_reanudar:
            return
        try:
            await sesion.try_play_async()
        except Exception:
            logger.exception("No se pudo reanudar la sesión de media")
