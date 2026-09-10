from unittest.mock import MagicMock, patch

import numpy as np

from loki.audio.transcriber import Transcriber, _PROMPT, _build_prompt, _is_hallucination


def test_build_prompt_returns_base_when_vocabulary_empty():
    assert _build_prompt(_PROMPT, []) == _PROMPT


def test_build_prompt_appends_terms_when_vocabulary_present():
    out = _build_prompt(_PROMPT, ["Claude Code", "Groq", "OpenSpec"])
    assert out.startswith(_PROMPT)
    assert "Claude Code" in out
    assert "Groq" in out
    assert "OpenSpec" in out


def test_transcribe_raises_if_not_loaded():
    t = Transcriber()
    try:
        t.transcribe(np.zeros(16000, dtype="float32"))
        assert False, "debería haber lanzado RuntimeError"
    except RuntimeError as e:
        assert "load()" in str(e)


def _make_loaded_transcriber(vocabulary: list[str], texto_resultado: str = "ok") -> Transcriber:
    with patch("loki.audio.transcriber.load_vocabulary", return_value=vocabulary), \
         patch("loki.audio.transcriber.os.environ.get", return_value="fake-key"), \
         patch("loki.audio.transcriber.Groq") as MockGroq:
        client = MagicMock()
        result = MagicMock()
        result.text = texto_resultado
        client.audio.transcriptions.create.return_value = result
        MockGroq.return_value = client

        t = Transcriber(timeout_s=5.0)
        t.load()
        return t


def test_load_pasa_el_timeout_configurado_al_cliente():
    with patch("loki.audio.transcriber.load_vocabulary", return_value=[]), \
         patch("loki.audio.transcriber.os.environ.get", return_value="fake-key"), \
         patch("loki.audio.transcriber.Groq") as MockGroq:
        t = Transcriber(timeout_s=7.5)
        t.load()
        assert MockGroq.call_args.kwargs["timeout"] == 7.5


def test_load_caches_prompt_with_vocabulary():
    t = _make_loaded_transcriber(["Claude Code", "Groq"])
    assert t._prompt.startswith(_PROMPT)
    assert "Claude Code" in t._prompt
    assert "Groq" in t._prompt


def test_load_caches_base_prompt_when_no_vocabulary():
    t = _make_loaded_transcriber([])
    assert t._prompt == _PROMPT


def test_transcribe_sends_cached_prompt_to_groq():
    t = _make_loaded_transcriber(["Claude Code", "Groq"])
    audio = np.zeros(16000, dtype="float32")

    t.transcribe(audio)

    call_kwargs = t._client.audio.transcriptions.create.call_args.kwargs
    assert call_kwargs["prompt"] == t._prompt
    assert "Claude Code" in call_kwargs["prompt"]


def test_transcribe_calls_groq_with_spanish_language():
    t = _make_loaded_transcriber([])
    audio = np.zeros(16000, dtype="float32")

    t.transcribe(audio)

    call_kwargs = t._client.audio.transcriptions.create.call_args.kwargs
    assert call_kwargs["language"] == "es"
    assert call_kwargs["model"] == "whisper-large-v3"


def test_transcribe_does_not_rebuild_prompt_on_each_call():
    t = _make_loaded_transcriber(["Claude Code"])
    audio = np.zeros(16000, dtype="float32")
    first = t._prompt

    t.transcribe(audio)
    t.transcribe(audio)
    t.transcribe(audio)

    assert t._prompt is first


def test_transcribe_descarta_alucinaciones_conocidas():
    t = _make_loaded_transcriber([], texto_resultado="gracias por ver el video")
    audio = np.zeros(16000, dtype="float32")

    assert t.transcribe(audio) == ""


def test_transcribe_devuelve_texto_real_sin_tocar():
    t = _make_loaded_transcriber([], texto_resultado="Abrí la terminal del tablero.")
    audio = np.zeros(16000, dtype="float32")

    assert t.transcribe(audio) == "Abrí la terminal del tablero."


def test_is_hallucination_ignora_mayusculas_y_puntuacion():
    assert _is_hallucination("Gracias.")
    assert _is_hallucination("  SUSCRIBETE  ")
    assert not _is_hallucination("Abrí la terminal.")
