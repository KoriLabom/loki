import json

import pytest

from loki.herramientas.canal_local import ServidorCanalLocal, generar_token
from loki.herramientas.confirmacion import RegistroConfirmaciones
from loki.herramientas.manejadores_canal_local import ManejadoresCriticos
from loki.herramientas.orca import Orca
from loki.herramientas.servidor_mcp import ClienteCanalLocal, construir_servidor


def _texto_de(resultado) -> dict:
    return json.loads(resultado.content[0].text)


class _ClienteFalso:
    def __init__(self) -> None:
        self.llamadas: list[tuple[str, dict]] = []

    async def llamar(self, accion: str, datos: dict) -> dict:
        self.llamadas.append((accion, datos))
        return {"ok": True}


@pytest.mark.asyncio
async def test_pedir_confirmacion_relaya_accion_y_datos():
    cliente = _ClienteFalso()
    servidor = construir_servidor(cliente)
    await servidor.call_tool("pedir_confirmacion", {"accion": "cerrar_terminal", "objetivo": "term-1"})
    assert cliente.llamadas == [("pedir_confirmacion", {"accion": "cerrar_terminal", "objetivo": "term-1"})]


@pytest.mark.asyncio
async def test_cerrar_terminal_relaya_terminal_y_confirmacion_id():
    cliente = _ClienteFalso()
    servidor = construir_servidor(cliente)
    await servidor.call_tool("cerrar_terminal", {"terminal": "term-1", "confirmacion_id": "abc"})
    assert cliente.llamadas == [("cerrar_terminal", {"terminal": "term-1", "confirmacion_id": "abc"})]


@pytest.mark.asyncio
async def test_eliminar_worktree_relaya_worktree_y_confirmacion_id():
    cliente = _ClienteFalso()
    servidor = construir_servidor(cliente)
    await servidor.call_tool("eliminar_worktree", {"worktree": "wt-1", "confirmacion_id": "abc"})
    assert cliente.llamadas == [("eliminar_worktree", {"worktree": "wt-1", "confirmacion_id": "abc"})]


@pytest.mark.asyncio
async def test_enviar_a_terminal_relaya_sin_confirmacion_id():
    cliente = _ClienteFalso()
    servidor = construir_servidor(cliente)
    await servidor.call_tool("enviar_a_terminal", {"terminal": "term-1", "texto": "hola"})
    assert cliente.llamadas == [
        ("enviar_a_terminal", {"terminal": "term-1", "texto": "hola", "confirmacion_id": None})
    ]


@pytest.mark.asyncio
async def test_herramientas_no_criticas_relayan_sin_argumentos_extra():
    cliente = _ClienteFalso()
    servidor = construir_servidor(cliente)

    await servidor.call_tool("media_pausar", {})
    await servidor.call_tool("media_reanudar", {})
    await servidor.call_tool("media_estado", {})
    await servidor.call_tool("overlay_estado", {"texto": "pensando"})
    await servidor.call_tool("sesion_relay_activar", {"terminal": "term-1"})
    await servidor.call_tool("sesion_relay_salir", {})
    await servidor.call_tool("monitorear_terminal", {"terminal": "term-1", "etiqueta": "apply"})
    await servidor.call_tool("listar_proyectos", {})
    await servidor.call_tool("config_modelos", {})

    nombres = [accion for accion, _ in cliente.llamadas]
    assert nombres == [
        "media_pausar", "media_reanudar", "media_estado", "overlay_estado",
        "sesion_relay_activar", "sesion_relay_salir", "monitorear_terminal",
        "listar_proyectos", "config_modelos",
    ]


# --- Integración real: canal local + manejadores + confirmación + MCP ---


@pytest.fixture
def entorno_critico():
    token = generar_token()
    registro = RegistroConfirmaciones()

    async def orca_ejecutor(argv: list[str]) -> str:
        # orca terminal show --terminal <handle> --json
        handle = argv[argv.index("--terminal") + 1]
        titulo = "✳ Claude Code" if handle == "term-claude" else "PowerShell"
        return json.dumps({"result": {"terminal": {"title": titulo}}})

    orca = Orca(ejecutor=orca_ejecutor)

    ejecutados: list[tuple] = []

    async def ejecutar_cerrar_terminal(terminal: str) -> dict:
        ejecutados.append(("cerrar_terminal", terminal))
        return {"terminal": terminal}

    async def ejecutar_eliminar_worktree(worktree: str) -> dict:
        ejecutados.append(("eliminar_worktree", worktree))
        return {"worktree": worktree}

    async def ejecutar_enviar_texto(terminal: str, texto: str) -> dict:
        ejecutados.append(("enviar_a_terminal", terminal, texto))
        return {"terminal": terminal}

    manejadores = ManejadoresCriticos(
        registro=registro,
        orca=orca,
        ejecutar_cerrar_terminal=ejecutar_cerrar_terminal,
        ejecutar_eliminar_worktree=ejecutar_eliminar_worktree,
        ejecutar_enviar_texto=ejecutar_enviar_texto,
    )

    canal = ServidorCanalLocal(puerto=0, token=token)
    canal.registrar("cerrar_terminal", manejadores.cerrar_terminal)
    canal.registrar("eliminar_worktree", manejadores.eliminar_worktree)
    canal.registrar("enviar_a_terminal", manejadores.enviar_a_terminal)
    canal.iniciar()

    cliente = ClienteCanalLocal(puerto=canal.puerto_real, token=token)
    servidor_mcp = construir_servidor(cliente)

    yield servidor_mcp, registro, ejecutados
    canal.detener()


@pytest.mark.asyncio
async def test_cerrar_terminal_sin_confirmacion_id_se_rechaza(entorno_critico):
    servidor_mcp, _registro, ejecutados = entorno_critico
    resultado = await servidor_mcp.call_tool("cerrar_terminal", {"terminal": "term-1", "confirmacion_id": ""})
    cuerpo = _texto_de(resultado)
    assert cuerpo.get("ejecutado") is False
    assert ejecutados == []


@pytest.mark.asyncio
async def test_cerrar_terminal_con_confirmacion_id_valido_se_ejecuta(entorno_critico):
    servidor_mcp, registro, ejecutados = entorno_critico
    id_ = registro.crear("cerrar_terminal", "term-1")
    registro.confirmar(id_)

    resultado = await servidor_mcp.call_tool(
        "cerrar_terminal", {"terminal": "term-1", "confirmacion_id": id_}
    )
    cuerpo = _texto_de(resultado)
    assert cuerpo.get("ejecutado") is True
    assert ejecutados == [("cerrar_terminal", "term-1")]


@pytest.mark.asyncio
async def test_eliminar_worktree_sin_confirmacion_id_se_rechaza(entorno_critico):
    servidor_mcp, _registro, ejecutados = entorno_critico
    resultado = await servidor_mcp.call_tool("eliminar_worktree", {"worktree": "wt-1", "confirmacion_id": ""})
    cuerpo = _texto_de(resultado)
    assert cuerpo.get("ejecutado") is False
    assert ejecutados == []


@pytest.mark.asyncio
async def test_eliminar_worktree_con_id_de_otra_accion_se_rechaza(entorno_critico):
    servidor_mcp, registro, ejecutados = entorno_critico
    id_ = registro.crear("cerrar_terminal", "term-1")  # confirmado para OTRA acción
    registro.confirmar(id_)

    resultado = await servidor_mcp.call_tool(
        "eliminar_worktree", {"worktree": "wt-1", "confirmacion_id": id_}
    )
    cuerpo = _texto_de(resultado)
    assert cuerpo.get("ejecutado") is False
    assert ejecutados == []


@pytest.mark.asyncio
async def test_enviar_a_terminal_a_sesion_claude_code_no_exige_confirmacion(entorno_critico):
    servidor_mcp, _registro, ejecutados = entorno_critico
    resultado = await servidor_mcp.call_tool(
        "enviar_a_terminal", {"terminal": "term-claude", "texto": "segui"}
    )
    cuerpo = _texto_de(resultado)
    assert cuerpo.get("ejecutado") is True
    assert ejecutados == [("enviar_a_terminal", "term-claude", "segui")]


@pytest.mark.asyncio
async def test_enviar_a_terminal_a_sesion_no_claude_sin_confirmacion_se_rechaza(entorno_critico):
    servidor_mcp, _registro, ejecutados = entorno_critico
    resultado = await servidor_mcp.call_tool(
        "enviar_a_terminal", {"terminal": "term-powershell", "texto": "rm -rf /"}
    )
    cuerpo = _texto_de(resultado)
    assert cuerpo.get("ejecutado") is False
    assert ejecutados == []


@pytest.mark.asyncio
async def test_enviar_a_terminal_a_sesion_no_claude_con_confirmacion_se_ejecuta(entorno_critico):
    servidor_mcp, registro, ejecutados = entorno_critico
    id_ = registro.crear("enviar_a_terminal_no_claude", "term-powershell")
    registro.confirmar(id_)

    resultado = await servidor_mcp.call_tool(
        "enviar_a_terminal",
        {"terminal": "term-powershell", "texto": "dir", "confirmacion_id": id_},
    )
    cuerpo = _texto_de(resultado)
    assert cuerpo.get("ejecutado") is True
    assert ejecutados == [("enviar_a_terminal", "term-powershell", "dir")]
