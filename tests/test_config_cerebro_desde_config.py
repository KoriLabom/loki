from pathlib import Path

from loki.cerebro.claude_headless import config_cerebro_desde_config


def test_arma_config_cerebro_desde_el_dict_de_configuracion(tmp_path):
    config = {
        "modelos": {"cerebro": "sonnet"},
        "cerebro": {
            "allowed_tools": ["Bash(orca *)", "mcp__loki__*"],
            "disallowed_tools": ["Bash(orca terminal close*)"],
            "timeout_turno_s": 90,
        },
    }
    persona = tmp_path / "system_prompt.md"
    persona.write_text("Sos Loki.", encoding="utf-8")

    resultado = config_cerebro_desde_config(config, ruta_persona=persona, cwd=tmp_path)

    assert resultado.modelo == "sonnet"
    assert resultado.allowed_tools == ["Bash(orca *)", "mcp__loki__*"]
    assert resultado.disallowed_tools == ["Bash(orca terminal close*)"]
    assert resultado.timeout_turno_s == 90.0
    assert resultado.cwd == tmp_path


def test_usa_defaults_si_faltan_claves(tmp_path):
    persona = tmp_path / "system_prompt.md"
    persona.write_text("Sos Loki.", encoding="utf-8")

    resultado = config_cerebro_desde_config({}, ruta_persona=persona, cwd=tmp_path)

    assert resultado.modelo == "haiku"
    assert resultado.allowed_tools == []
    assert resultado.disallowed_tools == []
    assert resultado.timeout_turno_s == 120.0
