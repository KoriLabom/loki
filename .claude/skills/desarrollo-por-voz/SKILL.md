---
name: desarrollo-por-voz
description: Orquesta por voz el ciclo explore/propose/apply de OpenSpec en un repo de Orca, con el modelo correcto por etapa y aviso al terminar. Usar cuando el usuario exprese la intención de construir, cambiar o mejorar algo en un proyecto (incluido Loki mismo), o pida avanzar esa exploración a propose o apply.
metadata:
  author: loki
  version: "1.0"
---

Este es tu flujo para llevar adelante trabajo de desarrollo real en un
repo de Orca a partir de lo que el usuario dice. Vos (el cerebro de Loki)
solo orquestás: quien explora, propone y aplica es otro Claude Code
corriendo en una terminal aparte. Vos abrís esa terminal, le mandás
comandos, y hacés de relay entre el usuario y esa sesión.

## Cuándo entra este flujo

Entra cuando el usuario dice que quiere agregar, cambiar o arreglar algo
en un proyecto — el suyo o el propio Loki ("quiero que te acuerdes de
X", "agregate la función Y"). No entra para preguntas de conocimiento
general, ni para pedidos de una sola acción simple (listar terminales,
abrir una sesión, leer un archivo).

Si no tenés claro a qué proyecto se refiere, resolvé el nombre con
`listar_proyectos()` y los alias de la configuración local antes de
seguir; si es ambiguo, preguntá por voz en vez de adivinar.

## 1. Explore

1. Llamá a `config_modelos()` y tomá el modelo de `explore`.
2. Abrí una terminal nueva con Bash: `orca terminal create --worktree
   path:<ruta del repo> --command "claude --model <modelo-explore>"
   --json`. Guardate el `handle` que te devuelve.
3. Activá el relay con esa terminal: `sesion_relay_activar(terminal)`.
4. Mandale el primer mensaje con la herramienta MCP `enviar_a_terminal`
   (nunca por Bash: `orca terminal send` está deshabilitado), con el
   texto tal cual lo dijo el usuario: `/opsx:explore <idea del usuario>`.
   Como el destino es una sesión de Claude Code, esto no pide
   confirmación.

Si el usuario ya venía hablando con vos de una idea para un proyecto
existente, mandale esa idea completa como argumento del `/opsx:explore`,
no solo la última frase.

**Mientras el relay sigue activo, vos seguís recibiendo cada turno del
usuario** (la aplicación no te lo esconde). En cada uno, decidís:

- Si es una instrucción de flujo (proponer, aplicar, listar changes,
  volver a hablar con vos), actuás como se describe más abajo.
- Si no, es algo dirigido al otro agente: reenvialo con `enviar_a_terminal`
  exactamente como lo dijo el usuario, sin agregar ni sacar nada. Después
  de reenviarlo, la aplicación espera la respuesta del agente y te la va
  a pasar para que la resumas en voz; no hace falta que vos sondees nada.

## 2. Propose

- Si el usuario pide "proponelo" o "armá la propuesta" **sin que haya
  una exploración activa en esta misma sesión de relay**, no mandes el
  propose: decile que primero hay que explorar la idea, y ofrecé
  arrancar el explore.
- Si ya hay una exploración en curso en la terminal activa, mandale
  `/opsx:propose` con `enviar_a_terminal` (no lo reenvíes tal cual lo
  dijo el usuario: acá vos traducís el pedido al comando exacto).
  Cuando el agente termine, decile al usuario por voz el nombre del
  change que quedó creado.

## 3. Apply

Cuando el usuario pida aplicar un change:

1. Verificá que el change existe (podés pedirle a la sesión activa que
   liste los changes, o inferirlo de la conversación). Si no existe,
   decile al usuario qué changes hay disponibles y no sigas.
2. Llamá a `config_modelos()` y tomá el modelo de `apply`.
3. Creá el worktree para el apply, **sin agente**, con Bash: `orca
   worktree create --repo <selector del repo> --name <nombre del change>
   --json`. El apply nunca se corre en el checkout principal.
4. En ese worktree nuevo, abrí una terminal con Bash, con el comando de
   arranque **ya incluido en `--command`** (no lo mandes por separado
   como si fuera texto de shell): `orca terminal create --worktree
   <worktree nuevo> --command "claude --model <modelo-apply>" --json`.
5. Esperá a que esa terminal esté lista (podés chequear con `orca
   terminal show`) y recién ahí mandale el primer mensaje con la
   herramienta MCP `enviar_a_terminal` (nunca por Bash): el texto exacto
   `/opsx:apply <nombre del change>`, con la barra `/` inicial y nada
   más pegado adelante. Por ejemplo, si el change se llama
   `agregar-contributing`, el `texto` de `enviar_a_terminal` es
   exactamente `/opsx:apply agregar-contributing` — nunca combines el
   comando de arranque de Claude Code con el comando de OpenSpec en un
   solo texto ni en un solo paso.
6. Registrá el monitoreo de esa terminal: `monitorear_terminal(terminal,
   etiqueta="apply de <nombre del change>")`. Esto corre en segundo
   plano; no hace falta que sigas esperando ahí. Confirmale al usuario
   por voz que el apply arrancó, en una oración.
7. El aviso de que terminó, de que preguntó algo, o de que quedó
   esperando permiso llega solo más adelante gracias al monitor: no
   tenés que consultarlo vos activamente.

## Reglas generales

- Los comandos de Orca que abren terminales o worktrees nuevos (`terminal
  create`, `worktree create`) no son críticos: se ejecutan sin pedir
  confirmación. Cerrar una terminal o eliminar un worktree sí lo son:
  nunca se hacen acá, van por las herramientas MCP correspondientes con
  confirmación.
- Modelos por defecto (overridables por configuración): explore y
  propose en `fable`, apply en `sonnet`, tu propia conversación diaria en
  `haiku`.
- Si en algún punto no sabés en qué terminal estás parado o si el relay
  sigue activo, usá `orca terminal list` para reorientarte antes de
  mandar nada.
