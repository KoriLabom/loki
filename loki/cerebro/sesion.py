"""Registro de sesiones de agente y resolución de alias de proyectos.

Ver spec `sesiones-de-agentes` y `cerebro` (alias de proyectos), D9.
"""
from __future__ import annotations

from dataclasses import dataclass
from difflib import get_close_matches
from typing import Union

from loki.herramientas.orca import Orca


@dataclass
class SesionAgente:
    handle: str
    repo: str
    titulo: str
    modelo: str
    cursor: str | None = None


class RegistroSesiones:
    """Sesiones de agente abiertas y cuál es la sesión de relay activa."""

    def __init__(self) -> None:
        self._sesiones: dict[str, SesionAgente] = {}
        self._relay_activa: str | None = None

    def registrar(self, sesion: SesionAgente) -> None:
        self._sesiones[sesion.handle] = sesion

    def obtener(self, handle: str) -> SesionAgente | None:
        return self._sesiones.get(handle)

    def todas(self) -> list[SesionAgente]:
        return list(self._sesiones.values())

    def actualizar_cursor(self, handle: str, cursor: str) -> None:
        sesion = self._sesiones.get(handle)
        if sesion is not None:
            sesion.cursor = cursor

    def quitar(self, handle: str) -> None:
        self._sesiones.pop(handle, None)
        if self._relay_activa == handle:
            self._relay_activa = None

    @property
    def relay_activa(self) -> str | None:
        return self._relay_activa

    @property
    def sesion_relay(self) -> SesionAgente | None:
        if self._relay_activa is None:
            return None
        return self._sesiones.get(self._relay_activa)

    def activar_relay(self, handle: str) -> None:
        self._relay_activa = handle

    def salir_relay(self) -> None:
        self._relay_activa = None


@dataclass
class CandidatoRepo:
    id: str
    nombre: str


ResultadoResolucion = Union[CandidatoRepo, list[CandidatoRepo]]


class ResolvedorProyectos:
    """Resuelve nombres coloquiales de proyectos a repos de Orca, usando
    los alias de `config.local.yaml` y, si no hay alias, el nombre exacto
    o los candidatos más parecidos entre los repos registrados."""

    def __init__(self, orca: Orca, alias: dict[str, str] | None = None) -> None:
        self._orca = orca
        self._alias = {k.strip().lower(): v for k, v in (alias or {}).items()}

    async def resolver(self, nombre: str) -> ResultadoResolucion:
        nombre_norm = nombre.strip().lower()
        respuesta = await self._orca.listar_repos()
        repos = respuesta.get("result", {}).get("repos", [])
        candidatos = [CandidatoRepo(id=r["id"], nombre=r["displayName"]) for r in repos]

        alias_destino = self._alias.get(nombre_norm)
        if alias_destino is not None:
            for c in candidatos:
                if c.id == alias_destino or c.nombre.lower() == alias_destino.lower():
                    return c
            # El alias apunta a algo que ya no existe: sigue por nombre exacto/parecidos.

        for c in candidatos:
            if c.nombre.lower() == nombre_norm:
                return c

        nombres_normalizados = [c.nombre.lower() for c in candidatos]
        parecidos = get_close_matches(nombre_norm, nombres_normalizados, n=3, cutoff=0.4)
        return [c for c in candidatos if c.nombre.lower() in parecidos]
