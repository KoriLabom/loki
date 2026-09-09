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

Se lanza un subproceso `claude -p --input-format stream-json --output-format stream-json --verbose --model <m> --append-system-prompt-file <persona> --allowedTools <lista> --disallowedTools <lista> --permission-mode default`, con cwd en el repo de Loki, y se lo mantiene vivo durante toda la sesión. Cada frase del usuario se escribe como un mensaje JSON de usuario en stdin; los eventos de stdout se leen línea a línea y los `content_block_delta` de texto alimentan la voz de salida. El mensaje `result` marca el fin del turno.

- Por qué: es el CLI oficial con la suscripción, ya instalado (2.1.265), y expone exactamente lo que hace falta: modelo, prompt de sistema, herramientas permitidas, MCP del proyecto, streaming. Mantener el proceso vivo evita el arranque frío en cada turno.
- Alternativas: Agent SDK (mismo protocolo pero pide API key); Messages API (paga y sin herramientas de Claude Code); un `claude -p` nuevo por turno con `--resume` (arranque frío de 2 a 4 segundos por turno).
- Supuesto a validar en la primera tarea: que el modo `--input-format stream-json` acepta varios turnos en la misma invocación con la versión instalada. Si no, se usa `--resume <session-id>` por turno y se acepta la latencia.
- Reinicio de conversación: se mata el subproceso y se lanza otro.

### D2. Permisos del cerebro: lista blanca de herramientas y acciones críticas solo por MCP

El cerebro corre en modo de permisos por defecto pero sin nadie que responda prompts, así que todo lo que no esté en `allowedTools` se rechaza solo. Se permite: `Bash(orca *)`, `Read`, `Glob`, `Grep` limitados al repo, y las herramientas MCP de Loki. Se prohíbe explícitamente con `disallowedTools`: `Bash(orca terminal close*)`, `Bash(orca worktree rm*)`, `Bash(orca terminal send*)`, `Write`, `Edit`, `Bash(rm *)`, `Bash(del *)`, `Bash(Remove-Item*)`. Las operaciones críticas se exponen únicamente como herramientas MCP de Loki (`cerrar_terminal`, `eliminar_worktree`, `enviar_a_terminal`) que exigen un `confirmacion_id` válido.

- Por qué: la confirmación queda garantizada por código en el servidor MCP, no por el prompt. El cerebro puede afirmar lo que quiera; sin id válido la herramienta no ejecuta.
- `terminal send` se bloquea por Bash y se reexpone por MCP porque es la vía del relay: hacia sesiones de Claude Code no requiere confirmación, hacia cualquier otra terminal sí. El servidor MCP consulta `orca terminal show` para decidir.
- Alternativa: `--permission-mode bypassPermissions`. Descartada, elimina la única red de seguridad.

### D3. Herramientas propias por servidor MCP local en stdio

Un servidor MCP en Python (paquete `mcp`) declarado en `.mcp.json` del repo, lanzado por Claude Code como subproceso. Herramientas: `pedir_confirmacion(accion, objetivo)` que habla, escucha y devuelve `confirmacion_id`; `cerrar_terminal`, `eliminar_worktree`, `enviar_a_terminal` con `confirmacion_id`; `media_pausar`, `media_reanudar`, `media_estado`; `overlay_estado(texto)`; `sesion_relay_activar(terminal)`, `sesion_relay_salir()`; `monitorear_terminal(terminal, etiqueta)` para el aviso de fin de apply; `listar_proyectos()` que mezcla `orca repo list --json` con los alias de la config local; `config_modelos()` que devuelve los modelos por etapa.

- Problema: el servidor MCP es un proceso hijo de Claude Code, y la voz, el overlay y el estado viven en el proceso principal de Loki. Se resuelve con un canal local: el proceso principal abre un servidor HTTP en localhost en un puerto configurable con un token aleatorio por sesión; el servidor MCP le hace las llamadas. Es la forma más simple que funciona en Windows sin sockets Unix ni pipes con nombre.
- Alternativa: MCP por HTTP servido desde el proceso principal. Claude Code lo soporta pero suma configuración de transporte; se deja para después si el canal intermedio molesta.

### D4. Wake word con openWakeWord y modelo preentrenado `hey_jarvis`

Detección local con ONNX Runtime a 16 kHz, en el hilo de audio. La ruta del modelo se lee de la configuración para poder reemplazarlo por uno propio sin tocar código. El detector sigue activo mientras Loki habla para permitir interrupción.

- Por qué: gratis, offline, sin cuenta, y el modelo ya existe. Entrenar "Loki" es la primera tarea de automejora.
- Alternativa: Picovoice Porcupine. Mejor calidad y palabra propia en minutos, pero pide cuenta y access key. Queda anotado como alternativa si openWakeWord da falsos positivos molestos.
- Supuesto: el micrófono se abre directamente a 16 kHz mono. Si el dispositivo no lo soporta se graba a la tasa nativa y se remuestrea con una decimación simple antes del detector.

### D5. Fin de frase por energía, no por VAD neuronal

Después de la activación se acumula audio y se calcula RMS por bloque. Se considera que el usuario empezó a hablar cuando el RMS supera un umbral configurable, y que terminó cuando se mantiene por debajo durante 1,2 segundos. Corte duro a los 30 segundos. Sin voz en 5 segundos, se vuelve a dormido.

- Por qué: cero dependencias nuevas, suficiente para un usuario en ambiente de trabajo. Los umbrales son configurables.
- Alternativa: Silero VAD. Mucho más robusto con ruido de fondo pero trae PyTorch o requiere empaquetar ONNX aparte. Se anota como mejora si el corte por energía falla con música de fondo. Mitigación: el media se pausa antes de grabar, así que el ruido de fondo principal desaparece.

### D6. Transcripción con Groq Whisper, módulos copiados de voice-transcript

Se copian `recorder.py`, `transcriber.py`, `vocabulary.py`, `vocabulary.txt` y `overlay.py` al paquete `loki/`, adaptados: el recorder pasa a ser un stream continuo que alimenta al detector de wake word y al grabador de frase a la vez; el transcriber se mantiene casi igual; el overlay cambia paleta y estados. El reescritor de prompts no se copia: Loki habla con un LLM que entiende habla natural.

- Por qué copiar y no depender: los módulos van a divergir rápido y Loki los va a editar. Un solo repo simplifica la instalación por terceros.

### D7. Voz de salida con edge-tts, por oraciones, con reproducción por cola

El texto parcial del cerebro se acumula hasta encontrar un fin de oración (punto, signo de pregunta o exclamación seguido de espacio, o salto de línea). Cada oración se limpia (se quitan bloques de código, URLs, rutas y marcas markdown) y se sintetiza con edge-tts a MP3 en memoria. Un hilo reproductor consume una cola ordenada, decodifica con `miniaudio` y reproduce con sounddevice. Interrumpir vacía la cola y corta la reproducción actual.

- Voz por defecto: `es-MX-DaliaNeural`. Configurable.
- Por qué edge-tts: gratis, sin key, buena calidad, voces neutras. Por qué miniaudio: decodifica MP3 sin ffmpeg instalado, con wheel para Windows.
- Alternativa: Windows SAPI. Sin red pero voces notoriamente peores. ElevenLabs: mejor, pago; anotado en el backlog.

### D8. Control de media con la sesión de media de Windows

Se usa `GlobalSystemMediaTransportControlsSessionManager` a través del paquete WinRT de Python para consultar la sesión actual y su estado de reproducción, pausar con `TryPauseAsync` y reanudar con `TryPlayAsync` sobre la misma sesión. Loki guarda el identificador de la sesión que pausó y solo reanuda esa.

- Por qué la API y no la tecla multimedia: la tecla alterna, y si el estado cambió mientras Loki hablaba se termina reproduciendo algo que estaba pausado. La API permite pausar y reanudar de forma explícita y saber si ya estaba pausado.
- Fallback: si el paquete WinRT no carga, se usa la tecla multimedia play/pause con pyautogui y se acepta el riesgo de alternar.
- Regla de reanudación: se reanuda cuando la máquina de estados vuelve a dormido sin confirmación pendiente. Para avisos no solicitados: pausar, hablar, esperar 4 segundos una activación, reanudar.

### D9. Relay con Orca: `terminal create`, `send`, `wait --for tui-idle`, `read`

Abrir sesión: `orca terminal create --worktree path:<repo> --title "<nombre>" --command "claude --model <m>" --json` y guardar el handle. Enviar: MCP `enviar_a_terminal` que usa `orca terminal send --terminal <h> --text <t> --enter`. Leer: `orca terminal wait --terminal <h> --for tui-idle --timeout-ms <t>` y después `orca terminal read --terminal <h> --cursor <último>`. El texto leído se le pasa al cerebro con la instrucción de resumirlo en voz y clasificar si el agente terminó, preguntó o pidió permiso.

- Por qué resumir con el LLM en vez de parsear: la salida de un TUI es ruidosa y cambia con cada versión. El cerebro es bueno resumiendo texto sucio, y la spec pide un resumen breve, no fidelidad literal.
- Supuesto: `--cursor` de `terminal read` permite leer solo lo nuevo. Si no, se guarda la longitud anterior y se recorta.

### D10. Flujo explore/propose/apply como skill del repo, no como código

El flujo se describe en `.claude/skills/desarrollo-por-voz/SKILL.md` dentro del repo de Loki, que el cerebro carga por correr con cwd ahí. La skill dice: qué comandos de Orca ejecutar en cada etapa, con qué modelo (leído de la herramienta MCP `config_modelos()`), y que un propose sin explore previo debe rechazarse. El apply crea el worktree con `orca worktree create --repo <sel> --name <change> --json` sin agente, y luego `orca terminal create --worktree <nuevo> --command "claude --model <impl>"` enviando `/opsx:apply <change>`.

- Por qué skill y no código: el reconocimiento de intención es lenguaje natural y el cerebro ya es un LLM. Codificar intents con expresiones regulares sería frágil. La skill es editable por Loki mismo en su ciclo de automejora.
- El comando inicial del explore lleva la idea del usuario como argumento: `/opsx:explore <texto dictado>`.
- Modelos por defecto: explore y propose `fable`, apply `sonnet`, cerebro `haiku`. En `config.yaml` del repo, sobreescribibles en `config.local.yaml`.

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

### D12. Configuración en tres capas

`config.yaml` (commiteado, defaults: modelos, voz, umbrales, ruta del modelo de wake word, lista de acciones críticas), `config.local.yaml` (ignorado: alias de proyectos, términos privados para la auditoría, posición del overlay, overrides), `.env` (ignorado: `GROQ_API_KEY`). Se incluyen `config.local.example.yaml` y `.env.example`.

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
