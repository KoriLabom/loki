"""Monitor en segundo plano de una terminal: espera tui-idle, lee, pide al
cerebro que clasifique y dispara el aviso hablado respetando la
secuencia de media (D9, D10, flujo-de-desarrollo-por-voz)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable

from loki.cerebro.claude_headless import CerebroHeadless
from loki.cerebro.relay import INSTRUCCION_RESUMEN, TIMEOUT_TUI_IDLE_MS, extraer_clasificacion
from loki.herramientas.coordinador_media import CoordinadorMedia
from loki.herramientas.orca import Orca, extraer_texto_y_cursor


async def _no_hacer_nada(_texto: str) -> None:
    return None


@dataclass
class AvisoMonitor:
    terminal: str
    etiqueta: str
    nombre_proyecto: str
    clasificacion: str
    resumen: str
    texto_hablado: str


class MonitorTerminal:
    """Cada instancia monitorea una sola terminal; correr varias a la vez
    (una por proyecto/etiqueta) es lo que permite distinguir sus avisos."""

    def __init__(
        self,
        terminal: str,
        etiqueta: str,
        nombre_proyecto: str,
        orca: Orca,
        cerebro: CerebroHeadless,
        coordinador_media: CoordinadorMedia,
        cursor_inicial: str | None = None,
        timeout_ms: int = TIMEOUT_TUI_IDLE_MS,
        on_hablar: Callable[[str], Awaitable[None]] | None = None,
    ) -> None:
        self._terminal = terminal
        self._etiqueta = etiqueta
        self._nombre_proyecto = nombre_proyecto
        self._orca = orca
        self._cerebro = cerebro
        self._coordinador_media = coordinador_media
        self._cursor = cursor_inicial
        self._timeout_ms = timeout_ms
        self._on_hablar = on_hablar or _no_hacer_nada

    async def ejecutar(self) -> AvisoMonitor:
        await self._orca.esperar_tui_idle(self._terminal, timeout_ms=self._timeout_ms)

        leido = await self._orca.leer(self._terminal, cursor=self._cursor)
        texto_nuevo, nuevo_cursor = extraer_texto_y_cursor(leido)
        self._cursor = nuevo_cursor or self._cursor

        respuesta = await self._cerebro.enviar_turno(INSTRUCCION_RESUMEN + texto_nuevo)
        clasificacion, resumen = extraer_clasificacion(respuesta)

        texto_hablado = f"{self._nombre_proyecto}, {self._etiqueta}: {resumen}"
        aviso = AvisoMonitor(
            terminal=self._terminal,
            etiqueta=self._etiqueta,
            nombre_proyecto=self._nombre_proyecto,
            clasificacion=clasificacion,
            resumen=resumen,
            texto_hablado=texto_hablado,
        )

        async def hablar() -> None:
            await self._on_hablar(aviso.texto_hablado)

        await self._coordinador_media.dar_aviso(hablar)
        return aviso
