from pathlib import Path

from loki.config import cargar_config


def _escribir(raiz: Path, nombre: str, contenido: str) -> None:
    (raiz / nombre).write_text(contenido, encoding="utf-8")


def test_usa_defaults_sin_archivo_local(tmp_path):
    _escribir(
        tmp_path,
        "config.yaml",
        "modelos:\n  cerebro: haiku\nvoz:\n  nombre: es-MX-DaliaNeural\n",
    )
    config = cargar_config(tmp_path)
    assert config["modelos"]["cerebro"] == "haiku"
    assert config["voz"]["nombre"] == "es-MX-DaliaNeural"


def test_override_local_gana_sobre_default(tmp_path):
    _escribir(tmp_path, "config.yaml", "modelos:\n  cerebro: haiku\n  apply: sonnet\n")
    _escribir(tmp_path, "config.local.yaml", "modelos:\n  cerebro: sonnet\n")
    config = cargar_config(tmp_path)
    assert config["modelos"]["cerebro"] == "sonnet"
    assert config["modelos"]["apply"] == "sonnet"


def test_env_groq_api_key_se_expone_en_config(tmp_path, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "clave-de-prueba")
    _escribir(tmp_path, "config.yaml", "modelos:\n  cerebro: haiku\n")
    config = cargar_config(tmp_path)
    assert config["groq_api_key"] == "clave-de-prueba"


def test_sin_groq_api_key_devuelve_cadena_vacia(tmp_path, monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    _escribir(tmp_path, "config.yaml", "modelos:\n  cerebro: haiku\n")
    config = cargar_config(tmp_path)
    assert config["groq_api_key"] == ""
