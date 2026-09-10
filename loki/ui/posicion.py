"""Persistencia de la posición del overlay en config.local.yaml (D12).

Si el monitor guardado ya no existe (posición fuera de todas las pantallas
actuales), se descarta y se usa la posición por defecto.
"""
from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

import yaml


class Rect(NamedTuple):
    x: int
    y: int
    width: int
    height: int


def _dentro_de_algun_monitor(x: int, y: int, monitores: list[Rect]) -> bool:
    return any(
        m.x <= x < m.x + m.width and m.y <= y < m.y + m.height for m in monitores
    )


def resolver_posicion(
    posicion_guardada: dict | None,
    monitores: list[Rect],
    posicion_por_defecto: tuple[int, int],
) -> tuple[int, int]:
    """Devuelve la posición a usar: la guardada si cae dentro de algún
    monitor actual, o la posición por defecto en cualquier otro caso."""
    if not posicion_guardada:
        return posicion_por_defecto
    x = posicion_guardada.get("x")
    y = posicion_guardada.get("y")
    if x is None or y is None:
        return posicion_por_defecto
    if not _dentro_de_algun_monitor(x, y, monitores):
        return posicion_por_defecto
    return (x, y)


def guardar_posicion(ruta_config_local: Path, x: int, y: int) -> None:
    """Escribe overlay.posicion en config.local.yaml, preservando el resto
    del archivo si ya existe."""
    datos: dict = {}
    if ruta_config_local.exists():
        datos = yaml.safe_load(ruta_config_local.read_text(encoding="utf-8")) or {}
    datos.setdefault("overlay", {})
    datos["overlay"]["posicion"] = {"x": x, "y": y}
    ruta_config_local.write_text(
        yaml.safe_dump(datos, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )


def monitores_reales() -> list[Rect]:
    from PyQt6.QtWidgets import QApplication

    return [
        Rect(g.x(), g.y(), g.width(), g.height())
        for g in (pantalla.geometry() for pantalla in QApplication.screens())
    ]
