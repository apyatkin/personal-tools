import yaml
from click.testing import CliRunner
from hat.cli import main


def test_ssh_add_host(tmp_path, monkeypatch):
    monkeypatch.setenv("HAT_CONFIG_DIR", str(tmp_path))
    company_dir = tmp_path / "companies" / "acme"
    company_dir.mkdir(parents=True)
    (company_dir / "config.yaml").write_text(
        yaml.dump({"name": "acme", "ssh": {"keys": []}})
    )

    runner = CliRunner()
    result = runner.invoke(
        main, ["ssh", "add", "acme", "bastion", "10.0.1.1", "-u", "deploy"]
    )
    assert result.exit_code == 0

    config = yaml.safe_load((company_dir / "config.yaml").read_text())
    assert "bastion" in config["ssh"]["hosts"]
    assert config["ssh"]["hosts"]["bastion"]["address"] == "10.0.1.1"
    assert config["ssh"]["hosts"]["bastion"]["user"] == "deploy"


def test_ssh_add_host_with_key_and_port(tmp_path, monkeypatch):
    monkeypatch.setenv("HAT_CONFIG_DIR", str(tmp_path))
    company_dir = tmp_path / "companies" / "acme"
    company_dir.mkdir(parents=True)
    (company_dir / "config.yaml").write_text(yaml.dump({"name": "acme", "ssh": {}}))

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "ssh",
            "add",
            "acme",
            "db",
            "db.internal",
            "-u",
            "postgres",
            "-p",
            "5432",
            "-k",
            "acme-db-key",
        ],
    )
    assert result.exit_code == 0

    config = yaml.safe_load((company_dir / "config.yaml").read_text())
    assert config["ssh"]["hosts"]["db"]["key_ref"] == "keychain:acme-db-key"
    assert config["ssh"]["hosts"]["db"]["port"] == 5432


def test_ssh_hosts_list(tmp_path, monkeypatch):
    monkeypatch.setenv("HAT_CONFIG_DIR", str(tmp_path))
    company_dir = tmp_path / "companies" / "acme"
    company_dir.mkdir(parents=True)
    (company_dir / "config.yaml").write_text(
        yaml.dump(
            {
                "name": "acme",
                "ssh": {
                    "default_user": "deploy",
                    "hosts": {
                        "bastion": {"address": "10.0.1.1"},
                        "web": {"address": "10.0.1.10", "user": "root", "port": 2222},
                    },
                },
            }
        )
    )

    runner = CliRunner()
    result = runner.invoke(main, ["ssh", "list", "acme"])
    assert result.exit_code == 0
    assert "bastion" in result.output
    assert "10.0.1.10" in result.output
    assert "port=2222" in result.output
    assert "user=root" in result.output


def test_ssh_remove_host(tmp_path, monkeypatch):
    monkeypatch.setenv("HAT_CONFIG_DIR", str(tmp_path))
    company_dir = tmp_path / "companies" / "acme"
    company_dir.mkdir(parents=True)
    (company_dir / "config.yaml").write_text(
        yaml.dump(
            {
                "name": "acme",
                "ssh": {"hosts": {"old": {"address": "1.2.3.4"}}},
            }
        )
    )

    runner = CliRunner()
    result = runner.invoke(main, ["ssh", "remove", "acme", "old"])
    assert result.exit_code == 0

    config = yaml.safe_load((company_dir / "config.yaml").read_text())
    assert "old" not in config["ssh"]["hosts"]


def test_ssh_config_set_defaults(tmp_path, monkeypatch):
    monkeypatch.setenv("HAT_CONFIG_DIR", str(tmp_path))
    company_dir = tmp_path / "companies" / "acme"
    company_dir.mkdir(parents=True)
    (company_dir / "config.yaml").write_text(yaml.dump({"name": "acme", "ssh": {}}))

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "ssh",
            "config",
            "acme",
            "--default-user",
            "deploy",
            "--default-key",
            "acme-sshkey",
        ],
    )
    assert result.exit_code == 0
    assert "deploy" in result.output

    config = yaml.safe_load((company_dir / "config.yaml").read_text())
    assert config["ssh"]["default_user"] == "deploy"
    assert config["ssh"]["default_key_ref"] == "keychain:acme-sshkey"


def test_ssh_config_set_jump(tmp_path, monkeypatch):
    monkeypatch.setenv("HAT_CONFIG_DIR", str(tmp_path))
    company_dir = tmp_path / "companies" / "acme"
    company_dir.mkdir(parents=True)
    (company_dir / "config.yaml").write_text(yaml.dump({"name": "acme", "ssh": {}}))

    runner = CliRunner()
    result = runner.invoke(
        main, ["ssh", "config", "acme", "--jump", "deploy@bastion.acme.com"]
    )
    assert result.exit_code == 0

    config = yaml.safe_load((company_dir / "config.yaml").read_text())
    assert config["ssh"]["jump_host"] == "bastion.acme.com"
    assert config["ssh"]["jump_user"] == "deploy"
