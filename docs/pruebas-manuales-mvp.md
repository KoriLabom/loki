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
| A1 | Decir "hey Jarvis" en estado dormido dispara el callback en menos de 500 ms | captura-de-voz | Pendiente | |
| A2 | Hablar con otra persona sin decir la palabra de activación no graba ni transcribe nada | captura-de-voz | Pendiente | |
| A3 | Con un modelo de wake word configurado a un archivo inexistente, Loki avisa el error (overlay + log) y no se cierra | captura-de-voz | Hecho (test automatizado, tarea 4.2) | `ModeloWakeWordNoEncontrado` con mensaje claro; cubierto por `tests/test_wake_word.py` |

## Silencio y fin de frase

| # | Escenario | Spec | Estado | Resultado |
|---|-----------|------|--------|-----------|
| S1 | El usuario deja de hablar más del umbral de silencio (1,2 s por defecto): la grabación termina y pasa a transcripción | captura-de-voz | Pendiente | Lógica del detector cubierta por tests sintéticos (`tests/test_fin_de_frase.py`); falta la corrida con voz real |
| S2 | Pasan 5 s desde la activación sin voz: Loki vuelve a dormido sin transcribir | captura-de-voz | Pendiente | Ídem: lógica cubierta por test, falta la corrida real |
| S3 | La grabación llega a los 30 s: se corta y se transcribe lo grabado hasta ahí | captura-de-voz | Pendiente | Ídem |
| S4 | Transcripción vacía o alucinada: Loki vuelve a dormido sin llamar al cerebro y avisa brevemente | captura-de-voz | Pendiente | Filtro de alucinaciones cubierto por test (`tests/test_transcriber.py`); falta la corrida real con silencio/ruido |

## Interrupción

| # | Escenario | Spec | Estado | Resultado |
|---|-----------|------|--------|-----------|
| I1 | Loki hablando + el usuario dice la palabra de activación: la voz se corta en menos de 300 ms y pasa a escuchando | captura-de-voz, voz-de-salida | Pendiente | Transición de estados y corte de cola cubiertos por tests (`tests/test_estados.py`, `tests/test_reproductor.py`); falta medir el tiempo real |

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
| O1 | Los cinco estados se ven distinguibles (dormido, escuchando, pensando, hablando, agente trabajando) | overlay-de-estado | Parcial | Render offscreen verificado (capturas PNG durante la tarea 6.2): la onda, el punto tenue de dormido y los indicadores de relay/agente se ven correctos; el entorno de renderizado sin pantalla no tiene fuentes instaladas, así que el texto salió en blanco en las capturas. En una pantalla real con Segoe UI instalada (todas las Windows) esto no debería pasar, pero falta confirmarlo mirando la ventana real. |
| O2 | La onda reacciona al volumen mientras escucha | overlay-de-estado | Pendiente | Lógica de amplitud cubierta por test; falta verla moverse con voz real |
| O3 | Primera ejecución sin posición guardada: aparece centrado abajo en el monitor principal | overlay-de-estado | Pendiente | Resolución de posición cubierta por `tests/test_posicion.py`; falta la corrida real |
| O4 | Mover el overlay y cerrar Loki: la próxima vez aparece en el mismo lugar si el monitor sigue conectado | overlay-de-estado | Pendiente | Ídem |
| O5 | La posición guardada corresponde a un monitor desconectado: vuelve a la posición por defecto | overlay-de-estado | Hecho (test automatizado) | `tests/test_posicion.py::test_posicion_fuera_de_todas_las_pantallas_se_descarta` |
| O6 | Cambiar el acento en `paleta.py` cambia la onda y los textos sin tocar otro código | overlay-de-estado | **Hecho** | Verificado visualmente (tarea 6.1): capturas antes/después con acento cambiado de terracota a azul, la onda cambió de color. |

## Bandeja del sistema

| # | Escenario | Spec | Estado | Resultado |
|---|-----------|------|--------|-----------|
| B1 | Mostrar/ocultar overlay desde el menú de la bandeja | overlay-de-estado | Pendiente | Wiring del menú cubierto por `tests/test_bandeja.py`; falta clickearlo de verdad |
| B2 | Reiniciar conversación desde la bandeja | overlay-de-estado | Pendiente | Ídem |
| B3 | Salir detiene la escucha, cierra el cerebro y termina sin procesos huérfanos | overlay-de-estado | Parcial | El orden de cierre (audio, cerebro, canal local) está cubierto por `tests/test_bandeja.py`. Además, al terminar la tarea 10.1 se mató el árbol completo de procesos de una corrida real de `python -m loki.main` (incluido el subproceso de `claude`) y no quedaron huérfanos — pero fue con `taskkill /T`, no clickeando "Salir" en la bandeja real. Falta esa verificación puntual. |

## Voz de salida

| # | Escenario | Spec | Estado | Resultado |
|---|-----------|------|--------|-----------|
| V1 | La voz por defecto (`es-MX-DaliaNeural`) se escucha en español neutro | voz-de-salida | Parcial | La síntesis real contra el servicio de edge-tts produjo un MP3 válido y de duración razonable (tarea 3.2); falta escucharlo con parlantes reales. |
| V2 | Una respuesta larga empieza a sonar antes de terminar de generarse | voz-de-salida | Pendiente | Segmentación por oración y cola de reproducción cubiertas por tests (`tests/test_tts.py`, `tests/test_reproductor.py`); falta la percepción real de la latencia |
| V3 | Un bloque de código en la respuesta no se lee en voz alta | voz-de-salida | Hecho (test automatizado) | `tests/test_limpieza_texto.py` |
| V4 | Si falla la síntesis, el texto completo queda visible en el overlay y Loki sigue operativo | voz-de-salida | Hecho (test automatizado) | `tests/test_salida.py` |

---

**Resumen**: de los escenarios sin cobertura automática completa, los que
dependían de poder ejecutar comandos reales contra Claude Code, Orca o
Windows (media, MCP, confirmación crítica, relay, skill, CLAUDE.md) se
verificaron en vivo durante la implementación. Los que dependen de
escuchar, hablar, o mirar la pantalla real (activación por voz, timings
de silencio e interrupción al oído, calidad de la voz, posición del
overlay en un monitor real, los tres ítems de la bandeja) quedan
pendientes de que alguien con micrófono, parlantes y pantalla los corra
y complete la columna de resultado antes de cerrar el change.
