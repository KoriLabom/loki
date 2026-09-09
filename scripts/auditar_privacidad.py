"""Auditoría de privacidad del diff antes de publicar (D13, spec
privacidad-del-repositorio).

Busca en las líneas agregadas del diff: rutas de usuario de Windows y
macOS, correos, patrones de keys/tokens, y los términos de la lista
privada de `config.local.yaml`. Termina con código distinto de cero si
encuentra algo.

Uso: python scripts/auditar_privacidad.py [rango-de-git]
Por defecto compara la rama actual contra origin/main.
Con `--arbol`, audita todo el árbol de trabajo en vez de un diff (pensado
para correr una sola vez antes del primer push a un repo público).
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

import yaml

_PATRON_RUTA_WINDOWS = re.compile(r"[A-Za-z]:[\\/]Users[\\/][^\\/\s\"']+", re.IGNORECASE)
_PATRON_RUTA_MACOS = re.compile(r"/Users/[^/\s\"']+")
_PATRON_CORREO = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_PATRON_KEY = re.compile(r"\b(sk-[A-Za-z0-9_-]{10,}|gsk_[A-Za-z0-9_-]{10,}|ghp_[A-Za-z0-9_-]{10,})\b")
_PATRON_KEY_GENERICA = re.compile(
    r"\b\w*(?:key|token|secret)\w*\s*[:=]\s*['\"]?[A-Za-z0-9+/_.-]{16,}['\"]?", re.IGNORECASE
)


class Hallazgo(NamedTuple):
    archivo: str
    linea: int
    tipo: str
    detalle: str


def _lineas_agregadas(diff_texto: str):
    """Genera (archivo, número de línea en la versión nueva, contenido)
    para cada línea agregada de un diff unificado de git."""
    archivo_actual: str | None = None
    numero_linea = 0
    for linea in diff_texto.splitlines():
        if linea.startswith("+++ "):
            ruta = linea[4:].strip()
            if ruta.startswith("b/"):
                ruta = ruta[2:]
            archivo_actual = None if ruta == "/dev/null" else ruta
            continue
        if linea.startswith("@@"):
            m = re.search(r"\+(\d+)", linea)
            numero_linea = int(m.group(1)) if m else 0
            continue
        if linea.startswith("+++") or linea.startswith("---"):
            continue
        if linea.startswith("+"):
            if archivo_actual is not None:
                yield archivo_actual, numero_linea, linea[1:]
            numero_linea += 1
        elif linea.startswith("-"):
            continue
        elif not linea.startswith("\\"):
            numero_linea += 1


def _cargar_terminos_privados(raiz: Path) -> list[str]:
    ruta = raiz / "config.local.yaml"
    if not ruta.exists():
        return []
    datos = yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}
    return [t for t in datos.get("terminos_privados", []) if t]


def _hallazgos_en_lineas(lineas_iter, terminos_privados: list[str]) -> list[Hallazgo]:
    hallazgos: list[Hallazgo] = []
    for archivo, numero, contenido in lineas_iter:
        if _PATRON_RUTA_WINDOWS.search(contenido):
            hallazgos.append(Hallazgo(archivo, numero, "ruta_windows", contenido.strip()))
        if _PATRON_RUTA_MACOS.search(contenido):
            hallazgos.append(Hallazgo(archivo, numero, "ruta_macos", contenido.strip()))
        if _PATRON_CORREO.search(contenido):
            hallazgos.append(Hallazgo(archivo, numero, "correo", contenido.strip()))
        if _PATRON_KEY.search(contenido) or _PATRON_KEY_GENERICA.search(contenido):
            hallazgos.append(Hallazgo(archivo, numero, "posible_key_o_token", contenido.strip()))
        for termino in terminos_privados:
            if termino.lower() in contenido.lower():
                # No se imprime la línea completa ni la lista de términos:
                # ambas cosas podrían ser justamente el dato privado.
                hallazgos.append(Hallazgo(archivo, numero, "termino_privado", "(oculto)"))
    return hallazgos


def auditar(diff_texto: str, terminos_privados: list[str] | None = None) -> list[Hallazgo]:
    return _hallazgos_en_lineas(_lineas_agregadas(diff_texto), terminos_privados or [])


def _archivos_del_arbol(raiz: Path) -> list[str]:
    """Todo lo que entraría en el próximo commit: lo ya trackeado más lo
    nuevo que no está ignorado (no solo lo modificado)."""
    resultado = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        capture_output=True, text=True, encoding="utf-8", cwd=raiz,
    )
    return [l for l in resultado.stdout.splitlines() if l]


def _lineas_de_archivo(raiz: Path, archivos: list[str]):
    for archivo in archivos:
        ruta = raiz / archivo
        try:
            texto = ruta.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue  # binario o ilegible: no es texto que pueda filtrar datos por patrón
        for numero, contenido in enumerate(texto.splitlines(), start=1):
            yield archivo, numero, contenido


def auditar_arbol(raiz: Path, terminos_privados: list[str] | None = None) -> list[Hallazgo]:
    """Audita todo el árbol de trabajo (no solo un diff): pensado para
    correr una vez antes del primer push a un repo público."""
    archivos = _archivos_del_arbol(raiz)
    return _hallazgos_en_lineas(_lineas_de_archivo(raiz, archivos), terminos_privados or [])


def _obtener_diff(rango: str) -> str:
    resultado = subprocess.run(
        ["git", "diff", rango], capture_output=True, text=True, encoding="utf-8"
    )
    return resultado.stdout


def _rango_por_defecto() -> str:
    rama = subprocess.run(
        ["git", "branch", "--show-current"], capture_output=True, text=True, encoding="utf-8"
    ).stdout.strip()
    return f"origin/main...{rama}" if rama else "origin/main"


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    raiz = Path.cwd()
    terminos_privados = _cargar_terminos_privados(raiz)

    if argv and argv[0] == "--arbol":
        hallazgos = auditar_arbol(raiz, terminos_privados)
    else:
        rango = argv[0] if argv else _rango_por_defecto()
        diff_texto = _obtener_diff(rango)
        hallazgos = auditar(diff_texto, terminos_privados)

    if not hallazgos:
        print("Auditoría de privacidad: sin hallazgos.")
        return 0

    for h in hallazgos:
        if h.tipo == "termino_privado":
            print(f"{h.archivo}:{h.linea}: término privado configurado encontrado")
        else:
            print(f"{h.archivo}:{h.linea}: {h.tipo}: {h.detalle}")
    print(f"\n{len(hallazgos)} hallazgo(s). Revisá el diff antes de publicar.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
