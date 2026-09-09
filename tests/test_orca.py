import json

import pytest

from loki.herramientas.orca import Orca, extraer_texto_y_cursor


def _orca_con_ejecutor(respuestas: dict | list | None = None):
    llamadas: list[list[str]] = []

    async def ejecutor(argv: list[str]) -> str:
        llamadas.append(argv)
        return json.dumps(respuestas if respuestas is not None else {"ok": True})

    return Orca(ejecutor=ejecutor), llamadas


@pytest.mark.asyncio
async def test_listar_repos_arma_el_comando_correcto():
    orca, llamadas = _orca_con_ejecutor()
    await orca.listar_repos()
    assert llamadas == [["repo", "list", "--json"]]


@pytest.mark.asyncio
async def test_listar_terminales_sin_worktree():
    orca, llamadas = _orca_con_ejecutor()
    await orca.listar_terminales()
    assert llamadas == [["terminal", "list", "--json"]]


@pytest.mark.asyncio
async def test_listar_terminales_con_worktree():
    orca, llamadas = _orca_con_ejecutor()
    await orca.listar_terminales(worktree="active")
    assert llamadas == [["terminal", "list", "--worktree", "active", "--json"]]


@pytest.mark.asyncio
async def test_mostrar_terminal():
    orca, llamadas = _orca_con_ejecutor()
    await orca.mostrar_terminal("term_abc123")
    assert llamadas == [["terminal", "show", "--terminal", "term_abc123", "--json"]]


@pytest.mark.asyncio
async def test_crear_terminal_con_comando_y_modelo():
    orca, llamadas = _orca_con_ejecutor()
    await orca.crear_terminal("path:/repo", "claude --model haiku")
    assert llamadas == [
        ["terminal", "create", "--worktree", "path:/repo", "--command", "claude --model haiku", "--json"]
    ]


@pytest.mark.asyncio
async def test_crear_terminal_con_titulo_y_focus():
    orca, llamadas = _orca_con_ejecutor()
    await orca.crear_terminal("active", "codex", titulo="RUNNER", focus=True)
    assert llamadas == [
        [
            "terminal", "create", "--worktree", "active", "--command", "codex",
            "--title", "RUNNER", "--focus", "--json",
        ]
    ]


@pytest.mark.asyncio
async def test_enviar_texto_con_enter():
    orca, llamadas = _orca_con_ejecutor()
    await orca.enviar_texto("term_1", "hola")
    assert llamadas == [["terminal", "send", "--terminal", "term_1", "--text", "hola", "--enter", "--json"]]


@pytest.mark.asyncio
async def test_enviar_texto_sin_enter():
    orca, llamadas = _orca_con_ejecutor()
    await orca.enviar_texto("term_1", "hola", enter=False)
    assert llamadas == [["terminal", "send", "--terminal", "term_1", "--text", "hola", "--json"]]


@pytest.mark.asyncio
async def test_esperar_tui_idle():
    orca, llamadas = _orca_con_ejecutor()
    await orca.esperar_tui_idle("term_1", timeout_ms=600000)
    assert llamadas == [
        ["terminal", "wait", "--terminal", "term_1", "--for", "tui-idle", "--timeout-ms", "600000", "--json"]
    ]


@pytest.mark.asyncio
async def test_leer_con_cursor_y_limit():
    orca, llamadas = _orca_con_ejecutor()
    await orca.leer("term_1", cursor=42, limit=1000)
    assert llamadas == [
        ["terminal", "read", "--terminal", "term_1", "--cursor", "42", "--limit", "1000", "--json"]
    ]


@pytest.mark.asyncio
async def test_leer_sin_cursor_ni_limit():
    orca, llamadas = _orca_con_ejecutor()
    await orca.leer("term_1")
    assert llamadas == [["terminal", "read", "--terminal", "term_1", "--json"]]


@pytest.mark.asyncio
async def test_crear_worktree_sin_agente_no_agrega_flag_agent():
    orca, llamadas = _orca_con_ejecutor()
    await orca.crear_worktree_sin_agente("id:repo123", "mi-change")
    argv = llamadas[0]
    assert argv == ["worktree", "create", "--repo", "id:repo123", "--name", "mi-change", "--json"]
    assert "--agent" not in argv


@pytest.mark.asyncio
async def test_crear_worktree_con_base_branch():
    orca, llamadas = _orca_con_ejecutor()
    await orca.crear_worktree_sin_agente("id:repo123", "mi-change", base_branch="develop")
    assert llamadas == [
        [
            "worktree", "create", "--repo", "id:repo123", "--name", "mi-change",
            "--base-branch", "develop", "--json",
        ]
    ]


@pytest.mark.asyncio
async def test_cerrar_terminal_arma_el_comando_correcto():
    orca, llamadas = _orca_con_ejecutor()
    await orca.cerrar_terminal("term_abc123")
    assert llamadas == [["terminal", "close", "--terminal", "term_abc123", "--json"]]


@pytest.mark.asyncio
async def test_eliminar_worktree_arma_el_comando_correcto():
    orca, llamadas = _orca_con_ejecutor()
    await orca.eliminar_worktree("path:/repo/worktree")
    assert llamadas == [["worktree", "rm", "--worktree", "path:/repo/worktree", "--json"]]


@pytest.mark.asyncio
async def test_resultado_se_parsea_como_json():
    orca, _ = _orca_con_ejecutor(respuestas={"result": {"handle": "term_abc"}})
    resultado = await orca.mostrar_terminal("term_abc")
    assert resultado == {"result": {"handle": "term_abc"}}


def test_extraer_texto_y_cursor_de_la_forma_real_del_cli():
    # Forma real de `orca terminal read --json` (no `result.text`/`result.output`,
    # que era un supuesto sin verificar corregido en la tarea 9.2).
    resultado_leer = {
        "result": {
            "terminal": {
                "tail": ["primera línea", "segunda línea"],
                "nextCursor": "42",
            }
        }
    }
    texto, cursor = extraer_texto_y_cursor(resultado_leer)
    assert texto == "primera línea\nsegunda línea"
    assert cursor == "42"


def test_extraer_texto_y_cursor_sin_tail_devuelve_vacio():
    texto, cursor = extraer_texto_y_cursor({"result": {"terminal": {}}})
    assert texto == ""
    assert cursor is None
