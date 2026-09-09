# Backlog de Loki

Asistente de voz que maneja la computadora a través de Orca, Claude Code y herramientas propias.
Este archivo es la memoria de producto del proyecto: decisiones tomadas, ideas por construir y preguntas abiertas.
Lo que entra a construirse pasa a un change de OpenSpec en `openspec/changes/`. Lo demás vive acá.

Última actualización: 2026-09-09

## Identidad

- **Nombre**: Loki, como el gato naranja del autor. Naranja como la estética Anthropic a la que apunta el proyecto, y con temática Marvel. Dos sílabas, no se parece fonéticamente a "Claude", "Cloud", "Code" ni "Orca", palabras que se dicen todo el día mientras se trabaja. Descartados Jarvis (solo inspiración), Claw, Claudio y Claudia por colisión con "Claude", y Ámbar (propuesta anterior).
- **Voz**: femenina, formal, español neutro sin acento regional. Arranca con Edge TTS voz `es-MX-DaliaNeural`, configurable.
- **Personalidad**: formal, concisa, sin muletillas regionales.
- **Estética**: paleta Anthropic. Fondo oscuro cálido, acentos y onda de voz en naranja terracota, tipografía limpia.
- **Wake word**: provisorio "hey Jarvis" (modelo preentrenado gratis de openWakeWord). La primera tarea de automejora de Loki es entrenar su propio wake word con su nombre real.

## Decisiones tomadas

- **Cerebro**: Claude Code en modo headless (`claude -p` con entrada y salida `stream-json`), manejado desde una app propia en Python. Usa la suscripción de Claude Code, sin API key de Anthropic. Descartado el Agent SDK porque su camino documentado exige API key. El diseño es el mismo: la SDK es una envoltura de ese comando.
- **Herramientas propias**: se exponen al cerebro por un servidor MCP local del proyecto (pausar media, hablar, estado del overlay, monitores). El CLI de Orca se usa directo con Bash.
- **Manos**: Orca es la capa de ejecución. Su CLI (234 comandos, schema en `orca agent-context --json`) cubre terminales, worktrees con agente, computer-use en Windows, browser embebido con perfiles, automations y orquestación. No se reimplementa nada de eso.
- **Elección de modelo en Orca**: `worktree create --agent` no acepta modelo. Se crea el worktree sin agente y se lanza `terminal create --command "claude --model <m>"`.
- **Activación**: wake word desde el MVP, no push-to-talk. Fin de frase por detección de silencio.
- **STT**: Groq Whisper large-v3, reutilizando el transcriptor de voice-transcript. La GPU local (NVIDIA T500, 4GB) es floja para Whisper local.
- **Base de código de voz**: los módulos útiles del repo `voice-transcript` del mismo autor (grabador, transcriptor, vocabulario, overlay) se copian y adaptan dentro de este repo. No se depende del otro repo.
- **Flujo de codear por voz**: explore -> propose -> apply. El explore lo hace una sesión de Claude Code con `/opsx:explore` en el repo destino; Loki es relay de voz bidireccional con esa terminal. Nunca un propose directo sin explore previo.
- **Modelos por etapa**:
  - Explore y propose: el más potente disponible (hoy `claude-fable-5-1`).
  - Apply: `claude-sonnet-5` por defecto, con escalada a `claude-opus-5` si una tarea falla tests dos veces o el propose la marcó como compleja.
  - Cerebro de Loki (bucle de voz diario): modelo rápido, Haiku 4.5 o Sonnet 5 según latencia. Haiku 4.5 está disponible como modelo principal bajo suscripción.
- **Automejora**: los agentes trabajan en worktrees de Orca, nunca en el main donde corre el Loki vivo. Un supervisor reinicia a Loki con el código nuevo y vuelve a la versión anterior si no arranca.
- **Confirmación hablada**: obligatoria antes de cerrar terminales, borrar worktrees o archivos, y mandar texto a terminales que no sean de Claude Code. Todo lo demás se ejecuta directo.
- **Repo**: GitHub público, nombre `loki`, misma cuenta que voice-transcript. Antes de cada merge, auditoría del diff buscando datos personales, paths locales, secretos y nombres de proyectos del trabajo. Lo privado vive en archivos locales ignorados por git (`.env`, `config.local.*`). README con instalación completa para que otra persona lo corra en su máquina.
- **Metodología**: OpenSpec, artefactos en español.

## MVP (change `loki-mvp`)

- Decir "hey Jarvis", hablar, y que Loki responda por voz.
- Abrir una sesión de Claude Code en un repo de Orca, mandarle lo que digo y leerme la respuesta.
- Reconocer "quiero hacer tal cosa en tal proyecto" y arrancar el flujo explore con el modelo potente. Propose y apply se disparan por voz.
- Pausar el media que esté sonando mientras hablo y reanudarlo al terminar.
- Overlay flotante chico con estados y última frase, estética Anthropic.

## Ideas por construir (fuera del MVP)

Orden aproximado de valor. Una línea por idea.

- **Wake word propio**: entrenar "Loki" con openWakeWord (una tarde en Colab, gratis) o Picovoice (minutos, cuenta gratis personal). Primera tarea de automejora.
- **Supervisor con rollback**: proceso tonto que lanza a Loki, la reinicia cuando hay código nuevo en main y vuelve al commit anterior si el nuevo no levanta.
- **Monitores**: detectar cuántos hay conectados (hot-plug, es una laptop) y mover ventanas entre ellos. "Poneme esto en el segundo monitor". Orca computer-use lista ventanas pero no las mueve: herramienta propia con Win32.
- **YouTube**: "poneme un video nuevo de Martín Sirio que no haya visto". Feed RSS del canal, sin API key. Lista propia de videos vistos en la memoria de Loki. Abrir en el browser en el monitor indicado.
- **Campus virtual**: "vamos a estudiar tal materia". Entrar al campus con el browser de Orca usando un perfil de sesión con login persistente, bajar los archivos de la materia y abrir una sesión de Claude Code para estudiar con ellos.
- **Organizar carpetas**: mover, renombrar y ordenar archivos por voz. Requiere confirmación antes de borrar.
- **Memoria persistente**: preferencias, videos vistos, proyectos abiertos, cosas que le dije. Arranca como archivos markdown.
- **Escalada automática de modelo en apply**: detectar dos fallos de tests en una tarea y relanzarla en Opus.
- **Automations de Orca**: usar `orca automations` para cosas programadas que Loki decide crear por voz.
- **Multi-agente**: Loki coordinando varios workers de Orca en paralelo con `orca orchestration`.
- **ElevenLabs**: subir la calidad de voz si Edge TTS no convence.

## Preguntas abiertas

- Cómo detectar que hay media reproduciéndose y en qué app, para pausar solo cuando corresponde. Candidato: sesión de media de Windows (`GlobalSystemMediaTransportControlsSessionManager`) más la tecla multimedia play/pause.
- Qué hace Loki cuando reconoce mal y ejecuta algo no pedido. Deshacer donde se pueda.
- Cómo se siente la latencia total (wake word + STT + cerebro + TTS) y si el cerebro diario va en Haiku o Sonnet.
- **Latencia de edge-tts hasta la primera oración (medida en la tarea 10.3, segunda sesión de pruebas del 2026-09-09): ~1,8 s, por encima del objetivo de <1,5 s de la spec `voz-de-salida`.** Parece ser latencia de red del propio servicio, no de la cola/síntesis de Loki (que ya procesa en orden estricto, ver design.md D7). Si molesta en el uso diario, revisar con ElevenLabs u otro proveedor con menor latencia antes que seguir optimizando el lado de Loki.

## Hallazgos del entorno (2026-09-08)

- Orca instalado en `%LOCALAPPDATA%\Programs\orca`. Runtime corriendo, computer-use de Windows operativo (UIAutomation, screenshots, click, tipeo, hotkeys).
- Claude Code 2.1.265, Python 3.12.10, Node 24.16.
- Varios repos de trabajo registrados en Orca; sus alias van en `config.local.yaml`, no en el repo.
- Dos monitores hoy: DISPLAY1 1536x864 principal (laptop), DISPLAY2 1920x1080 a la derecha.
- Esta carpeta ya está registrada como repo en Orca y esta sesión de Claude Code corre dentro de una terminal de Orca.
- voice-transcript: Python 3.12, PyQt6, sounddevice, Groq Whisper large-v3, pynput, overlay con onda de voz, reescritor de prompts con Groq llama. Ya usa OpenSpec.
