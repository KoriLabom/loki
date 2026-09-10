# Loki

Asistente de voz para Windows que se sienta encima de Orca y Claude Code:
escucha una palabra de activación, transcribe lo que decís, conversa con
un cerebro de Claude Code en modo headless (usa tu suscripción, sin API
key de Anthropic), y puede abrir y manejar sesiones de Claude Code en
otros repos para explorar, proponer y aplicar cambios de código por voz.

Ver `openspec/changes/loki-mvp/proposal.md` y `design.md` para el detalle
de esta primera versión, y `BACKLOG.md` para lo que todavía no entró a un
change.

## Prerrequisitos

- Windows 11.
- Python 3.12.
- [Claude Code](https://claude.com/claude-code) instalado y logueado con
  tu suscripción (`claude` en el PATH).
- [Orca](https://orca.dev) instalado y corriendo, con los repos que
  quieras manejar por voz ya registrados.
- Una cuenta de [Groq](https://console.groq.com) con una API key (se usa
  para la transcripción; tiene nivel gratuito).

## Instalación

1. Cloná este repo.
2. Corré `scripts\setup.bat`. Crea un entorno virtual en `.venv`, instala
   las dependencias de `requirements.txt`, y registra a Loki para que
   arranque solo la próxima vez que inicies sesión en Windows.
3. Copiá `config.local.example.yaml` a `config.local.yaml` y completá lo
   que quieras: alias de proyectos, términos privados para la auditoría,
   overrides de modelos. Es opcional; sin este archivo Loki arranca con
   los defaults de `config.yaml`.
4. Copiá `.env.example` a `.env` y completá `GROQ_API_KEY` con tu clave
   de Groq.
5. La primera vez, descargá el modelo de la palabra de activación si
   `modelos/hey_jarvis.onnx` no está en el repo:
   ```
   .venv\Scripts\python -c "from openwakeword.utils import download_models; download_models(model_names=['hey_jarvis'])"
   ```
   (esto también deja los modelos compartidos de openWakeWord en su
   ubicación por defecto, que Loki necesita además del modelo propio).

## Arrancar Loki

Sin reiniciar Windows, después de instalar:

```
.venv\Scripts\pythonw -m loki.main
```

O simplemente iniciá sesión de nuevo en Windows si corriste
`setup.bat` (queda registrado para arrancar solo).

Al arrancar aparece el overlay flotante en estado dormido y un ícono en
la bandeja del sistema. Decí "hey Jarvis" para activarlo.

## Correr los tests

```
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\pytest
```

## Antes de publicar un cambio

Este repo es público. Antes de cada merge o push a la rama pública,
corré la auditoría de privacidad sobre el diff:

```
.venv\Scripts\python scripts\auditar_privacidad.py
```

Revisá cualquier hallazgo (rutas de tu máquina, correos, posibles keys,
términos de tu lista privada) antes de seguir. La skill
`/auditar-privacidad` hace lo mismo desde una sesión de Claude Code en
este repo. Nunca commitees `.env` ni `config.local.yaml`: ambos están en
`.gitignore` y solo existen las plantillas de ejemplo.
