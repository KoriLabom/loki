import pytest
from PyQt6.QtGui import QIcon

from loki.ui.bandeja import Bandeja


def _bandeja(qapp, **overrides):
    async def _noop():
        return None

    defaults = dict(
        icono=QIcon(),
        on_alternar_overlay=lambda: None,
        on_reiniciar_conversacion=lambda: None,
        cerrar_audio=_noop,
        cerrar_cerebro=_noop,
        cerrar_canal_local=_noop,
    )
    defaults.update(overrides)
    return Bandeja(**defaults)


def test_menu_tiene_las_tres_acciones(qapp):
    bandeja = _bandeja(qapp)
    textos = [accion.text() for accion in bandeja.contextMenu().actions() if accion.text()]
    assert textos == ["Mostrar/Ocultar overlay", "Reiniciar conversación", "Salir"]


def test_alternar_overlay_llama_al_callback(qapp):
    llamado = []
    bandeja = _bandeja(qapp, on_alternar_overlay=lambda: llamado.append(True))
    bandeja.accion_overlay.trigger()
    assert llamado == [True]


def test_reiniciar_conversacion_llama_al_callback(qapp):
    llamado = []
    bandeja = _bandeja(qapp, on_reiniciar_conversacion=lambda: llamado.append(True))
    bandeja.accion_reiniciar.trigger()
    assert llamado == [True]


@pytest.mark.asyncio
async def test_cerrar_todo_cierra_en_orden_audio_cerebro_canal_local(qapp):
    orden: list[str] = []

    async def cerrar_audio():
        orden.append("audio")

    async def cerrar_cerebro():
        orden.append("cerebro")

    async def cerrar_canal_local():
        orden.append("canal local")

    bandeja = _bandeja(
        qapp,
        cerrar_audio=cerrar_audio,
        cerrar_cerebro=cerrar_cerebro,
        cerrar_canal_local=cerrar_canal_local,
    )

    await bandeja._cerrar_todo()

    assert orden == ["audio", "cerebro", "canal local"]


@pytest.mark.asyncio
async def test_cerrar_todo_sigue_aunque_uno_falle(qapp):
    orden: list[str] = []

    async def cerrar_audio():
        orden.append("audio")
        raise RuntimeError("el stream ya estaba cerrado")

    async def cerrar_cerebro():
        orden.append("cerebro")

    async def cerrar_canal_local():
        orden.append("canal local")

    bandeja = _bandeja(
        qapp,
        cerrar_audio=cerrar_audio,
        cerrar_cerebro=cerrar_cerebro,
        cerrar_canal_local=cerrar_canal_local,
    )

    await bandeja._cerrar_todo()  # no debe lanzar

    assert orden == ["audio", "cerebro", "canal local"]
