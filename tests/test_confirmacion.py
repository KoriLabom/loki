import pytest

from loki.herramientas.confirmacion import (
    Clasificacion,
    RegistroConfirmaciones,
    clasificar_respuesta,
    pedir_confirmacion,
)


def test_clasificar_respuestas_afirmativas():
    assert clasificar_respuesta("sí") == Clasificacion.CONFIRMA
    assert clasificar_respuesta("Dale, hacelo.") == Clasificacion.CONFIRMA
    assert clasificar_respuesta("  SI  ") == Clasificacion.CONFIRMA


def test_clasificar_respuestas_negativas():
    assert clasificar_respuesta("no") == Clasificacion.NIEGA
    assert clasificar_respuesta("No, cancelá eso.") == Clasificacion.NIEGA


def test_clasificar_respuestas_ambiguas():
    assert clasificar_respuesta("no sé, quizás") == Clasificacion.AMBIGUA
    assert clasificar_respuesta("¿de qué me hablás?") == Clasificacion.AMBIGUA
    assert clasificar_respuesta("") == Clasificacion.AMBIGUA


class _Reloj:
    def __init__(self, inicio: float = 1000.0) -> None:
        self.ahora = inicio

    def __call__(self) -> float:
        return self.ahora

    def avanzar(self, segundos: float) -> None:
        self.ahora += segundos


def test_confirmar_dentro_del_tiempo_de_espera_deja_valida_la_confirmacion():
    reloj = _Reloj()
    registro = RegistroConfirmaciones(reloj=reloj)
    id_ = registro.crear("cerrar_terminal", "terminal-1")

    reloj.avanzar(5)  # menos que ESPERA_RESPUESTA_S (10s)
    assert registro.confirmar(id_) is True
    assert registro.es_valida(id_, "cerrar_terminal") is True


def test_id_vencido_sin_confirmar_se_rechaza():
    reloj = _Reloj()
    registro = RegistroConfirmaciones(reloj=reloj)
    id_ = registro.crear("cerrar_terminal", "terminal-1")

    reloj.avanzar(11)  # pasó ESPERA_RESPUESTA_S sin confirmar
    assert registro.confirmar(id_) is False
    assert registro.es_valida(id_, "cerrar_terminal") is False


def test_confirmacion_expira_tras_la_ventana_de_validez():
    reloj = _Reloj()
    registro = RegistroConfirmaciones(reloj=reloj)
    id_ = registro.crear("eliminar_worktree", "repo-x")
    registro.confirmar(id_)

    reloj.avanzar(59)
    assert registro.es_valida(id_, "eliminar_worktree") is True

    reloj.avanzar(2)  # total 61s > VALIDEZ_S (60s)
    assert registro.es_valida(id_, "eliminar_worktree") is False


def test_id_de_otra_accion_se_rechaza():
    reloj = _Reloj()
    registro = RegistroConfirmaciones(reloj=reloj)
    id_ = registro.crear("cerrar_terminal", "terminal-1")
    registro.confirmar(id_)

    assert registro.es_valida(id_, "eliminar_worktree") is False


def test_id_inexistente_se_rechaza():
    registro = RegistroConfirmaciones()
    assert registro.es_valida("id-que-no-existe", "cerrar_terminal") is False


def test_cancelar_invalida_la_confirmacion():
    registro = RegistroConfirmaciones()
    id_ = registro.crear("cerrar_terminal", "terminal-1")
    registro.confirmar(id_)
    registro.cancelar(id_)
    assert registro.es_valida(id_, "cerrar_terminal") is False


@pytest.mark.asyncio
async def test_secuencia_confirma():
    registro = RegistroConfirmaciones()
    dichos = []

    async def hablar(texto):
        dichos.append(texto)

    async def escuchar(espera_s):
        return "sí, dale"

    id_ = await pedir_confirmacion(registro, "cerrar_terminal", "terminal-1", hablar, escuchar)

    assert registro.es_valida(id_, "cerrar_terminal") is True
    assert any("Listo" in d for d in dichos)


@pytest.mark.asyncio
async def test_secuencia_niega():
    registro = RegistroConfirmaciones()

    async def hablar(texto):
        pass

    async def escuchar(espera_s):
        return "no, dejalo"

    id_ = await pedir_confirmacion(registro, "cerrar_terminal", "terminal-1", hablar, escuchar)

    assert registro.es_valida(id_, "cerrar_terminal") is False


@pytest.mark.asyncio
async def test_secuencia_ambigua_no_confirma():
    registro = RegistroConfirmaciones()

    async def hablar(texto):
        pass

    async def escuchar(espera_s):
        return "eh, no sé qué decís"

    id_ = await pedir_confirmacion(registro, "cerrar_terminal", "terminal-1", hablar, escuchar)

    assert registro.es_valida(id_, "cerrar_terminal") is False


@pytest.mark.asyncio
async def test_secuencia_sin_respuesta_cancela():
    registro = RegistroConfirmaciones()
    dichos = []

    async def hablar(texto):
        dichos.append(texto)

    async def escuchar(espera_s):
        return None

    id_ = await pedir_confirmacion(registro, "cerrar_terminal", "terminal-1", hablar, escuchar)

    assert registro.es_valida(id_, "cerrar_terminal") is False
    assert any("No hubo respuesta" in d for d in dichos)
