import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from auditar_privacidad import _cargar_permitidos, auditar, auditar_arbol


def _diff(archivo: str, lineas_agregadas: list[str], numero_inicial: int = 1) -> str:
    cuerpo = "\n".join(f"+{l}" for l in lineas_agregadas)
    return (
        f"diff --git a/{archivo} b/{archivo}\n"
        f"index 111..222 100644\n"
        f"--- a/{archivo}\n"
        f"+++ b/{archivo}\n"
        f"@@ -0,0 +{numero_inicial},{len(lineas_agregadas)} @@\n"
        f"{cuerpo}\n"
    )


def test_diff_limpio_no_produce_hallazgos():
    diff = _diff("loki/config.py", ["def cargar():", "    return {}"])
    assert auditar(diff) == []


def test_ruta_windows_con_usuario_se_detecta():
    diff = _diff("README.md", [r"El log queda en C:\Users\usuarioejemplo\AppData\Local"])
    hallazgos = auditar(diff)
    assert len(hallazgos) == 1
    assert hallazgos[0].tipo == "ruta_windows"
    assert hallazgos[0].archivo == "README.md"
    assert hallazgos[0].linea == 1


def test_ruta_macos_con_usuario_se_detecta():
    diff = _diff("scripts/setup.sh", ["export HOME=/Users/usuarioejemplo/proyecto"])
    hallazgos = auditar(diff)
    assert any(h.tipo == "ruta_macos" for h in hallazgos)


def test_correo_se_detecta():
    diff = _diff("config.yaml", ["contacto: persona@ejemplo.com"])
    hallazgos = auditar(diff)
    assert any(h.tipo == "correo" for h in hallazgos)


def test_key_de_groq_se_detecta():
    diff = _diff(".env", ["GROQ_API_KEY=gsk_abcdefghijklmnopqrstuvwx1234"])
    hallazgos = auditar(diff)
    assert any(h.tipo == "posible_key_o_token" for h in hallazgos)


def test_token_generico_asignado_se_detecta():
    diff = _diff("notas.txt", ["api_token: 'ab12cd34ef56gh78ij90kl12mn34op56'"])
    hallazgos = auditar(diff)
    assert any(h.tipo == "posible_key_o_token" for h in hallazgos)


def test_nombre_de_constante_con_key_o_token_no_se_detecta():
    """Un identificador de código (constante, variable) que solo contiene
    la palabra "token"/"key"/"secret" no es un secreto: no tiene dígitos."""
    diff = _diff("loki/herramientas/canal_local.py", ['VARIABLE_ENTORNO_TOKEN = "LOKI_CANAL_LOCAL_TOKEN"'])
    assert auditar(diff) == []


def test_llamada_a_metodo_encadenada_con_token_no_se_detecta():
    diff = _diff("loki/herramientas/canal_local.py", ["token_recibido = autorizacion.removeprefix(\"Bearer \")"])
    assert auditar(diff) == []


def test_key_generica_sin_prefijo_conocido_pero_con_digitos_se_detecta():
    diff = _diff("notas.txt", ["secret_value = 'no-es-un-prefijo-conocido-1234'"])
    hallazgos = auditar(diff)
    assert any(h.tipo == "posible_key_o_token" for h in hallazgos)


def test_archivo_permitido_por_glob_no_produce_hallazgos():
    diff = _diff("tests/fixtures/con_datos_de_ejemplo.py", ["contacto: persona@ejemplo.com"])
    assert auditar(diff, archivos_permitidos=["tests/**"]) == []


def test_archivo_no_cubierto_por_glob_permitido_igual_se_detecta():
    diff = _diff("loki/config.py", ["contacto: persona@ejemplo.com"])
    hallazgos = auditar(diff, archivos_permitidos=["tests/**"])
    assert any(h.tipo == "correo" for h in hallazgos)


def test_patron_permitido_suprime_el_hallazgo_en_cualquier_archivo():
    diff = _diff("scripts/auditar_privacidad.py", ['_PATRON_RUTA_MACOS = re.compile(r"/Users/[^/\\s\\"\']+")'])
    hallazgos = auditar(diff, patrones_permitidos=[r"^_PATRON_\w+\s*=\s*re\.compile"])
    assert hallazgos == []


def test_termino_privado_configurado_se_detecta_sin_mostrar_la_linea():
    diff = _diff("BACKLOG.md", ["Estamos migrando ProyectoSecretoXYZ a la nube"])
    hallazgos = auditar(diff, terminos_privados=["ProyectoSecretoXYZ"])
    assert len(hallazgos) == 1
    assert hallazgos[0].tipo == "termino_privado"
    assert hallazgos[0].detalle == "(oculto)"


def test_lineas_quitadas_no_se_auditan():
    diff = (
        "diff --git a/x.py b/x.py\n"
        "--- a/x.py\n"
        "+++ b/x.py\n"
        "@@ -1,1 +1,1 @@\n"
        "-contacto: viejo@ejemplo.com\n"
        "+contacto: nuevo@ejemplo.com\n"
    )
    hallazgos = auditar(diff)
    assert len(hallazgos) == 1
    assert "nuevo@ejemplo.com" in hallazgos[0].detalle


def test_numero_de_linea_correcto_con_varias_lineas():
    diff = _diff("a.txt", ["linea limpia", "GROQ_API_KEY=gsk_abcdefghijklmnopqrstuvwx1234"], numero_inicial=10)
    hallazgos = auditar(diff)
    assert len(hallazgos) == 1
    assert hallazgos[0].linea == 11


def _repo_git(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    return tmp_path


def test_auditar_arbol_encuentra_hallazgos_en_archivos_no_commiteados(tmp_path):
    repo = _repo_git(tmp_path)
    (repo / "config.yaml").write_text("contacto: persona@ejemplo.com\n", encoding="utf-8")

    hallazgos = auditar_arbol(repo)
    assert any(h.tipo == "correo" and h.archivo == "config.yaml" for h in hallazgos)


def test_auditar_arbol_ignora_archivos_en_gitignore(tmp_path):
    repo = _repo_git(tmp_path)
    (repo / ".gitignore").write_text(".env\n", encoding="utf-8")
    (repo / ".env").write_text("GROQ_API_KEY=gsk_realsecretkeyabcdefghij1234\n", encoding="utf-8")

    hallazgos = auditar_arbol(repo)
    assert hallazgos == []


def test_auditar_arbol_sin_hallazgos_en_arbol_limpio(tmp_path):
    repo = _repo_git(tmp_path)
    (repo / "README.md").write_text("# Un proyecto cualquiera\n", encoding="utf-8")

    assert auditar_arbol(repo) == []


def test_cargar_permitidos_lee_config_yaml(tmp_path):
    (tmp_path / "config.yaml").write_text(
        "auditoria_privacidad:\n"
        "  archivos_permitidos:\n"
        "    - 'tests/**'\n"
        "  patrones_permitidos:\n"
        "    - '@ejemplo\\.com'\n",
        encoding="utf-8",
    )
    archivos, patrones = _cargar_permitidos(tmp_path)
    assert archivos == ["tests/**"]
    assert patrones == [r"@ejemplo\.com"]


def test_cargar_permitidos_sin_config_yaml_devuelve_listas_vacias(tmp_path):
    assert _cargar_permitidos(tmp_path) == ([], [])
