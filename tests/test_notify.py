from hat.notify import is_enabled, send_notification


def test_not_enabled(tmp_path, monkeypatch):
    monkeypatch.setenv("HAT_CONFIG_DIR", str(tmp_path))
    assert not is_enabled()


def test_enabled(tmp_path, monkeypatch):
    monkeypatch.setenv("HAT_CONFIG_DIR", str(tmp_path))
    (tmp_path / "config.yaml").write_text("notifications: true\n")
    assert is_enabled()


def test_send_disabled(tmp_path, monkeypatch):
    from unittest.mock import patch

    monkeypatch.setenv("HAT_CONFIG_DIR", str(tmp_path))
    with patch("hat.notify.subprocess.Popen") as mock:
        send_notification("test", "msg")
    mock.assert_not_called()
