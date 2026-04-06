import os
from unittest.mock import patch, call, MagicMock

from hat.modules.ssh import SSHModule


def test_ssh_activate_adds_file_keys():
    mod = SSHModule()
    config = {"keys": ["~/.ssh/acme_ed25519", "~/.ssh/acme_bastion"]}
    with patch("hat.modules.ssh.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mod.activate(config, secrets={})
    expected_calls = [
        call(["ssh-add", "~/.ssh/acme_ed25519"], capture_output=True, text=True),
        call(["ssh-add", "~/.ssh/acme_bastion"], capture_output=True, text=True),
    ]
    assert mock_run.call_args_list == expected_calls
    assert mod.status().active


def test_ssh_activate_keychain_key():
    mod = SSHModule()
    config = {"keys": ["keychain:acme-sshkey"]}
    secrets = {"keychain:acme-sshkey": "-----BEGIN OPENSSH PRIVATE KEY-----\nfake\n-----END OPENSSH PRIVATE KEY-----\n"}
    with patch("hat.modules.ssh.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mod.activate(config, secrets)

    # Should have called ssh-add with a temp file path
    add_call = mock_run.call_args_list[0]
    temp_path = add_call.args[0][1]
    assert temp_path.startswith("/") and "hat-ssh-" in temp_path
    assert mod.status().active
    assert len(mod._temp_files) == 1


def test_ssh_deactivate_removes_file_keys():
    mod = SSHModule()
    config = {"keys": ["~/.ssh/acme_ed25519"]}
    with patch("hat.modules.ssh.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mod.activate(config, secrets={})
        mod.deactivate()
    last_call = mock_run.call_args_list[-1]
    assert last_call == call(
        ["ssh-add", "-d", "~/.ssh/acme_ed25519"], capture_output=True, text=True
    )


def test_ssh_deactivate_cleans_temp_files():
    mod = SSHModule()
    config = {"keys": ["keychain:acme-sshkey"]}
    secrets = {"keychain:acme-sshkey": "fake-key-data"}
    with patch("hat.modules.ssh.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mod.activate(config, secrets)
        temp_path = mod._temp_files[0]
        assert os.path.exists(temp_path)
        mod.deactivate()
        assert not os.path.exists(temp_path)


def test_ssh_no_keys():
    mod = SSHModule()
    mod.activate({}, secrets={})
    assert not mod.status().active
