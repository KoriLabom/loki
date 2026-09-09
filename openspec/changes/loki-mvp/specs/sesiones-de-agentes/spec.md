## Purpose

Permite hablarle a una sesión de Claude Code que corre en Orca: abrirla en el repo correcto, dictarle mensajes y escuchar lo que responde.

## ADDED Requirements

### Requirement: Abrir una sesión de Claude Code en un repo de Orca
El sistema SHALL poder abrir una terminal de Orca en un repo registrado, con Claude Code corriendo con el modelo indicado, y SHALL guardar el identificador de esa terminal para dirigirle mensajes después. Cuando el usuario no indica repo, el sistema MUST preguntar cuál usar.

#### Scenario: Abrir sesión por voz
- **WHEN** el usuario pide abrir Claude Code en un proyecto conocido
- **THEN** aparece una terminal nueva en Orca en ese repo con Claude Code iniciado, y Loki confirma por voz con el nombre del proyecto

#### Scenario: Repo no indicado
- **WHEN** el usuario pide abrir Claude Code sin decir en qué proyecto
- **THEN** Loki pregunta por voz en qué proyecto, nombrando los repos registrados en Orca

#### Scenario: Orca no disponible
- **WHEN** el runtime de Orca no está corriendo
- **THEN** Loki avisa por voz que Orca no está abierto y ofrece abrirlo

### Requirement: Sesión activa de relay
El sistema SHALL mantener una única sesión de agente activa para el relay de voz en cada momento, SHALL poder cambiarla por voz entre las terminales de Claude Code abiertas y SHALL indicar en el overlay con cuál está hablando.

#### Scenario: Cambiar de sesión
- **WHEN** el usuario pide hablar con la sesión de otro proyecto que ya está abierta
- **THEN** los mensajes siguientes van a esa terminal y el overlay muestra su nombre

#### Scenario: Sesión cerrada externamente
- **WHEN** la terminal activa ya no existe en Orca
- **THEN** Loki avisa que la sesión se cerró y pide elegir otra o abrir una nueva

### Requirement: Enviar texto dictado a la sesión activa
El sistema SHALL enviar el texto dictado a la terminal de la sesión activa como entrada seguida de Enter, sin agregar encabezados ni reescrituras que el usuario no dijo.

#### Scenario: Dictado enviado
- **WHEN** el usuario dicta un mensaje estando en modo relay
- **THEN** el texto aparece en la terminal de Claude Code y se envía, y el overlay pasa a estado agente trabajando

### Requirement: Leer la respuesta del agente en voz
El sistema SHALL esperar a que la terminal de la sesión activa quede ociosa, SHALL leer la salida nueva desde el último envío y SHALL resumirla en voz de forma breve, distinguiendo si el agente terminó, hizo una pregunta o quedó esperando permiso.

#### Scenario: El agente respondió
- **WHEN** la terminal queda ociosa después de un envío
- **THEN** Loki lee un resumen hablado de la respuesta en no más de cuatro oraciones

#### Scenario: El agente pregunta algo
- **WHEN** la salida termina con una pregunta o un pedido de permiso
- **THEN** Loki lo transmite como pregunta y queda escuchando la respuesta del usuario para reenviarla

#### Scenario: El agente tarda demasiado
- **WHEN** la terminal no queda ociosa dentro del tiempo límite configurado (por defecto 10 minutos)
- **THEN** Loki avisa que el agente sigue trabajando y seguirá esperando en segundo plano

### Requirement: Salir del modo relay
El sistema SHALL volver a hablar con el cerebro de Loki cuando el usuario lo pida, sin cerrar la sesión de agente.

#### Scenario: Volver a Loki
- **WHEN** el usuario pide volver o hablar con Loki
- **THEN** los mensajes siguientes van al cerebro y la terminal del agente sigue abierta
