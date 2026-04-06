from unittest.mock import patch

from hat.modules.cloud import CloudModule


def test_cloud_env_vars(tmp_path, monkeypatch):
    monkeypatch.setenv("HAT_CONFIG_DIR", str(tmp_path))
    mod = CloudModule()
    config = {
        "nomad": {
            "addr": "https://nomad.acme.com:4646",
            "token_ref": "keychain:nomad-token",
        },
        "vault": {"addr": "https://vault.acme.com:8200"},
        "consul": {"addr": "https://consul.acme.com:8500"},
        "hetzner": {"token_ref": "keychain:hcloud-token"},
        "kubernetes": {"kubeconfig": "~/.config/ctx/companies/acme/kubeconfig"},
    }
    secrets = {
        "keychain:nomad-token": "s3cret",
        "keychain:hcloud-token": "hetzner123",
    }
    with patch("hat.modules.cloud.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mod.activate(config, secrets)

    env_file = tmp_path / "state.env"
    content = env_file.read_text()
    assert 'NOMAD_ADDR="https://nomad.acme.com:4646"' in content
    assert 'NOMAD_TOKEN="s3cret"' in content
    assert 'VAULT_ADDR="https://vault.acme.com:8200"' in content
    assert 'CONSUL_HTTP_ADDR="https://consul.acme.com:8500"' in content
    assert 'HCLOUD_TOKEN="hetzner123"' in content
    assert "KUBECONFIG" in content


def test_cloud_yandex_profile():
    mod = CloudModule()
    config = {"yandex": {"profile": "acme"}}
    with patch("hat.modules.cloud.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mod.activate(config, secrets={})
    mock_run.assert_any_call(
        ["yc", "config", "profile", "activate", "acme"],
        capture_output=True,
        text=True,
    )


def test_cloud_digitalocean_context():
    mod = CloudModule()
    config = {"digitalocean": {"context": "acme"}}
    with patch("hat.modules.cloud.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mod.activate(config, secrets={})
    mock_run.assert_any_call(
        ["doctl", "auth", "switch", "--context", "acme"],
        capture_output=True,
        text=True,
    )


def test_cloud_aws_sso():
    mod = CloudModule()
    config = {"aws": {"profile": "acme-prod", "sso": True}}
    with patch("hat.modules.cloud.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mod.activate(config, secrets={})
    mock_run.assert_any_call(
        ["aws", "sso", "login", "--profile", "acme-prod"],
        capture_output=True,
        text=True,
    )


def test_cloud_no_config():
    mod = CloudModule()
    mod.activate({}, secrets={})
    assert not mod.status().active
