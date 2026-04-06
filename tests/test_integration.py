import json

import yaml
from click.testing import CliRunner

from hat.cli import main


def test_full_lifecycle(tmp_path, monkeypatch):
    monkeypatch.setenv("HAT_CONFIG_DIR", str(tmp_path))

    runner = CliRunner()

    # Init a company
    result = runner.invoke(main, ["init", "acme"])
    assert result.exit_code == 0

    # Write a real config
    config = {
        "name": "acme",
        "description": "Acme Corp",
        "env": {"ACME_ENV": "production", "API_URL": "https://api.acme.com"},
        "git": {
            "identity": {"name": "Alex Pyatkin", "email": "alex@acme.com"},
        },
    }
    config_file = tmp_path / "companies" / "acme" / "config.yaml"
    config_file.write_text(yaml.dump(config))

    # List — should show acme
    result = runner.invoke(main, ["list"])
    assert "acme" in result.output

    # Use acme
    result = runner.invoke(main, ["on", "acme"])
    assert result.exit_code == 0
    assert "Activating acme" in result.output

    # Check state.json
    state = json.loads((tmp_path / "state.json").read_text())
    assert state["active_company"] == "acme"

    # Check state.env has our env vars
    env_content = (tmp_path / "state.env").read_text()
    assert "ACME_ENV" in env_content
    assert "GIT_AUTHOR_NAME" in env_content

    # Status
    result = runner.invoke(main, ["status"])
    assert "acme" in result.output
    assert "env" in result.output

    # Init second company
    runner.invoke(main, ["init", "globex"])
    config2 = {
        "name": "globex",
        "description": "Globex Corp",
        "env": {"GLOBEX_KEY": "abc123"},
    }
    config_file2 = tmp_path / "companies" / "globex" / "config.yaml"
    config_file2.write_text(yaml.dump(config2))

    # Switch to globex — should deactivate acme first
    result = runner.invoke(main, ["on", "globex"])
    assert "Deactivating acme" in result.output
    assert "Activating globex" in result.output

    state = json.loads((tmp_path / "state.json").read_text())
    assert state["active_company"] == "globex"

    # Off
    result = runner.invoke(main, ["off"])
    assert "Deactivating globex" in result.output

    result = runner.invoke(main, ["status"])
    assert "No active context" in result.output
