import asyncio

import pytest

from loki.estados import Estado, MaquinaEstados
from loki.herramientas.coordinador_media import CoordinadorMedia


class _ControlMediaFalso:
    def __init__(self) -> None:
        self.llamadas: list[str] = []

    async def pausar_si_hay_reproduccion(self) -> None:
        self.llamadas.append("pausar")

    async def reanudar(self) -> None:
        self.llamadas.append("reanudar")


@pytest.mark.asyncio
async def test_wake_word_pausa_media_al_pasar_a_escuchando():
    maquina = MaquinaEstados()
    control = _ControlMediaFalso()
    coordinador = CoordinadorMedia(maquina, control)

    maquina.wake_word_detectada()
    await coordinador.esperar_tareas_pendientes()

    assert control.llamadas == ["pausar"]


@pytest.mark.asyncio
async def test_volver_a_dormido_sin_confirmacion_pendiente_reanuda():
    maquina = MaquinaEstados(estado_inicial=Estado.HABLANDO)
    control = _ControlMediaFalso()
    coordinador = CoordinadorMedia(maquina, control, hay_confirmacion_pendiente=lambda: False)

    maquina.fin_de_reproduccion()
    await coordinador.esperar_tareas_pendientes()

    assert control.llamadas == ["reanudar"]


@pytest.mark.asyncio
async def test_volver_a_dormido_con_confirmacion_pendiente_no_reanuda():
    maquina = MaquinaEstados(estado_inicial=Estado.HABLANDO)
    control = _ControlMediaFalso()
    coordinador = CoordinadorMedia(maquina, control, hay_confirmacion_pendiente=lambda: True)

    maquina.fin_de_reproduccion()
    await coordinador.esperar_tareas_pendientes()

    assert control.llamadas == []


@pytest.mark.asyncio
async def test_dar_aviso_pausa_habla_espera_y_reanuda_si_no_hay_activacion():
    maquina = MaquinaEstados()
    control = _ControlMediaFalso()
    coordinador = CoordinadorMedia(maquina, control, segundos_espera_aviso=0.05)

    habló = []

    async def hablar():
        habló.append(True)

    await coordinador.dar_aviso(hablar)

    assert control.llamadas == ["pausar", "reanudar"]
    assert habló == [True]


@pytest.mark.asyncio
async def test_dar_aviso_no_reanuda_si_el_usuario_activa_durante_la_espera():
    maquina = MaquinaEstados()
    control = _ControlMediaFalso()
    coordinador = CoordinadorMedia(maquina, control, segundos_espera_aviso=2.0)

    async def hablar():
        # Simula que, mientras se anuncia, el usuario dice la palabra de
        # activación (otro hilo/tarea la detectaría en la app real).
        pass

    async def activar_pronto():
        await asyncio.sleep(0.05)
        maquina.wake_word_detectada()

    tarea_activacion = asyncio.ensure_future(activar_pronto())
    await coordinador.dar_aviso(hablar)
    await tarea_activacion
    await coordinador.esperar_tareas_pendientes()

    # "pausar" por dar_aviso, y otro "pausar" disparado por la transición a
    # escuchando (interrupción); nunca un "reanudar" del timeout del aviso.
    assert control.llamadas == ["pausar", "pausar"]
