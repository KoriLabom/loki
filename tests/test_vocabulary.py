from pathlib import Path
from unittest.mock import patch

from loki.audio.vocabulary import load_vocabulary


def test_parses_valid_file_with_comments_and_blanks(tmp_path):
    f = tmp_path / "vocab.txt"
    f.write_text(
        "# Comentario\n"
        "Claude Code\n"
        "\n"
        "Groq\n"
        "  OpenSpec  \n",
        encoding="utf-8",
    )
    assert load_vocabulary(str(f)) == ["Claude Code", "Groq", "OpenSpec"]


def test_returns_empty_when_file_missing(tmp_path):
    missing = tmp_path / "nope.txt"
    assert load_vocabulary(str(missing)) == []


def test_returns_empty_for_empty_file(tmp_path):
    f = tmp_path / "empty.txt"
    f.write_text("", encoding="utf-8")
    assert load_vocabulary(str(f)) == []


def test_returns_empty_for_comments_and_blanks_only(tmp_path):
    f = tmp_path / "only_comments.txt"
    f.write_text("# nada\n\n   \n# tampoco\n", encoding="utf-8")
    assert load_vocabulary(str(f)) == []


def test_deduplicates_preserving_first_occurrence(tmp_path):
    f = tmp_path / "dup.txt"
    f.write_text("Claude Code\nGroq\nClaude Code\nOpenSpec\nGroq\n", encoding="utf-8")
    assert load_vocabulary(str(f)) == ["Claude Code", "Groq", "OpenSpec"]


def test_env_var_overrides_default(tmp_path, monkeypatch):
    f = tmp_path / "from_env.txt"
    f.write_text("Anthropic\n", encoding="utf-8")
    monkeypatch.setenv("VOICE_VOCABULARY_PATH", str(f))
    assert load_vocabulary() == ["Anthropic"]


def test_explicit_path_beats_env(tmp_path, monkeypatch):
    env_file = tmp_path / "env.txt"
    env_file.write_text("Anthropic\n", encoding="utf-8")
    arg_file = tmp_path / "arg.txt"
    arg_file.write_text("Groq\n", encoding="utf-8")
    monkeypatch.setenv("VOICE_VOCABULARY_PATH", str(env_file))
    assert load_vocabulary(str(arg_file)) == ["Groq"]


def test_default_path_is_next_to_script(monkeypatch, tmp_path):
    monkeypatch.delenv("VOICE_VOCABULARY_PATH", raising=False)
    fake_default = tmp_path / "vocabulary.txt"
    fake_default.write_text("PyQt6\n", encoding="utf-8")
    with patch("loki.audio.vocabulary._default_path", return_value=str(fake_default)):
        assert load_vocabulary() == ["PyQt6"]


def test_returns_empty_when_read_fails(tmp_path, monkeypatch):
    f = tmp_path / "vocab.txt"
    f.write_text("Claude Code\n", encoding="utf-8")

    real_open = Path.open

    def boom(self, *args, **kwargs):
        if str(self) == str(f):
            raise PermissionError("denied")
        return real_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", boom)
    assert load_vocabulary(str(f)) == []
