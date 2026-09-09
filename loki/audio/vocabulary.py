import os
from pathlib import Path


def _default_path() -> str:
    return str(Path(__file__).parent / "vocabulary.txt")


def load_vocabulary(path: str | None = None) -> list[str]:
    resolved = path or os.environ.get("VOICE_VOCABULARY_PATH") or _default_path()
    file_path = Path(resolved)
    try:
        with file_path.open("r", encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        return []

    seen: set[str] = set()
    terms: list[str] = []
    for raw in lines:
        term = raw.strip()
        if not term or term.startswith("#"):
            continue
        if term in seen:
            continue
        seen.add(term)
        terms.append(term)
    return terms
