"""Overlay flotante de estado de Loki (D15).

Cinco estados visuales (dormido, escuchando, pensando, hablando, y el
indicador paralelo de agente trabajando), onda reactiva al volumen,
última frase del usuario, última respuesta y nombre de la sesión de
relay. Todos los colores salen de `loki.ui.paleta`.
"""
from __future__ import annotations

import math
from typing import Callable

from PyQt6.QtCore import QPoint, Qt, QTimer
from PyQt6.QtGui import QBrush, QColor, QPen
from PyQt6.QtGui import QPainter
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from loki.ui import paleta

_ANCHO = 340
_ALTO_ONDA = 36


class _Onda(QWidget):
    """Zona de estado: onda reactiva, punto tenue, o punto pulsante."""

    INACTIVA = "inactiva"
    PULSANDO = "pulsando"
    ONDA = "onda"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._amplitud = 0.0
        self._objetivo = 0.0
        self._fase = 0.0
        self._modo = self.INACTIVA
        self._color = paleta.ACENTO
        self.setFixedHeight(_ALTO_ONDA)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)

    def closeEvent(self, event) -> None:
        self._timer.stop()
        super().closeEvent(event)

    def set_color(self, color: QColor) -> None:
        self._color = color
        self.update()

    def set_modo(self, modo: str) -> None:
        self._modo = modo
        if modo != self.ONDA:
            self._objetivo = 0.0
        self.update()

    def set_amplitud(self, valor: float) -> None:
        if self._modo == self.ONDA:
            self._objetivo = min(math.sqrt(max(valor, 0.0) * 40), 1.0)

    def _tick(self) -> None:
        self._fase = (self._fase + 0.12) % (2 * math.pi)
        if self._modo == self.ONDA:
            self._amplitud += (self._objetivo - self._amplitud) * 0.15
        self.update()

    def _puntos_onda(self, w: int, h: int) -> list[tuple[int, int]]:
        mid = h / 2
        pts = []
        for x in range(0, w + 2, 2):
            t = x / max(w, 1)
            y = mid + mid * 0.72 * self._amplitud * (
                0.55 * math.sin(3 * t * 2 * math.pi + self._fase)
                + 0.30 * math.sin(7 * t * 2 * math.pi + self._fase * 1.37)
                + 0.15 * math.sin(11 * t * 2 * math.pi + self._fase * 0.71)
            )
            pts.append((int(x), int(y)))
        return pts

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            cy = self.height() // 2

            if self._modo == self.INACTIVA:
                color = QColor(self._color)
                color.setAlpha(90)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(color))
                painter.drawEllipse(self.width() // 2 - 3, cy - 3, 6, 6)
                return

            if self._modo == self.PULSANDO:
                alpha = int(120 + 100 * abs(math.sin(self._fase)))
                color = QColor(self._color)
                color.setAlpha(alpha)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(color))
                painter.drawEllipse(self.width() // 2 - 4, cy - 4, 8, 8)
                return

            pts = self._puntos_onda(self.width(), self.height())
            glow = QColor(self._color)
            glow.setAlpha(40)
            pen = QPen(glow)
            pen.setWidth(6)
            painter.setPen(pen)
            for i in range(1, len(pts)):
                painter.drawLine(pts[i - 1][0], pts[i - 1][1], pts[i][0], pts[i][1])

            pen = QPen(self._color)
            pen.setWidth(2)
            painter.setPen(pen)
            for i in range(1, len(pts)):
                painter.drawLine(pts[i - 1][0], pts[i - 1][1], pts[i][0], pts[i][1])
        finally:
            painter.end()


class Overlay(QWidget):
    """Ventana flotante sin bordes con el estado de Loki."""

    def __init__(self, on_posicion_cambiada: Callable[[int, int], None] | None = None) -> None:
        super().__init__()
        self._estado = "dormido"
        self._drag_offset: QPoint | None = None
        self._on_posicion_cambiada = on_posicion_cambiada
        self._setup_ventana()
        self._setup_ui()
        self.mostrar_dormido()

    def _setup_ventana(self) -> None:
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(_ANCHO)

    @staticmethod
    def _estilo_texto(color: QColor, tamano: int, bold: bool = False) -> str:
        peso = "bold" if bold else "normal"
        return (
            f"color: rgba({color.red()}, {color.green()}, {color.blue()}, {color.alpha()}); "
            f"font-family: '{paleta.FUENTE}'; font-size: {tamano}px; font-weight: {peso};"
        )

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 10, 16, 10)
        root.setSpacing(4)

        self._label_estado = QLabel("dormido")
        self._label_estado.setStyleSheet(self._estilo_texto(paleta.TEXTO, 11, bold=True))
        root.addWidget(self._label_estado)

        self._onda = _Onda(self)
        root.addWidget(self._onda)

        self._label_frase_usuario = QLabel("")
        self._label_frase_usuario.setWordWrap(True)
        self._label_frase_usuario.setStyleSheet(self._estilo_texto(paleta.TEXTO, 12))
        root.addWidget(self._label_frase_usuario)

        self._label_respuesta = QLabel("")
        self._label_respuesta.setWordWrap(True)
        self._label_respuesta.setStyleSheet(self._estilo_texto(paleta.TEXTO_SECUNDARIO, 11))
        root.addWidget(self._label_respuesta)

        self._label_relay = QLabel("")
        self._label_relay.setStyleSheet(self._estilo_texto(paleta.ACENTO_SUAVE, 10, bold=True))
        self._label_relay.hide()
        root.addWidget(self._label_relay)

        self._label_agente = QLabel("")
        self._label_agente.setStyleSheet(self._estilo_texto(paleta.ACENTO, 10, bold=True))
        self._label_agente.hide()
        root.addWidget(self._label_agente)

        self.adjustSize()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            r = self.rect().adjusted(0, 0, -1, -1)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(paleta.FONDO))
            painter.drawRoundedRect(r, 16, 16)
            painter.setPen(QPen(paleta.BORDE))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(r, 16, 16)
        finally:
            painter.end()

    # --- Drag con el mouse ---
    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:
        # Se arrastró: persistir la posición nueva (D12, tarea 6.3). Antes
        # `guardar_posicion`/`resolver_posicion` existían con tests pero
        # nunca se llamaban desde la app real (encontrado en tarea 10.3,
        # prueba O4): mover el overlay no quedaba guardado en ningún lado.
        if self._drag_offset is not None and self._on_posicion_cambiada is not None:
            punto = self.frameGeometry().topLeft()
            self._on_posicion_cambiada(punto.x(), punto.y())
        self._drag_offset = None

    # --- Estados: un método por estado ---
    def mostrar_dormido(self) -> None:
        self._estado = "dormido"
        self._label_estado.setText("dormido")
        self._onda.set_color(paleta.ACENTO)
        self._onda.set_modo(_Onda.INACTIVA)

    def mostrar_escuchando(self) -> None:
        self._estado = "escuchando"
        self._label_estado.setText("escuchando")
        self._onda.set_color(paleta.ACENTO)
        self._onda.set_modo(_Onda.ONDA)

    def mostrar_pensando(self) -> None:
        self._estado = "pensando"
        self._label_estado.setText("pensando")
        self._onda.set_color(paleta.ACENTO_SUAVE)
        self._onda.set_modo(_Onda.PULSANDO)

    def mostrar_hablando(self) -> None:
        self._estado = "hablando"
        self._label_estado.setText("hablando")
        self._onda.set_color(paleta.ACENTO_SUAVE)
        self._onda.set_modo(_Onda.ONDA)

    @property
    def estado_actual(self) -> str:
        return self._estado

    def set_amplitud(self, valor: float) -> None:
        self._onda.set_amplitud(valor)

    def mostrar_ultima_frase_usuario(self, texto: str) -> None:
        self._label_frase_usuario.setText(texto)

    def mostrar_ultima_respuesta(self, texto: str) -> None:
        self._label_respuesta.setText(texto)

    def mostrar_sesion_relay(self, nombre: str | None) -> None:
        if nombre:
            self._label_relay.setText(f"hablando con: {nombre}")
            self._label_relay.show()
        else:
            self._label_relay.hide()

    def mostrar_agente_trabajando(self, nombre_proyecto: str | None) -> None:
        if nombre_proyecto:
            self._label_agente.setText(f"agente trabajando: {nombre_proyecto}")
            self._label_agente.show()
        else:
            self._label_agente.hide()
