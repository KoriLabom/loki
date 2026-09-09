"""Arranque de Loki (D11): arma los hilos (Qt, audio, cerebro/voz), conecta
la máquina de estados con el overlay, y levanta el subproceso del cerebro.

Hilo principal: Qt (overlay y bandeja).
Hilo de audio: stream continuo de sounddevice (wake word, fin de frase,
amplitud para el overlay); el callback corre en el hilo de PortAudio.
Hilo de cerebro y voz: un loop de asyncio propio que maneja el
subproceso de Claude Code, la síntesis y la cola de reproducción.
El canal local (HTTP) y el reproductor de audio ya manejan sus propios
hilos internamente.
"""
from __future__ import annotations

import asyncio
import logging
import sys
import threading
from pathlib import Path

import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from loki.audio.fin_de_frase import DetectorFinDeFrase, ResultadoBloque
from loki.audio.recorder import GrabadorContinuo
from loki.audio.transcriber import Transcriber
from loki.audio.wake_word import DetectorWakeWord, ModeloWakeWordNoEncontrado
from loki.cerebro.claude_headless import CerebroHeadless, config_cerebro_desde_config
from loki.cerebro.relay import RelayVoz
from loki.cerebro.sesion import RegistroSesiones, SesionAgente
from loki.config import cargar_config
from loki.estados import Estado, MaquinaEstados
from loki.herramientas.canal_local import (
    VARIABLE_ENTORNO_PUERTO,
    VARIABLE_ENTORNO_TOKEN,
    ServidorCanalLocal,
    generar_token,
)
from loki.herramientas.confirmacion import RegistroConfirmaciones
from loki.herramientas.coordinador_media import CoordinadorMedia
from loki.herramientas.manejadores_canal_local import ManejadoresCriticos
from loki.herramientas.media import ControlMedia
from loki.herramientas.monitor import MonitorTerminal
from loki.herramientas.orca import Orca
from loki.ui.bandeja import Bandeja
from loki.ui.paleta import icono_bandeja
from loki.ui.overlay import Overlay
from loki.ui.posicion import guardar_posicion, monitores_reales, resolver_posicion
from loki.voz.limpieza_texto import limpiar_para_voz
from loki.voz.reproductor import Reproductor
from loki.voz.salida import hablar_oraciones
from loki.voz.tts import SegmentadorOraciones

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

RAIZ = Path(__file__).resolve().parent.parent


class _SenalesEstado(QObject):
    """Puente thread-safe entre el hilo de audio/asyncio y el hilo de Qt."""

    cambio_estado = pyqtSignal(object, object)
    amplitud = pyqtSignal(float)
    frase_usuario = pyqtSignal(str)
    respuesta = pyqtSignal(str)
    sesion_relay = pyqtSignal(object)
    agente_trabajando = pyqtSignal(object)


class Loki:
    def __init__(self) -> None:
        self.config = cargar_config(RAIZ)
        self.maquina = MaquinaEstados()
        self.registro_sesiones = RegistroSesiones()
        self.registro_confirmaciones = RegistroConfirmaciones()
        self.orca = Orca()
        self.control_media = ControlMedia()
        self.coordinador_media = CoordinadorMedia(self.maquina, self.control_media)
        self.transcriber = Transcriber(timeout_s=self.config.get("transcripcion", {}).get("timeout_s", 15))

        self.senales = _SenalesEstado()
        self.maquina.observar(lambda a, n: self.senales.cambio_estado.emit(a, n))

        self._segmentador = SegmentadorOraciones()
        self._monitores_activos: set[str] = set()
        self._hilo_asyncio: threading.Thread | None = None
        self._loop_asyncio: asyncio.AbstractEventLoop | None = None
        self._grabador: GrabadorContinuo | None = None
        self._detector_wake_word: DetectorWakeWord | None = None
        self._detector_fin_de_frase: DetectorFinDeFrase | None = None
        self._buffer_frase: list[np.ndarray] = []
        self._generacion_actual = 0
        self._generacion_turno_en_curso = 0

        persona = RAIZ / "loki" / "persona" / "system_prompt.md"
        config_cerebro = config_cerebro_desde_config(self.config, ruta_persona=persona, cwd=RAIZ)
        self.cerebro = CerebroHeadless(
            config_cerebro, on_texto_parcial=self._on_texto_parcial_cerebro
        )
        self.relay = RelayVoz(self.registro_sesiones, self.orca, self.cerebro, self.maquina)
        self.reproductor = Reproductor()

        token = generar_token()
        puerto = self.config.get("canal_local", {}).get("puerto", 8765)
        self.canal_local = ServidorCanalLocal(puerto=puerto, token=token)
        self._token_canal_local = token
        self._registrar_manejadores_canal_local()

    # --- Canal local / MCP -------------------------------------------------

    def _registrar_manejadores_canal_local(self) -> None:
        manejadores = ManejadoresCriticos(
            registro=self.registro_confirmaciones,
            orca=self.orca,
            ejecutar_cerrar_terminal=self._ejecutar_cerrar_terminal,
            ejecutar_eliminar_worktree=self._ejecutar_eliminar_worktree,
            ejecutar_enviar_texto=self._ejecutar_enviar_a_terminal,
        )
        self.canal_local.registrar("cerrar_terminal", manejadores.cerrar_terminal)
        self.canal_local.registrar("eliminar_worktree", manejadores.eliminar_worktree)
        self.canal_local.registrar("enviar_a_terminal", manejadores.enviar_a_terminal)
        self.canal_local.registrar("pedir_confirmacion", self._manejar_pedir_confirmacion)
        self.canal_local.registrar("media_pausar", lambda _d: self._correr_en_asyncio(self.control_media.pausar_si_hay_reproduccion()) or {"ok": True})
        self.canal_local.registrar("media_reanudar", lambda _d: self._correr_en_asyncio(self.control_media.reanudar()) or {"ok": True})
        self.canal_local.registrar("overlay_estado", self._manejar_overlay_estado)
        self.canal_local.registrar("sesion_relay_activar", self._manejar_sesion_relay_activar)
        self.canal_local.registrar("sesion_relay_salir", self._manejar_sesion_relay_salir)
        self.canal_local.registrar("monitorear_terminal", self._manejar_monitorear_terminal)
        self.canal_local.registrar("listar_proyectos", self._manejar_listar_proyectos)
        self.canal_local.registrar("config_modelos", lambda _d: self.config.get("modelos", {}))

    def _correr_en_asyncio(self, coro):
        if self._loop_asyncio is None:
            return None
        return asyncio.run_coroutine_threadsafe(coro, self._loop_asyncio).result(timeout=30)

    def _ejecutar_cerrar_terminal(self, terminal: str):
        # Cerrar una terminal es una acción real de Orca, no expuesta por
        # Orca() como método propio todavía: se ejecuta vía CLI directo.
        async def _cerrar():
            proc = await asyncio.create_subprocess_exec(
                "orca", "terminal", "close", "--terminal", terminal, "--json",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            return {"terminal": terminal}

        return _cerrar()

    def _ejecutar_eliminar_worktree(self, worktree: str):
        async def _eliminar():
            proc = await asyncio.create_subprocess_exec(
                "orca", "worktree", "rm", "--worktree", worktree, "--json",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            return {"worktree": worktree}

        return _eliminar()

    async def _ejecutar_enviar_a_terminal(self, terminal: str, texto: str) -> dict:
        await self.orca.enviar_texto(terminal, texto, enter=True)
        if terminal == self.registro_sesiones.relay_activa and self._loop_asyncio is not None:
            # Este método corre dentro del loop temporal que abre
            # ManejadoresCriticos.enviar_a_terminal vía asyncio.run() en el
            # hilo del servidor HTTP del canal local: ese loop se cierra al
            # terminar esta corrutina, así que hay que lanzar el sondeo del
            # relay en el loop real de la app, no en este temporal.
            asyncio.run_coroutine_threadsafe(self._reaccionar_relay(terminal), self._loop_asyncio)
        return {"terminal": terminal}

    async def _reaccionar_relay(self, terminal: str) -> None:
        try:
            resultado = await self.relay.esperar_leer_y_clasificar(terminal)
            await self._hablar(resultado.resumen)
            self.senales.respuesta.emit(resultado.resumen)
        except Exception:
            logger.exception("Fallo reaccionando al relay de %s", terminal)

    def _manejar_pedir_confirmacion(self, datos: dict) -> dict:
        from loki.herramientas.confirmacion import pedir_confirmacion

        async def _pedir():
            async def hablar(texto: str) -> None:
                await self._hablar(texto)

            async def escuchar(espera_s: float) -> str | None:
                # TODO: implementar escucha real sin wake word (requiere el
                # hilo de audio en modo "confirmación"); de momento no hay
                # forma de escuchar fuera del ciclo normal de wake word.
                return None

            return await pedir_confirmacion(
                self.registro_confirmaciones, datos.get("accion", ""), datos.get("objetivo", ""), hablar, escuchar
            )

        return self._correr_en_asyncio(_pedir())

    def _manejar_overlay_estado(self, datos: dict) -> dict:
        self.senales.respuesta.emit(datos.get("texto", ""))
        return {"ok": True}

    def _manejar_sesion_relay_activar(self, datos: dict) -> dict:
        handle = datos.get("terminal", "")

        async def _info():
            return await self.orca.mostrar_terminal(handle)

        if self.registro_sesiones.obtener(handle) is None:
            info = self._correr_en_asyncio(_info()) or {}
            titulo = info.get("result", {}).get("terminal", {}).get("title", handle)
            self.registro_sesiones.registrar(
                SesionAgente(handle=handle, repo="", titulo=titulo, modelo="", cursor=None)
            )
        self.registro_sesiones.activar_relay(handle)
        sesion = self.registro_sesiones.obtener(handle)
        self.senales.sesion_relay.emit(sesion.titulo if sesion else handle)
        return {"ok": True}

    def _manejar_sesion_relay_salir(self, _datos: dict) -> dict:
        self.registro_sesiones.salir_relay()
        self.senales.sesion_relay.emit(None)
        return {"ok": True}

    def _manejar_monitorear_terminal(self, datos: dict) -> dict:
        terminal = datos.get("terminal", "")
        etiqueta = datos.get("etiqueta", "")
        if terminal in self._monitores_activos:
            return {"ok": True, "ya_activo": True}
        self._monitores_activos.add(terminal)

        async def _hablar_aviso(texto: str) -> None:
            await self._hablar(texto)
            self.senales.respuesta.emit(texto)

        monitor = MonitorTerminal(
            terminal=terminal,
            etiqueta=etiqueta,
            nombre_proyecto=datos.get("proyecto", "un proyecto"),
            orca=self.orca,
            cerebro=self.cerebro,
            coordinador_media=self.coordinador_media,
            on_hablar=_hablar_aviso,
        )

        async def _correr():
            try:
                await monitor.ejecutar()
            except Exception:
                logger.exception("Fallo el monitor de %s", terminal)
            finally:
                self._monitores_activos.discard(terminal)

        if self._loop_asyncio is not None:
            asyncio.run_coroutine_threadsafe(_correr(), self._loop_asyncio)
        return {"ok": True}

    def _manejar_listar_proyectos(self, _datos: dict) -> dict:
        async def _listar():
            respuesta = await self.orca.listar_repos()
            repos = respuesta.get("result", {}).get("repos", [])
            alias = self.config.get("alias_proyectos", {})
            return {
                "proyectos": [{"id": r["id"], "nombre": r["displayName"]} for r in repos],
                "alias": alias,
            }

        return self._correr_en_asyncio(_listar())

    # --- Voz de salida -------------------------------------------------

    def _on_texto_parcial_cerebro(self, texto_delta: str) -> None:
        if self._generacion_turno_en_curso != self._generacion_actual:
            return  # este turno ya fue interrumpido: no sintetizar más
        oraciones = self._segmentador.agregar(texto_delta)
        for oracion in oraciones:
            generacion = self._generacion_actual
            if self._loop_asyncio is not None:
                asyncio.run_coroutine_threadsafe(self._hablar(oracion, generacion), self._loop_asyncio)

    async def _hablar(self, texto: str, generacion: int | None = None) -> None:
        if generacion is not None and generacion != self._generacion_actual:
            return  # se interrumpió mientras se sintetizaba: no encolar
        limpio = limpiar_para_voz(texto)
        if not limpio:
            return

        await hablar_oraciones(
            oraciones=[limpio],
            texto_completo=texto,
            voz=self.config.get("voz", {}).get("nombre", "es-MX-DaliaNeural"),
            reproductor=self.reproductor,
            on_fallo_sintesis=lambda t: self.senales.respuesta.emit(t),
        )

    # --- Turno de conversación ------------------------------------------

    async def _procesar_turno(self, texto_usuario: str) -> None:
        self.senales.frase_usuario.emit(texto_usuario)
        self.maquina.fin_de_voz()
        self._generacion_turno_en_curso = self._generacion_actual
        mi_generacion = self._generacion_actual
        try:
            if self.registro_sesiones.relay_activa is not None:
                sesion = self.registro_sesiones.sesion_relay
                self.maquina.agente_empezo_a_trabajar(sesion.handle if sesion else "relay")
            self.maquina.primera_oracion_lista()
            respuesta = await self.cerebro.enviar_turno(texto_usuario)
            resto = self._segmentador.flush()
            if resto:
                await self._hablar(resto, mi_generacion)
            self.senales.respuesta.emit(respuesta)
        finally:
            self.maquina.fin_de_reproduccion()

    # --- Audio -----------------------------------------------------------

    def _on_bloque_audio(self, bloque: np.ndarray) -> None:
        self.senales.amplitud.emit(float(np.abs(bloque).mean()))

        if self._detector_wake_word is not None:
            bloque_int16 = np.clip(bloque * 32767, -32768, 32767).astype(np.int16).flatten()
            self._detector_wake_word.procesar_bloque(bloque_int16)

        if self.maquina.estado == Estado.ESCUCHANDO and self._detector_fin_de_frase is not None:
            self._buffer_frase.append(bloque.copy())
            duracion_bloque_s = len(bloque) / self._grabador.tasa_efectiva if self._grabador else 0.0
            resultado = self._detector_fin_de_frase.procesar_bloque(bloque, duracion_bloque_s)
            if resultado == ResultadoBloque.SIN_VOZ:
                self._buffer_frase = []
                self.maquina.sin_voz_tras_activacion()
            elif resultado in (ResultadoBloque.FIN_POR_SILENCIO, ResultadoBloque.MAXIMO_ALCANZADO):
                audio = np.concatenate(self._buffer_frase) if self._buffer_frase else np.array([], dtype="float32")
                self._buffer_frase = []
                self._detector_fin_de_frase.reiniciar()
                if self._loop_asyncio is not None:
                    asyncio.run_coroutine_threadsafe(self._transcribir_y_procesar(audio), self._loop_asyncio)

    async def _transcribir_y_procesar(self, audio: np.ndarray) -> None:
        loop = asyncio.get_event_loop()
        texto = await loop.run_in_executor(None, self.transcriber.transcribe, audio, self._grabador.tasa_efectiva)
        if not texto:
            self.maquina.sin_voz_tras_activacion()
            return
        await self._procesar_turno(texto)

    def _on_wake_word(self) -> None:
        # Corta lo que se esté hablando/sintetizando y descarta lo que
        # quedaba pendiente de un turno anterior (D5/D11: interrupción en
        # menos de 300 ms). Inofensivo si no había nada sonando.
        self._generacion_actual += 1
        self.reproductor.interrumpir()

        self._buffer_frase = []
        if self._detector_fin_de_frase is not None:
            self._detector_fin_de_frase.reiniciar()
        self.maquina.wake_word_detectada()
        if self._loop_asyncio is not None:
            asyncio.run_coroutine_threadsafe(self.coordinador_media.esperar_tareas_pendientes(), self._loop_asyncio)

    # --- Arranque / cierre -------------------------------------------------

    def iniciar_audio(self) -> None:
        try:
            self.transcriber.load()
        except RuntimeError:
            logger.exception("No se pudo inicializar el transcriptor (falta GROQ_API_KEY?)")
            self.senales.respuesta.emit("No pude iniciar la transcripción: revisá GROQ_API_KEY en .env.")

        self._grabador = GrabadorContinuo()

        ruta_modelo = RAIZ / self.config.get("audio", {}).get("wake_word", {}).get("modelo", "modelos/hey_jarvis.onnx")
        umbral = self.config.get("audio", {}).get("wake_word", {}).get("umbral", 0.5)
        try:
            self._detector_wake_word = DetectorWakeWord(
                ruta_modelo=ruta_modelo, umbral=umbral, on_deteccion=self._on_wake_word
            )
        except ModeloWakeWordNoEncontrado:
            logger.exception("No se encontró el modelo de wake word; la activación por voz queda deshabilitada")
            self.senales.respuesta.emit("No encontré el modelo de la palabra de activación.")

        fin_frase_cfg = self.config.get("audio", {}).get("fin_de_frase", {})
        self._detector_fin_de_frase = DetectorFinDeFrase(
            umbral_rms=fin_frase_cfg.get("umbral_rms", 0.02),
            silencio_s=fin_frase_cfg.get("silencio_s", 1.2),
            sin_voz_s=fin_frase_cfg.get("sin_voz_s", 5),
            maximo_s=fin_frase_cfg.get("maximo_s", 30),
        )

        self._grabador.suscribir(self._on_bloque_audio)
        self._grabador.iniciar()

    def iniciar_asyncio(self) -> None:
        def _correr_loop() -> None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._loop_asyncio = loop
            loop.run_forever()

        self._hilo_asyncio = threading.Thread(target=_correr_loop, daemon=True)
        self._hilo_asyncio.start()

        import time

        while self._loop_asyncio is None:
            time.sleep(0.01)

        self.coordinador_media.establecer_loop(self._loop_asyncio)

        import os

        os.environ[VARIABLE_ENTORNO_PUERTO] = str(self.canal_local.puerto_real)
        os.environ[VARIABLE_ENTORNO_TOKEN] = self._token_canal_local
        self.canal_local.iniciar()
        self.reproductor.iniciar()

        asyncio.run_coroutine_threadsafe(self.cerebro.iniciar(), self._loop_asyncio).result(timeout=30)

    async def _cerrar_audio(self) -> None:
        if self._grabador is not None:
            self._grabador.detener()

    async def _cerrar_cerebro(self) -> None:
        await self.cerebro.detener()

    async def _cerrar_canal_local(self) -> None:
        self.canal_local.detener()

    def cerrar_audio_sync(self) -> None:
        if self._grabador is not None:
            self._grabador.detener()

    def cerrar_canal_local_sync(self) -> None:
        self.canal_local.detener()


def main() -> None:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    loki = Loki()
    loki.iniciar_asyncio()
    overlay = Overlay()

    def _al_cambiar_estado(anterior, nuevo) -> None:
        metodo = {
            Estado.DORMIDO: overlay.mostrar_dormido,
            Estado.ESCUCHANDO: overlay.mostrar_escuchando,
            Estado.PENSANDO: overlay.mostrar_pensando,
            Estado.HABLANDO: overlay.mostrar_hablando,
        }.get(nuevo)
        if metodo is not None:
            metodo()

    loki.senales.cambio_estado.connect(_al_cambiar_estado)
    loki.senales.amplitud.connect(overlay.set_amplitud)
    loki.senales.frase_usuario.connect(overlay.mostrar_ultima_frase_usuario)
    loki.senales.respuesta.connect(overlay.mostrar_ultima_respuesta)
    loki.senales.sesion_relay.connect(overlay.mostrar_sesion_relay)

    overlay.show()

    async def _cerrar_audio_async():
        await loki._cerrar_audio()

    def _alternar_overlay() -> None:
        overlay.setVisible(not overlay.isVisible())

    def _reiniciar_conversacion() -> None:
        if loki._loop_asyncio is not None:
            asyncio.run_coroutine_threadsafe(loki.cerebro.reiniciar_conversacion(), loki._loop_asyncio)

    bandeja = Bandeja(
        icono=icono_bandeja(),
        on_alternar_overlay=_alternar_overlay,
        on_reiniciar_conversacion=_reiniciar_conversacion,
        cerrar_audio=loki._cerrar_audio,
        cerrar_cerebro=loki._cerrar_cerebro,
        cerrar_canal_local=loki._cerrar_canal_local,
        loop=loki._loop_asyncio,
    )
    bandeja.show()

    loki.iniciar_audio()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
