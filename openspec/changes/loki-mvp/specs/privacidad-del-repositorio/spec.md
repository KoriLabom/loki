## Purpose

Permite publicar el código de Loki en un repositorio público sin filtrar datos personales, secretos, rutas locales ni nombres de proyectos del trabajo, y que otra persona pueda instalarlo en su máquina.

## ADDED Requirements

### Requirement: Configuración privada fuera del control de versiones
El sistema SHALL leer secretos desde un archivo `.env` y configuración específica de la máquina (rutas, alias de proyectos, nombres de repos, posición del overlay) desde un archivo de configuración local, y ambos MUST estar excluidos del control de versiones. El repo SHALL incluir plantillas de ejemplo de ambos sin datos reales.

#### Scenario: Primera instalación
- **WHEN** alguien clona el repo y copia las plantillas de ejemplo
- **THEN** Loki arranca con valores por defecto y pide por voz o en el log lo que falta configurar

#### Scenario: Archivo local ausente
- **WHEN** no existe el archivo de configuración local
- **THEN** Loki funciona con los valores por defecto del repo y sin alias de proyectos

### Requirement: Auditoría de privacidad antes de publicar
El sistema SHALL proveer una auditoría ejecutable sobre el diff a publicar que detecta rutas de usuario de Windows, direcciones de correo, patrones de API keys y tokens, y una lista configurable de términos privados (nombres de proyectos del trabajo, personas, empresas). La auditoría MUST fallar con un listado de hallazgos y ubicación cuando encuentra algo, y MUST ejecutarse antes de cada merge o push a la rama pública.

#### Scenario: Diff limpio
- **WHEN** se ejecuta la auditoría sobre un diff sin hallazgos
- **THEN** termina con éxito e informa que no encontró datos privados

#### Scenario: Ruta local en el diff
- **WHEN** el diff contiene una ruta con un nombre de usuario de Windows
- **THEN** la auditoría falla e indica archivo y línea

#### Scenario: Término privado configurado
- **WHEN** el diff contiene un término de la lista privada local
- **THEN** la auditoría falla e indica archivo y línea sin imprimir la lista completa de términos

### Requirement: Instalación reproducible
El repo SHALL incluir instrucciones y un script de instalación que dejen a Loki corriendo en otra máquina Windows con solo Python, Claude Code y Orca instalados, indicando qué cuentas y claves hacen falta.

#### Scenario: Instalación en máquina nueva
- **WHEN** alguien sigue las instrucciones del README en una máquina con los prerrequisitos
- **THEN** Loki arranca, muestra el overlay y responde a la palabra de activación
