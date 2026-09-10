## Purpose

Evita que un reconocimiento de voz erróneo produzca daño irreversible: las acciones críticas requieren un "sí" hablado explícito antes de ejecutarse.

## Requirements

### Requirement: Lista de acciones críticas
El sistema SHALL tratar como críticas, como mínimo, estas acciones: cerrar terminales de Orca, eliminar worktrees, borrar o sobrescribir archivos fuera de los directorios de trabajo del propio Loki, y enviar texto a una terminal que no sea una sesión de Claude Code. La lista MUST ser ampliable por configuración.

#### Scenario: Acción crítica pedida
- **WHEN** el usuario pide una acción de la lista
- **THEN** Loki no la ejecuta hasta obtener confirmación

#### Scenario: Acción no crítica
- **WHEN** el usuario pide listar terminales o abrir una sesión nueva
- **THEN** Loki la ejecuta sin pedir confirmación

### Requirement: Pregunta de confirmación hablada
El sistema SHALL pedir confirmación por voz describiendo la acción concreta y su objetivo (por ejemplo, el nombre de la terminal), SHALL escuchar la respuesta sin requerir la palabra de activación y SHALL ejecutar solo si la respuesta es una afirmación clara.

#### Scenario: Usuario confirma
- **WHEN** Loki pregunta y el usuario responde con una afirmación clara dentro del tiempo límite (por defecto 10 segundos)
- **THEN** la acción se ejecuta y Loki confirma que se hizo

#### Scenario: Usuario niega o duda
- **WHEN** el usuario responde con una negación, con otra cosa, o la respuesta es ambigua
- **THEN** la acción no se ejecuta y Loki dice que la canceló

#### Scenario: Sin respuesta
- **WHEN** pasa el tiempo límite sin respuesta
- **THEN** la acción se cancela y Loki lo informa brevemente

### Requirement: Confirmación no delegable al cerebro
El sistema SHALL verificar la confirmación en una capa independiente del cerebro conversacional: la acción crítica MUST NOT poder ejecutarse aunque el cerebro afirme que el usuario ya confirmó, si esa capa no registró una confirmación válida y reciente para esa acción concreta.

#### Scenario: Cerebro intenta saltar la confirmación
- **WHEN** el cerebro invoca una acción crítica sin una confirmación válida registrada para ella
- **THEN** la acción se rechaza y el cerebro recibe la instrucción de pedir confirmación
