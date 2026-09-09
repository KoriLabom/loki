"""Registro y flujo de confirmación de acciones críticas.

Ver spec `confirmacion-de-acciones-criticas` y D2/D3 de design.md. La
confirmación se verifica acá, en una capa independiente del cerebro: sin
un id válido, reciente y de la acción exacta, la acción crítica no se
ejecuta, sin importar lo que el cerebro afirme.
"""
from __future__ import annotations

import re
import time
import uuid
from dataclasses import dataclass
from typing import Awaitable, Callable

ESPERA_RESPUESTA_S = 10.0
VALIDEZ_S = 60.0

_AFIRMACIONES = {
    "si", "sí", "dale", "hacelo", "hazlo", "confirmo", "correcto", "sip",
    "obvio", "afirmativo", "adelante", "ok", "listo",
}
_NEGACIONES = {
    "no", "nel", "cancela", "cancelá", "negativo", "para", "pará", "nunca",
}
_MARCAS_AMBIGUAS = ("no sé", "no se", "no estoy seguro", "no estoy segura", "quizás", "quizas", "tal vez")


class Clasificacion:
    CONFIRMA = "confirma"
    NIEGA = "niega"
    AMBIGUA = "ambigua"


def clasificar_respuesta(texto: str) -> str:
    """Sí/no/ambigua a partir de una frase transcripta, sin depender de
    coincidencia exacta: mira las palabras sueltas de afirmación o negación."""
    normalizado = texto.strip().lower().rstrip(".!¡?¿ ")
    if any(marca in normalizado for marca in _MARCAS_AMBIGUAS):
        return Clasificacion.AMBIGUA
    palabras = set(re.findall(r"\w+", normalizado, flags=re.UNICODE))
    tiene_afirmacion = bool(palabras & _AFIRMACIONES)
    tiene_negacion = bool(palabras & _NEGACIONES)
    if tiene_afirmacion and not tiene_negacion:
        return Clasificacion.CONFIRMA
    if tiene_negacion and not tiene_afirmacion:
        return Clasificacion.NIEGA
    return Clasificacion.AMBIGUA


@dataclass
class _Confirmacion:
    id: str
    accion: str
    objetivo: str
    vence_en: float
    confirmada_hasta: float | None = None


class RegistroConfirmaciones:
    """Guarda confirmaciones pendientes/confirmadas con vencimiento.
    `reloj` es inyectable para poder testear el paso del tiempo."""

    def __init__(self, reloj: Callable[[], float] = time.monotonic) -> None:
        self._reloj = reloj
        self._registro: dict[str, _Confirmacion] = {}

    def crear(self, accion: str, objetivo: str) -> str:
        id_confirmacion = str(uuid.uuid4())
        self._registro[id_confirmacion] = _Confirmacion(
            id=id_confirmacion,
            accion=accion,
            objetivo=objetivo,
            vence_en=self._reloj() + ESPERA_RESPUESTA_S,
        )
        return id_confirmacion

    def confirmar(self, id_confirmacion: str) -> bool:
        """Marca como confirmada, con `VALIDEZ_S` segundos de validez desde
        ahora. False si el id no existe o ya venció el tiempo de espera."""
        c = self._registro.get(id_confirmacion)
        if c is None:
            return False
        if self._reloj() > c.vence_en:
            del self._registro[id_confirmacion]
            return False
        c.confirmada_hasta = self._reloj() + VALIDEZ_S
        return True

    def cancelar(self, id_confirmacion: str) -> None:
        self._registro.pop(id_confirmacion, None)

    def es_valida(self, id_confirmacion: str, accion: str) -> bool:
        """True solo si el id existe, es para esa acción exacta, fue
        confirmada, y sigue dentro de la ventana de validez."""
        c = self._registro.get(id_confirmacion)
        if c is None or c.accion != accion or c.confirmada_hasta is None:
            return False
        if self._reloj() > c.confirmada_hasta:
            del self._registro[id_confirmacion]
            return False
        return True


HablarFn = Callable[[str], Awaitable[None]]
EscucharFn = Callable[[float], Awaitable[str | None]]


async def pedir_confirmacion(
    registro: RegistroConfirmaciones,
    accion: str,
    objetivo: str,
    hablar: HablarFn,
    escuchar: EscucharFn,
) -> str:
    """Habla la pregunta de confirmación, escucha la respuesta (el
    `escuchar` inyectado debe hacerlo sin requerir la palabra de
    activación) y clasifica sí/no/ambigua. Devuelve el id de confirmación;
    solo queda válido si el usuario confirmó a tiempo."""
    id_confirmacion = registro.crear(accion, objetivo)
    await hablar(f"¿Confirmás {accion} en {objetivo}?")
    texto = await escuchar(ESPERA_RESPUESTA_S)

    if texto is None:
        registro.cancelar(id_confirmacion)
        await hablar("No hubo respuesta, cancelo la acción.")
        return id_confirmacion

    clasificacion = clasificar_respuesta(texto)
    if clasificacion == Clasificacion.CONFIRMA:
        registro.confirmar(id_confirmacion)
        await hablar("Listo, lo hago.")
    else:
        registro.cancelar(id_confirmacion)
        await hablar("Cancelo la acción.")

    return id_confirmacion
