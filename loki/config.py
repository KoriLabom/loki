"""Carga de configuración en tres capas: config.yaml, config.local.yaml, .env."""
from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

_RAIZ = Path(__file__).resolve().parent.parent


def _fusionar(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    resultado = copy.deepcopy(base)
    for clave, valor in override.items():
        if isinstance(valor, dict) and isinstance(resultado.get(clave), dict):
            resultado[clave] = _fusionar(resultado[clave], valor)
        else:
            resultado[clave] = valor
    return resultado


def _cargar_yaml(ruta: Path) -> dict[str, Any]:
    if not ruta.exists():
        return {}
    with ruta.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def cargar_config(raiz: Path | None = None) -> dict[str, Any]:
    """Carga config.yaml, le aplica encima config.local.yaml si existe, y
    agrega las variables de entorno de .env. Los overrides locales ganan
    sobre los defaults commiteados."""
    raiz = raiz or _RAIZ
    load_dotenv(raiz / ".env", override=False)

    base = _cargar_yaml(raiz / "config.yaml")
    local = _cargar_yaml(raiz / "config.local.yaml")
    config = _fusionar(base, local)
    config["groq_api_key"] = os.environ.get("GROQ_API_KEY", "")
    return config
