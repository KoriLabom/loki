import pytest

from loki.voz.tts import SegmentadorOraciones, sintetizar_mp3


def test_stream_de_tres_oraciones_produce_tres_segmentos_en_orden():
    segmentador = SegmentadorOraciones()
    fragmentos = [
        "Hola, ",
        "como estas. ",
        "Todo bien por aca",
        "? Nos vemos manana",
        ".",
    ]
    resultado: list[str] = []
    for fragmento in fragmentos:
        resultado.extend(segmentador.agregar(fragmento))
    resto = segmentador.flush()
    if resto:
        resultado.append(resto)

    assert resultado == [
        "Hola, como estas.",
        "Todo bien por aca?",
        "Nos vemos manana.",
    ]


def test_agregar_no_corta_a_mitad_de_palabra_sin_puntuacion():
    segmentador = SegmentadorOraciones()
    assert segmentador.agregar("Esto sigue ") == []
    assert segmentador.agregar("sin terminar") == []
    assert segmentador.flush() == "Esto sigue sin terminar"


def test_flush_sin_contenido_pendiente_devuelve_none():
    segmentador = SegmentadorOraciones()
    segmentador.agregar("Oracion completa. ")
    assert segmentador.flush() is None


class _FakeAsyncIter:
    def __init__(self, chunks: list[dict]) -> None:
        self._chunks = list(chunks)

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self._chunks:
            raise StopAsyncIteration
        return self._chunks.pop(0)


class _FakeComunicador:
    def __init__(self, texto: str, voz: str) -> None:
        self.texto = texto
        self.voz = voz

    def stream(self):
        return _FakeAsyncIter(
            [
                {"type": "audio", "data": b"abc"},
                {"type": "WordBoundary", "offset": 0},
                {"type": "audio", "data": b"def"},
            ]
        )


@pytest.mark.asyncio
async def test_sintetizar_mp3_concatena_solo_los_chunks_de_audio():
    audio = await sintetizar_mp3("hola", "es-MX-DaliaNeural", fabrica=_FakeComunicador)
    assert audio == b"abcdef"
