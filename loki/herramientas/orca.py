"""Envoltorio del CLI de Orca con salida `--json` (D9)."""
from __future__ import annotations

import asyncio
import json
from typing import Any, Awaitable, Callable

EjecutorOrca = Callable[[list[str]], Awaitable[str]]


class ErrorOrca(Exception):
    pass


async def _ejecutar_por_defecto(argv: list[str]) -> str:
    proc = await asyncio.create_subprocess_exec(
        "orca",
        *argv,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise ErrorOrca(
            stderr.decode("utf-8", errors="replace")
            or f"orca {' '.join(argv)} salió con código {proc.returncode}"
        )
    return stdout.decode("utf-8")


class Orca:
    """Cada método arma los argumentos del subcomando correspondiente y
    siempre agrega `--json`, devolviendo el resultado ya parseado."""

    def __init__(self, ejecutor: EjecutorOrca = _ejecutar_por_defecto) -> None:
        self._ejecutor = ejecutor

    async def _correr(self, argv: list[str]) -> dict[str, Any]:
        salida = await self._ejecutor(argv + ["--json"])
        return json.loads(salida)

    async def listar_repos(self) -> dict:
        return await self._correr(["repo", "list"])

    async def listar_terminales(self, worktree: str | None = None) -> dict:
        argv = ["terminal", "list"]
        if worktree is not None:
            argv += ["--worktree", worktree]
        return await self._correr(argv)

    async def mostrar_terminal(self, handle: str) -> dict:
        return await self._correr(["terminal", "show", "--terminal", handle])

    async def crear_terminal(
        self,
        worktree: str,
        comando: str,
        titulo: str | None = None,
        focus: bool = False,
    ) -> dict:
        argv = ["terminal", "create", "--worktree", worktree, "--command", comando]
        if titulo is not None:
            argv += ["--title", titulo]
        if focus:
            argv.append("--focus")
        return await self._correr(argv)

    async def enviar_texto(self, handle: str, texto: str, enter: bool = True) -> dict:
        argv = ["terminal", "send", "--terminal", handle, "--text", texto]
        if enter:
            argv.append("--enter")
        return await self._correr(argv)

    async def esperar_tui_idle(self, handle: str, timeout_ms: int) -> dict:
        return await self._correr(
            [
                "terminal",
                "wait",
                "--terminal",
                handle,
                "--for",
                "tui-idle",
                "--timeout-ms",
                str(timeout_ms),
            ]
        )

    async def leer(self, handle: str, cursor: str | None = None, limit: int | None = None) -> dict:
        argv = ["terminal", "read", "--terminal", handle]
        if cursor is not None:
            argv += ["--cursor", str(cursor)]
        if limit is not None:
            argv += ["--limit", str(limit)]
        return await self._correr(argv)

    async def crear_worktree_sin_agente(
        self, repo: str, nombre: str, base_branch: str | None = None
    ) -> dict:
        argv = ["worktree", "create", "--repo", repo, "--name", nombre]
        if base_branch is not None:
            argv += ["--base-branch", base_branch]
        return await self._correr(argv)


def extraer_texto_y_cursor(resultado_leer: dict) -> tuple[str, str | None]:
    """Extrae el texto nuevo y el cursor siguiente de un resultado de
    `Orca.leer`. El CLI real devuelve `result.terminal.tail` (una lista
    de líneas) y `result.terminal.nextCursor` (string), no `result.text`
    ni `result.output` (hallazgo de la tarea 9.2: no había caso de test
    con la forma real del CLI, solo con supuestos sin verificar)."""
    terminal = resultado_leer.get("result", {}).get("terminal", {})
    tail = terminal.get("tail") or []
    texto = "\n".join(tail)
    cursor = terminal.get("nextCursor")
    return texto, cursor
