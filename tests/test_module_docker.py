from unittest.mock import patch, call

from ctx.modules.docker import DockerModule


def test_docker_activate():
    mod = DockerModule()
    config = {
        "registries": [
            {
                "host": "registry.acme.com",
                "username_ref": "keychain:reg-user",
                "password_ref": "keychain:reg-pass",
            }
        ]
    }
    secrets = {
        "keychain:reg-user": "admin",
        "keychain:reg-pass": "s3cret",
    }
    with patch("ctx.modules.docker.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mod.activate(config, secrets)
    mock_run.assert_called_once_with(
        ["docker", "login", "registry.acme.com",
         "-u", "admin", "--password-stdin"],
        input="s3cret",
        capture_output=True,
        text=True,
    )


def test_docker_deactivate():
    mod = DockerModule()
    config = {
        "registries": [{"host": "registry.acme.com", "username_ref": "keychain:u", "password_ref": "keychain:p"}]
    }
    secrets = {"keychain:u": "a", "keychain:p": "b"}
    with patch("ctx.modules.docker.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mod.activate(config, secrets)
        mod.deactivate()
    last_call = mock_run.call_args_list[-1]
    assert last_call == call(
        ["docker", "logout", "registry.acme.com"],
        capture_output=True, text=True,
    )


def test_docker_no_config():
    mod = DockerModule()
    mod.activate({}, secrets={})
    assert not mod.status().active
