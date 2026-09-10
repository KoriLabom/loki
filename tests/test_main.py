"""Escucha de confirmación sin wake word (spec
confirmacion-de-acciones-criticas), wireada en `loki.main.Loki`.

Antes era un stub con TODO que siempre devolvía `None`: la confirmación
hablada nunca se completaba, encontrado con hardware real (tarea 10.3,
prueba C2)."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

import numpy as np
import pytest

from loki.herramientas.orca import ErrorOrca
from loki.main import Loki


@pytest.fixture
async def loki() -> Loki:
    instancia = Loki()
    instancia._loop_asyncio = asyncio.get_running_loop()
    instancia._grabador = SimpleNamespace(tasa_efectiva=16000)
    return instancia


def _bloque(rms: float, muestras: int = 400) -> np.ndarray:
    return np.full(muestras, rms, dtype="float32")


async def _alimentar_tras_arrancar(loki: Loki, bloques: list[np.ndarray]) -> None:
    await asyncio.sleep(0)  # deja que _escuchar_para_confirmacion arme su estado
    for bloque in bloques:
        loki._on_bloque_audio(bloque)


@pytest.mark.asyncio
async def test_respuesta_hablada_se_transcribe(loki: Loki):
    loki.transcriber.transcribe = lambda audio, tasa: "sí, confirmo"

    bloques = [_bloque(0.05) for _ in range(20)] + [_bloque(0.0) for _ in range(60)]
    tarea_alimentar = asyncio.create_task(_alimentar_tras_arrancar(loki, bloques))
    texto = await loki._escuchar_para_confirmacion(espera_s=10.0)
    await tarea_alimentar

    assert texto == "sí, confirmo"
    assert loki._escuchando_confirmacion is False
    assert loki._futuro_confirmacion is None


@pytest.mark.asyncio
async def test_sin_voz_devuelve_none_sin_transcribir(loki: Loki):
    llamado = False

    def _transcribe(audio, tasa):
        nonlocal llamado
        llamado = True
        return "no debería llegar acá"

    loki.transcriber.transcribe = _transcribe

    bloques = [_bloque(0.0) for _ in range(40)]
    tarea_alimentar = asyncio.create_task(_alimentar_tras_arrancar(loki, bloques))
    texto = await loki._escuchar_para_confirmacion(espera_s=1.0)
    await tarea_alimentar

    assert texto is None
    assert llamado is False


@pytest.mark.asyncio
async def test_primera_oracion_lista_espera_una_oracion_real(loki: Loki):
    """Antes `primera_oracion_lista()` se llamaba apenas arrancaba el
    turno (antes de que el cerebro generara nada): el overlay mostraba
    "hablando" segundos antes de que sonara audio (hardware real, tarea
    10.3)."""
    from loki.estados import Estado

    loki.maquina._estado = Estado.ESCUCHANDO
    loki.maquina.fin_de_voz()
    loki._primera_oracion_pendiente = True
    assert loki.maquina.estado == Estado.PENSANDO

    loki._on_texto_parcial_cerebro("todavía sin punto final")
    assert loki.maquina.estado == Estado.PENSANDO

    loki._on_texto_parcial_cerebro(" ahora sí. ")
    assert loki.maquina.estado == Estado.HABLANDO


@pytest.mark.asyncio
async def test_primera_oracion_lista_se_dispara_al_final_si_nunca_hubo_una_oracion_completa(loki: Loki):
    """Resguardo: si la respuesta entera no tuvo puntuación final, el
    estado no debe quedarse en "pensando" para siempre."""
    from loki.estados import Estado

    async def enviar_turno_falso(texto):
        loki._on_texto_parcial_cerebro("una respuesta sin punto final")
        return "una respuesta sin punto final"

    async def hablar_oraciones_falso(*args, **kwargs):
        return None

    import loki.main as main_mod

    original = main_mod.hablar_oraciones
    main_mod.hablar_oraciones = hablar_oraciones_falso
    loki.cerebro.enviar_turno = enviar_turno_falso
    loki.maquina._estado = Estado.ESCUCHANDO

    tarea_consumidor = asyncio.create_task(loki._consumir_cola_habla())
    try:
        await loki._procesar_turno("hola")
    finally:
        tarea_consumidor.cancel()
        main_mod.hablar_oraciones = original

    assert loki.maquina.estado == Estado.DORMIDO  # fin_de_reproduccion() sí pudo transicionar


@pytest.mark.asyncio
async def test_las_oraciones_se_encolan_en_orden_de_generacion_no_de_sintesis(loki: Loki):
    """Antes cada oración disparaba su propia tarea concurrente de síntesis
    (`asyncio.run_coroutine_threadsafe` por oración): la que ganaba la
    carrera de red de edge-tts se escuchaba primero, sin importar el
    orden en que el cerebro las generó (hardware real, tarea 10.3, V2:
    viola "orden preservado" de la spec voz-de-salida)."""
    encoladas: list[str] = []
    demoras = {"uno": 0.06, "dos": 0.01, "tres": 0.03}

    async def hablar_oraciones_falso(oraciones, texto_completo, voz, reproductor, on_fallo_sintesis=None, sintetizador=None):
        clave = texto_completo.rstrip(".")
        await asyncio.sleep(demoras.get(clave, 0.0))
        encoladas.append(clave)

    import loki.main as main_mod

    monkeypatch_objetivo = main_mod.hablar_oraciones
    main_mod.hablar_oraciones = hablar_oraciones_falso
    try:
        tarea_consumidor = asyncio.create_task(loki._consumir_cola_habla())
        loki._on_texto_parcial_cerebro("uno. dos. tres. ")
        await asyncio.wait_for(loki._cola_habla.join(), timeout=2)
    finally:
        tarea_consumidor.cancel()
        main_mod.hablar_oraciones = monkeypatch_objetivo

    assert encoladas == ["uno", "dos", "tres"]


@pytest.mark.asyncio
async def test_ejecutar_cerrar_terminal_reporta_ok_true_si_orca_lo_confirma(loki: Loki):
    async def cerrar_terminal_falso(handle):
        return {"result": {}}

    loki.orca.cerrar_terminal = cerrar_terminal_falso
    resultado = await loki._ejecutar_cerrar_terminal("term_abc123")
    assert resultado == {"terminal": "term_abc123", "ok": True}


@pytest.mark.asyncio
async def test_ejecutar_cerrar_terminal_reporta_el_fallo_en_vez_de_afirmar_exito(loki: Loki):
    """Antes se ignoraba el resultado del subproceso de `orca terminal
    close` y siempre se afirmaba éxito, aunque el `terminal` no fuera un
    handle válido (hardware real, tarea 10.3, C2: el cerebro pasó una
    descripción en vez del handle y Loki igual dijo "listo, lo hago")."""

    async def cerrar_terminal_falso(handle):
        raise ErrorOrca("terminal_handle_stale")

    loki.orca.cerrar_terminal = cerrar_terminal_falso
    resultado = await loki._ejecutar_cerrar_terminal("prueba 1")
    assert resultado == {"terminal": "prueba 1", "ok": False, "error": "terminal_handle_stale"}


@pytest.mark.asyncio
async def test_ejecutar_eliminar_worktree_reporta_el_fallo(loki: Loki):
    async def eliminar_worktree_falso(worktree):
        raise ErrorOrca("worktree no encontrado")

    loki.orca.eliminar_worktree = eliminar_worktree_falso
    resultado = await loki._ejecutar_eliminar_worktree("path:/repo/x")
    assert resultado == {"worktree": "path:/repo/x", "ok": False, "error": "worktree no encontrado"}


@pytest.mark.asyncio
async def test_no_interfiere_con_el_dictado_normal_mientras_escucha(loki: Loki):
    """Mientras se espera una confirmación, los bloques no deben caer en
    el buffer de dictado normal aunque el estado sea ESCUCHANDO."""
    from loki.audio.fin_de_frase import DetectorFinDeFrase
    from loki.estados import Estado

    loki._detector_fin_de_frase = DetectorFinDeFrase()
    loki.maquina._estado = Estado.ESCUCHANDO  # fuerza el estado sin pasar por transición
    loki.transcriber.transcribe = lambda audio, tasa: "sí"

    bloques = [_bloque(0.05) for _ in range(5)] + [_bloque(0.0) for _ in range(40)]
    tarea_alimentar = asyncio.create_task(_alimentar_tras_arrancar(loki, bloques))
    await loki._escuchar_para_confirmacion(espera_s=1.0)
    await tarea_alimentar

    assert loki._buffer_frase == []
