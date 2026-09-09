import json

import pytest

from loki.cerebro.sesion import RegistroSesiones, ResolvedorProyectos, SesionAgente
from loki.herramientas.orca import Orca

_REPOS = [
    {"id": "repo-tablero", "displayName": "Andromeda"},
    {"id": "repo-cvs", "displayName": "Nebulosa"},
    {"id": "repo-fenix", "displayName": "Cosmos"},
]


def _orca_con_repos():
    async def ejecutor(argv):
        return json.dumps({"result": {"repos": _REPOS}})

    return Orca(ejecutor=ejecutor)


# --- RegistroSesiones ---


def test_registrar_y_obtener_sesion():
    registro = RegistroSesiones()
    sesion = SesionAgente(handle="term-1", repo="Andromeda", titulo="Claude Code", modelo="haiku")
    registro.registrar(sesion)

    assert registro.obtener("term-1") is sesion
    assert registro.obtener("no-existe") is None
    assert registro.todas() == [sesion]


def test_actualizar_cursor():
    registro = RegistroSesiones()
    sesion = SesionAgente(handle="term-1", repo="Andromeda", titulo="Claude Code", modelo="haiku")
    registro.registrar(sesion)

    registro.actualizar_cursor("term-1", 42)
    assert registro.obtener("term-1").cursor == 42


def test_relay_activa_por_defecto_es_ninguna():
    registro = RegistroSesiones()
    assert registro.relay_activa is None
    assert registro.sesion_relay is None


def test_activar_y_salir_de_relay():
    registro = RegistroSesiones()
    sesion = SesionAgente(handle="term-1", repo="Andromeda", titulo="Claude Code", modelo="haiku")
    registro.registrar(sesion)

    registro.activar_relay("term-1")
    assert registro.relay_activa == "term-1"
    assert registro.sesion_relay is sesion

    registro.salir_relay()
    assert registro.relay_activa is None


def test_quitar_sesion_activa_de_relay_tambien_limpia_la_relay_activa():
    registro = RegistroSesiones()
    sesion = SesionAgente(handle="term-1", repo="Andromeda", titulo="Claude Code", modelo="haiku")
    registro.registrar(sesion)
    registro.activar_relay("term-1")

    registro.quitar("term-1")
    assert registro.obtener("term-1") is None
    assert registro.relay_activa is None


# --- ResolvedorProyectos ---


@pytest.mark.asyncio
async def test_alias_conocido_resuelve_al_repo_correcto():
    orca = _orca_con_repos()
    resolvedor = ResolvedorProyectos(orca, alias={"el tablero": "Andromeda"})

    resultado = await resolvedor.resolver("el tablero")
    assert resultado.id == "repo-tablero"
    assert resultado.nombre == "Andromeda"


@pytest.mark.asyncio
async def test_nombre_exacto_sin_alias_resuelve_directo():
    orca = _orca_con_repos()
    resolvedor = ResolvedorProyectos(orca)

    resultado = await resolvedor.resolver("Nebulosa")
    assert resultado.id == "repo-cvs"


@pytest.mark.asyncio
async def test_proyecto_desconocido_devuelve_candidatos_parecidos():
    orca = _orca_con_repos()
    resolvedor = ResolvedorProyectos(orca)

    resultado = await resolvedor.resolver("andrómeda")
    assert isinstance(resultado, list)
    assert any(c.nombre == "Andromeda" for c in resultado)


@pytest.mark.asyncio
async def test_proyecto_sin_ningun_parecido_devuelve_lista_vacia():
    orca = _orca_con_repos()
    resolvedor = ResolvedorProyectos(orca)

    resultado = await resolvedor.resolver("xyz completamente distinto 123")
    assert resultado == []


@pytest.mark.asyncio
async def test_alias_que_apunta_a_repo_inexistente_cae_a_candidatos():
    orca = _orca_con_repos()
    resolvedor = ResolvedorProyectos(orca, alias={"el viejo proyecto": "repo-que-ya-no-existe"})

    resultado = await resolvedor.resolver("el viejo proyecto")
    assert resultado == []
