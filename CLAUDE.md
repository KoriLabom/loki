# Loki

Asistente de voz para Windows que se sienta encima de Orca y Claude Code:
escucha una palabra de activación, transcribe, conversa con un cerebro de
Claude Code en modo headless, y puede abrir y manejar sesiones de Claude
Code en otros repos para explorar, proponer y aplicar cambios de código
por voz. Ver `openspec/changes/loki-mvp/proposal.md` y `design.md` para
el detalle de la primera versión, y `BACKLOG.md` para decisiones e ideas
que todavía no entraron a un change.

## Convención de OpenSpec

Este repo usa [OpenSpec](https://github.com/anthropics/openspec) para
planificar y documentar cambios. Toda propuesta, spec, diseño y lista de
tareas se escribe **en español**, salvo los encabezados estructurales y
las palabras clave `SHALL`/`MUST`/`WHEN`/`THEN` de los requirements, que
se dejan en inglés por convención del formato.

## Auditoría de privacidad antes de cada PR

Este repo es público. Antes de abrir un PR o hacer push, correr la
auditoría de privacidad (`scripts/auditar_privacidad.py`, o la skill
`/auditar-privacidad`) contra el diff. Nunca commitear `.env`,
`config.local.yaml`, ni rutas o datos específicos de la máquina de
desarrollo.

## Dónde está cada cosa

- `loki/` — paquete de la aplicación (audio, cerebro, voz, herramientas
  MCP, interfaz, configuración).
- `config.yaml` — defaults commiteados. `config.local.yaml` (ignorado)
  para overrides privados; ver `config.local.example.yaml`.
- `openspec/` — planificación de changes.
- `BACKLOG.md` — memoria de producto: decisiones tomadas, ideas futuras,
  preguntas abiertas que todavía no son un change.
