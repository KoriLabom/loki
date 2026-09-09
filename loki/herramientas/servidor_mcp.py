"""Servidor MCP de Loki (D3): expone las herramientas propias al cerebro,
relayando cada llamada al canal local del proceso principal por HTTP.

Se lanza como subproceso de Claude Code (ver `.mcp.json`), y recibe el
puerto y el token del canal local por variable de entorno.
"""
from __future__ import annotations

import asyncio
import json
import os
import urllib.error
import urllib.request

from mcp.server.mcpserver import MCPServer

from loki.herramientas.canal_local import VARIABLE_ENTORNO_PUERTO, VARIABLE_ENTORNO_TOKEN


class ClienteCanalLocal:
    """Llama al canal local del proceso principal por HTTP."""

    def __init__(self, puerto: int, token: str) -> None:
        self._puerto = puerto
        self._token = token

    def _post_sync(self, accion: str, datos: dict) -> dict:
        url = f"http://127.0.0.1:{self._puerto}/rpc"
        cuerpo = json.dumps({"accion": accion, "datos": datos}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=cuerpo,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._token}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            return json.loads(e.read())
        except OSError as e:
            return {"error": f"canal local no disponible: {e}"}

    async def llamar(self, accion: str, datos: dict) -> dict:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._post_sync, accion, datos)


def construir_servidor(cliente: ClienteCanalLocal) -> MCPServer:
    servidor: MCPServer = MCPServer("loki")

    @servidor.tool()
    async def pedir_confirmacion(accion: str, objetivo: str) -> dict:
        """Pide confirmación hablada para una acción crítica y devuelve un
        confirmacion_id. Solo queda válido si el usuario confirmó.

        `accion` MUST ser exactamente uno de: 'cerrar_terminal',
        'eliminar_worktree', 'enviar_a_terminal_no_claude' (el identificador
        literal, no una descripción). `objetivo` es libre, por ejemplo el
        nombre o handle de la terminal."""
        return await cliente.llamar("pedir_confirmacion", {"accion": accion, "objetivo": objetivo})

    @servidor.tool()
    async def cerrar_terminal(terminal: str, confirmacion_id: str) -> dict:
        """Cierra una terminal de Orca. Exige un confirmacion_id válido
        para la acción 'cerrar_terminal'."""
        return await cliente.llamar(
            "cerrar_terminal", {"terminal": terminal, "confirmacion_id": confirmacion_id}
        )

    @servidor.tool()
    async def eliminar_worktree(worktree: str, confirmacion_id: str) -> dict:
        """Elimina un worktree de Orca. Exige un confirmacion_id válido
        para la acción 'eliminar_worktree'."""
        return await cliente.llamar(
            "eliminar_worktree", {"worktree": worktree, "confirmacion_id": confirmacion_id}
        )

    @servidor.tool()
    async def enviar_a_terminal(terminal: str, texto: str, confirmacion_id: str | None = None) -> dict:
        """Envía texto a una terminal. Solo exige confirmación cuando la
        terminal destino no corre una sesión de Claude Code."""
        return await cliente.llamar(
            "enviar_a_terminal",
            {"terminal": terminal, "texto": texto, "confirmacion_id": confirmacion_id},
        )

    @servidor.tool()
    async def media_pausar() -> dict:
        return await cliente.llamar("media_pausar", {})

    @servidor.tool()
    async def media_reanudar() -> dict:
        return await cliente.llamar("media_reanudar", {})

    @servidor.tool()
    async def media_estado() -> dict:
        return await cliente.llamar("media_estado", {})

    @servidor.tool()
    async def overlay_estado(texto: str) -> dict:
        return await cliente.llamar("overlay_estado", {"texto": texto})

    @servidor.tool()
    async def sesion_relay_activar(terminal: str) -> dict:
        return await cliente.llamar("sesion_relay_activar", {"terminal": terminal})

    @servidor.tool()
    async def sesion_relay_salir() -> dict:
        return await cliente.llamar("sesion_relay_salir", {})

    @servidor.tool()
    async def monitorear_terminal(terminal: str, etiqueta: str) -> dict:
        return await cliente.llamar("monitorear_terminal", {"terminal": terminal, "etiqueta": etiqueta})

    @servidor.tool()
    async def listar_proyectos() -> dict:
        return await cliente.llamar("listar_proyectos", {})

    @servidor.tool()
    async def config_modelos() -> dict:
        return await cliente.llamar("config_modelos", {})

    return servidor


def main() -> None:
    puerto = int(os.environ[VARIABLE_ENTORNO_PUERTO])
    token = os.environ[VARIABLE_ENTORNO_TOKEN]
    cliente = ClienteCanalLocal(puerto, token)
    servidor = construir_servidor(cliente)
    asyncio.run(servidor.run_stdio_async())


if __name__ == "__main__":
    main()
