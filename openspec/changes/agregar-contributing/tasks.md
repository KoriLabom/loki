## 1. Redacción

- [ ] 1.1 Crear `CONTRIBUTING.md` en la raíz, en español, con la sección "Prerrequisitos": Windows, Python 3.12 y git; aclarar que las dependencias `winrt-*` y `pyautogui` impiden instalar en Linux o macOS; verificar que el archivo existe y que no contiene rutas de usuario, correos ni nombres de proyectos privados
- [ ] 1.2 Agregar la sección "Instalar dependencias de desarrollo" con los comandos `python -m venv .venv`, activación en PowerShell y `cmd`, `python -m pip install --upgrade pip` y `pip install -r requirements.txt`; explicar que ese único archivo ya incluye `pytest` y `pytest-asyncio`; verificar que los comandos coinciden con `requirements.txt` y `.gitignore` (`.venv/` ya está ignorado)
- [ ] 1.3 Agregar la sección "Correr los tests" con `python -m pytest` y `python -m pytest tests/test_x.py -q` para un archivo puntual; aclarar que no hace falta micrófono, pantalla ni `.env` porque `tests/conftest.py` fuerza Qt en modo offscreen, y que `pytest.ini` activa `asyncio_mode = auto`; mencionar que `tests/test_canal_local.py` puede fallar de forma intermitente en Windows por una conexión de socket abortada y que basta reintentar; verificar que cada afirmación se corresponde con `conftest.py` y `pytest.ini`
- [ ] 1.4 Cerrar con un párrafo breve que remita a `BACKLOG.md` como memoria de producto y aclare que las convenciones de OpenSpec, la auditoría de privacidad y el flujo de PRs se documentan en `CLAUDE.md` y `README.md`; verificar que no se duplica contenido previsto en las tareas 10.2 y 11.3 de `loki-mvp`

## 2. Verificación

- [ ] 2.1 Seguir el documento al pie de la letra en un venv nuevo dentro del scratchpad o en una carpeta temporal fuera del repo: crear el venv, instalar `requirements.txt` y correr `python -m pytest -q`; verificar que la instalación termina sin errores y que la suite pasa (171 tests al momento de escribir esto), reintentando una vez si el único rojo es el test intermitente de `test_canal_local`
- [ ] 2.2 Revisar `CONTRIBUTING.md` con `git diff` buscando rutas con nombre de usuario de Windows, correos y términos de `config.local.yaml`; verificar que el diff está limpio antes de dar la tarea por cerrada
