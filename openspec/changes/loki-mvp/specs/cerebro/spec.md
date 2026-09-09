## Purpose

Define cómo Loki piensa: una conversación continua con Claude Code en modo headless que usa la suscripción del usuario, con un modelo configurable, un conjunto acotado de herramientas y una personalidad definida.

## ADDED Requirements

### Requirement: Conversación continua con Claude Code headless
El sistema SHALL mantener una sesión de Claude Code en modo headless como cerebro conversacional, SHALL enviar cada frase transcripta como un turno de usuario y SHALL conservar el contexto entre turnos hasta que el usuario pida empezar de nuevo o se reinicie la aplicación. El sistema MUST funcionar con la autenticación existente de Claude Code y MUST NOT requerir una API key de Anthropic.

#### Scenario: Turno normal
- **WHEN** llega una frase transcripta
- **THEN** el cerebro responde teniendo en cuenta los turnos anteriores de la misma sesión

#### Scenario: Reinicio de conversación por voz
- **WHEN** el usuario pide empezar de nuevo o borrar la conversación
- **THEN** el cerebro descarta el contexto anterior y confirma por voz que arrancó una conversación nueva

#### Scenario: Claude Code no disponible
- **WHEN** el proceso de Claude Code no puede iniciarse o se cae
- **THEN** Loki avisa por voz que el cerebro no está disponible, lo indica en el overlay y reintenta iniciarlo en el próximo turno

### Requirement: Modelo configurable para el uso diario
El sistema SHALL usar para el cerebro conversacional el modelo indicado en la configuración, con Haiku 4.5 como valor por defecto, y MUST permitir cambiarlo sin modificar código.

#### Scenario: Modelo por defecto
- **WHEN** la configuración no indica modelo
- **THEN** el cerebro usa Haiku 4.5

#### Scenario: Modelo configurado
- **WHEN** la configuración indica otro alias o id de modelo válido
- **THEN** el cerebro usa ese modelo desde el próximo inicio de sesión

### Requirement: Respuesta en texto parcial
El sistema SHALL entregar el texto de la respuesta del cerebro a medida que se genera, de modo que la voz de salida pueda empezar antes de que la respuesta termine.

#### Scenario: Respuesta larga
- **WHEN** el cerebro genera una respuesta de varias oraciones
- **THEN** la primera oración está disponible para la voz de salida antes de que la última se haya generado

### Requirement: Herramientas acotadas
El sistema SHALL permitir al cerebro únicamente las herramientas necesarias para su función: comandos del CLI de Orca, las herramientas propias de Loki y lectura de archivos del propio repo. El cerebro MUST NOT poder ejecutar las acciones críticas definidas en `confirmacion-de-acciones-criticas` sin pasar por la confirmación.

#### Scenario: Comando de Orca permitido
- **WHEN** el cerebro decide listar terminales de Orca
- **THEN** el comando se ejecuta sin pedir permiso interactivo

#### Scenario: Herramienta fuera de la lista
- **WHEN** el cerebro intenta usar una herramienta que no está en la lista permitida
- **THEN** la herramienta se rechaza y el cerebro recibe el rechazo como resultado, sin bloquear la aplicación esperando un permiso interactivo

### Requirement: Personalidad y estilo de respuesta
El sistema SHALL responder en español neutro, con tono formal y conciso, sin muletillas regionales, con respuestas pensadas para ser escuchadas: oraciones cortas, sin listas largas ni bloques de código leídos en voz alta. Cuando ejecuta una acción, SHALL decir qué hizo en una oración.

#### Scenario: Acción ejecutada
- **WHEN** el cerebro abre una terminal a pedido del usuario
- **THEN** la respuesta hablada confirma la acción en una oración corta, sin detalles técnicos innecesarios

#### Scenario: Pregunta abierta
- **WHEN** el usuario hace una pregunta de conocimiento general
- **THEN** la respuesta hablada no supera las tres o cuatro oraciones salvo que el usuario pida más detalle

### Requirement: Alias de proyectos
El sistema SHALL resolver nombres coloquiales de proyectos ("el tablero") a repos registrados en Orca usando los alias de la configuración local, y cuando no puede resolver un nombre MUST preguntar al usuario a cuál se refiere en vez de adivinar.

#### Scenario: Alias conocido
- **WHEN** el usuario menciona un alias definido en la configuración local
- **THEN** el cerebro trabaja sobre el repo de Orca asociado

#### Scenario: Proyecto ambiguo
- **WHEN** el usuario menciona un proyecto que no coincide con ningún alias ni nombre de repo
- **THEN** Loki pregunta por voz a cuál se refiere, listando los candidatos más parecidos
