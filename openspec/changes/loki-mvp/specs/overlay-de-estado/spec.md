## Purpose

Muestra en todo momento qué está haciendo Loki y qué fue lo último que se dijo, en una ventana chica, siempre visible y con la estética del proyecto.

## ADDED Requirements

### Requirement: Ventana flotante siempre visible
El sistema SHALL mostrar una ventana flotante sin bordes, siempre encima de las demás, que no roba el foco, arrastrable con el mouse y que recuerda su posición entre ejecuciones. Por defecto se ubica centrada abajo en el monitor principal.

#### Scenario: Primera ejecución
- **WHEN** Loki arranca sin posición guardada
- **THEN** el overlay aparece centrado en la parte inferior del monitor principal

#### Scenario: Usuario lo mueve
- **WHEN** el usuario arrastra el overlay a otro lugar o a otro monitor y cierra Loki
- **THEN** en la próxima ejecución aparece en el mismo lugar, si ese monitor sigue conectado

#### Scenario: Monitor desconectado
- **WHEN** la posición guardada corresponde a un monitor que ya no está
- **THEN** el overlay vuelve a la posición por defecto del monitor principal

### Requirement: Estados visibles
El sistema SHALL representar de forma distinguible los estados dormido, escuchando, pensando, hablando y agente trabajando, con una animación de onda que responde al volumen del micrófono mientras escucha.

#### Scenario: Cambio de estado
- **WHEN** Loki pasa de un estado a otro
- **THEN** el overlay refleja el nuevo estado en menos de 100 ms

#### Scenario: Escuchando
- **WHEN** Loki está escuchando y el usuario habla
- **THEN** la onda del overlay se mueve en proporción al volumen

### Requirement: Última frase y sesión activa
El sistema SHALL mostrar el último texto transcripto del usuario y la última respuesta de Loki, y cuando hay una sesión de agente activa en modo relay SHALL mostrar el nombre de esa sesión o proyecto.

#### Scenario: Turno completo
- **WHEN** el usuario dijo algo y Loki respondió
- **THEN** ambas frases son visibles en el overlay hasta el próximo turno

#### Scenario: Modo relay
- **WHEN** Loki está en modo relay con una sesión de agente
- **THEN** el overlay indica el nombre del proyecto de esa sesión

### Requirement: Estética del proyecto
El sistema SHALL usar la paleta definida en el diseño: fondo oscuro cálido, acentos y onda en naranja terracota, texto claro y tipografía limpia. Los colores MUST estar centralizados para poder cambiarlos en un solo lugar.

#### Scenario: Cambio de paleta
- **WHEN** se modifica el valor del color de acento en la definición central
- **THEN** todos los elementos que usan el acento cambian sin tocar otro código

### Requirement: Icono en la bandeja del sistema
El sistema SHALL mostrar un icono en la bandeja de Windows con un menú para mostrar u ocultar el overlay, reiniciar la conversación y salir.

#### Scenario: Salir desde la bandeja
- **WHEN** el usuario elige salir en el menú de la bandeja
- **THEN** Loki detiene la escucha, cierra el cerebro y termina sin dejar procesos huérfanos
