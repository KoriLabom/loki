## 1. Estructura del repo y configuración

- [x] 1.1 Inicializar git en la carpeta, crear `.gitignore` (venv, `.env`, `config.local.yaml`, `__pycache__`, logs, posición del overlay) y verificar con `git status` que ninguno de esos archivos aparece como rastreable
- [x] 1.2 Crear la estructura de paquetes de D14 (`loki/` con `audio/`, `cerebro/`, `voz/`, `herramientas/`, `ui/`, `persona/`, más `scripts/` y `tests/`) con `__init__.py` vacíos y verificar que `python -c "import loki"` funciona desde la raíz
- [x] 1.3 Crear `requirements.txt` con PyQt6, sounddevice, numpy, groq, python-dotenv, openwakeword, onnxruntime, edge-tts, miniaudio, mcp, pyyaml, winrt-Windows.Media.Control (y sus paquetes WinRT base), pyautogui, pytest; verificar que `pip install -r requirements.txt` termina sin errores en un venv limpio
- [x] 1.4 Implementar `loki/config.py` con carga en tres capas (`config.yaml`, `config.local.yaml`, `.env`) según D12, escribir `config.yaml` con los defaults (modelos haiku/fable/sonnet, voz es-MX-DaliaNeural, umbrales de silencio 1,2 s / 5 s / 30 s, ruta del modelo de wake word, lista de acciones críticas, puerto del canal local) y las plantillas `config.local.example.yaml` y `.env.example`; verificar con tests que un override en la capa local gana sobre el default y que sin archivo local se usan los defaults
- [x] 1.5 Copiar `vocabulary.py`, `vocabulary.txt` y los tests de vocabulario desde voice-transcript a `loki/audio/`, adaptar imports y verificar que `pytest tests/test_vocabulary.py` pasa

## 2. Cerebro: Claude Code headless

- [x] 2.1 Spike de validación de D1: script en `scripts/spike_claude_headless.py` que lanza `claude -p --input-format stream-json --output-format stream-json --verbose --model haiku`, envía dos mensajes de usuario en la misma invocación y comprueba que el segundo turno recuerda el primero; registrar el resultado en design.md (multi-turno funciona, o se pasa al fallback con `--resume`) y verificar que el script imprime los `content_block_delta` de texto en orden
- [x] 2.2 Implementar `loki/cerebro/claude_headless.py`: arranque del subproceso con los flags de D1 y D2 (modelo, `--append-system-prompt-file`, `--allowedTools`, `--disallowedTools`, cwd en el repo), escritura de turnos en stdin, lectura asíncrona de stdout con encoding UTF-8, callback de texto parcial y detección del evento `result`; verificar con tests que usan un subproceso falso que los deltas llegan en orden y que el fin de turno se detecta
- [x] 2.3 Implementar reinicio de conversación (matar y relanzar el subproceso), reintento automático si el proceso murió, y timeout de turno de 120 s con aviso; verificar con tests que tras un fallo simulado el próximo turno relanza el proceso
- [x] 2.4 Escribir `loki/persona/system_prompt.md` con la personalidad de la spec `cerebro` (español neutro, formal, conciso, respuestas para ser escuchadas, decir qué hizo en una oración, preguntar ante ambigüedad de proyecto) y las reglas de uso de las herramientas MCP y del CLI de Orca; verificar manualmente con el spike que una pregunta simple recibe una respuesta de menos de cuatro oraciones y que un pedido de cerrar una terminal termina en una llamada a `pedir_confirmacion`

## 3. Voz de salida

- [x] 3.1 Implementar `loki/voz/limpieza_texto.py` que quita bloques de código, URLs, rutas largas y marcas markdown reemplazándolos por menciones breves; verificar con tests las cuatro clases de contenido
- [x] 3.2 Implementar `loki/voz/tts.py` con segmentación de texto parcial en oraciones y síntesis con edge-tts a MP3 en memoria usando la voz de la configuración; verificar con un test que un stream de texto con tres oraciones produce tres segmentos en orden, y manualmente que la voz por defecto se escucha en español neutro
- [x] 3.3 Implementar `loki/voz/reproductor.py`: hilo con cola ordenada, decodificación con miniaudio, reproducción con sounddevice, método `interrumpir()` que vacía la cola y corta la reproducción actual; verificar con tests que interrumpir descarta los pendientes y manualmente que una respuesta larga empieza a sonar antes de terminar de generarse
- [x] 3.4 Fallback ante fallo de síntesis: mostrar el texto completo en el overlay y registrar el error sin perder el turno; verificar con un test que simula el fallo de edge-tts

## 4. Captura de voz

- [x] 4.1 Adaptar `recorder.py` de voice-transcript a `loki/audio/recorder.py` como stream continuo a 16 kHz mono con remuestreo por decimación si el dispositivo no lo soporta, entregando bloques a suscriptores (detector de wake word, grabador de frase, amplitud para el overlay); verificar con tests que los suscriptores reciben los mismos bloques
- [x] 4.2 Implementar `loki/audio/wake_word.py` con openWakeWord y el modelo `hey_jarvis`, ruta y umbral desde configuración, error claro si el archivo del modelo no existe; verificar con un test que un archivo inexistente produce el error sin cerrar la app y manualmente que decir "hey Jarvis" dispara el callback en menos de 500 ms
- [x] 4.3 Implementar `loki/audio/fin_de_frase.py` con la lógica de D5 (inicio de voz por RMS, corte por 1,2 s de silencio, sin voz en 5 s, máximo 30 s), umbrales desde configuración; verificar con tests que alimentan señales sintéticas para los tres casos de la spec
- [x] 4.4 Copiar y adaptar `transcriber.py` a `loki/audio/transcriber.py` (Groq Whisper large-v3, vocabulario, filtro de alucinaciones, timeout configurable); verificar que los tests de transcripción copiados y adaptados pasan

## 5. Máquina de estados y control de media

- [x] 5.1 Implementar `loki/estados.py` con los estados dormido, escuchando, pensando, hablando y el estado paralelo agente trabajando, las transiciones de D11 y una lista de observadores; verificar con tests cada transición de la spec, incluida la interrupción por wake word durante hablando
- [x] 5.2 Implementar `loki/herramientas/media.py` con WinRT (`GlobalSystemMediaTransportControlsSessionManager`): estado actual, pausar recordando la sesión, reanudar solo esa sesión, no tocar media ya pausado, fallback a tecla multimedia si WinRT no carga; verificar con tests que usan un manager falso los tres escenarios de la spec y manualmente con YouTube en el browser
- [x] 5.3 Conectar media con la máquina de estados: pausar al detectar wake word si hay reproducción, reanudar al volver a dormido sin confirmación pendiente, y secuencia de aviso no solicitado (pausar, hablar, esperar 4 s, reanudar); verificar con tests de la máquina de estados que las llamadas a media ocurren en el momento correcto

## 6. Overlay y bandeja

- [x] 6.1 Crear `loki/ui/paleta.py` con los colores y tipografía de D15 y adaptar el overlay copiado de voice-transcript para que tome todos sus colores de ahí; verificar visualmente que cambiar el acento en un solo lugar cambia onda y textos
- [x] 6.2 Implementar en `loki/ui/overlay.py` los cinco estados visuales, la onda reactiva al volumen, la última frase del usuario, la última respuesta y el nombre de la sesión de relay; verificar manualmente con un script que recorre los estados y con un test de que el widget expone un método por estado
- [x] 6.3 Implementar persistencia de la posición del overlay en `config.local.yaml` con vuelta a la posición por defecto si el monitor guardado no existe; verificar con un test que una posición fuera de todas las pantallas se descarta
- [x] 6.4 Implementar `loki/ui/bandeja.py` con menú mostrar/ocultar overlay, reiniciar conversación y salir, con cierre ordenado de audio, cerebro y canal local; verificar manualmente que tras salir no queda ningún proceso `claude` ni Python huérfano

## 7. Herramientas MCP y canal local

- [x] 7.1 Implementar `loki/herramientas/canal_local.py`: servidor HTTP en localhost con puerto configurable y token aleatorio por sesión, generado por el proceso principal y pasado al servidor MCP por variable de entorno; verificar con tests que una llamada sin token o con token incorrecto se rechaza
- [x] 7.2 Implementar `loki/herramientas/confirmacion.py`: registro de confirmaciones con id, acción, objetivo y vencimiento (10 s de espera, validez de 60 s tras confirmar), y la secuencia hablar la pregunta, escuchar sin wake word, clasificar sí/no/ambiguo; verificar con tests los escenarios confirma, niega, ambiguo y sin respuesta, y que un id vencido o de otra acción se rechaza
- [x] 7.3 Implementar `loki/herramientas/orca.py` como envoltorio del CLI de Orca con salida `--json`: listar repos, listar terminales, mostrar terminal, crear terminal con comando, enviar texto, esperar tui-idle, leer desde cursor, crear worktree sin agente; verificar con tests que arman los argumentos correctos y manualmente contra el runtime real que `terminal create` con `claude --model haiku` abre una sesión visible en Orca
- [x] 7.4 Implementar `loki/herramientas/servidor_mcp.py` con las herramientas de D3 (`pedir_confirmacion`, `cerrar_terminal`, `eliminar_worktree`, `enviar_a_terminal`, `media_*`, `overlay_estado`, `sesion_relay_activar`, `sesion_relay_salir`, `monitorear_terminal`, `listar_proyectos`, `config_modelos`) que llaman al canal local, y `.mcp.json` que lo declara; verificar con tests que las tres herramientas críticas rechazan la llamada sin `confirmacion_id` válido y que `enviar_a_terminal` solo exige confirmación cuando la terminal destino no corre Claude Code
- [x] 7.5 Definir las listas `allowedTools` y `disallowedTools` de D2 en `config.yaml` y pasarlas al arranque del cerebro; verificar manualmente que el cerebro puede ejecutar `orca terminal list` y que un intento de `orca terminal close` por Bash es rechazado y termina en una llamada a la herramienta MCP con confirmación

## 8. Sesiones de agentes y relay

- [x] 8.1 Implementar `loki/cerebro/sesion.py` con el registro de sesiones de agente (handle, repo, título, modelo, cursor de lectura), la sesión de relay activa, y la resolución de alias de proyectos desde `config.local.yaml` más `orca repo list`; verificar con tests que un alias resuelve al repo correcto y que un nombre desconocido devuelve candidatos
- [x] 8.2 Implementar el modo relay en la máquina de estados: el texto dictado va a la terminal activa por `enviar_a_terminal`, luego `wait --for tui-idle` con timeout de 10 min, lectura desde cursor y envío del texto al cerebro con la instrucción de resumir y clasificar (terminó, preguntó, pidió permiso); verificar con tests con salida de terminal simulada que los tres casos producen el estado y el aviso correctos
- [x] 8.3 Implementar la salida del modo relay y el cambio de sesión por voz, con actualización del overlay; verificar con tests que tras salir los mensajes vuelven al cerebro y la sesión sigue registrada
- [x] 8.4 Implementar el monitor en segundo plano de `monitorear_terminal`: espera tui-idle, lee, pide al cerebro la clasificación y dispara el aviso hablado con nombre de proyecto y etiqueta, respetando la secuencia de media; verificar con tests que dos monitores simultáneos producen avisos identificables

## 9. Flujo de desarrollo por voz

- [x] 9.1 Escribir `.claude/skills/desarrollo-por-voz/SKILL.md` con el flujo de D10: cuándo reconocer una intención de construir, cómo abrir la sesión de explore con el modelo de `config_modelos()`, enviar `/opsx:explore <idea>`, activar relay, rechazar propose sin explore previo, enviar `/opsx:propose`, y para apply crear worktree sin agente más terminal con `claude --model <impl>` enviando `/opsx:apply <change>` y registrar el monitor; verificar manualmente que el cerebro carga la skill (aparece en su lista de skills al arrancar)
- [x] 9.2 Prueba de extremo a extremo del flujo con el propio repo de Loki: decir por voz que se quiere agregar una función, confirmar que se abre una sesión con el modelo de exploración en Orca y que Loki hace relay; pedir el propose y confirmar que Loki dice el nombre del change; pedir el apply y confirmar que aparece un worktree con Claude Code en Sonnet y que Loki avisa al terminar; registrar en design.md cualquier ajuste al flujo

## 10. Integración, arranque y pruebas manuales

- [x] 10.1 Implementar `loki/main.py` que arma los hilos de D11 (Qt, audio, cerebro y voz, canal local), conecta observadores de la máquina de estados con el overlay y arranca el subproceso del cerebro; verificar que `python -m loki.main` levanta el overlay en estado dormido y responde a "hey Jarvis" con una respuesta hablada
- [x] 10.2 Escribir `CLAUDE.md` del repo con la descripción del proyecto, la convención de OpenSpec en español, la regla de correr la auditoría de privacidad antes de cada PR y el puntero a BACKLOG.md; verificar que una sesión nueva de Claude Code en el repo lo lee (lo menciona al preguntarle qué es el proyecto)
- [ ] 10.3 Recorrer una lista de pruebas manuales que cubra cada escenario de las specs con "manualmente" o sin test automático (activación, silencio, interrupción, media, relay, confirmación, overlay, bandeja) y registrar el resultado en `docs/pruebas-manuales-mvp.md`; verificar que ninguna prueba queda en rojo antes de dar por terminado el change
- [ ] 10.4 Ajustar umbrales de wake word, RMS y silencio con uso real y dejar los valores finales en `config.yaml`; verificar que tres activaciones seguidas funcionan sin falsos positivos en un minuto de conversación normal

## 11. Privacidad y publicación

- [x] 11.1 Implementar `scripts/auditar_privacidad.py` según D13 (rutas de usuario de Windows y macOS, correos, patrones de keys y tokens, términos privados desde `config.local.yaml`), con salida de archivo y línea y código de salida distinto de cero ante hallazgos; verificar con tests que cada clase de hallazgo se detecta y que un diff limpio devuelve cero
- [x] 11.2 Escribir `.claude/skills/auditar-privacidad/SKILL.md` que ejecuta el script contra `origin/main` y explica los hallazgos, y un hook `pre-push` opcional documentado; verificar que la skill aparece al invocarla en una sesión de Claude Code del repo
- [x] 11.3 Escribir `README.md` con prerrequisitos (Windows, Python 3.12, Claude Code logueado, Orca, cuenta de Groq), instalación con `scripts/setup.bat` adaptado de voice-transcript, configuración de las plantillas, arranque, y la regla de auditoría antes de publicar; verificar siguiendo el README en un venv limpio que Loki arranca
- [x] 11.4 Ejecutar la auditoría sobre todo el árbol (no solo el diff), corregir hallazgos, y con confirmación explícita del usuario crear el repo público `loki` en GitHub con `gh repo create` y hacer el primer push; verificar que el repo remoto no contiene `.env`, `config.local.yaml` ni rutas de usuario
