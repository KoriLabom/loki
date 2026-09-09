"""Manejadores del canal local para las herramientas críticas (D2, D3).

Se registran en el `ServidorCanalLocal` del proceso principal. La
confirmación se verifica acá, en una capa independiente del cerebro: sin
un `confirmacion_id` válido para la acción exacta, la acción no se
ejecuta, sin importar lo que el cerebro afirme.
"""
from __future__ import annotations

import asyncio
from typing import Awaitable, Callable

from loki.herramientas.confirmacion import RegistroConfirmaciones
from loki.herramientas.orca import Orca

EjecutorCerrarTerminal = Callable[[str], Awaitable[dict]]
EjecutorEliminarWorktree = Callable[[str], Awaitable[dict]]
EjecutorEnviarTexto = Callable[[str, str], Awaitable[dict]]


def _terminal_corre_claude_code(info_terminal: dict) -> bool:
    titulo = info_terminal.get("result", {}).get("terminal", {}).get("title", "") or ""
    return "Claude Code" in titulo


class ManejadoresCriticos:
    """Cada método es sincrónico (lo exige `ServidorCanalLocal.registrar`)
    y corre lo asíncrono adentro con `asyncio.run`."""

    def __init__(
        self,
        registro: RegistroConfirmaciones,
        orca: Orca,
        ejecutar_cerrar_terminal: EjecutorCerrarTerminal,
        ejecutar_eliminar_worktree: EjecutorEliminarWorktree,
        ejecutar_enviar_texto: EjecutorEnviarTexto,
    ) -> None:
        self._registro = registro
        self._orca = orca
        self._ejecutar_cerrar_terminal = ejecutar_cerrar_terminal
        self._ejecutar_eliminar_worktree = ejecutar_eliminar_worktree
        self._ejecutar_enviar_texto = ejecutar_enviar_texto

    def cerrar_terminal(self, datos: dict) -> dict:
        return asyncio.run(self._cerrar_terminal(datos))

    async def _cerrar_terminal(self, datos: dict) -> dict:
        terminal = datos.get("terminal", "")
        confirmacion_id = datos.get("confirmacion_id") or ""
        if not self._registro.es_valida(confirmacion_id, "cerrar_terminal"):
            return {"error": "confirmación inválida o vencida", "ejecutado": False}
        resultado = await self._ejecutar_cerrar_terminal(terminal)
        return {"ejecutado": True, **resultado}

    def eliminar_worktree(self, datos: dict) -> dict:
        return asyncio.run(self._eliminar_worktree(datos))

    async def _eliminar_worktree(self, datos: dict) -> dict:
        worktree = datos.get("worktree", "")
        confirmacion_id = datos.get("confirmacion_id") or ""
        if not self._registro.es_valida(confirmacion_id, "eliminar_worktree"):
            return {"error": "confirmación inválida o vencida", "ejecutado": False}
        resultado = await self._ejecutar_eliminar_worktree(worktree)
        return {"ejecutado": True, **resultado}

    def enviar_a_terminal(self, datos: dict) -> dict:
        return asyncio.run(self._enviar_a_terminal(datos))

    async def _enviar_a_terminal(self, datos: dict) -> dict:
        terminal = datos.get("terminal", "")
        texto = datos.get("texto", "")
        confirmacion_id = datos.get("confirmacion_id") or ""

        info = await self._orca.mostrar_terminal(terminal)
        if not _terminal_corre_claude_code(info):
            if not self._registro.es_valida(confirmacion_id, "enviar_a_terminal_no_claude"):
                return {"error": "confirmación inválida o vencida", "ejecutado": False}

        resultado = await self._ejecutar_enviar_texto(terminal, texto)
        return {"ejecutado": True, **resultado}
