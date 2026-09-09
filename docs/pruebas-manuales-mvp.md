# Pruebas manuales del MVP

Escenarios de las specs marcados como "manualmente" en `tasks.md`, o que
no tienen (ni pueden tener razonablemente) un test automático porque
dependen de hardware real: micrófono, parlantes, un segundo monitor, o
la vista de una persona.

Durante la implementación (tareas 1 a 10.2) se corrieron varias de estas
pruebas contra el runtime real (Claude Code, Orca, Windows) desde una
sesión sin micrófono ni parlantes; esas quedan marcadas como **hecho**
con la evidencia. Las que dependen de escuchar, hablar o mirar la
pantalla real quedan **pendientes**: alguien con el hardware tiene que
correrlas y completar la columna de resultado antes de cerrar el change.

## Activación

| # | Escenario | Spec | Estado | Resultado |
|---|-----------|------|--------|-----------|
| A1 | Decir "hey Jarvis" en estado dormido dispara el callback en menos de 500 ms | captura-de-voz | **Hecho** | Confirmado con hardware real: la onda empieza a moverse y el estado pasa a escuchando al decir "hey Jarvis". |
| A2 | Hablar con otra persona sin decir la palabra de activación no graba ni transcribe nada | captura-de-voz | Pendiente | No se probó explícitamente, pero se infiere del diseño (el detector de wake word es el único gate hacia escuchando). |
| A3 | Con un modelo de wake word configurado a un archivo inexistente, Loki avisa el error (overlay + log) y no se cierra | captura-de-voz | Hecho (test automatizado, tarea 4.2) | `ModeloWakeWordNoEncontrado` con mensaje claro; cubierto por `tests/test_wake_word.py` |

## Silencio y fin de frase

| # | Escenario | Spec | Estado | Resultado |
|---|-----------|------|--------|-----------|
| S1 | El usuario deja de hablar más del umbral de silencio (1,2 s por defecto): la grabación termina y pasa a transcripción | captura-de-voz | **Hecho** | Confirmado con voz real: **encontrado y corregido un bug real** — `main.py` nunca calculaba la duración real de cada bloque de audio (quedaba fija en `0.0`), así que el reloj interno del detector de silencio nunca avanzaba y jamás cortaba. Corregido calculando la duración desde el tamaño del bloque y la tasa de muestreo. |
| S2 | Pasan 5 s desde la activación sin voz: Loki vuelve a dormido sin transcribir | captura-de-voz | **Hecho** | Confirmado con el mismo fix: activar y quedarse en silencio vuelve a dormido sin llamar al cerebro. |
| S3 | La grabación llega a los 30 s: se corta y se transcribe lo grabado hasta ahí | captura-de-voz | Pendiente | Mismo mecanismo que S1/S2, ya corregido; falta la corrida específica de 30 s hablando sin parar. |
| S4 | Transcripción vacía o alucinada: Loki vuelve a dormido sin llamar al cerebro y avisa brevemente | captura-de-voz | Pendiente | Filtro de alucinaciones cubierto por test (`tests/test_transcriber.py`); falta la corrida real con silencio/ruido |

## Interrupción

| # | Escenario | Spec | Estado | Resultado |
|---|-----------|------|--------|-----------|
| I1 | Loki hablando + el usuario dice la palabra de activación: la voz se corta en menos de 300 ms y pasa a escuchando | captura-de-voz, voz-de-salida | **Hecho** | Confirmado con voz real: **encontrado y corregido un bug real** — nada llamaba a `reproductor.interrumpir()` al detectar la palabra de activación mientras Loki hablaba, así que seguía terminando su respuesta y encolando la siguiente. Corregido en `_on_wake_word` (llama a `interrumpir()` y descarta con un contador de "generación" las oraciones del turno viejo que todavía no se habían sintetizado). |

## Media

| # | Escenario | Spec | Estado | Resultado |
|---|-----------|------|--------|-----------|
| M1 | Video reproduciéndose + activación: se pausa en menos de 500 ms y Loki recuerda que fue él quien pausó | control-de-media | **Hecho** | Verificado en vivo contra un video real de YouTube en Chrome (tarea 5.2): `pausar_si_hay_reproduccion()` pasó el estado de PLAYING a PAUSED por la API de Windows, y `reanudar()` lo devolvió a PLAYING. Ver `loki/herramientas/media.py`. |
| M2 | Nada reproduciéndose + activación: no se envía ninguna orden de media | control-de-media | Hecho (test automatizado) | `tests/test_media.py::test_nada_reproduciendose_no_envia_ninguna_orden` |
| M3 | Media ya pausado antes de la activación: Loki no lo toca y no lo reanuda al terminar | control-de-media | Hecho (test automatizado) | `tests/test_media.py::test_media_ya_pausado_no_se_toca_y_no_se_reanuda_despues` |
| M4 | Aviso no solicitado con media reproduciéndose: pausa, habla, espera 4 s una activación, reanuda si no la hay | control-de-media | Hecho (test automatizado) | `tests/test_coordinador_media.py`, `tests/test_monitor.py` |
| M5 | Falla la consulta de la API de media: Loki sigue la interacción con normalidad | control-de-media | Hecho (test automatizado) | `tests/test_media.py::test_fallo_al_consultar_sesion_no_interrumpe_la_interaccion` |

## Relay y flujo de desarrollo por voz

| # | Escenario | Spec | Estado | Resultado |
|---|-----------|------|--------|-----------|
| R1 | Pedir agregar una función abre una sesión de explore con el modelo configurado y activa el relay | sesiones-de-agentes, flujo-de-desarrollo-por-voz | **Hecho** | Prueba de punta a punta real (tarea 9.2) contra el propio repo de Loki: se abrió una sesión con Fable y se activó el relay por MCP. |
| R2 | Pedir "proponelo" durante el relay envía `/opsx:propose` y Loki dice el nombre del change creado | flujo-de-desarrollo-por-voz | **Hecho** | Misma prueba: se creó el change real `agregar-contributing` (existe en `openspec/changes/`). |
| R3 | Pedir "aplicalo" crea un worktree nuevo con una terminal en el modelo de implementación (Sonnet) | flujo-de-desarrollo-por-voz | **Hecho** | Misma prueba: worktree y rama nuevos, terminal con Sonnet 5 corriendo `/opsx:apply`. El worktree de la prueba se descartó después (`orca worktree rm --force`) por ser un artefacto de la prueba, no un cambio real pedido por el usuario. |
| R4 | El monitor de una terminal en apply avisa por voz al terminar, preguntar, o pedir permiso, respetando la secuencia de media | flujo-de-desarrollo-por-voz | Hecho (test automatizado) + parcialmente en vivo | `tests/test_monitor.py`; en la prueba en vivo el monitor se registró contra la terminal correcta pero no llegó a completarse el ciclo (se cortó al detectar que el apply había tomado el change equivocado, tarea 9.2) |
| R5 | Dos monitores simultáneos producen avisos identificables (nombre de proyecto distinto) | flujo-de-desarrollo-por-voz | Hecho (test automatizado) | `tests/test_monitor.py::test_dos_monitores_simultaneos_producen_avisos_identificables` |
| R6 | Salir del relay hace que los mensajes vuelvan al cerebro sin cerrar la sesión de agente | sesiones-de-agentes | Hecho (test automatizado) | `tests/test_controlador_conversacion.py` |
| R7 | Cambiar de sesión de relay por voz actualiza el overlay con el nuevo nombre | sesiones-de-agentes | Hecho (test automatizado) | `tests/test_controlador_conversacion.py` |

## Confirmación de acciones críticas

| # | Escenario | Spec | Estado | Resultado |
|---|-----------|------|--------|-----------|
| C1 | Pedir cerrar una terminal termina en `pedir_confirmacion` y no se ejecuta sin `confirmacion_id` válido | confirmacion-de-acciones-criticas, cerebro | **Hecho** | Verificado en vivo (tarea 7.5): el cerebro rechazó `Bash(orca terminal close)` y llamó a `pedir_confirmacion` con el identificador exacto, y `cerrar_terminal` solo ejecutó tras un `confirmacion_id` válido. |
| C2 | Usuario confirma con una afirmación clara dentro de los 10 s: la acción se ejecuta | confirmacion-de-acciones-criticas | Pendiente (secuencia de voz real) | Lógica de clasificación y vencimiento cubierta por `tests/test_confirmacion.py`; falta correrla con una respuesta hablada real |
| C3 | Usuario niega, duda, o no responde: la acción se cancela y Loki lo dice | confirmacion-de-acciones-criticas | Pendiente (secuencia de voz real) | Ídem, cubierto por test con `escuchar` simulado |
| C4 | Un `confirmacion_id` vencido o de otra acción se rechaza | confirmacion-de-acciones-criticas | Hecho (test automatizado) | `tests/test_confirmacion.py`, `tests/test_servidor_mcp.py` |

## Overlay

| # | Escenario | Spec | Estado | Resultado |
|---|-----------|------|--------|-----------|
| O1 | Los cinco estados se ven distinguibles (dormido, escuchando, pensando, hablando, agente trabajando) | overlay-de-estado | Parcial | **Hecho** para dormido/escuchando/pensando/hablando: confirmados visualmente en pantalla real durante una conversación de punta a punta, con texto legible (a diferencia del render offscreen de la tarea 6.2, que no tenía fuentes). Falta ver "agente trabajando" (requiere una sesión de relay o un monitor de apply activo). |
| O2 | La onda reacciona al volumen mientras escucha | overlay-de-estado | **Hecho** | Confirmado: la onda se mueve al hablar después de decir "hey Jarvis". |
| O3 | Primera ejecución sin posición guardada: aparece centrado abajo en el monitor principal | overlay-de-estado | **Hecho** | Confirmado en la primera corrida (sin `config.local.yaml`): apareció centrado abajo. |
| O4 | Mover el overlay y cerrar Loki: la próxima vez aparece en el mismo lugar si el monitor sigue conectado | overlay-de-estado | Pendiente | No se probó (no se arrastró el overlay todavía). |
| O5 | La posición guardada corresponde a un monitor desconectado: vuelve a la posición por defecto | overlay-de-estado | Hecho (test automatizado) | `tests/test_posicion.py::test_posicion_fuera_de_todas_las_pantallas_se_descarta` |
| O6 | Cambiar el acento en `paleta.py` cambia la onda y los textos sin tocar otro código | overlay-de-estado | **Hecho** | Verificado visualmente (tarea 6.1): capturas antes/después con acento cambiado de terracota a azul, la onda cambió de color. |

## Bandeja del sistema

| # | Escenario | Spec | Estado | Resultado |
|---|-----------|------|--------|-----------|
| B1 | Mostrar/ocultar overlay desde el menú de la bandeja | overlay-de-estado | **Hecho** | Confirmado clickeando de verdad: el overlay aparece y desaparece. |
| B2 | Reiniciar conversación desde la bandeja | overlay-de-estado | **Hecho** | Confirmado clickeando de verdad. |
| B3 | Salir detiene la escucha, cierra el cerebro y termina sin procesos huérfanos | overlay-de-estado | **Hecho** | Confirmado clickeando "Salir" en la bandeja real: el overlay y el ícono desaparecieron, el proceso terminó con código 0, y no quedó ningún `python.exe` ni subproceso `claude` huérfano. **Encontrado y corregido un bug real en el camino**: el menú de la bandeja corre en el hilo de Qt, que no tiene loop de asyncio propio, así que `_salir()` agendaba el cierre con `asyncio.ensure_future` en un loop que nadie corría y no pasaba nada. Se corrigió pasándole a `Bandeja` el loop real de la app y usando `run_coroutine_threadsafe`. |

## Voz de salida

| # | Escenario | Spec | Estado | Resultado |
|---|-----------|------|--------|-----------|
| V1 | La voz por defecto (`es-MX-DaliaNeural`) se escucha en español neutro | voz-de-salida | **Hecho** | Confirmado con parlantes reales: se escucha clara, en español neutro. |
| V2 | Una respuesta larga empieza a sonar antes de terminar de generarse | voz-de-salida | Pendiente | Se escuchó una respuesta completa correctamente, pero no se midió específicamente la latencia hasta la primera oración en una respuesta larga. |
| V3 | Un bloque de código en la respuesta no se lee en voz alta | voz-de-salida | Hecho (test automatizado) | `tests/test_limpieza_texto.py` |
| V4 | Si falla la síntesis, el texto completo queda visible en el overlay y Loki sigue operativo | voz-de-salida | Hecho (test automatizado) | `tests/test_salida.py` |

---

## Sesión de pruebas con hardware real (2026-09-09)

Con el usuario frente a la máquina, micrófono y parlantes reales, se
corrió `python -m loki.main` de verdad y se probó el flujo completo:
activación, silencio, interrupción, transcripción, respuesta hablada, y
los tres ítems de la bandeja. **Se encontraron y corrigieron 5 bugs
reales** que ningún test automatizado podía atrapar porque dependían de
la integración real entre hilos (Qt, audio, asyncio) y del hardware:

1. **Ícono de bandeja vacío** (`main.py` le pasaba un `QIcon()` sin
   imagen a `Bandeja`). Se agregó `loki/ui/paleta.py:icono_bandeja()`,
   que genera un círculo terracota simple en código.
2. **`CoordinadorMedia` no podía lanzar corrutinas desde el hilo de
   audio** (el callback de wake word corre en el hilo de PortAudio, sin
   loop de asyncio propio; `asyncio.ensure_future` fallaba con
   `RuntimeError`). Se le agregó un loop explícito y
   `run_coroutine_threadsafe`.
3. **El detector de fin de frase nunca avanzaba su reloj interno**:
   `main.py` nunca calculaba la duración real de cada bloque de audio
   (quedaba en `0.0` fija), así que ni el silencio ni el máximo de 30 s
   cortaban nunca la grabación. Se corrigió calculando la duración real
   desde el tamaño del bloque y la tasa de muestreo.
4. **La interrupción por wake word no cortaba la voz**: nada llamaba a
   `reproductor.interrumpir()` al detectar la activación mientras Loki
   hablaba. Se agregó la llamada, más un contador de "generación" para
   descartar oraciones de un turno ya interrumpido que todavía no se
   habían sintetizado.
5. **"Salir" de la bandeja no hacía nada**: el menú corre en el hilo de
   Qt, sin loop de asyncio propio, así que `asyncio.ensure_future`
   agendaba el cierre en un loop que nadie corría. Se le pasó a
   `Bandeja` el loop real de la app y se usó `run_coroutine_threadsafe`.

Después de estos arreglos, se confirmó en vivo: activación por wake
word, fin de frase por silencio, transcripción real, respuesta hablada
en español neutro, los cuatro estados principales del overlay con la
onda reactiva, la posición por defecto centrada abajo, interrupción por
wake word mientras habla, y las tres acciones de la bandeja (mostrar/
ocultar, reiniciar, salir sin procesos huérfanos).

**Resumen general**: de los escenarios sin cobertura automática
completa, los que dependían de poder ejecutar comandos reales contra
Claude Code, Orca o Windows (media, MCP, confirmación crítica, relay,
skill, CLAUDE.md) se verificaron en vivo durante la implementación; los
que dependían de escuchar, hablar o mirar la pantalla real se
verificaron en esta sesión con el usuario y el hardware real. Quedan
pendientes: A2 (conversación ajena sin wake word), S3 (corte a los 30 s
hablando sin parar), S4 (transcripción vacía/alucinada con silencio o
ruido real), O1 el indicador de "agente trabajando", O4 (persistencia de
posición movida), V2 (medir la latencia real hasta la primera oración),
y C2/C3 (la secuencia hablada de confirmación de una acción crítica, que
requiere disparar una acción como cerrar una terminal por voz).
