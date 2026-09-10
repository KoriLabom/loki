## Context

Ver proposal.md para la motivación. Lo que condiciona el diseño:

- **Sin API key de Anthropic.** El único camino oficial para usar la suscripción es el CLI de Claude Code. El Agent SDK exige API key según la documentación, así que se descarta.
- **Orca ya es la capa de ejecución.** Su CLI expone 234 comandos con schema legible (`orca agent-context --json`): terminales, worktrees, computer-use, browser, automations. `worktree create --agent` no permite elegir modelo; `terminal create --command` sí.
- **Base de voz existente.** `voice-transcript` (mismo autor) ya resuelve grabación con sounddevice, transcripción con Groq Whisper large-v3 con vocabulario técnico y filtro de alucinaciones, overlay PyQt6 sin bordes con onda de voz, y arranque con Windows. Es push-to-talk y pega texto; Loki necesita wake word, corte por silencio y voz de salida.
- **Máquina objetivo.** Windows 11, Python 3.12, Node 24, GPU NVIDIA T500 de 4GB (insuficiente para Whisper local con buena latencia). Laptop con monitor externo a veces conectado.
- **Sesión de trabajo.** Esta misma sesión corre dentro de una terminal de Orca en el repo; Loki va a poder hacer lo mismo que se hizo acá.

## Goals / Non-Goals

**Goals:**
- Latencia percibida de conversación aceptable: menos de 3 segundos entre que el usuario termina de hablar y Loki empieza a responder en un turno simple.
- Un único proceso Python fácil de arrancar, sin servicios externos propios.
- Que el cerebro no pueda hacer daño irreversible por un error de reconocimiento, con la garantía fuera del prompt.
- Que todo lo específico de la máquina viva fuera del repo.
- Que el propio Loki pueda leer el repo y abrir agentes para mejorarse.

**Non-Goals:**
- Wake word con el nombre real, supervisor con rollback, monitores, YouTube, campus, carpetas, memoria persistente, escalada automática de modelo, multi-agente coordinado, ElevenLabs. Todo listado en BACKLOG.md.
- Correr en macOS o Linux. Solo Windows en el MVP.
- Parsear con precisión la interfaz de Claude Code en las terminales de relay. Se resume con el LLM.

## Decisions

### D1. Cerebro: `claude -p` persistente con entrada y salida `stream-json`

Se lanza un subproceso `claude -p --input-format stream-json --output-format stream-json --include-partial-messages --verbose --model <m> --system-prompt <persona> --setting-sources project --allowedTools <lista> --disallowedTools <lista> --permission-mode manual --permission-prompts none`, con cwd en el repo de Loki, y se lo mantiene vivo durante toda la sesión. Cada frase del usuario se escribe como un mensaje JSON de usuario en stdin; los eventos de stdout se leen línea a línea y los `content_block_delta` de texto alimentan la voz de salida. El evento `{"type": "result", ...}` marca el fin del turno.

- Por qué: es el CLI oficial con la suscripción, ya instalado (2.1.266), y expone exactamente lo que hace falta: modelo, prompt de sistema, herramientas permitidas, MCP del proyecto, streaming. Mantener el proceso vivo evita el arranque frío en cada turno.
- Alternativas: Agent SDK (mismo protocolo pero pide API key); Messages API (paga y sin herramientas de Claude Code); un `claude -p` nuevo por turno con `--resume` (arranque frío de 2 a 4 segundos por turno).
- Supuesto a validar en la primera tarea: que el modo `--input-format stream-json` acepta varios turnos en la misma invocación con la versión instalada. Si no, se usa `--resume <session-id>` por turno y se acepta la latencia.
- Reinicio de conversación: se mata el subproceso y se lanza otro.

**Validado en la tarea 2.1 (spike `scripts/spike_claude_headless.py`), con ajustes sobre lo asumido más arriba:**

- **Multi-turno confirmado.** Un mismo subproceso recuerda turnos anteriores sin `--resume`: se probó pidiéndole que recordara un número y preguntándoselo en el turno siguiente, y lo recuperó correctamente. Se descarta el fallback de D1.
- **`--append-system-prompt-file` no existe** en el CLI instalado (2.1.266); solo hay `--append-system-prompt <texto>` y `--system-prompt <texto>` (reemplaza el prompt de sistema por defecto en vez de agregarle algo). `claude_headless.py` lee `persona/system_prompt.md` en Python y lo pasa como argumento de texto.
- **`--permission-mode default` no existe.** Los valores válidos son `acceptEdits`, `auto`, `bypassPermissions`, `manual`, `dontAsk`, `plan`. Se usa `manual` junto con `--permission-prompts none` (en vez del default `host`, que espera que alguien conteste el prompt) para que cualquier herramienta fuera de `allowedTools` se rechace sola en lugar de esperar una respuesta que nadie va a dar.
- **Riesgo nuevo encontrado: sin aislar la config, el cerebro hereda los hooks y la memoria automática de la cuenta del usuario.** Sin más flags, el subproceso carga la configuración de nivel "user" (hooks globales tipo el de `superpowers`, sistema de auto-memoria) y el modelo, en vez de responder directo, intenta usar herramientas de archivo para guardar "recuerdos" — ruido, latencia y una vía de escritura de archivos no contemplada por D2. `--bare` evitaría esto pero exige `ANTHROPIC_API_KEY` o `apiKeyHelper` (nunca OAuth), lo cual viola el requisito de no usar API key. La solución que sí preserva la autenticación por suscripción es `--setting-sources project`, que excluye las fuentes "user" y "local" y deja solo la configuración del propio repo de Loki (su `.mcp.json`, sus skills). Se agrega a D1 y a la lista de flags de la tarea 2.2.
- **`--output-format stream-json` exige `--verbose`** con `-p`, si no el proceso corta con error inmediato; ya estaba en la lista de D1, queda confirmado como obligatorio y no opcional.
- El evento de fin de turno es efectivamente `{"type": "result", ...}` con `duration_api_ms`, `stop_reason`, `session_id`, `total_cost_usd`, `usage`, tal como asumía D1.

**Ajuste encontrado en la tarea 9.2: los turnos concurrentes rompían el subproceso.** El diseño ya asumía un único cerebro compartido para la conversación normal, la clasificación de relay (D9) y la del monitor de apply (tarea 8.4), pero `CerebroHeadless.enviar_turno` no serializaba el acceso: si dos llamadas coincidían (por ejemplo, la clasificación en segundo plano de una ronda de relay justo cuando el usuario pide avanzar a propose), ambas leían el mismo `stdout` a la vez y una moría con `readuntil() called while another coroutine is already waiting for incoming data`. Se agregó un `asyncio.Lock` interno: los turnos concurrentes ahora se encolan en vez de competir por el stream. Cualquier pieza que comparta un `CerebroHeadless` (relay, monitor, conversación) puede llamarlo con seguridad desde tareas en paralelo.

### D2. Permisos del cerebro: lista blanca de herramientas y acciones críticas solo por MCP

El cerebro corre con `--permission-mode manual --permission-prompts none` (ver validación en D1), sin nadie que responda prompts, así que todo lo que no esté en `allowedTools` se rechaza solo. Se permite: `Bash(orca *)`, `Read`, `Glob`, `Grep` limitados al repo, y las herramientas MCP de Loki. Se prohíbe explícitamente con `disallowedTools`: `Bash(orca terminal close*)`, `Bash(orca worktree rm*)`, `Bash(orca terminal send*)`, `Write`, `Edit`, `Bash(rm *)`, `Bash(del *)`, `Bash(Remove-Item*)`. Las operaciones críticas se exponen únicamente como herramientas MCP de Loki (`cerrar_terminal`, `eliminar_worktree`, `enviar_a_terminal`) que exigen un `confirmacion_id` válido.

- Por qué: la confirmación queda garantizada por código en el servidor MCP, no por el prompt. El cerebro puede afirmar lo que quiera; sin id válido la herramienta no ejecuta.
- `terminal send` se bloquea por Bash y se reexpone por MCP porque es la vía del relay: hacia sesiones de Claude Code no requiere confirmación, hacia cualquier otra terminal sí. El servidor MCP consulta `orca terminal show` para decidir.
- Alternativa: `--permission-mode bypassPermissions`. Descartada, elimina la única red de seguridad.

**Ajustes encontrados en la tarea 10.3 (secuencia de voz real, C2/C3), los tres solo de comportamiento del cerebro, no del gate:**

1. **La escucha de confirmación nunca estaba implementada.** `_manejar_pedir_confirmacion` en `main.py` tenía un `escuchar()` con un TODO ("requiere el hilo de audio en modo confirmación") que siempre devolvía `None`: la confirmación nunca se completaba de verdad, en ningún test manual anterior. Se implementó `_escuchar_para_confirmacion` con su propio `DetectorFinDeFrase` corriendo en paralelo al ciclo normal de wake word, usando `concurrent.futures.Future` + `asyncio.wrap_future` para volver al loop desde el callback de audio (mismo patrón de D11). De paso apareció un problema de eco: arrancaba a escuchar apenas se encolaba el audio de la pregunta (no cuando terminaba de sonar), así que el micrófono transcribía la propia voz de Loki como respuesta del usuario. Se agregó `Reproductor.esperar_vacia()` (basado en el conteo de tareas de `queue.Queue`, sin condición de carrera) y la confirmación espera a que termine de sonar antes de escuchar.
2. **El cerebro no encadenaba la confirmación con la acción real.** `pedir_confirmacion` siempre devuelve un `confirmacion_id` (nunca le dice al cerebro en texto si el usuario confirmó: esa decisión vive solo en el gate del servidor), pero el system prompt no dejaba explícito que había que llamar de inmediato a la herramienta crítica real con ese id. El cerebro se quedaba conforme con haber preguntado, sin ejecutar nada. Se reforzó `system_prompt.md` con la regla explícita de encadenar siempre las dos llamadas en el mismo turno.
3. **El parámetro `terminal`/`worktree` recibía una descripción en vez del handle real, y Loki afirmaba éxito sin verificar.** El cerebro pasaba texto como `"prueba 1"` (el `objetivo` libre de `pedir_confirmacion`) en vez del handle de Orca (`term_...`) al llamar a `cerrar_terminal`/`eliminar_worktree`, y `_ejecutar_cerrar_terminal`/`_ejecutar_eliminar_worktree` en `main.py` ignoraban por completo el resultado del subproceso (ni exit code ni el `ok` del JSON), devolviendo siempre éxito. Se agregaron `Orca.cerrar_terminal`/`Orca.eliminar_worktree` (mismo manejo de errores que el resto de `Orca`, que sí valida exit code), se propaga `ok`/`error` real hasta el cerebro, y se reforzaron el system prompt y las docstrings de las herramientas MCP para exigir el handle exacto. Verificado en vivo contra `orca terminal list`: el conteo de terminales bajó de 15 a 14 y el handle correcto desapareció.

### D3. Herramientas propias por servidor MCP local en stdio

Un servidor MCP en Python (paquete `mcp`) declarado en `.mcp.json` del repo, lanzado por Claude Code como subproceso. Herramientas: `pedir_confirmacion(accion, objetivo)` que habla, escucha y devuelve `confirmacion_id`; `cerrar_terminal`, `eliminar_worktree`, `enviar_a_terminal` con `confirmacion_id`; `media_pausar`, `media_reanudar`, `media_estado`; `overlay_estado(texto)`; `sesion_relay_activar(terminal)`, `sesion_relay_salir()`; `monitorear_terminal(terminal, etiqueta)` para el aviso de fin de apply; `listar_proyectos()` que mezcla `orca repo list --json` con los alias de la config local; `config_modelos()` que devuelve los modelos por etapa.

- Problema: el servidor MCP es un proceso hijo de Claude Code, y la voz, el overlay y el estado viven en el proceso principal de Loki. Se resuelve con un canal local: el proceso principal abre un servidor HTTP en localhost en un puerto configurable con un token aleatorio por sesión; el servidor MCP le hace las llamadas. Es la forma más simple que funciona en Windows sin sockets Unix ni pipes con nombre.
- Alternativa: MCP por HTTP servido desde el proceso principal. Claude Code lo soporta pero suma configuración de transporte; se deja para después si el canal intermedio molesta.

**Ajuste encontrado en la tarea 10.3 (uso real, prueba C2): el timeout del cliente HTTP (15 s) era menor que la duración real de `pedir_confirmacion`.** Esa llamada puede tardar ~19 s (hablar la pregunta + escuchar hasta 13 s + transcribir), así que el cliente abortaba la conexión antes de que el canal local terminara de responder, y el cerebro lo veía como "un problema de comunicación". Se subió el timeout de `ClienteCanalLocal._post_sync` a 45 s. Además, las excepciones del lado del servidor (`ServidorCanalLocal.do_POST`) se devolvían como JSON pero nunca se logueaban, así que este bug fue invisible en el log hasta que se agregó `logger.exception` ahí.

**Ajuste encontrado en la tarea 9.2: el servidor MCP del repo queda "Pending approval" la primera vez.** Cualquier sesión nueva de Claude Code que arranca con un `.mcp.json` sin aprobar antes se queda esperando una confirmación interactiva ("New MCP server found... Use this MCP server / Continue without using this MCP server") que nadie puede responder en una terminal headless — la terminal de explore/apply queda colgada para siempre en ese punto. La sesión del cerebro (headless, `-p`) no lo sufre porque el diálogo de confirmación se salta en modo no interactivo, pero las sesiones interactivas que Loki abre para explore/propose/apply sí. Se agregó `.claude/settings.json` con `{"enableAllProjectMcpServers": true}` al repo: aprueba automáticamente los servidores MCP declarados en `.mcp.json` del propio proyecto para cualquier sesión interactiva que arranque ahí, sin tocar el estado global del usuario (`~/.claude.json`) y funcionando igual para cualquiera que clone el repo.

### D4. Wake word con openWakeWord y modelo preentrenado `hey_jarvis`

Detección local con ONNX Runtime a 16 kHz, en el hilo de audio. La ruta del modelo se lee de la configuración para poder reemplazarlo por uno propio sin tocar código. El detector sigue activo mientras Loki habla para permitir interrupción.

- Por qué: gratis, offline, sin cuenta, y el modelo ya existe. Entrenar "Loki" es la primera tarea de automejora.
- Alternativa: Picovoice Porcupine. Mejor calidad y palabra propia en minutos, pero pide cuenta y access key. Queda anotado como alternativa si openWakeWord da falsos positivos molestos.
- Supuesto: el micrófono se abre directamente a 16 kHz mono. Si el dispositivo no lo soporta se graba a la tasa nativa y se remuestrea con una decimación simple antes del detector.

### D5. Fin de frase por energía, no por VAD neuronal

Después de la activación se acumula audio y se calcula RMS por bloque. Se considera que el usuario empezó a hablar cuando el RMS supera un umbral configurable, y que terminó cuando se mantiene por debajo durante 1,2 segundos. Corte duro a los 30 segundos. Sin voz en 5 segundos, se vuelve a dormido.

- Por qué: cero dependencias nuevas, suficiente para un usuario en ambiente de trabajo. Los umbrales son configurables.
- Alternativa: Silero VAD. Mucho más robusto con ruido de fondo pero trae PyTorch o requiere empaquetar ONNX aparte. Se anota como mejora si el corte por energía falla con música de fondo. Mitigación: el media se pausa antes de grabar, así que el ruido de fondo principal desaparece.

**Ajuste encontrado en la tarea 10.3 (uso real): `umbral_rms` por defecto (0,02) estaba muy por encima de la voz real del usuario.** Medido el micrófono directamente: la voz normal ronda 0,002-0,03 con picos aislados, casi nunca por encima de 0,02. El detector de fin de frase cortaba a los pocos segundos de hablar sin parar (nunca llegaba a los 30 s). Se bajó a `0,004` en `config.yaml`, valor final validado con tres activaciones seguidas sin falsos positivos.

### D6. Transcripción con Groq Whisper, módulos copiados de voice-transcript

Se copian `recorder.py`, `transcriber.py`, `vocabulary.py`, `vocabulary.txt` y `overlay.py` al paquete `loki/`, adaptados: el recorder pasa a ser un stream continuo que alimenta al detector de wake word y al grabador de frase a la vez; el transcriber se mantiene casi igual; el overlay cambia paleta y estados. El reescritor de prompts no se copia: Loki habla con un LLM que entiende habla natural.

- Por qué copiar y no depender: los módulos van a divergir rápido y Loki los va a editar. Un solo repo simplifica la instalación por terceros.

### D7. Voz de salida con edge-tts, por oraciones, con reproducción por cola

El texto parcial del cerebro se acumula hasta encontrar un fin de oración (punto, signo de pregunta o exclamación seguido de espacio, o salto de línea). Cada oración se limpia (se quitan bloques de código, URLs, rutas y marcas markdown) y se sintetiza con edge-tts a MP3 en memoria. Un hilo reproductor consume una cola ordenada, decodifica con `miniaudio` y reproduce con sounddevice. Interrumpir vacía la cola y corta la reproducción actual.

- Voz por defecto: `es-MX-DaliaNeural`. Configurable.
- Por qué edge-tts: gratis, sin key, buena calidad, voces neutras. Por qué miniaudio: decodifica MP3 sin ffmpeg instalado, con wheel para Windows.
- Alternativa: Windows SAPI. Sin red pero voces notoriamente peores. ElevenLabs: mejor, pago; anotado en el backlog.

**Ajuste encontrado en la tarea 10.3 (prueba V2, hardware real): las oraciones se escuchaban fuera de orden.** `_on_texto_parcial_cerebro` disparaba una tarea concurrente independiente (`asyncio.run_coroutine_threadsafe`) por cada oración detectada; como cada una hace su propia llamada de red a edge-tts con latencia variable (medida entre 1,3 y 2,5 s), la que terminaba de sintetizar primero se encolaba primero, sin importar el orden en que el cerebro las generó — viola directamente "orden preservado" de esta spec. Se cambió a una cola FIFO (`Loki._cola_habla`, un `asyncio.Queue`) con un único consumidor (`_consumir_cola_habla`) que sintetiza y encola las oraciones de a una, en el orden en que se generaron. Verificado con timing real en el log en dos turnos seguidos (uno interrumpido a mitad de respuesta): el orden de reproducción coincide con el de generación.

**Limitación conocida, sin fix en este change:** la latencia real medida desde que una oración está lista hasta que empieza a sonar ronda 1,8 s en varias corridas, por encima del objetivo de esta spec (<1,5 s). Parece ser latencia de red del propio servicio de edge-tts (no de la síntesis/cola de Loki), y no es algo que el código pueda acortar sin cambiar de proveedor de voz. Anotado en BACKLOG.md como algo a revisar si en el uso real molesta.

### D8. Control de media con la sesión de media de Windows

Se usa `GlobalSystemMediaTransportControlsSessionManager` a través del paquete WinRT de Python para consultar la sesión actual y su estado de reproducción, pausar con `TryPauseAsync` y reanudar con `TryPlayAsync` sobre la misma sesión. Loki guarda el identificador de la sesión que pausó y solo reanuda esa.

- Por qué la API y no la tecla multimedia: la tecla alterna, y si el estado cambió mientras Loki hablaba se termina reproduciendo algo que estaba pausado. La API permite pausar y reanudar de forma explícita y saber si ya estaba pausado.
- Fallback: si el paquete WinRT no carga, se usa la tecla multimedia play/pause con pyautogui y se acepta el riesgo de alternar.
- Regla de reanudación: se reanuda cuando la máquina de estados vuelve a dormido sin confirmación pendiente. Para avisos no solicitados: pausar, hablar, esperar 4 segundos una activación, reanudar.

### D9. Relay con Orca: `terminal create`, `send`, `wait --for tui-idle`, `read`

Abrir sesión: `orca terminal create --worktree path:<repo> --title "<nombre>" --command "claude --model <m>" --json` y guardar el handle. Enviar: MCP `enviar_a_terminal` que usa `orca terminal send --terminal <h> --text <t> --enter`. Leer: `orca terminal wait --terminal <h> --for tui-idle --timeout-ms <t>` y después `orca terminal read --terminal <h> --cursor <último>`. El texto leído se le pasa al cerebro con la instrucción de resumirlo en voz y clasificar si el agente terminó, preguntó o pidió permiso.

- Por qué resumir con el LLM en vez de parsear: la salida de un TUI es ruidosa y cambia con cada versión. El cerebro es bueno resumiendo texto sucio, y la spec pide un resumen breve, no fidelidad literal.
- Supuesto: `--cursor` de `terminal read` permite leer solo lo nuevo. Si no, se guarda la longitud anterior y se recorta.

**Ajuste encontrado en la tarea 9.2: la forma real de `orca terminal read --json`.** Las tareas 8.2 y 8.4 asumían sin verificar que el resultado traía `result.text` o `result.output` y `result.nextCursor`. El CLI real devuelve `result.terminal.tail` (una lista de líneas) y `result.terminal.nextCursor` (un string, no necesariamente numérico). Se corrigió con un helper único, `loki/herramientas/orca.py:extraer_texto_y_cursor`, que usan tanto `RelayVoz` como `MonitorTerminal`; `SesionAgente.cursor` pasó de `int` a `str | None`. Antes del arreglo, la clasificación del agente siempre recibía texto vacío.

**Ajuste encontrado en la tarea 9.2 (prueba de punta a punta): quién envía el texto dictado durante el relay.**

La implementación original de las tareas 8.2/8.3 hacía que, con una sesión de relay activa, el texto dictado se enviara a la terminal *sin pasar por el cerebro* (para cumplir al pie de la letra "sin agregar reescrituras que el usuario no dijo" de la spec `sesiones-de-agentes`). Al probar el flujo real de principio a fin, esto resultó incompatible con `flujo-de-desarrollo-por-voz`: si el cerebro nunca ve el turno mientras hay relay activo, no tiene forma de reconocer un pedido de "proponé" o "aplicá" y traducirlo a `/opsx:propose` o `/opsx:apply <change>` — literalmente escribiría "proponé" en la terminal del otro agente.

Se corrige así: **todo el texto dictado pasa siempre por el cerebro**, con o sin relay activo. Mientras hay una sesión de relay activa, el propio cerebro decide en cada turno si reenvía lo dictado tal cual con la herramienta MCP `enviar_a_terminal` (satisface igual el "sin reescrituras", porque quien no reescribe es el cerebro por instrucción de la skill, no un bypass de la aplicación) o si lo traduce a un comando de OpenSpec. `enviar_a_terminal` hacia una sesión de Claude Code no pide confirmación, así que esto no agrega fricción.

Como consecuencia:
- `loki/cerebro/relay.py` (`RelayVoz`) ya no envía texto: su método pasó de `procesar_dictado(texto)` a `esperar_leer_y_clasificar(handle)`, y se invoca *después* de que el cerebro ya mandó algo por `enviar_a_terminal` (quien conecte ese envío con el sondeo de la respuesta — hoy `main.py`, tarea 10.1 — dispara `esperar_leer_y_clasificar` en segundo plano cuando el destino es la sesión de relay activa).
- `loki/cerebro/controlador_conversacion.py` (`ControladorConversacion`) ya no bifurca entre cerebro y relay: `procesar_dictado` siempre llama a `cerebro.enviar_turno`. Su único trabajo pasa a ser llevar qué sesión está activa para el overlay.
- La skill `.claude/skills/desarrollo-por-voz/SKILL.md` se ajustó para dejar explícito que el primer mensaje de cada etapa (y cualquier reenvío durante el relay) va por la herramienta MCP `enviar_a_terminal`, nunca por `Bash(orca terminal send)` (que está deshabilitado).

### D10. Flujo explore/propose/apply como skill del repo, no como código

El flujo se describe en `.claude/skills/desarrollo-por-voz/SKILL.md` dentro del repo de Loki, que el cerebro carga por correr con cwd ahí. La skill dice: qué comandos de Orca ejecutar en cada etapa, con qué modelo (leído de la herramienta MCP `config_modelos()`), y que un propose sin explore previo debe rechazarse. El apply crea el worktree con `orca worktree create --repo <sel> --name <change> --json` sin agente, y luego `orca terminal create --worktree <nuevo> --command "claude --model <impl>"` enviando `/opsx:apply <change>`.

- Por qué skill y no código: el reconocimiento de intención es lenguaje natural y el cerebro ya es un LLM. Codificar intents con expresiones regulares sería frágil. La skill es editable por Loki mismo en su ciclo de automejora.
- El comando inicial del explore lleva la idea del usuario como argumento: `/opsx:explore <texto dictado>`.
- Modelos por defecto: explore y propose `fable`, apply `sonnet`, cerebro `haiku`. En `config.yaml` del repo, sobreescribibles en `config.local.yaml`.

**Validado en la tarea 9.2 (prueba de punta a punta con el propio repo de Loki), con dos ajustes:**

- **El ciclo completo funciona de verdad.** Explore abrió una sesión real con Fable y activó el relay; propose creó un change real de OpenSpec (`agregar-contributing`, con `proposal.md` y `tasks.md`); apply creó un worktree nuevo de verdad (`orca/workspaces/Asistente/apply-contributing`, rama aparte) con una terminal corriendo Sonnet 5, y el monitor se registró contra esa terminal nueva (no contra ninguna preexistente).
- **Encontrado: el cerebro puede mandar el comando de arranque y el comando de OpenSpec pegados en un solo texto, y eso rompe el apply.** En la primera prueba del apply, en vez de (1) crear la terminal con `--command "claude --model sonnet"` y (2) mandar por separado `/opsx:apply agregar-contributing` por `enviar_a_terminal`, el cerebro combinó ambas cosas en un solo texto (`"claude --model sonnet opsx:apply agregar-contributing"`), sin la barra inicial del comando de OpenSpec. El resultado: la sesión de apply no reconoció el nombre del change, tomó por defecto el único change "activo" que encontró (`loki-mvp`, este mismo) y arrancó a re-implementarlo en el worktree aislado. No corrompió el checkout principal (los worktrees son checkouts separados) pero fue trabajo desperdiciado que hubo que limpiar (`orca worktree rm --force`). Se reforzó la skill con un ejemplo literal del `texto` exacto esperado por `enviar_a_terminal` y la instrucción explícita de nunca combinar el arranque de Claude Code con el comando de OpenSpec en un solo paso.
- **Riesgo de proceso descubierto (no del diseño de Loki): al probar en vivo, un intento previo del cerebro reusó una terminal existente en vez de crear una para el apply, y esa terminal resultó ser la propia sesión de Claude Code donde se estaba construyendo Loki.** El texto que el cerebro le mandó apareció como si fuera un mensaje del usuario real. No se actuó sobre ese texto como instrucción genuina (se verificó el origen antes de proceder) y no hubo impacto porque coincidía con lo que ya se estaba probando a propósito, pero es una advertencia real para cualquier prueba en vivo del flujo de relay: verificar siempre a qué terminal se apunta antes de mandarle texto, y preferir pedirle a la skill que cree una terminal nueva en vez de reusar una de la lista cuando no se puede garantizar que todas las terminales existentes son ajenas a quien está operando la prueba.

### D11. Arquitectura de proceso y concurrencia

Un solo proceso Python. Hilo principal: Qt (overlay y bandeja). Hilo de audio: stream continuo de sounddevice que alimenta el detector de wake word y el buffer de frase. Hilo de cerebro y voz: un bucle asyncio que maneja el subproceso de Claude Code, la síntesis y la cola de reproducción. Hilo HTTP local: recibe las llamadas del servidor MCP. Comunicación entre hilos con `queue.Queue` y señales Qt para todo lo que toca la interfaz.

Máquina de estados central, dueña del estado y de las transiciones:

```
        +----------+  wake word   +------------+  silencio   +----------+
        | dormido  | -----------> | escuchando | ----------> | pensando |
        +----------+              +------------+             +----------+
             ^                          ^                         |
             |  fin de voz, sin         |  wake word              | primera oracion
             |  confirmacion pendiente  |  (interrumpe)           v
             |                          |                    +----------+
             +--------------------------+------------------- | hablando |
                                                             +----------+
        Estado paralelo "agente trabajando": uno o mas monitores de terminal
        en segundo plano que pueden disparar un aviso hablado en cualquier
        momento en que el estado principal sea dormido.
```

- Por qué un solo proceso: instalación y arranque triviales, y el MVP no necesita aislamiento. El supervisor con rollback (fuera del MVP) es el que justificará un segundo proceso.

**Validado en una sesión de pruebas con hardware real (tarea 10.3, 2026-09-09): 5 bugs reales de integración entre hilos, invisibles para los tests con dobles.**

Los tests automatizados de cada pieza (canal_local, coordinador_media, bandeja, detector de fin de frase) pasan usando dobles que no reproducen el hecho de que en la app real hay tres hilos con distinta relación con el loop de asyncio: el de Qt (sin loop propio), el de audio/PortAudio (sin loop propio), y el propio loop de asyncio de la app. Corriendo `python -m loki.main` de verdad con micrófono y parlantes aparecieron:

1. **Ícono de bandeja vacío**: `main.py` pasaba `QIcon()` sin imagen. Se agregó `loki/ui/paleta.py:icono_bandeja()` (un círculo terracota generado en código, sin depender de un archivo de imagen).
2. **`CoordinadorMedia._lanzar` usaba `asyncio.ensure_future`**, que necesita un loop "actual" del hilo que llama. La transición a escuchando por wake word dispara los observadores de `MaquinaEstados` sincrónicamente en el hilo de audio, que no tiene loop propio: `RuntimeError: There is no current event loop in thread 'Dummy-N'`. Se le agregó a `CoordinadorMedia` un `loop` explícito (seteado después de `iniciar_asyncio()`) y se cambió a `run_coroutine_threadsafe`, con las tareas pendientes trackeadas como `concurrent.futures.Future` y esperadas con `asyncio.wrap_future`.
3. **El mismo problema en `_ejecutar_enviar_a_terminal`**: ese método corre dentro del loop temporal que abre `ManejadoresCriticos.enviar_a_terminal` con `asyncio.run()` en el hilo del servidor HTTP del canal local; ese loop se cierra en cuanto termina la corrutina, así que `asyncio.ensure_future` para lanzar el sondeo del relay en segundo plano quedaba huérfano. Se cambió a `run_coroutine_threadsafe` contra el loop real de la app.
4. **El detector de fin de frase nunca cortaba nada**: `main.py` calculaba la duración de cada bloque de audio una sola vez como `0.0` y nunca la actualizaba, así que el reloj interno de `DetectorFinDeFrase` no avanzaba nunca — ni el silencio de 1,2 s, ni los 5 s sin voz, ni el máximo de 30 s cortaban la grabación jamás. Se corrigió calculando la duración real en cada bloque a partir de su tamaño y la tasa de muestreo efectiva.
5. **La interrupción por wake word no cortaba la voz**: nada llamaba a `Reproductor.interrumpir()` al detectar la activación mientras Loki hablaba, así que terminaba la respuesta en curso y encolaba la siguiente pregunta a continuación en vez de cortar. Se agregó la llamada en `_on_wake_word`, más un contador de "generación" (se incrementa en cada activación) que `_hablar`/`_on_texto_parcial_cerebro` chequean antes de sintetizar o encolar, para descartar sin reproducir las oraciones de un turno que ya quedó viejo.
6. **"Salir" de la bandeja no hacía nada**: el mismo problema que en (2)/(3) pero en el hilo de Qt: `Bandeja._salir()` usaba `asyncio.ensure_future` sin loop propio del hilo de Qt. Se le agregó a `Bandeja` un parámetro `loop` opcional (pasado desde `main.py` una vez que `iniciar_asyncio()` ya corrió) y se usa `run_coroutine_threadsafe` cuando está seteado.

Ninguno de estos bugs rompía ningún test existente porque cada test corre su pieza sola dentro de un único loop de asyncio (vía `pytest-asyncio`), que es justamente el caso que sí tiene un loop "actual" para `ensure_future`. Se agregaron regresiones puntuales donde tenía sentido (`test_bandeja.py::test_salir_desde_un_hilo_sin_loop_propio_igual_cierra_todo` lanza un loop real en otro hilo para reproducir el bug). Después de estos arreglos se confirmaron en vivo: activación por wake word, corte por silencio, transcripción real, respuesta hablada, interrupción por wake word mientras habla, y las tres acciones de la bandeja. Detalle completo en `docs/pruebas-manuales-mvp.md`.

**Ajuste encontrado en una segunda sesión de la tarea 10.3: `primera_oracion_lista()` se llamaba antes de tener una oración real.** `_procesar_turno` llamaba a esa transición (pensando -> hablando) inmediatamente después de arrancar `cerebro.enviar_turno`, no cuando efectivamente había una oración lista para sonar. El overlay mostraba "hablando" varios segundos antes de que hubiera cualquier audio, y la onda (D15, sincronizada con la reproducción) se veía sin actividad todo ese tiempo. Se movió el disparo a `_on_texto_parcial_cerebro`, en la primera oración real de cada turno, con un resguardo en `_procesar_turno` para el caso de una respuesta que nunca tiene puntuación final (si no, el estado quedaría trabado en "pensando" para siempre, porque `fin_de_reproduccion()` solo transiciona desde "hablando").

### D12. Configuración en tres capas

`config.yaml` (commiteado, defaults: modelos, voz, umbrales, ruta del modelo de wake word, lista de acciones críticas), `config.local.yaml` (ignorado: alias de proyectos, términos privados para la auditoría, posición del overlay, overrides), `.env` (ignorado: `GROQ_API_KEY`). Se incluyen `config.local.example.yaml` y `.env.example`.

**Ajuste encontrado en la tarea 10.3 (prueba O4): la posición del overlay nunca se leía ni se guardaba de verdad.** `loki/ui/posicion.py` (tarea 6.3: `guardar_posicion`, `resolver_posicion`, `monitores_reales`) tenía tests unitarios completos pero `main.py` solo las importaba sin llamarlas nunca: mover el overlay no persistía nada en `config.local.yaml`, y el arranque no leía ninguna posición guardada (`Overlay` simplemente aparecía donde Qt decidiera por defecto). Se conectó `Overlay` a `guardar_posicion` al soltar el arrastre (`on_posicion_cambiada`), y `main()` calcula la posición inicial con `resolver_posicion` a partir de `config.get("overlay", {}).get("posicion")` y el tamaño real del overlay. Confirmado en vivo: se movió el overlay, se reinició Loki, y apareció en la misma posición.

### D13. Auditoría de privacidad como script más skill

`scripts/auditar_privacidad.py` recibe un rango de git (por defecto la rama actual contra `origin/main`) y busca en el diff: rutas de usuario de Windows y macOS, correos, patrones de keys (`sk-`, `gsk_`, `ghp_`, cadenas base64 largas junto a palabras como key o token), y los términos de la lista privada de `config.local.yaml`. Falla con código distinto de cero listando archivo y línea. Una skill `/auditar-privacidad` del repo lo ejecuta y explica los hallazgos. El README indica correrlo antes de cada PR. Un hook pre-push opcional lo ejecuta automáticamente.

- Por qué no un GitHub Action: la lista de términos privados es local y no debe subirse; la auditoría tiene que correr donde está esa lista.

### D14. Estructura del repo

```
loki/
  __init__.py
  main.py              arranque, hilos, maquina de estados
  config.py            carga de las tres capas
  estados.py           maquina de estados y eventos
  audio/               recorder, wake_word, fin_de_frase, transcriber, vocabulary
  cerebro/             claude_headless (subproceso y protocolo), sesion
  voz/                 tts, limpieza_texto, reproductor
  herramientas/        servidor_mcp, canal_local, media, orca, confirmacion
  ui/                  overlay, bandeja, paleta
  persona/             system_prompt.md
scripts/               setup.bat, auditar_privacidad.py
tests/
.claude/skills/        desarrollo-por-voz, auditar-privacidad
.mcp.json
config.yaml, config.local.example.yaml, .env.example
CLAUDE.md, README.md, BACKLOG.md
openspec/
```

### D15. Paleta y estética

Fondo `#1F1A17` con 92% de opacidad, borde `#3A2E27`, acento terracota `#D97757`, acento suave `#E8A87C`, texto `#F5EDE4`, texto secundario `#A89A8C`, error `#C4462A`. Tipografía Segoe UI. Estados: dormido sin onda con punto tenue; escuchando onda terracota reactiva; pensando puntos pulsantes; hablando onda suave sincronizada con la reproducción; agente trabajando indicador naranja fijo con el nombre del proyecto. Todo en `ui/paleta.py`.

## Risks / Trade-offs

- [El modo stream-json multi-turno no funciona como se asume en la versión instalada] -> La tarea 2.1 lo valida antes de construir encima. Fallback: `--resume` por turno con latencia mayor.
- [Falsos positivos del wake word "hey Jarvis" con ruido o TV] -> Umbral de confianza configurable; un falso positivo cuesta una pausa de media y un "no entendí". Alternativa Porcupine anotada.
- [El corte por energía no detecta fin de frase con ruido de fondo] -> Se pausa el media antes de grabar; umbrales configurables; Silero VAD como mejora.
- [El resumen del LLM de la salida del TUI se equivoca sobre si el agente terminó] -> El aviso siempre ofrece hablar con la sesión; el usuario puede pedir que lea más. Área a observar.
- [Claude Code headless se queda esperando un permiso que nadie responde] -> Listas blanca y negra explícitas; timeout por turno de 120 segundos con aviso hablado y reinicio del subproceso.
- [Consumo de la ventana de 5 horas de la suscripción por conversación continua] -> Cerebro diario en Haiku; el contexto se reinicia por voz; explore con Fable solo cuando se pide.
- [El canal HTTP local entre MCP y proceso principal es un punto de falla más] -> Token por sesión, solo localhost, y las herramientas devuelven error claro al cerebro si el canal no responde.
- [Datos privados se filtran al repo público] -> Auditoría obligatoria antes de push, plantillas sin datos, y el primer push se hace después de auditar todo el árbol, no solo el diff.
- [edge-tts depende de un servicio no oficial de Microsoft que puede cambiar] -> Interfaz de TTS con una sola implementación por ahora; SAPI como fallback de emergencia si falla la síntesis.

## Migration Plan

No hay migración: es un proyecto nuevo. Orden de puesta en marcha: inicializar git en la carpeta actual, primer commit con la estructura y OpenSpec, auditoría de todo el árbol, creación del repo público `loki` en GitHub y push, con confirmación del usuario antes del push por ser una acción externa. La carpeta local sigue llamándose `Asistente` porque Orca ya la tiene registrada.

## Open Questions

- Si openWakeWord con `hey_jarvis` da demasiados falsos positivos en el ambiente real del usuario. Se mide en uso; no cambia el diseño, cambia el proveedor detrás de la misma interfaz.
- Si Haiku 4.5 alcanza como cerebro diario o se sube a Sonnet. Es un valor de configuración.
- Umbrales finales de silencio y RMS. Se ajustan con uso.
