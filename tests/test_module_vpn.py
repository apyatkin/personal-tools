from unittest.mock import patch

from hat.modules.vpn import VPNModule


def _mock_find(name):
    return name


def test_vpn_wireguard_activate():
    mod = VPNModule()
    config = {
        "provider": "wireguard",
        "config": "/etc/wireguard/wg-acme.conf",
        "interface": "wg-acme",
    }
    with (
        patch("hat.modules.vpn.subprocess.run") as mock_run,
        patch("hat.modules.vpn.click.confirm"),
        patch("hat.modules.vpn.find_binary", side_effect=_mock_find),
        patch("hat.modules.vpn.Path") as mock_path,
    ):
        mock_path.return_value.expanduser.return_value.exists.return_value = True
        mock_run.return_value.returncode = 0
        mod.activate(config, secrets={})
    args = mock_run.call_args
    assert args.args[0] == ["sudo", "wg-quick", "up", "/etc/wireguard/wg-acme.conf"]
    assert args.kwargs["check"] is True


def test_vpn_tailscale_activate():
    from unittest.mock import MagicMock

    mod = VPNModule()
    config = {"provider": "tailscale"}

    def fake_run(*args, **kwargs):
        result = MagicMock()
        cmd = args[0]
        if cmd[0] == "tailscale" and cmd[1] == "status":
            # Not connected — status check
            result.returncode = 1
            result.stdout = "stopped"
        else:
            result.returncode = 0
        return result

    with (
        patch("hat.modules.vpn.subprocess.run", side_effect=fake_run),
        patch("hat.modules.vpn.click.confirm"),
        patch("hat.modules.vpn.find_binary", side_effect=_mock_find),
    ):
        mod.activate(config, secrets={})
    assert mod.status().active


def test_vpn_deactivate_wireguard():
    mod = VPNModule()
    config = {
        "provider": "wireguard",
        "config": "/etc/wireguard/wg-acme.conf",
        "interface": "wg-acme",
    }
    with (
        patch("hat.modules.vpn.subprocess.run") as mock_run,
        patch("hat.modules.vpn.click.confirm"),
        patch("hat.modules.vpn.find_binary", side_effect=_mock_find),
        patch("hat.modules.vpn.Path") as mock_path,
    ):
        mock_path.return_value.expanduser.return_value.exists.return_value = True
        mock_run.return_value.returncode = 0
        mod.activate(config, secrets={})
        mod.deactivate()
    last_args = mock_run.call_args_list[-1]
    assert last_args.args[0] == ["sudo", "wg-quick", "down", "wg-acme"]


def test_vpn_no_config():
    mod = VPNModule()
    mod.activate({}, secrets={})
    assert not mod.status().active
