"""Spike de validación de design.md D1.

Lanza `claude -p` en modo stream-json de entrada y salida, manda dos turnos
de usuario en la misma invocación del subproceso y comprueba que el segundo
turno recuerda el primero (multi-turno dentro de un solo proceso, sin
`--resume`). Imprime los `content_block_delta` de texto en orden a medida
que llegan.

Hallazgos registrados en design.md:
- `--append-system-prompt-file` no existe en el CLI instalado; se usa
  `--system-prompt` con el texto ya leído en Python.
- `--permission-mode default` no existe; los valores válidos son
  acceptEdits/auto/bypassPermissions/manual/dontAsk/plan. Se usa `manual`
  junto con `--permission-prompts none` para que lo no permitido se
  rechace solo en vez de esperar una respuesta que nadie va a dar.
- Sin `--setting-sources project`, el proceso carga los hooks y el sistema
  de memoria automática del usuario (nivel "user"), y el modelo intenta
  usar herramientas de archivo para guardar recuerdos en vez de responder
  directo. `--bare` evitaría esto pero exige API key de Anthropic, lo cual
  está prohibido por este proyecto. La solución es `--setting-sources
  project` (excluye "user" y "local"), que sí funciona con la
  autenticación de la suscripción.
- El evento de fin de turno sí tiene `"type":"result"`, con
  `duration_api_ms`, `stop_reason`, `session_id`, `total_cost_usd` y
  `usage`, tal como asumía D1.

Uso: python scripts/spike_claude_headless.py
"""
from __future__ import annotations

import json
import queue
import subprocess
import sys
import threading


def _mensaje_usuario(texto: str) -> str:
    return json.dumps(
        {
            "type": "user",
            "message": {"role": "user", "content": [{"type": "text", "text": texto}]},
        }
    )


def _leer_stdout(proc: subprocess.Popen, turnos: "queue.Queue[str]") -> None:
    buffer_actual: list[str] = []
    for linea in proc.stdout:
        linea = linea.strip()
        if not linea:
            continue
        try:
            evento = json.loads(linea)
        except json.JSONDecodeError:
            print(f"[linea no-json] {linea}")
            continue

        tipo = evento.get("type")
        if tipo == "stream_event":
            sub = evento.get("event", {})
            if sub.get("type") == "content_block_delta":
                delta = sub.get("delta", {})
                texto = delta.get("text", "")
                if texto:
                    print(texto, end="", flush=True)
                    buffer_actual.append(texto)
        elif tipo == "result":
            print()
            turnos.put("".join(buffer_actual))
            buffer_actual = []
        elif tipo not in ("system", "assistant", "user", "rate_limit_event"):
            print(f"[evento {tipo}] {json.dumps(evento)[:200]}")


def main() -> int:
    persona = (
        "Sos Loki, un asistente de voz conciso en espanol neutro. "
        "Respondes en una sola oracion corta, sin usar herramientas de archivos "
        "ni de memoria, salvo que se te pida explicitamente ejecutar una accion."
    )
    cmd = [
        "claude",
        "-p",
        "--input-format",
        "stream-json",
        "--output-format",
        "stream-json",
        "--include-partial-messages",
        "--verbose",
        "--model",
        "haiku",
        "--permission-mode",
        "manual",
        "--permission-prompts",
        "none",
        "--system-prompt",
        persona,
        "--setting-sources",
        "project",
    ]
    print(f"Lanzando: {' '.join(cmd)}")
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        bufsize=1,
    )

    turnos: "queue.Queue[str]" = queue.Queue()
    hilo = threading.Thread(target=_leer_stdout, args=(proc, turnos), daemon=True)
    hilo.start()

    numero_secreto = "4217"
    proc.stdin.write(
        _mensaje_usuario(
            f"Recorda este numero secreto: {numero_secreto}. "
            "Respondeme en una sola oracion confirmando que lo guardaste, sin repetirlo."
        )
        + "\n"
    )
    proc.stdin.flush()

    try:
        primera_respuesta = turnos.get(timeout=60)
    except queue.Empty:
        print("TIMEOUT esperando el primer turno", file=sys.stderr)
        proc.kill()
        return 1

    proc.stdin.write(
        _mensaje_usuario("Que numero te pedi que recordaras? Respondeme solo con el numero.") + "\n"
    )
    proc.stdin.flush()

    try:
        segunda_respuesta = turnos.get(timeout=60)
    except queue.Empty:
        print("TIMEOUT esperando el segundo turno", file=sys.stderr)
        proc.kill()
        return 1

    proc.stdin.close()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()

    stderr_restante = proc.stderr.read()
    if stderr_restante:
        print(f"[stderr] {stderr_restante}", file=sys.stderr)

    recuerda = numero_secreto in segunda_respuesta
    print(f"Primera respuesta: {primera_respuesta!r}")
    print(f"Segunda respuesta: {segunda_respuesta!r}")
    print(f"--- RESULTADO: {'MULTI-TURNO OK' if recuerda else 'MULTI-TURNO FALLO'} ---")
    return 0 if recuerda else 1


if __name__ == "__main__":
    raise SystemExit(main())
