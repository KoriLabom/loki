## Purpose

Orquesta por voz el ciclo de desarrollo con OpenSpec: explorar la idea con el modelo más capaz, proponer el change y aplicarlo con un modelo económico en un worktree aislado, avisando al terminar.

## ADDED Requirements

### Requirement: Inicio de exploración por voz
El sistema SHALL reconocer cuando el usuario expresa la intención de construir o cambiar algo en un proyecto y SHALL abrir una sesión de Claude Code en ese repo con el modelo configurado para exploración (por defecto el más potente disponible), enviándole el comando de explore de OpenSpec con lo que el usuario dijo. El sistema MUST NOT lanzar un propose sin una exploración previa en la misma sesión.

#### Scenario: Idea nueva en un proyecto conocido
- **WHEN** el usuario dice que quiere agregar o cambiar algo en un proyecto que se puede resolver
- **THEN** se abre una sesión de Claude Code en ese repo con el modelo de exploración, recibe el comando de explore con la idea, y Loki entra en modo relay con esa sesión

#### Scenario: Idea sobre Loki mismo
- **WHEN** el usuario pide que Loki se mejore o se agregue una función a sí mismo
- **THEN** la sesión de explore se abre en el repo de Loki

#### Scenario: Pedido de propose sin explore
- **WHEN** el usuario pide proponer sin haber explorado en la sesión activa
- **THEN** Loki propone empezar por la exploración y no envía el propose

### Requirement: Avance a propose por voz
El sistema SHALL enviar el comando de propose de OpenSpec a la sesión de explore activa cuando el usuario lo pide, y SHALL leer en voz el nombre del change creado.

#### Scenario: Usuario pide proponer
- **WHEN** el usuario pide proponer o armar la propuesta durante una exploración
- **THEN** la sesión recibe el comando de propose y Loki informa por voz el nombre del change cuando termina

### Requirement: Apply aislado con modelo económico
El sistema SHALL crear un worktree de Orca para el change en el repo correspondiente y SHALL lanzar en él una sesión de Claude Code con el modelo configurado para implementación (por defecto Sonnet), enviándole el comando de apply del change. El apply MUST NOT ejecutarse en el checkout principal del repo.

#### Scenario: Usuario pide aplicar
- **WHEN** el usuario pide aplicar un change que existe
- **THEN** aparece un worktree nuevo en Orca con Claude Code ejecutando el apply de ese change con el modelo de implementación, y Loki confirma por voz

#### Scenario: Change inexistente
- **WHEN** el usuario pide aplicar un change que no existe en el repo
- **THEN** Loki dice qué changes hay disponibles y no crea el worktree

### Requirement: Monitoreo y aviso de fin
El sistema SHALL seguir en segundo plano la terminal del apply y SHALL avisar por voz cuando el agente terminó, hizo una pregunta que necesita al usuario, o superó el tiempo límite configurado, mientras el usuario sigue con otras cosas.

#### Scenario: Apply terminado
- **WHEN** la terminal del apply queda ociosa y la salida indica que las tareas se completaron
- **THEN** Loki avisa por voz que terminó, con el nombre del change, y ofrece hablar con esa sesión

#### Scenario: Apply trabado en una pregunta
- **WHEN** la terminal queda ociosa y la salida termina en una pregunta o pedido de permiso
- **THEN** Loki avisa que el agente necesita una respuesta y transmite la pregunta

#### Scenario: Varios agentes en paralelo
- **WHEN** hay más de una sesión monitoreada
- **THEN** cada aviso identifica a qué proyecto y change corresponde

### Requirement: Modelos por etapa configurables
El sistema SHALL tomar de la configuración el modelo para exploración y propose, y el modelo para implementación, con valores por defecto definidos en el proyecto.

#### Scenario: Cambio de modelo de implementación
- **WHEN** la configuración indica otro modelo para implementación
- **THEN** el próximo apply se lanza con ese modelo
