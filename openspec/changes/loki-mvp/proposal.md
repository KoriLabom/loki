## Why

Hoy el trabajo diario con agentes de código pasa por teclear en terminales de Orca y Claude Code, y cada interrupción para pedirle algo a un agente corta lo que se está haciendo, ya sea trabajar o mirar un video. Loki es un asistente de voz que se sienta encima de Orca y Claude Code para que esas órdenes se den hablando, con un flujo de desarrollo disciplinado (explore, propose, apply) y con el objetivo explícito de poder mejorarse a sí mismo con los mismos agentes que maneja. Este change construye la primera versión usable.

## What Changes

- Nueva aplicación de escritorio para Windows en Python que escucha una palabra de activación, graba hasta que el usuario deja de hablar, transcribe y responde por voz.
- Nuevo cerebro conversacional basado en Claude Code en modo headless, que usa la suscripción existente sin API key de Anthropic, con modelo configurable para el uso diario.
- Nueva capacidad de abrir sesiones de Claude Code en repos registrados en Orca, mandarles texto dictado y leer sus respuestas en voz (relay de voz bidireccional).
- Nuevo flujo de desarrollo por voz: "quiero hacer X en tal proyecto" abre una sesión de explore con el modelo más potente; "proponelo" y "aplicá" avanzan a propose y apply, este último en un worktree aislado con un modelo más económico. Loki monitorea y avisa al terminar.
- Nuevo control de media: si hay algo reproduciéndose cuando el usuario habla, se pausa y se reanuda cuando Loki termina.
- Nuevo overlay flotante siempre visible con el estado de Loki y la última frase, con estética Anthropic.
- Nueva política de confirmación hablada antes de acciones irreversibles.
- Nuevo repositorio público en GitHub con instalación reproducible, configuración privada fuera del control de versiones y una auditoría de privacidad del diff antes de cada merge.
- Reutilización adaptada de los módulos de audio, transcripción y overlay del proyecto `voice-transcript` del mismo autor. Se copian dentro de este repo; no se depende del otro.

## Capabilities

### New Capabilities
- `captura-de-voz`: activación por palabra clave, grabación con corte automático por silencio y transcripción a texto en español.
- `cerebro`: conversación de varios turnos con Claude Code headless, selección de modelo, herramientas disponibles y reglas de comportamiento de Loki.
- `voz-de-salida`: síntesis de voz de las respuestas, arrancando antes de que la respuesta completa esté lista, con interrupción por el usuario.
- `control-de-media`: pausa y reanudación de lo que se esté reproduciendo alrededor de cada interacción.
- `sesiones-de-agentes`: apertura de sesiones de Claude Code en repos de Orca, envío de texto dictado y lectura en voz de las respuestas.
- `flujo-de-desarrollo-por-voz`: orquestación por voz de explore, propose y apply con el modelo correcto por etapa, y aviso al terminar.
- `confirmacion-de-acciones-criticas`: qué acciones requieren un "sí" hablado y cómo se pide.
- `overlay-de-estado`: ventana flotante con estados, última frase y estética definida.
- `privacidad-del-repositorio`: separación de configuración privada, y auditoría del diff antes de publicar cambios.

### Modified Capabilities
<!-- Ninguna: el proyecto no tiene specs previas. -->

## Impact

- **Código nuevo**: paquete Python `loki/` con módulos de audio, cerebro, voz, herramientas MCP, interfaz y configuración; scripts de instalación y auditoría; skills de Claude Code propios del repo.
- **Dependencias externas nuevas**: openWakeWord con ONNX Runtime (wake word local), Groq (transcripción, API key ya existente), Edge TTS (voz, sin key), PyQt6, sounddevice, un decodificador de audio para la reproducción, el paquete WinRT de Python para la sesión de media de Windows, y el SDK MCP de Python para exponer herramientas al cerebro.
- **Sistemas externos**: Claude Code CLI 2.1.x en modo headless (consume la ventana de uso de la suscripción); Orca CLI para terminales y worktrees; Windows para media y audio.
- **Proyecto existente**: `voice-transcript` no se modifica; se copian módulos. Este repo, hoy vacío salvo OpenSpec, pasa a ser un repositorio git público llamado `loki`.
- **Riesgo principal**: Claude Code headless con acceso a Bash puede ejecutar acciones destructivas por un reconocimiento de voz erróneo. Se mitiga con lista de herramientas permitidas y la política de confirmación.
