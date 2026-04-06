import yaml
from click.testing import CliRunner
from hat.cli import main


def test_config_add_host(tmp_path, monkeypatch):
    monkeypatch.setenv("HAT_CONFIG_DIR", str(tmp_path))
    company_dir = tmp_path / "companies" / "acme"
    company_dir.mkdir(parents=True)
    (company_dir / "config.yaml").write_text(yaml.dump({"name": "acme", "ssh": {"keys": []}}))

    runner = CliRunner()
    result = runner.invoke(main, ["config", "add-host", "acme", "bastion", "10.0.1.1", "-u", "deploy"])
    assert result.exit_code == 0

    config = yaml.safe_load((company_dir / "config.yaml").read_text())
    assert "bastion" in config["ssh"]["hosts"]
    assert config["ssh"]["hosts"]["bastion"]["address"] == "10.0.1.1"
    assert config["ssh"]["hosts"]["bastion"]["user"] == "deploy"


def test_config_add_host_with_key(tmp_path, monkeypatch):
    monkeypatch.setenv("HAT_CONFIG_DIR", str(tmp_path))
    company_dir = tmp_path / "companies" / "acme"
    company_dir.mkdir(parents=True)
    (company_dir / "config.yaml").write_text(yaml.dump({"name": "acme", "ssh": {}}))

    runner = CliRunner()
    result = runner.invoke(main, ["config", "add-host", "acme", "db", "db.internal", "-u", "postgres", "-k", "acme-db-key"])
    assert result.exit_code == 0

    config = yaml.safe_load((company_dir / "config.yaml").read_text())
    assert config["ssh"]["hosts"]["db"]["key_ref"] == "keychain:acme-db-key"
