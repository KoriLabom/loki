import asyncio
import json

import pytest

from loki.cerebro.claude_headless import (
    CerebroHeadless,
    ConfigCerebro,
    TurnoTimeoutError,
    _armar_comando,
)


class _FakeStdin:
    def __init__(self) -> None:
        self.escrito: list[bytes] = []

    def write(self, data: bytes) -> None:
        self.escrito.append(data)

    async def drain(self) -> None:
        return None


class _FakeStdout:
    def __init__(self, lineas: list[bytes]) -> None:
        self._lineas = list(lineas)

    async def readline(self) -> bytes:
        if not self._lineas:
            return b""
        return self._lineas.pop(0)


class _FakeStdoutBloqueado:
    async def readline(self) -> bytes:
        await asyncio.sleep(10)
        return b""


class _FakeProceso:
    def __init__(self, lineas_stdout: list[bytes], stdout=None) -> None:
        self.stdin = _FakeStdin()
        self.stdout = stdout if stdout is not None else _FakeStdout(lineas_stdout)
        self.returncode: int | None = None

    async def wait(self) -> int:
        if self.returncode is None:
            self.returncode = 0
        return self.returncode

    def kill(self) -> None:
        self.returncode = -9


def _evento_delta(texto: str) -> bytes:
    return (
        json.dumps({"type": "stream_event", "event": {"type": "content_block_delta", "delta": {"type": "text_delta", "text": texto}}})
        + "\n"
    ).encode("utf-8")


def _evento_result() -> bytes:
    return json.dumps({"type": "result", "stop_reason": "end_turn"}).encode("utf-8") + b"\n"


def _config(tmp_path, **overrides) -> ConfigCerebro:
    persona = tmp_path / "system_prompt.md"
    persona.write_text("Sos Loki.", encoding="utf-8")
    base = dict(modelo="haiku", ruta_persona=persona, cwd=tmp_path)
    base.update(overrides)
    return ConfigCerebro(**base)


def test_arma_comando_con_flags_de_d1_d2(tmp_path):
    config = _config(
        tmp_path,
        allowed_tools=["Bash(orca *)", "Read"],
        disallowed_tools=["Write", "Edit"],
    )
    cmd = _armar_comando(config)

    assert cmd[0] == "claude"
    assert "-p" in cmd
    assert cmd[cmd.index("--input-format") + 1] == "stream-json"
    assert cmd[cmd.index("--output-format") + 1] == "stream-json"
    assert "--include-partial-messages" in cmd
    assert "--verbose" in cmd
    assert cmd[cmd.index("--model") + 1] == "haiku"
    assert cmd[cmd.index("--system-prompt") + 1] == "Sos Loki."
    assert cmd[cmd.index("--setting-sources") + 1] == "project"
    assert cmd[cmd.index("--permission-mode") + 1] == "manual"
    assert cmd[cmd.index("--permission-prompts") + 1] == "none"
    i = cmd.index("--allowedTools")
    assert cmd[i + 1 : i + 3] == ["Bash(orca *)", "Read"]
    j = cmd.index("--disallowedTools")
    assert cmd[j + 1 : j + 3] == ["Write", "Edit"]


def test_arma_comando_sin_listas_de_herramientas_no_agrega_flags(tmp_path):
    config = _config(tmp_path)
    cmd = _armar_comando(config)
    assert "--allowedTools" not in cmd
    assert "--disallowedTools" not in cmd


@pytest.mark.asyncio
async def test_enviar_turno_entrega_deltas_en_orden_y_detecta_fin(tmp_path):
    lineas = [
        _evento_delta("Hola"),
        _evento_delta(" mundo"),
        _evento_delta("."),
        _evento_result(),
    ]
    proceso = _FakeProceso(lineas)
    deltas_recibidos: list[str] = []

    async def lanzador(cmd, cwd):
        return proceso

    cerebro = CerebroHeadless(
        _config(tmp_path),
        on_texto_parcial=deltas_recibidos.append,
        lanzador=lanzador,
    )
    await cerebro.iniciar()
    respuesta = await cerebro.enviar_turno("hola")

    assert deltas_recibidos == ["Hola", " mundo", "."]
    assert respuesta == "Hola mundo."


@pytest.mark.asyncio
async def test_enviar_turno_escribe_mensaje_de_usuario_en_stdin(tmp_path):
    proceso = _FakeProceso([_evento_result()])

    async def lanzador(cmd, cwd):
        return proceso

    cerebro = CerebroHeadless(_config(tmp_path), lanzador=lanzador)
    await cerebro.iniciar()
    await cerebro.enviar_turno("como estas")

    escrito = json.loads(proceso.stdin.escrito[0].decode("utf-8").strip())
    assert escrito["type"] == "user"
    assert escrito["message"]["content"][0]["text"] == "como estas"


@pytest.mark.asyncio
async def test_turnos_concurrentes_se_serializan_sin_mezclar_resultados(tmp_path):
    # Dos turnos disparados a la vez (por ejemplo una clasificación de
    # relay en segundo plano y un nuevo dictado del usuario) comparten un
    # único stdin/stdout: si no se serializan, uno puede leer líneas del
    # otro turno. El buffer simula ese único stream compartido.
    lineas_compartidas = [
        _evento_delta("primer turno, "),
        _evento_delta("parte dos. "),
        _evento_result(),
        _evento_delta("segundo turno, "),
        _evento_delta("parte dos. "),
        _evento_result(),
    ]
    proceso = _FakeProceso(lineas_compartidas)

    async def lanzador(cmd, cwd):
        return proceso

    cerebro = CerebroHeadless(_config(tmp_path), lanzador=lanzador)
    await cerebro.iniciar()

    resultado_1, resultado_2 = await asyncio.gather(
        cerebro.enviar_turno("hola"), cerebro.enviar_turno("chau")
    )

    assert resultado_1 == "primer turno, parte dos. "
    assert resultado_2 == "segundo turno, parte dos. "


@pytest.mark.asyncio
async def test_detener_mata_el_proceso_si_sigue_vivo(tmp_path):
    proceso = _FakeProceso([])

    async def lanzador(cmd, cwd):
        return proceso

    cerebro = CerebroHeadless(_config(tmp_path), lanzador=lanzador)
    await cerebro.iniciar()
    assert cerebro.esta_vivo
    await cerebro.detener()

    assert proceso.returncode == -9
    assert not cerebro.esta_vivo


@pytest.mark.asyncio
async def test_reiniciar_conversacion_mata_y_relanza(tmp_path):
    procesos = [_FakeProceso([_evento_result()]), _FakeProceso([_evento_result()])]
    llamados: list[_FakeProceso] = []

    async def lanzador(cmd, cwd):
        p = procesos[len(llamados)]
        llamados.append(p)
        return p

    cerebro = CerebroHeadless(_config(tmp_path), lanzador=lanzador)
    await cerebro.iniciar()
    primero = cerebro._proceso
    await cerebro.reiniciar_conversacion()
    segundo = cerebro._proceso

    assert primero is procesos[0]
    assert segundo is procesos[1]
    assert primero.returncode == -9
    assert segundo.returncode is None


@pytest.mark.asyncio
async def test_reintenta_relanzando_si_el_proceso_murio_a_mitad_de_turno(tmp_path):
    proceso_muerto = _FakeProceso([])  # stdout vacío -> ConnectionError al primer readline
    proceso_nuevo = _FakeProceso([_evento_result()])
    procesos = [proceso_muerto, proceso_nuevo]

    async def lanzador(cmd, cwd):
        return procesos.pop(0)

    cerebro = CerebroHeadless(_config(tmp_path), lanzador=lanzador)
    await cerebro.iniciar()
    respuesta = await cerebro.enviar_turno("hola de nuevo")

    assert respuesta == ""
    assert cerebro._proceso is proceso_nuevo
    assert proceso_nuevo.stdin.escrito  # el turno se reintentó contra el proceso nuevo


@pytest.mark.asyncio
async def test_timeout_de_turno_levanta_turno_timeout_error(tmp_path):
    proceso = _FakeProceso([], stdout=_FakeStdoutBloqueado())

    async def lanzador(cmd, cwd):
        return proceso

    cerebro = CerebroHeadless(_config(tmp_path, timeout_turno_s=0.05), lanzador=lanzador)
    await cerebro.iniciar()

    with pytest.raises(TurnoTimeoutError):
        await cerebro.enviar_turno("hola")
