## Purpose

Convierte las respuestas de Loki en voz femenina, formal y de español neutro, empezando a hablar apenas hay una oración lista y dejando que el usuario la interrumpa.

## Requirements

### Requirement: Síntesis de voz configurable
El sistema SHALL sintetizar las respuestas del cerebro con una voz femenina de español neutro, configurable por nombre de voz, con un valor por defecto definido en la configuración. El servicio de voz MUST NOT requerir una API key.

#### Scenario: Voz por defecto
- **WHEN** la configuración no indica voz
- **THEN** Loki habla con la voz por defecto del proyecto

#### Scenario: Voz configurada
- **WHEN** la configuración indica otra voz válida del mismo servicio
- **THEN** Loki habla con esa voz desde la próxima respuesta

### Requirement: Habla por oraciones a medida que llega el texto
El sistema SHALL segmentar el texto parcial de la respuesta en oraciones y SHALL empezar a reproducir la primera oración sin esperar el final de la respuesta, manteniendo el orden.

#### Scenario: Primera oración disponible
- **WHEN** el cerebro terminó de generar la primera oración de una respuesta larga
- **THEN** Loki empieza a hablar esa oración en menos de 1,5 segundos

#### Scenario: Orden preservado
- **WHEN** la respuesta tiene varias oraciones
- **THEN** se escuchan en el mismo orden en que fueron generadas, sin superposición

### Requirement: Limpieza de texto no hablable
El sistema SHALL omitir de la voz bloques de código, rutas de archivo largas, URLs y marcas de formato, reemplazándolos por una mención breve cuando sea necesario para entender la respuesta.

#### Scenario: Respuesta con bloque de código
- **WHEN** la respuesta del cerebro contiene un bloque de código
- **THEN** Loki no lee el código y en su lugar dice que el detalle está en el overlay o en la terminal

### Requirement: Interrupción de la voz
El sistema SHALL detener la reproducción en curso y descartar las oraciones pendientes cuando el usuario interrumpe con la palabra de activación o cuando se pide detener por voz.

#### Scenario: Interrupción por palabra clave
- **WHEN** Loki está hablando y se detecta la palabra de activación
- **THEN** la reproducción se corta y no se reproducen las oraciones que faltaban

### Requirement: Fallo del servicio de voz
El sistema SHALL mostrar la respuesta completa en el overlay cuando la síntesis de voz falla, e indicar el fallo en el log, sin perder el turno de conversación.

#### Scenario: Servicio caído
- **WHEN** la síntesis de voz falla para una respuesta
- **THEN** el texto queda visible en el overlay y Loki sigue operativo para el próximo turno
