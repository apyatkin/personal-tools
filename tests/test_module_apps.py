from unittest.mock import patch

from hat.modules.apps import AppsModule


def test_apps_activate_slack():
    mod = AppsModule()
    config = {"slack": {"workspace": "acme-corp"}}
    with patch("hat.platform.subprocess.Popen") as mock_popen:
        mod.activate(config, secrets={})
    mock_popen.assert_called_once()
    cmd = mock_popen.call_args.args[0]
    assert "slack://channel?team=acme-corp" in " ".join(cmd)
    assert mod.status().active


def test_apps_no_config():
    mod = AppsModule()
    mod.activate({}, secrets={})
    assert not mod.status().active
