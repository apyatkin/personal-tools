import json

from click.testing import CliRunner

from hat.cli import main


def _setup_company(tmp_path, name="acme"):
    company_dir = tmp_path / "companies" / name
    company_dir.mkdir(parents=True)
    config = {
        "name": name,
        "description": f"{name} corp",
        "env": {"FOO": "bar"},
        "git": {"identity": {"name": "Alex", "email": "alex@acme.com"}},
    }
    import yaml

    (company_dir / "config.yaml").write_text(yaml.dump(config))
    return company_dir


def test_ctx_list(tmp_path, monkeypatch):
    monkeypatch.setenv("HAT_CONFIG_DIR", str(tmp_path))
    _setup_company(tmp_path, "acme")
    _setup_company(tmp_path, "globex")
    runner = CliRunner()
    result = runner.invoke(main, ["list"])
    assert result.exit_code == 0
    assert "acme" in result.output
    assert "globex" in result.output


def test_ctx_init(tmp_path, monkeypatch):
    monkeypatch.setenv("HAT_CONFIG_DIR", str(tmp_path))
    runner = CliRunner()
    result = runner.invoke(main, ["init", "newcorp"])
    assert result.exit_code == 0
    assert (tmp_path / "companies" / "newcorp" / "config.yaml").exists()


def test_ctx_status_no_active(tmp_path, monkeypatch):
    monkeypatch.setenv("HAT_CONFIG_DIR", str(tmp_path))
    runner = CliRunner()
    result = runner.invoke(main, ["status"])
    assert result.exit_code == 0
    assert "No active context" in result.output


def test_ctx_use_and_status(tmp_path, monkeypatch):
    monkeypatch.setenv("HAT_CONFIG_DIR", str(tmp_path))
    _setup_company(tmp_path, "acme")
    runner = CliRunner()
    result = runner.invoke(main, ["on", "acme"])
    assert result.exit_code == 0

    # Check state was written
    state_file = tmp_path / "state.json"
    assert state_file.exists()
    state = json.loads(state_file.read_text())
    assert state["active_company"] == "acme"

    # Check status shows active
    result = runner.invoke(main, ["status"])
    assert "acme" in result.output


def test_ctx_off(tmp_path, monkeypatch):
    monkeypatch.setenv("HAT_CONFIG_DIR", str(tmp_path))
    _setup_company(tmp_path, "acme")
    runner = CliRunner()
    runner.invoke(main, ["on", "acme"])
    result = runner.invoke(main, ["off"])
    assert result.exit_code == 0

    result = runner.invoke(main, ["status"])
    assert "No active context" in result.output
