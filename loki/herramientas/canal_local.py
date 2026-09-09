"""Canal HTTP local entre el servidor MCP y el proceso principal (D3).

Servidor en localhost con puerto configurable y un token aleatorio por
sesión, generado por el proceso principal y pasado al servidor MCP por
variable de entorno. Sin el token correcto, toda llamada se rechaza.
"""
from __future__ import annotations

import json
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable

ManejadorAccion = Callable[[dict], dict]

VARIABLE_ENTORNO_TOKEN = "LOKI_CANAL_LOCAL_TOKEN"
VARIABLE_ENTORNO_PUERTO = "LOKI_CANAL_LOCAL_PUERTO"


def generar_token() -> str:
    return secrets.token_urlsafe(32)


class ServidorCanalLocal:
    """Acciones registradas por nombre, invocadas por POST a /rpc con
    `{"accion": "...", "datos": {...}}` y el header
    `Authorization: Bearer <token>`."""

    def __init__(self, puerto: int, token: str) -> None:
        self._puerto = puerto
        self._token = token
        self._acciones: dict[str, ManejadorAccion] = {}
        self._servidor: ThreadingHTTPServer | None = None
        self._hilo: threading.Thread | None = None

    def registrar(self, nombre: str, manejador: ManejadorAccion) -> None:
        self._acciones[nombre] = manejador

    @property
    def puerto_real(self) -> int:
        if self._servidor is None:
            return self._puerto
        return self._servidor.server_address[1]

    def iniciar(self) -> None:
        canal = self

        class Manejador(BaseHTTPRequestHandler):
            def log_message(self, *args) -> None:  # silencia el log por defecto
                pass

            def do_POST(self) -> None:  # noqa: N802 (nombre impuesto por BaseHTTPRequestHandler)
                autorizacion = self.headers.get("Authorization", "")
                token_recibido = autorizacion.removeprefix("Bearer ").strip()
                if not token_recibido or not secrets.compare_digest(token_recibido, canal._token):
                    self._responder(401, {"error": "token inválido"})
                    return

                largo = int(self.headers.get("Content-Length", 0) or 0)
                crudo = self.rfile.read(largo) if largo else b"{}"
                try:
                    cuerpo = json.loads(crudo or b"{}")
                except json.JSONDecodeError:
                    self._responder(400, {"error": "JSON inválido"})
                    return

                nombre_accion = cuerpo.get("accion")
                manejador = canal._acciones.get(nombre_accion)
                if manejador is None:
                    self._responder(404, {"error": f"acción desconocida: {nombre_accion}"})
                    return

                try:
                    resultado = manejador(cuerpo.get("datos", {}))
                    self._responder(200, resultado)
                except Exception as exc:
                    self._responder(500, {"error": str(exc)})

            def _responder(self, codigo: int, cuerpo: dict) -> None:
                data = json.dumps(cuerpo).encode("utf-8")
                self.send_response(codigo)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self._servidor = ThreadingHTTPServer(("127.0.0.1", self._puerto), Manejador)
        self._hilo = threading.Thread(target=self._servidor.serve_forever, daemon=True)
        self._hilo.start()

    def detener(self) -> None:
        if self._servidor is not None:
            self._servidor.shutdown()
            self._servidor.server_close()
            self._servidor = None
        if self._hilo is not None:
            self._hilo.join(timeout=5)
            self._hilo = None
