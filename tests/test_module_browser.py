from unittest.mock import patch

from hat.modules.browser import BrowserModule


def test_browser_activate():
    mod = BrowserModule()
    config = {"profile": "Acme", "app": "google-chrome"}
    with patch("hat.platform.subprocess.Popen") as mock_popen:
        mod.activate(config, secrets={})
    mock_popen.assert_called_once()
    cmd = mock_popen.call_args.args[0]
    assert "--profile-directory=Acme" in cmd
    assert mod.status().active


def test_browser_no_config():
    mod = BrowserModule()
    mod.activate({}, secrets={})
    assert not mod.status().active


def test_browser_deactivate():
    mod = BrowserModule()
    config = {"profile": "Acme", "app": "google-chrome"}
    with patch("hat.platform.subprocess.Popen"):
        mod.activate(config, secrets={})
    mod.deactivate()
    assert not mod.status().active
