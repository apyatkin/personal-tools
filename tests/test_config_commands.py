import yaml
from unittest.mock import patch
from click.testing import CliRunner

from hat.cli import main
from hat.config import set_nested


def _setup_company(tmp_path, name="acme"):
    company_dir = tmp_path / "companies" / name
    company_dir.mkdir(parents=True)
    config = {"name": name, "ssh": {"keys": []}, "cloud": {}}
    (company_dir / "config.yaml").write_text(yaml.dump(config))


def test_set_nested_simple():
    config = {}
    set_nested(config, "cloud.nomad.addr", "https://nomad.acme.com")
    assert config["cloud"]["nomad"]["addr"] == "https://nomad.acme.com"


def test_set_nested_append():
    config = {"ssh": {"keys": ["~/.ssh/old"]}}
    set_nested(config, "ssh.keys[+]", "~/.ssh/new")
    assert config["ssh"]["keys"] == ["~/.ssh/old", "~/.ssh/new"]


def test_set_nested_append_creates_list():
    config = {"ssh": {}}
    set_nested(config, "ssh.keys[+]", "~/.ssh/key")
    assert config["ssh"]["keys"] == ["~/.ssh/key"]


def test_config_set_cli(tmp_path, monkeypatch):
    monkeypatch.setenv("HAT_CONFIG_DIR", str(tmp_path))
    _setup_company(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        main, ["config", "set", "acme", "cloud.nomad.addr", "https://nomad.acme.com"]
    )
    assert result.exit_code == 0

    config = yaml.safe_load(
        (tmp_path / "companies" / "acme" / "config.yaml").read_text()
    )
    assert config["cloud"]["nomad"]["addr"] == "https://nomad.acme.com"


def test_config_add_ssh_cli(tmp_path, monkeypatch):
    monkeypatch.setenv("HAT_CONFIG_DIR", str(tmp_path))
    _setup_company(tmp_path)
    key_file = tmp_path / "test_key"
    key_file.write_text("fake-ssh-key")
    runner = CliRunner()
    with patch("hat.platform.store_secret", return_value=True):
        result = runner.invoke(
            main, ["config", "add-ssh", "acme", "acme-sshkey", "-f", str(key_file)]
        )
    assert result.exit_code == 0

    config = yaml.safe_load(
        (tmp_path / "companies" / "acme" / "config.yaml").read_text()
    )
    assert "keychain:acme-sshkey" in config["ssh"]["keys"]


def test_config_add_ssh_appends(tmp_path, monkeypatch):
    monkeypatch.setenv("HAT_CONFIG_DIR", str(tmp_path))
    _setup_company(tmp_path)
    key1 = tmp_path / "key1"
    key1.write_text("fake-key-1")
    key2 = tmp_path / "key2"
    key2.write_text("fake-key-2")
    runner = CliRunner()
    with patch("hat.platform.store_secret", return_value=True):
        runner.invoke(main, ["config", "add-ssh", "acme", "key1", "-f", str(key1)])
        runner.invoke(main, ["config", "add-ssh", "acme", "key2", "-f", str(key2)])

    config = yaml.safe_load(
        (tmp_path / "companies" / "acme" / "config.yaml").read_text()
    )
    assert config["ssh"]["keys"] == ["keychain:key1", "keychain:key2"]
