"""Modo relay: tras enviar texto a la terminal activa, se espera a que
quede ociosa, se lee lo nuevo y se le pide al cerebro que lo resuma y
clasifique (D9, spec sesiones-de-agentes / flujo-de-desarrollo-por-voz).

El envío del texto a la terminal lo hace el cerebro con la herramienta
MCP `enviar_a_terminal` (ver design.md, hallazgo de la tarea 9.2): así el
mismo cerebro puede optar por reenviar literalmente lo que dijo el
usuario o traducirlo a un comando de OpenSpec (`/opsx:propose`,
`/opsx:apply <change>`) sin que la aplicación tenga que adivinar la
intención antes de que el cerebro la vea."""
from __future__ import annotations

from dataclasses import dataclass

from loki.cerebro.claude_headless import CerebroHeadless
from loki.cerebro.sesion import RegistroSesiones
from loki.estados import MaquinaEstados
from loki.herramientas.orca import Orca, extraer_texto_y_cursor

TIMEOUT_TUI_IDLE_MS = 10 * 60 * 1000  # 10 minutos, D9/sesiones-de-agentes


class ClasificacionRelay:
    TERMINO = "termino"
    PREGUNTA = "pregunta"
    PERMISO = "permiso"
    DESCONOCIDA = "desconocida"


_MARCAS = {
    "[TERMINO]": ClasificacionRelay.TERMINO,
    "[PREGUNTA]": ClasificacionRelay.PREGUNTA,
    "[PERMISO]": ClasificacionRelay.PERMISO,
}

INSTRUCCION_RESUMEN = (
    "Te paso la salida nueva de una sesión de agente de código en la que "
    "estás haciendo de relay. Resumila en voz, breve, en no más de cuatro "
    "oraciones. Empezá tu respuesta con exactamente una de estas marcas, "
    "sin nada antes: [TERMINO] si el agente completó la tarea y no "
    "necesita nada más, [PREGUNTA] si terminó haciendo una pregunta, "
    "[PERMISO] si quedó esperando un permiso o una confirmación. Después "
    "de la marca, un espacio y el resumen hablado.\n\nSalida del agente:\n"
)


def extraer_clasificacion(respuesta: str) -> tuple[str, str]:
    texto = respuesta.strip()
    for marca, clasificacion in _MARCAS.items():
        if texto.startswith(marca):
            return clasificacion, texto[len(marca):].strip()
    return ClasificacionRelay.DESCONOCIDA, texto


@dataclass
class ResultadoRelay:
    clasificacion: str
    resumen: str


class RelayVoz:
    def __init__(
        self,
        registro: RegistroSesiones,
        orca: Orca,
        cerebro: CerebroHeadless,
        maquina: MaquinaEstados,
        timeout_ms: int = TIMEOUT_TUI_IDLE_MS,
    ) -> None:
        self._registro = registro
        self._orca = orca
        self._cerebro = cerebro
        self._maquina = maquina
        self._timeout_ms = timeout_ms

    async def esperar_leer_y_clasificar(self, handle: str) -> ResultadoRelay:
        """Se llama después de que el cerebro ya envió texto a `handle` con
        la herramienta MCP `enviar_a_terminal` (el envío no es
        responsabilidad de esta clase: ver design.md, hallazgo de la tarea
        9.2, sobre por qué el envío pasa por el cerebro y no por acá)."""
        sesion = self._registro.obtener(handle)
        if sesion is None:
            raise RuntimeError(f"No hay sesión registrada para {handle!r}")

        self._maquina.agente_empezo_a_trabajar(sesion.handle)
        try:
            await self._orca.esperar_tui_idle(sesion.handle, timeout_ms=self._timeout_ms)

            leido = await self._orca.leer(sesion.handle, cursor=sesion.cursor)
            texto_nuevo, nuevo_cursor = extraer_texto_y_cursor(leido)
            self._registro.actualizar_cursor(sesion.handle, nuevo_cursor or sesion.cursor)

            respuesta = await self._cerebro.enviar_turno(INSTRUCCION_RESUMEN + texto_nuevo)
            clasificacion, resumen = extraer_clasificacion(respuesta)
            return ResultadoRelay(clasificacion=clasificacion, resumen=resumen)
        finally:
            self._maquina.agente_termino_de_trabajar(sesion.handle)
