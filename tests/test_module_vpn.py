from unittest.mock import patch, ANY

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
    with patch("hat.modules.vpn.subprocess.run") as mock_run, \
         patch("hat.modules.vpn.click.confirm"), \
         patch("hat.modules.vpn._find_binary", side_effect=_mock_find):
        mock_run.return_value.returncode = 0
        mod.activate(config, secrets={})
    args = mock_run.call_args
    assert args.args[0] == ["sudo", "wg-quick", "up", "/etc/wireguard/wg-acme.conf"]
    assert args.kwargs["check"] is True


def test_vpn_tailscale_activate():
    mod = VPNModule()
    config = {"provider": "tailscale"}
    with patch("hat.modules.vpn.subprocess.run") as mock_run, \
         patch("hat.modules.vpn.click.confirm"), \
         patch("hat.modules.vpn._find_binary", side_effect=_mock_find):
        mock_run.return_value.returncode = 0
        mod.activate(config, secrets={})
    args = mock_run.call_args
    assert args.args[0] == ["sudo", "tailscale", "up"]
    assert args.kwargs["check"] is True


def test_vpn_deactivate_wireguard():
    mod = VPNModule()
    config = {
        "provider": "wireguard",
        "config": "/etc/wireguard/wg-acme.conf",
        "interface": "wg-acme",
    }
    with patch("hat.modules.vpn.subprocess.run") as mock_run, \
         patch("hat.modules.vpn.click.confirm"), \
         patch("hat.modules.vpn._find_binary", side_effect=_mock_find):
        mock_run.return_value.returncode = 0
        mod.activate(config, secrets={})
        mod.deactivate()
    last_args = mock_run.call_args_list[-1]
    assert last_args.args[0] == ["sudo", "wg-quick", "down", "wg-acme"]


def test_vpn_no_config():
    mod = VPNModule()
    mod.activate({}, secrets={})
    assert not mod.status().active
