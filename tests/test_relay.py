import pytest

from loki.cerebro.relay import ClasificacionRelay, RelayVoz, TIMEOUT_TUI_IDLE_MS
from loki.cerebro.sesion import RegistroSesiones, SesionAgente
from loki.estados import MaquinaEstados


class _OrcaFalso:
    def __init__(self, texto_leido: str, siguiente_cursor: str = "99") -> None:
        self.llamadas: list[tuple] = []
        self._texto_leido = texto_leido
        self._siguiente_cursor = siguiente_cursor

    async def esperar_tui_idle(self, handle, timeout_ms):
        self.llamadas.append(("esperar_tui_idle", handle, timeout_ms))
        return {"result": {"idle": True}}

    async def leer(self, handle, cursor=None, limit=None):
        self.llamadas.append(("leer", handle, cursor))
        return {
            "result": {
                "terminal": {
                    "tail": [self._texto_leido],
                    "nextCursor": self._siguiente_cursor,
                }
            }
        }


class _CerebroFalso:
    def __init__(self, respuesta: str) -> None:
        self.turnos_recibidos: list[str] = []
        self._respuesta = respuesta

    async def enviar_turno(self, texto: str) -> str:
        self.turnos_recibidos.append(texto)
        return self._respuesta


def _entorno(respuesta_cerebro: str, texto_leido: str = "salida del agente"):
    registro = RegistroSesiones()
    sesion = SesionAgente(handle="term-1", repo="Andromeda", titulo="Claude Code", modelo="haiku", cursor="10")
    registro.registrar(sesion)
    registro.activar_relay("term-1")

    orca = _OrcaFalso(texto_leido=texto_leido)
    cerebro = _CerebroFalso(respuesta_cerebro)
    maquina = MaquinaEstados()
    relay = RelayVoz(registro, orca, cerebro, maquina)
    return relay, registro, orca, cerebro, maquina


@pytest.mark.asyncio
async def test_caso_termino():
    relay, _registro, orca, cerebro, maquina = _entorno("[TERMINO] Ya terminó de agregar la función.")
    resultado = await relay.esperar_leer_y_clasificar("term-1")

    assert resultado.clasificacion == ClasificacionRelay.TERMINO
    assert resultado.resumen == "Ya terminó de agregar la función."
    assert not maquina.hay_agentes_trabajando


@pytest.mark.asyncio
async def test_caso_pregunta():
    relay, *_ = _entorno("[PREGUNTA] Pregunta si querés que use TypeScript o JavaScript.")
    resultado = await relay.esperar_leer_y_clasificar("term-1")

    assert resultado.clasificacion == ClasificacionRelay.PREGUNTA
    assert "TypeScript" in resultado.resumen


@pytest.mark.asyncio
async def test_caso_permiso():
    relay, *_ = _entorno("[PERMISO] Quiere permiso para instalar una dependencia nueva.")
    resultado = await relay.esperar_leer_y_clasificar("term-1")

    assert resultado.clasificacion == ClasificacionRelay.PERMISO
    assert "permiso" in resultado.resumen.lower()


@pytest.mark.asyncio
async def test_espera_tui_idle_y_lee_desde_el_cursor_de_la_sesion():
    relay, _registro, orca, cerebro, _maquina = _entorno("[TERMINO] listo")
    await relay.esperar_leer_y_clasificar("term-1")

    assert orca.llamadas[0] == ("esperar_tui_idle", "term-1", TIMEOUT_TUI_IDLE_MS)
    assert orca.llamadas[1] == ("leer", "term-1", "10")


@pytest.mark.asyncio
async def test_actualiza_el_cursor_de_la_sesion_tras_leer():
    relay, registro, _orca, _cerebro, _maquina = _entorno("[TERMINO] listo")
    await relay.esperar_leer_y_clasificar("term-1")

    assert registro.obtener("term-1").cursor == "99"


@pytest.mark.asyncio
async def test_le_pasa_al_cerebro_la_instruccion_y_el_texto_leido():
    relay, _registro, _orca, cerebro, _maquina = _entorno("[TERMINO] listo", texto_leido="una respuesta cualquiera")
    await relay.esperar_leer_y_clasificar("term-1")

    assert len(cerebro.turnos_recibidos) == 1
    assert "una respuesta cualquiera" in cerebro.turnos_recibidos[0]
    assert "[TERMINO]" in cerebro.turnos_recibidos[0]


@pytest.mark.asyncio
async def test_handle_sin_sesion_registrada_lanza_error():
    registro = RegistroSesiones()
    orca = _OrcaFalso(texto_leido="")
    cerebro = _CerebroFalso("[TERMINO] listo")
    maquina = MaquinaEstados()
    relay = RelayVoz(registro, orca, cerebro, maquina)

    with pytest.raises(RuntimeError):
        await relay.esperar_leer_y_clasificar("term-que-no-existe")
