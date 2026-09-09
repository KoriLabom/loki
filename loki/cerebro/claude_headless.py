"""Subproceso persistente de `claude -p` en modo stream-json (D1, D2).

Ver openspec/changes/loki-mvp/design.md para las decisiones y los hallazgos
del spike de la tarea 2.1 (flags reales del CLI instalado).
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Awaitable, Callable, Protocol


class ProcesoAsync(Protocol):
    """Subconjunto de asyncio.subprocess.Process que usa este módulo."""

    stdin: asyncio.StreamWriter
    stdout: asyncio.StreamReader
    returncode: int | None

    async def wait(self) -> int: ...
    def kill(self) -> None: ...


LanzadorProceso = Callable[[list[str], Path], Awaitable[ProcesoAsync]]


async def _lanzador_por_defecto(cmd: list[str], cwd: Path) -> ProcesoAsync:
    return await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(cwd),
    )


@dataclass
class ConfigCerebro:
    modelo: str
    ruta_persona: Path
    allowed_tools: list[str] = field(default_factory=list)
    disallowed_tools: list[str] = field(default_factory=list)
    cwd: Path = field(default_factory=Path.cwd)
    timeout_turno_s: float = 120.0


class TurnoTimeoutError(Exception):
    """El cerebro no respondió dentro del timeout de turno configurado."""


def config_cerebro_desde_config(config: dict, ruta_persona: Path, cwd: Path) -> ConfigCerebro:
    """Arma ConfigCerebro a partir del dict cargado por loki.config (D12),
    tomando el modelo, las listas de herramientas y el timeout de turno."""
    seccion_cerebro = config.get("cerebro", {})
    return ConfigCerebro(
        modelo=config.get("modelos", {}).get("cerebro", "haiku"),
        ruta_persona=ruta_persona,
        allowed_tools=list(seccion_cerebro.get("allowed_tools", [])),
        disallowed_tools=list(seccion_cerebro.get("disallowed_tools", [])),
        cwd=cwd,
        timeout_turno_s=float(seccion_cerebro.get("timeout_turno_s", 120.0)),
    )


def _armar_comando(config: ConfigCerebro) -> list[str]:
    persona = config.ruta_persona.read_text(encoding="utf-8")
    cmd = [
        "claude",
        "-p",
        "--input-format",
        "stream-json",
        "--output-format",
        "stream-json",
        "--include-partial-messages",
        "--verbose",
        "--model",
        config.modelo,
        "--system-prompt",
        persona,
        "--setting-sources",
        "project",
        "--permission-mode",
        "manual",
        "--permission-prompts",
        "none",
    ]
    if config.allowed_tools:
        cmd.append("--allowedTools")
        cmd.extend(config.allowed_tools)
    if config.disallowed_tools:
        cmd.append("--disallowedTools")
        cmd.extend(config.disallowed_tools)
    return cmd


def _mensaje_usuario(texto: str) -> str:
    return json.dumps(
        {
            "type": "user",
            "message": {"role": "user", "content": [{"type": "text", "text": texto}]},
        }
    )


class CerebroHeadless:
    """Envuelve el subproceso de `claude -p` y expone turnos por texto."""

    def __init__(
        self,
        config: ConfigCerebro,
        on_texto_parcial: Callable[[str], None] | None = None,
        lanzador: LanzadorProceso = _lanzador_por_defecto,
    ) -> None:
        self._config = config
        self._on_texto_parcial = on_texto_parcial or (lambda _texto: None)
        self._lanzador = lanzador
        self._proceso: ProcesoAsync | None = None
        self._lock = asyncio.Lock()

    async def iniciar(self) -> None:
        cmd = _armar_comando(self._config)
        self._proceso = await self._lanzador(cmd, self._config.cwd)

    @property
    def esta_vivo(self) -> bool:
        return self._proceso is not None and self._proceso.returncode is None

    async def enviar_turno(self, texto: str) -> str:
        """Escribe un turno de usuario y devuelve el texto completo de la
        respuesta una vez que llega el evento de fin de turno (`result`).

        Solo hay un subproceso con un único stdin/stdout, así que los
        turnos se serializan: si ya hay uno en curso (por ejemplo, una
        clasificación de relay en segundo plano), este espera su turno en
        vez de leer el stream al mismo tiempo.

        Si el proceso ya murió, lo relanza y reintenta una vez antes de
        propagar el error. Si el turno no termina dentro de
        `timeout_turno_s`, levanta `TurnoTimeoutError`.
        """
        async with self._lock:
            if self._proceso is None or not self.esta_vivo:
                await self.iniciar()

            try:
                return await asyncio.wait_for(
                    self._enviar_turno_interno(texto), timeout=self._config.timeout_turno_s
                )
            except asyncio.TimeoutError:
                raise TurnoTimeoutError(
                    f"El cerebro no respondió en {self._config.timeout_turno_s} s"
                ) from None
            except ConnectionError:
                # El subproceso murió a mitad de turno: se relanza y se reintenta una vez.
                await self.iniciar()
                try:
                    return await asyncio.wait_for(
                        self._enviar_turno_interno(texto), timeout=self._config.timeout_turno_s
                    )
                except asyncio.TimeoutError:
                    raise TurnoTimeoutError(
                        f"El cerebro no respondió en {self._config.timeout_turno_s} s"
                    ) from None

    async def _enviar_turno_interno(self, texto: str) -> str:
        assert self._proceso is not None
        linea = (_mensaje_usuario(texto) + "\n").encode("utf-8")
        self._proceso.stdin.write(linea)
        await self._proceso.stdin.drain()

        buffer_actual: list[str] = []
        while True:
            cruda = await self._proceso.stdout.readline()
            if not cruda:
                raise ConnectionError("El subproceso del cerebro cerró stdout")
            linea_texto = cruda.decode("utf-8").strip()
            if not linea_texto:
                continue
            try:
                evento = json.loads(linea_texto)
            except json.JSONDecodeError:
                continue

            tipo = evento.get("type")
            if tipo == "stream_event":
                sub = evento.get("event", {})
                if sub.get("type") == "content_block_delta":
                    delta = sub.get("delta", {})
                    texto_delta = delta.get("text", "")
                    if texto_delta:
                        buffer_actual.append(texto_delta)
                        self._on_texto_parcial(texto_delta)
            elif tipo == "result":
                return "".join(buffer_actual)

    async def reiniciar_conversacion(self) -> None:
        """Mata el subproceso actual y lanza uno nuevo, sin contexto previo."""
        await self.detener()
        await self.iniciar()

    async def detener(self) -> None:
        if self._proceso is None:
            return
        if self._proceso.returncode is None:
            self._proceso.kill()
            await self._proceso.wait()
        self._proceso = None
