## Purpose

Hace que hablar con Loki no obligue a pausar a mano lo que se está mirando o escuchando: lo pausa al empezar la interacción y lo reanuda al terminar.

## Requirements

### Requirement: Pausa al activar
El sistema SHALL detectar si hay una sesión de media reproduciéndose en Windows en el momento en que se detecta la palabra de activación y, si la hay, SHALL pausarla antes de que el usuario termine de hablar. El sistema MUST recordar qué sesión pausó.

#### Scenario: Video reproduciéndose
- **WHEN** hay un video o audio reproduciéndose y el usuario dice la palabra de activación
- **THEN** la reproducción se pausa en menos de 500 ms y Loki recuerda que fue él quien pausó

#### Scenario: Nada reproduciéndose
- **WHEN** no hay ninguna sesión de media activa y el usuario dice la palabra de activación
- **THEN** Loki no envía ninguna orden de media

#### Scenario: Media ya pausado por el usuario
- **WHEN** hay una sesión de media en pausa antes de la activación
- **THEN** Loki no la toca y no la reanuda al terminar

### Requirement: Reanudación al terminar la interacción
El sistema SHALL reanudar la sesión que pausó cuando la interacción termina: Loki terminó de hablar y no está esperando una respuesta del usuario ni escuchando.

#### Scenario: Interacción simple
- **WHEN** Loki termina de hablar su respuesta y no hay confirmación pendiente
- **THEN** la reproducción que había pausado se reanuda

#### Scenario: Confirmación pendiente
- **WHEN** Loki hizo una pregunta de confirmación y espera el sí o no
- **THEN** la reproducción sigue pausada hasta que la confirmación se resuelve o expira

#### Scenario: Agente trabajando en segundo plano
- **WHEN** Loki delegó trabajo a un agente y terminó de avisarlo
- **THEN** la reproducción se reanuda mientras el agente trabaja

### Requirement: Aviso con media reproduciéndose
El sistema SHALL pausar el media antes de dar un aviso no solicitado, como el fin del trabajo de un agente, y SHALL reanudarlo al terminar el aviso si el usuario no responde.

#### Scenario: Agente terminó mientras se mira un video
- **WHEN** un agente termina y hay media reproduciéndose
- **THEN** Loki pausa, da el aviso por voz, espera el tiempo configurado (por defecto 4 segundos) por una activación, y si no la hay reanuda el media

### Requirement: Fallo del control de media
El sistema SHALL continuar la interacción con normalidad si el control de media no está disponible o falla, registrando el fallo en el log.

#### Scenario: API de media no disponible
- **WHEN** la consulta de sesiones de media falla
- **THEN** Loki escucha, piensa y habla igual, sin intentar pausar ni reanudar
