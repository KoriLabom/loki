## Why

Loki todavía no tiene ninguna guía para quien quiera tocar el código: no hay README, no hay CONTRIBUTING y la única forma de saber cómo instalar dependencias y correr los tests es leer `requirements.txt` y `pytest.ini`. Antes de que el repo sea público conviene tener un punto de entrada corto y en español que deje a alguien nuevo con la suite de tests en verde en pocos minutos.

## What Changes

- Se agrega `CONTRIBUTING.md` en la raíz del repo, en español, con tres secciones: prerrequisitos, instalación de dependencias de desarrollo con pip en un entorno virtual, y ejecución de tests con pytest.
- El documento describe el repo tal como está hoy: un único `requirements.txt` que ya incluye `pytest` y `pytest-asyncio`. No se separan dependencias de runtime y de desarrollo.
- El documento aclara que el proyecto solo instala en Windows con Python 3.12, que los tests no necesitan micrófono, pantalla ni claves de API, y menciona el test intermitente conocido de `tests/test_canal_local.py` para que un rojo aislado no se lea como una ruptura.
- El documento remite a `BACKLOG.md` como memoria de producto y aclara que el resto de convenciones (OpenSpec, auditoría de privacidad, PRs) llegan con `CLAUDE.md` y `README.md`, previstos en el change `loki-mvp`.

## Capabilities

### New Capabilities

Ninguna. Es documentación pura: no cambia comportamiento observable del sistema. El change declara `skip_specs: true` en su `.openspec.yaml`.

### Modified Capabilities

Ninguna. El requerimiento "Instalación reproducible" de `privacidad-del-repositorio` en `loki-mvp` cubre el README de usuario final y el script de instalación; esta guía es para contribuidores y no altera ese requerimiento.

## Impact

- Archivo nuevo: `CONTRIBUTING.md` en la raíz.
- Sin cambios en código, dependencias, configuración ni tests.
- Relación con `loki-mvp`: las tareas 10.2 (`CLAUDE.md`) y 11.3 (`README.md`) de ese change deberían enlazar a `CONTRIBUTING.md` en vez de repetir la sección de tests. Se anota como nota, no se modifica ese change desde acá.
