import yaml

from loki.ui.posicion import Rect, guardar_posicion, resolver_posicion

_MONITOR_PRINCIPAL = Rect(0, 0, 1920, 1080)
_MONITOR_SECUNDARIO = Rect(1920, 0, 1920, 1080)
_DEFECTO = (760, 900)


def test_sin_posicion_guardada_usa_la_posicion_por_defecto():
    resultado = resolver_posicion(None, [_MONITOR_PRINCIPAL], _DEFECTO)
    assert resultado == _DEFECTO


def test_posicion_dentro_del_monitor_guardado_se_respeta():
    guardada = {"x": 100, "y": 200}
    resultado = resolver_posicion(guardada, [_MONITOR_PRINCIPAL], _DEFECTO)
    assert resultado == (100, 200)


def test_posicion_en_un_monitor_secundario_tambien_se_respeta():
    guardada = {"x": 2000, "y": 300}
    resultado = resolver_posicion(
        guardada, [_MONITOR_PRINCIPAL, _MONITOR_SECUNDARIO], _DEFECTO
    )
    assert resultado == (2000, 300)


def test_posicion_fuera_de_todas_las_pantallas_se_descarta():
    # El monitor donde se guardó (por ejemplo un segundo monitor externo)
    # ya no está conectado.
    guardada = {"x": 2500, "y": 300}
    resultado = resolver_posicion(guardada, [_MONITOR_PRINCIPAL], _DEFECTO)
    assert resultado == _DEFECTO


def test_posicion_incompleta_se_descarta():
    resultado = resolver_posicion({"x": 100}, [_MONITOR_PRINCIPAL], _DEFECTO)
    assert resultado == _DEFECTO


def test_guardar_posicion_crea_el_archivo_si_no_existe(tmp_path):
    ruta = tmp_path / "config.local.yaml"
    guardar_posicion(ruta, 50, 60)

    datos = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    assert datos["overlay"]["posicion"] == {"x": 50, "y": 60}


def test_guardar_posicion_preserva_otras_claves_del_archivo(tmp_path):
    ruta = tmp_path / "config.local.yaml"
    ruta.write_text(
        yaml.safe_dump({"alias_proyectos": {"el tablero": "tablero-repo"}}),
        encoding="utf-8",
    )

    guardar_posicion(ruta, 10, 20)

    datos = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    assert datos["alias_proyectos"] == {"el tablero": "tablero-repo"}
    assert datos["overlay"]["posicion"] == {"x": 10, "y": 20}
