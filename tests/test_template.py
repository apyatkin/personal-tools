import yaml
from hat.config import clone_company_config


def test_clone_company_config(tmp_path, monkeypatch):
    monkeypatch.setenv("HAT_CONFIG_DIR", str(tmp_path))
    source_dir = tmp_path / "companies" / "acme"
    source_dir.mkdir(parents=True)
    (source_dir / "config.yaml").write_text(
        yaml.dump(
            {
                "name": "acme",
                "cloud": {
                    "nomad": {
                        "addr": "https://nomad.acme.com",
                        "token_ref": "keychain:acme-token",
                    }
                },
                "ssh": {"keys": ["keychain:acme-key"]},
            }
        )
    )

    path = clone_company_config("acme", "newcorp")
    config = yaml.safe_load(path.read_text())
    assert config["name"] == "newcorp"
    assert config["cloud"]["nomad"]["addr"] == "https://nomad.acme.com"
    assert config["cloud"]["nomad"]["token_ref"] == ""  # cleared
    assert config["ssh"]["keys"] == []  # cleared
