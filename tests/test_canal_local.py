import json
import urllib.error
import urllib.request

import pytest

from loki.herramientas.canal_local import ServidorCanalLocal, generar_token


@pytest.fixture
def servidor():
    token = generar_token()
    s = ServidorCanalLocal(puerto=0, token=token)
    s.registrar("saludar", lambda datos: {"saludo": f"hola {datos.get('nombre', '?')}"})
    s.iniciar()
    yield s, token
    s.detener()


def _post(puerto: int, token: str | None, cuerpo: dict) -> tuple[int, dict]:
    url = f"http://127.0.0.1:{puerto}/rpc"
    data = json.dumps(cuerpo).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def test_generar_token_produce_valores_distintos():
    assert generar_token() != generar_token()


def test_llamada_sin_token_se_rechaza(servidor):
    s, _token = servidor
    codigo, cuerpo = _post(s.puerto_real, None, {"accion": "saludar", "datos": {"nombre": "Loki"}})
    assert codigo == 401


def test_llamada_con_token_incorrecto_se_rechaza(servidor):
    s, _token = servidor
    codigo, cuerpo = _post(s.puerto_real, "token-equivocado", {"accion": "saludar"})
    assert codigo == 401


def test_llamada_con_token_correcto_ejecuta_la_accion(servidor):
    s, token = servidor
    codigo, cuerpo = _post(s.puerto_real, token, {"accion": "saludar", "datos": {"nombre": "Loki"}})
    assert codigo == 200
    assert cuerpo == {"saludo": "hola Loki"}


def test_accion_desconocida_devuelve_404(servidor):
    s, token = servidor
    codigo, cuerpo = _post(s.puerto_real, token, {"accion": "no_existe"})
    assert codigo == 404
