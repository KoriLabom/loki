## Purpose

Permite que el usuario le hable a Loki sin tocar el teclado: una palabra de activación despierta la escucha, la grabación termina sola cuando el usuario deja de hablar y el audio se convierte en texto en español listo para el cerebro.

## Requirements

### Requirement: Activación por palabra clave
El sistema SHALL escuchar el micrófono de forma continua mientras está en estado dormido y SHALL pasar a estado escuchando cuando detecta la palabra de activación configurada. La palabra de activación provisoria del MVP es "hey Jarvis"; el sistema MUST permitir reemplazarla por un modelo propio mediante configuración sin cambiar código.

#### Scenario: Palabra de activación detectada
- **WHEN** Loki está dormido y el usuario dice la palabra de activación
- **THEN** Loki pasa a estado escuchando en menos de 500 ms, lo indica en el overlay y empieza a grabar la frase del usuario

#### Scenario: Conversación normal sin la palabra clave
- **WHEN** el usuario habla con otra persona sin decir la palabra de activación
- **THEN** Loki permanece dormido y no graba ni transcribe nada

#### Scenario: Modelo de palabra clave configurado
- **WHEN** la configuración apunta a un archivo de modelo de palabra clave distinto al provisorio
- **THEN** Loki usa ese modelo al iniciar, y si el archivo no existe informa el error en el overlay y en el log sin cerrarse

### Requirement: Fin de frase por silencio
El sistema SHALL terminar la grabación automáticamente cuando detecta un silencio continuo mayor al umbral configurado (por defecto 1,2 segundos) después de que el usuario empezó a hablar, y MUST cortar también al alcanzar la duración máxima configurada (por defecto 30 segundos).

#### Scenario: El usuario termina de hablar
- **WHEN** el usuario deja de hablar durante más del umbral de silencio
- **THEN** la grabación termina, el overlay pasa a estado pensando y el audio se envía a transcripción

#### Scenario: El usuario no dice nada tras activar
- **WHEN** pasan 5 segundos desde la activación sin que se detecte voz
- **THEN** Loki vuelve a dormido sin transcribir y sin llamar al cerebro

#### Scenario: Frase demasiado larga
- **WHEN** la grabación alcanza la duración máxima
- **THEN** la grabación se corta en ese punto y se transcribe lo grabado

### Requirement: Transcripción a texto en español
El sistema SHALL transcribir el audio grabado a texto en español usando el servicio configurado, SHALL aplicar el vocabulario de términos técnicos del usuario para mejorar el reconocimiento y MUST descartar transcripciones vacías o que coincidan con alucinaciones conocidas del modelo sobre silencio.

#### Scenario: Transcripción exitosa
- **WHEN** el audio contiene una frase clara
- **THEN** el texto transcripto se entrega al cerebro y se muestra en el overlay

#### Scenario: Transcripción vacía o alucinada
- **WHEN** el servicio devuelve texto vacío o una frase de la lista de alucinaciones conocidas
- **THEN** Loki vuelve a dormido sin llamar al cerebro y muestra un aviso breve en el overlay

#### Scenario: Servicio de transcripción no disponible
- **WHEN** la llamada al servicio falla o excede el tiempo límite configurado
- **THEN** Loki avisa por voz que no pudo entender y vuelve a dormido

### Requirement: Interrupción mientras habla
El sistema SHALL seguir detectando la palabra de activación mientras Loki está hablando, y al detectarla MUST cortar la voz en curso y pasar a escuchar.

#### Scenario: El usuario interrumpe a Loki
- **WHEN** Loki está hablando y el usuario dice la palabra de activación
- **THEN** la voz se detiene en menos de 300 ms y Loki pasa a estado escuchando
