import pytest

from loki.voz.reproductor import Reproductor
from loki.voz.salida import hablar_oraciones


class _ReproductorFalso:
    def __init__(self) -> None:
        self.encolados: list[bytes] = []

    def encolar(self, audio: bytes) -> None:
        self.encolados.append(audio)


@pytest.mark.asyncio
async def test_fallo_de_sintesis_muestra_texto_completo_y_no_lanza_excepcion():
    async def sintetizador_que_falla(texto: str, voz: str) -> bytes:
        raise RuntimeError("edge-tts no responde")

    textos_mostrados: list[str] = []
    reproductor = _ReproductorFalso()

    await hablar_oraciones(
        oraciones=["Hola.", "Como estas?"],
        texto_completo="Hola. Como estas?",
        voz="es-MX-DaliaNeural",
        reproductor=reproductor,
        on_fallo_sintesis=textos_mostrados.append,
        sintetizador=sintetizador_que_falla,
    )

    assert textos_mostrados == ["Hola. Como estas?"]
    assert reproductor.encolados == []


@pytest.mark.asyncio
async def test_fallo_a_mitad_de_respuesta_no_pierde_lo_ya_sintetizado():
    llamadas = {"n": 0}

    async def sintetizador_falla_en_la_segunda(texto: str, voz: str) -> bytes:
        llamadas["n"] += 1
        if llamadas["n"] == 2:
            raise RuntimeError("fallo simulado")
        return b"audio-" + texto.encode()

    textos_mostrados: list[str] = []
    reproductor = _ReproductorFalso()

    await hablar_oraciones(
        oraciones=["Primera.", "Segunda.", "Tercera."],
        texto_completo="Primera. Segunda. Tercera.",
        voz="es-MX-DaliaNeural",
        reproductor=reproductor,
        on_fallo_sintesis=textos_mostrados.append,
        sintetizador=sintetizador_falla_en_la_segunda,
    )

    assert reproductor.encolados == [b"audio-Primera."]
    assert textos_mostrados == ["Primera. Segunda. Tercera."]


@pytest.mark.asyncio
async def test_sin_fallos_encola_todas_las_oraciones_sin_llamar_al_fallback():
    async def sintetizador_ok(texto: str, voz: str) -> bytes:
        return b"audio-" + texto.encode()

    textos_mostrados: list[str] = []
    reproductor = _ReproductorFalso()

    await hablar_oraciones(
        oraciones=["Uno.", "Dos."],
        texto_completo="Uno. Dos.",
        voz="es-MX-DaliaNeural",
        reproductor=reproductor,
        on_fallo_sintesis=textos_mostrados.append,
        sintetizador=sintetizador_ok,
    )

    assert reproductor.encolados == [b"audio-Uno.", b"audio-Dos."]
    assert textos_mostrados == []
