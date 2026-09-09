"""Transcripción con Groq Whisper large-v3, con vocabulario y filtro de
alucinaciones (D6). Adaptado de voice-transcript, con timeout configurable."""
from __future__ import annotations

import io
import os
import wave

import numpy as np
from groq import Groq

from loki.audio.vocabulary import load_vocabulary

_PROMPT = "Transcripción en español con puntuación correcta: comas, puntos, signos de interrogación y exclamación."


def _build_prompt(base: str, vocabulary: list[str]) -> str:
    if not vocabulary:
        return base
    glossary = " Términos que pueden aparecer: " + ", ".join(vocabulary) + "."
    return base + glossary


# Frases que Whisper alucina sobre silencio o ruido bajo. Son patrones aprendidos
# de subtítulos de YouTube. Si el resultado es solo una de estas (con o sin
# puntuación), lo descartamos.
_HALLUCINATIONS = {
    "gracias por ver el video",
    "gracias por ver el vídeo",
    "subtítulos realizados por la comunidad de amara.org",
    "subtítulos por la comunidad de amara.org",
    "subtitulado por la comunidad de amara.org",
    "más información www.alimmenta.com",
    "www.mooji.org",
    "subtítulos en español por araitz cazón",
    "suscríbete",
    "suscríbete al canal",
    "suscribete",
    "gracias",
    "buen video",
    "you",
    "thanks for watching",
    "thank you",
    "thanks",
    "okay",
    "ok",
    "bye",
    "yeah",
    ".",
    "...",
    "♪",
    "♫",
    "[música]",
    "[musica]",
    "música",
    "musica",
    "amén",
    "amen",
}


def _is_hallucination(text: str) -> bool:
    cleaned = text.strip().lower().rstrip(".!¡?¿ ").strip()
    return cleaned in _HALLUCINATIONS


class Transcriber:
    def __init__(self, timeout_s: float = 15.0) -> None:
        self._client: Groq | None = None
        self._prompt = _PROMPT
        self._timeout_s = timeout_s

    def load(self) -> None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY no encontrada. Agregala en el archivo .env")
        self._client = Groq(api_key=api_key, timeout=self._timeout_s)
        self._prompt = _build_prompt(_PROMPT, load_vocabulary())

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> str:
        return self._transcribe(audio, sample_rate, self._prompt)

    def _transcribe(self, audio: np.ndarray, sample_rate: int, prompt: str) -> str:
        if self._client is None:
            raise RuntimeError("Cliente no inicializado. Llamar load() primero.")
        wav_bytes = _to_wav_bytes(audio, sample_rate)
        result = self._client.audio.transcriptions.create(
            file=("audio.wav", wav_bytes),
            model="whisper-large-v3",
            language="es",
            prompt=prompt,
        )
        text = result.text or ""
        if _is_hallucination(text):
            return ""
        return text


def _to_wav_bytes(audio: np.ndarray, sample_rate: int) -> bytes:
    audio_int16 = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_int16.tobytes())
    return buf.getvalue()
