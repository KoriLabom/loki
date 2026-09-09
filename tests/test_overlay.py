from PyQt6.QtCore import QPoint, Qt

from loki.ui import paleta
from loki.ui.overlay import Overlay, _Onda


class _EventoMousePressFalso:
    """Duck-type mínimo de QMouseEvent: sólo lo que usa mousePressEvent."""

    def __init__(self, punto: QPoint) -> None:
        self._punto = punto

    def button(self):
        return Qt.MouseButton.LeftButton

    def globalPosition(self):
        punto = self._punto

        class _Posicion:
            def toPoint(self) -> QPoint:
                return punto

        return _Posicion()

    def accept(self) -> None:
        pass


def test_overlay_expone_un_metodo_por_estado(qapp):
    overlay = Overlay()

    overlay.mostrar_dormido()
    assert overlay.estado_actual == "dormido"

    overlay.mostrar_escuchando()
    assert overlay.estado_actual == "escuchando"

    overlay.mostrar_pensando()
    assert overlay.estado_actual == "pensando"

    overlay.mostrar_hablando()
    assert overlay.estado_actual == "hablando"


def test_dormido_deja_la_onda_inactiva_y_pensando_pulsando(qapp):
    overlay = Overlay()

    overlay.mostrar_dormido()
    assert overlay._onda._modo == _Onda.INACTIVA

    overlay.mostrar_escuchando()
    assert overlay._onda._modo == _Onda.ONDA

    overlay.mostrar_pensando()
    assert overlay._onda._modo == _Onda.PULSANDO

    overlay.mostrar_hablando()
    assert overlay._onda._modo == _Onda.ONDA


def test_ultima_frase_y_respuesta_se_muestran_en_sus_labels(qapp):
    overlay = Overlay()
    overlay.mostrar_ultima_frase_usuario("Abrí la terminal del tablero")
    overlay.mostrar_ultima_respuesta("Ya está abierta.")

    assert overlay._label_frase_usuario.text() == "Abrí la terminal del tablero"
    assert overlay._label_respuesta.text() == "Ya está abierta."


def test_sesion_relay_se_muestra_y_se_oculta(qapp):
    overlay = Overlay()
    assert overlay._label_relay.isHidden()

    overlay.mostrar_sesion_relay("el tablero")
    assert not overlay._label_relay.isHidden()
    assert "el tablero" in overlay._label_relay.text()

    overlay.mostrar_sesion_relay(None)
    assert overlay._label_relay.isHidden()


def test_agente_trabajando_se_muestra_con_nombre_de_proyecto(qapp):
    overlay = Overlay()
    overlay.mostrar_agente_trabajando("Nebulosa")
    assert not overlay._label_agente.isHidden()
    assert "Nebulosa" in overlay._label_agente.text()

    overlay.mostrar_agente_trabajando(None)
    assert overlay._label_agente.isHidden()


def test_soltar_tras_arrastrar_llama_al_callback_con_la_posicion_nueva(qapp):
    """Antes mover el overlay no llamaba a nada: `guardar_posicion`
    existía con tests pero nunca se conectaba desde la app real
    (encontrado en tarea 10.3, prueba O4)."""
    posiciones: list[tuple[int, int]] = []
    overlay = Overlay(on_posicion_cambiada=lambda x, y: posiciones.append((x, y)))

    overlay.mousePressEvent(_EventoMousePressFalso(QPoint(100, 100)))
    overlay.mouseReleaseEvent(None)

    assert len(posiciones) == 1
    esperado = overlay.frameGeometry().topLeft()
    assert posiciones[0] == (esperado.x(), esperado.y())


def test_soltar_sin_haber_apretado_no_llama_al_callback(qapp):
    posiciones: list[tuple[int, int]] = []
    overlay = Overlay(on_posicion_cambiada=lambda x, y: posiciones.append((x, y)))

    overlay.mouseReleaseEvent(None)

    assert posiciones == []


def test_sin_callback_soltar_no_rompe_nada(qapp):
    overlay = Overlay()
    overlay.mousePressEvent(_EventoMousePressFalso(QPoint(10, 10)))
    overlay.mouseReleaseEvent(None)  # no debe lanzar aunque no haya callback


def test_cambiar_el_acento_en_paleta_cambia_el_color_de_la_onda(qapp, monkeypatch):
    overlay = Overlay()
    overlay.mostrar_escuchando()
    color_original = overlay._onda._color.getRgb()

    monkeypatch.setattr(paleta, "ACENTO", paleta.ACENTO.__class__(0, 255, 0))
    overlay2 = Overlay()
    overlay2.mostrar_escuchando()
    color_nuevo = overlay2._onda._color.getRgb()

    assert color_original != color_nuevo
    assert color_nuevo[:3] == (0, 255, 0)
