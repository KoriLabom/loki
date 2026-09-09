import asyncio

import pytest

from loki.estados import MaquinaEstados
from loki.herramientas.coordinador_media import CoordinadorMedia
from loki.herramientas.monitor import MonitorTerminal


class _OrcaFalso:
    def __init__(self, texto_leido: str) -> None:
        self._texto_leido = texto_leido
        self.llamadas: list[tuple] = []

    async def esperar_tui_idle(self, handle, timeout_ms):
        self.llamadas.append(("esperar_tui_idle", handle))
        return {"result": {"idle": True}}

    async def leer(self, handle, cursor=None, limit=None):
        self.llamadas.append(("leer", handle, cursor))
        return {"result": {"terminal": {"tail": [self._texto_leido], "nextCursor": "5"}}}


class _CerebroFalso:
    def __init__(self, respuesta: str) -> None:
        self._respuesta = respuesta
        self.turnos: list[str] = []

    async def enviar_turno(self, texto: str) -> str:
        self.turnos.append(texto)
        return self._respuesta


class _ControlMediaFalso:
    def __init__(self) -> None:
        self.llamadas: list[str] = []

    async def pausar_si_hay_reproduccion(self) -> None:
        self.llamadas.append("pausar")

    async def reanudar(self) -> None:
        self.llamadas.append("reanudar")


@pytest.mark.asyncio
async def test_ejecutar_espera_lee_clasifica_y_da_el_aviso():
    orca = _OrcaFalso(texto_leido="El agente terminó de implementar la función.")
    cerebro = _CerebroFalso("[TERMINO] Terminó de implementar la función.")
    maquina = MaquinaEstados()
    control_media = _ControlMediaFalso()
    coordinador = CoordinadorMedia(maquina, control_media, segundos_espera_aviso=0.02)

    dichos: list[str] = []

    async def on_hablar(texto: str) -> None:
        dichos.append(texto)

    monitor = MonitorTerminal(
        terminal="term-apply-1",
        etiqueta="apply",
        nombre_proyecto="Nebulosa",
        orca=orca,
        cerebro=cerebro,
        coordinador_media=coordinador,
        on_hablar=on_hablar,
    )

    aviso = await monitor.ejecutar()

    assert aviso.clasificacion == "termino"
    assert aviso.nombre_proyecto == "Nebulosa"
    assert aviso.etiqueta == "apply"
    assert "Nebulosa" in aviso.texto_hablado
    assert "apply" in aviso.texto_hablado
    assert dichos == [aviso.texto_hablado]
    assert control_media.llamadas == ["pausar", "reanudar"]


@pytest.mark.asyncio
async def test_dos_monitores_simultaneos_producen_avisos_identificables():
    maquina = MaquinaEstados()
    control_media = _ControlMediaFalso()
    coordinador = CoordinadorMedia(maquina, control_media, segundos_espera_aviso=0.02)

    orca_a = _OrcaFalso(texto_leido="Terminé de agregar el endpoint.")
    cerebro_a = _CerebroFalso("[TERMINO] Terminé de agregar el endpoint.")
    monitor_a = MonitorTerminal(
        terminal="term-a",
        etiqueta="apply",
        nombre_proyecto="Nebulosa",
        orca=orca_a,
        cerebro=cerebro_a,
        coordinador_media=coordinador,
    )

    orca_b = _OrcaFalso(texto_leido="Necesito que confirmes instalar una dependencia.")
    cerebro_b = _CerebroFalso("[PERMISO] Necesita permiso para instalar una dependencia.")
    monitor_b = MonitorTerminal(
        terminal="term-b",
        etiqueta="apply",
        nombre_proyecto="Andromeda",
        orca=orca_b,
        cerebro=cerebro_b,
        coordinador_media=coordinador,
    )

    aviso_a, aviso_b = await asyncio.gather(monitor_a.ejecutar(), monitor_b.ejecutar())

    assert aviso_a.nombre_proyecto == "Nebulosa"
    assert aviso_a.clasificacion == "termino"
    assert aviso_b.nombre_proyecto == "Andromeda"
    assert aviso_b.clasificacion == "permiso"
    assert aviso_a.texto_hablado != aviso_b.texto_hablado
    assert "Nebulosa" in aviso_a.texto_hablado and "Andromeda" not in aviso_a.texto_hablado
    assert "Andromeda" in aviso_b.texto_hablado and "Nebulosa" not in aviso_b.texto_hablado
