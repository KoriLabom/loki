from loki.voz.limpieza_texto import limpiar_para_voz


def test_bloque_de_codigo_se_reemplaza_por_mencion_breve():
    texto = "Arreglé el bug.\n```python\ndef f():\n    return 1\n```\nYa está."
    resultado = limpiar_para_voz(texto)
    assert "def f()" not in resultado
    assert "el detalle está en el overlay" in resultado
    assert "Arreglé el bug." in resultado
    assert "Ya está." in resultado


def test_url_se_reemplaza_por_mencion_breve():
    texto = "Mirá https://example.com/docs/guia para más info."
    resultado = limpiar_para_voz(texto)
    assert "https://" not in resultado
    assert "un enlace" in resultado


def test_ruta_larga_se_reemplaza_por_mencion_breve():
    texto = r"El archivo está en C:\Users\usuarioejemplo\Documents\Proyectos\Asistente\config.yaml"
    resultado = limpiar_para_voz(texto)
    assert "C:\\Users" not in resultado
    assert "una ruta de archivo" in resultado


def test_marcas_markdown_se_quitan_conservando_el_texto():
    texto = "# Título\n- primer punto\n- segundo punto\nEsto es **importante** y también _relevante_, con `código` corto."
    resultado = limpiar_para_voz(texto)
    assert "#" not in resultado
    assert "*" not in resultado
    assert "_" not in resultado
    assert "`" not in resultado
    assert "primer punto" in resultado
    assert "importante" in resultado
    assert "relevante" in resultado
    assert "código" in resultado


def test_texto_plano_sin_marcas_no_cambia_de_contenido():
    texto = "Abrí la terminal del tablero y ya está corriendo."
    assert limpiar_para_voz(texto) == texto
