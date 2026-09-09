import pytest
from winrt.windows.media.control import (
    GlobalSystemMediaTransportControlsSessionPlaybackStatus as EstadoReproduccion,
)

from loki.herramientas.media import ControlMedia


class _InfoFalsa:
    def __init__(self, playback_status) -> None:
        self.playback_status = playback_status


class _SesionFalsa:
    def __init__(self, id_sesion: str, estado) -> None:
        self.source_app_user_model_id = id_sesion
        self._estado = estado
        self.pausada = False
        self.reanudada = False

    def get_playback_info(self) -> _InfoFalsa:
        return _InfoFalsa(self._estado)

    async def try_pause_async(self) -> bool:
        self.pausada = True
        self._estado = EstadoReproduccion.PAUSED
        return True

    async def try_play_async(self) -> bool:
        self.reanudada = True
        self._estado = EstadoReproduccion.PLAYING
        return True


class _ManagerFalso:
    def __init__(self, sesion: _SesionFalsa | None) -> None:
        self._sesion = sesion

    def get_current_session(self) -> _SesionFalsa | None:
        return self._sesion


def _control_con(sesion: _SesionFalsa | None) -> ControlMedia:
    async def fabrica():
        return _ManagerFalso(sesion)

    return ControlMedia(fabrica_manager=fabrica, forzar_fallback=False)


@pytest.mark.asyncio
async def test_video_reproduciendose_se_pausa_y_recuerda_la_sesion():
    sesion = _SesionFalsa("youtube", EstadoReproduccion.PLAYING)
    control = _control_con(sesion)

    await control.pausar_si_hay_reproduccion()

    assert sesion.pausada
    assert control._id_sesion_pausada == "youtube"


@pytest.mark.asyncio
async def test_nada_reproduciendose_no_envia_ninguna_orden():
    control = _control_con(None)

    await control.pausar_si_hay_reproduccion()

    assert control._id_sesion_pausada is None


@pytest.mark.asyncio
async def test_media_ya_pausado_no_se_toca_y_no_se_reanuda_despues():
    sesion = _SesionFalsa("spotify", EstadoReproduccion.PAUSED)
    control = _control_con(sesion)

    await control.pausar_si_hay_reproduccion()
    assert not sesion.pausada
    assert control._id_sesion_pausada is None

    await control.reanudar()
    assert not sesion.reanudada


@pytest.mark.asyncio
async def test_reanudar_reproduce_solo_la_sesion_que_se_pauso():
    sesion = _SesionFalsa("youtube", EstadoReproduccion.PLAYING)
    control = _control_con(sesion)

    await control.pausar_si_hay_reproduccion()
    await control.reanudar()

    assert sesion.reanudada


@pytest.mark.asyncio
async def test_reanudar_no_toca_una_sesion_distinta_a_la_que_se_pauso():
    sesion_original = _SesionFalsa("youtube", EstadoReproduccion.PLAYING)
    control = _control_con(sesion_original)
    await control.pausar_si_hay_reproduccion()

    # Entre medio, cambió la sesión activa (por ejemplo el usuario abrió otra app).
    otra_sesion = _SesionFalsa("spotify", EstadoReproduccion.PAUSED)

    async def fabrica_otra():
        return _ManagerFalso(otra_sesion)

    control._fabrica_manager = fabrica_otra
    await control.reanudar()

    assert not otra_sesion.reanudada


@pytest.mark.asyncio
async def test_fallo_al_consultar_sesion_no_interrumpe_la_interaccion():
    async def fabrica_que_falla():
        raise RuntimeError("API de media no disponible")

    control = ControlMedia(fabrica_manager=fabrica_que_falla, forzar_fallback=False)

    # No debe lanzar excepción.
    await control.pausar_si_hay_reproduccion()
    await control.reanudar()


@pytest.mark.asyncio
async def test_modo_fallback_usa_tecla_multimedia_para_pausar_y_reanudar():
    teclas_presionadas: list[str] = []
    control = ControlMedia(forzar_fallback=True, tecla_multimedia=lambda: teclas_presionadas.append("playpause"))

    await control.pausar_si_hay_reproduccion()
    assert teclas_presionadas == ["playpause"]

    await control.reanudar()
    assert teclas_presionadas == ["playpause", "playpause"]


@pytest.mark.asyncio
async def test_modo_fallback_no_reanuda_si_no_habia_pausado_antes():
    teclas_presionadas: list[str] = []
    control = ControlMedia(forzar_fallback=True, tecla_multimedia=lambda: teclas_presionadas.append("playpause"))

    await control.reanudar()
    assert teclas_presionadas == []
