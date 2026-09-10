import pytest

from loki.cerebro.controlador_conversacion import ControladorConversacion
from loki.cerebro.sesion import RegistroSesiones, SesionAgente


class _CerebroFalso:
    def __init__(self) -> None:
        self.turnos: list[str] = []

    async def enviar_turno(self, texto: str) -> str:
        self.turnos.append(texto)
        return f"respuesta del cerebro a: {texto}"


def _entorno():
    registro = RegistroSesiones()
    registro.registrar(SesionAgente(handle="term-1", repo="Andromeda", titulo="Claude Code (tablero)", modelo="haiku"))
    cerebro = _CerebroFalso()
    overlay_llamadas: list[str | None] = []
    controlador = ControladorConversacion(registro, cerebro, overlay_llamadas.append)
    return controlador, registro, cerebro, overlay_llamadas


@pytest.mark.asyncio
async def test_todo_el_dictado_va_siempre_al_cerebro_haya_o_no_relay_activa():
    controlador, _registro, cerebro, _overlay = _entorno()
    respuesta = await controlador.procesar_dictado("hola")

    assert not controlador.en_relay
    assert cerebro.turnos == ["hola"]
    assert respuesta == "respuesta del cerebro a: hola"


@pytest.mark.asyncio
async def test_activar_relay_muestra_el_nombre_en_el_overlay_y_el_dictado_sigue_yendo_al_cerebro():
    controlador, _registro, cerebro, overlay = _entorno()
    controlador.activar_relay("term-1")

    assert controlador.en_relay
    assert overlay == ["Claude Code (tablero)"]

    respuesta = await controlador.procesar_dictado("segui con la tarea")
    assert cerebro.turnos == ["segui con la tarea"]
    assert respuesta == "respuesta del cerebro a: segui con la tarea"


@pytest.mark.asyncio
async def test_salir_del_relay_limpia_el_overlay_y_la_sesion_sigue_registrada():
    controlador, registro, cerebro, overlay = _entorno()
    controlador.activar_relay("term-1")

    controlador.salir_relay()

    assert not controlador.en_relay
    assert overlay[-1] is None
    # La sesión de agente sigue registrada, solo se salió del relay.
    assert registro.obtener("term-1") is not None

    respuesta = await controlador.procesar_dictado("hola de nuevo")
    assert cerebro.turnos == ["hola de nuevo"]
    assert respuesta == "respuesta del cerebro a: hola de nuevo"


def test_cambiar_de_sesion_actualiza_el_overlay_con_la_nueva():
    controlador, registro, _cerebro, overlay = _entorno()
    registro.registrar(SesionAgente(handle="term-2", repo="cvs", titulo="Claude Code (cvs)", modelo="sonnet"))

    controlador.activar_relay("term-1")
    controlador.cambiar_sesion("term-2")

    assert registro.relay_activa == "term-2"
    assert overlay == ["Claude Code (tablero)", "Claude Code (cvs)"]
