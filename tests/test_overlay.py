from loki.ui import paleta
from loki.ui.overlay import Overlay, _Onda


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
