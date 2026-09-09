"""Bandeja del sistema: mostrar/ocultar overlay, reiniciar conversación,
salir con cierre ordenado de audio, cerebro y canal local (D11, D14)."""
from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable

from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

logger = logging.getLogger(__name__)

CierreAsync = Callable[[], Awaitable[None]]


class Bandeja(QSystemTrayIcon):
    def __init__(
        self,
        icono: QIcon,
        on_alternar_overlay: Callable[[], None],
        on_reiniciar_conversacion: Callable[[], None],
        cerrar_audio: CierreAsync,
        cerrar_cerebro: CierreAsync,
        cerrar_canal_local: CierreAsync,
        parent=None,
        loop: asyncio.AbstractEventLoop | None = None,
    ) -> None:
        super().__init__(icono, parent)
        self._on_alternar_overlay = on_alternar_overlay
        self._on_reiniciar_conversacion = on_reiniciar_conversacion
        self._cerrar_audio = cerrar_audio
        self._cerrar_cerebro = cerrar_cerebro
        self._cerrar_canal_local = cerrar_canal_local
        self._loop = loop

        self._menu = QMenu()

        self.accion_overlay = QAction("Mostrar/Ocultar overlay", self._menu)
        self.accion_overlay.triggered.connect(lambda: self._on_alternar_overlay())
        self._menu.addAction(self.accion_overlay)

        self.accion_reiniciar = QAction("Reiniciar conversación", self._menu)
        self.accion_reiniciar.triggered.connect(lambda: self._on_reiniciar_conversacion())
        self._menu.addAction(self.accion_reiniciar)

        self._menu.addSeparator()

        self.accion_salir = QAction("Salir", self._menu)
        self.accion_salir.triggered.connect(self._salir)
        self._menu.addAction(self.accion_salir)

        self.setContextMenu(self._menu)

    def _salir(self) -> None:
        # El menú de la bandeja corre en el hilo de Qt, que no tiene loop
        # de asyncio propio: sin un loop explícito, ensure_future agenda
        # la corrutina en un loop que nadie corre y no pasa nada.
        if self._loop is not None:
            asyncio.run_coroutine_threadsafe(self._cerrar_todo(), self._loop)
        else:
            asyncio.ensure_future(self._cerrar_todo())

    async def _cerrar_todo(self) -> None:
        """Cierra audio, cerebro y canal local en ese orden. Si uno falla,
        se registra el error y se sigue con los demás antes de salir."""
        for nombre, cerrar in (
            ("audio", self._cerrar_audio),
            ("cerebro", self._cerrar_cerebro),
            ("canal local", self._cerrar_canal_local),
        ):
            try:
                await cerrar()
            except Exception:
                logger.exception("Fallo cerrando %s al salir", nombre)

        app = QApplication.instance()
        if app is not None:
            app.quit()
