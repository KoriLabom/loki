"""Paleta y tipografía de Loki (D15). Único lugar de donde el overlay toma
sus colores: cambiar el acento acá cambia la onda y los textos."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor, QIcon, QPainter, QPixmap

FONDO = QColor(0x1F, 0x1A, 0x17, round(255 * 0.92))
BORDE = QColor(0x3A, 0x2E, 0x27)
ACENTO = QColor(0xD9, 0x77, 0x57)
ACENTO_SUAVE = QColor(0xE8, 0xA8, 0x7C)
TEXTO = QColor(0xF5, 0xED, 0xE4)
TEXTO_SECUNDARIO = QColor(0xA8, 0x9A, 0x8C)
ERROR = QColor(0xC4, 0x46, 0x2A)
FUENTE = "Segoe UI"


def icono_bandeja(tamano: int = 64) -> QIcon:
    """Ícono de la bandeja: un círculo terracota simple, generado en
    código para no depender de un archivo de imagen aparte."""
    pixmap = QPixmap(tamano, tamano)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    try:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(ACENTO))
        margen = round(tamano * 0.1)
        painter.drawEllipse(margen, margen, tamano - 2 * margen, tamano - 2 * margen)
    finally:
        painter.end()
    return QIcon(pixmap)
