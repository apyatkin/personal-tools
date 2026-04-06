from hat.state import StateManager


def test_load_empty_state(tmp_path, monkeypatch):
    monkeypatch.setenv("HAT_CONFIG_DIR", str(tmp_path))
    sm = StateManager()
    assert sm.active_company is None
    assert sm.activated_modules == []


def test_save_and_load_state(tmp_path, monkeypatch):
    monkeypatch.setenv("HAT_CONFIG_DIR", str(tmp_path))
    sm = StateManager()
    sm.set_active("acme", ["secrets", "vpn", "env"])
    sm.save()

    sm2 = StateManager()
    assert sm2.active_company == "acme"
    assert sm2.activated_modules == ["secrets", "vpn", "env"]
    assert sm2.activated_at is not None


def test_clear_state(tmp_path, monkeypatch):
    monkeypatch.setenv("HAT_CONFIG_DIR", str(tmp_path))
    sm = StateManager()
    sm.set_active("acme", ["env"])
    sm.save()
    sm.clear()
    sm.save()
    assert sm.active_company is None

    sm2 = StateManager()
    assert sm2.active_company is None


def test_write_env_file(tmp_path, monkeypatch):
    monkeypatch.setenv("HAT_CONFIG_DIR", str(tmp_path))
    sm = StateManager()
    sm.write_env({"FOO": "bar", "BAZ": "qux with spaces"})
    env_file = tmp_path / "state.env"
    assert env_file.exists()
    content = env_file.read_text()
    assert 'export FOO="bar"' in content
    assert 'export BAZ="qux with spaces"' in content


def test_clear_env_file(tmp_path, monkeypatch):
    monkeypatch.setenv("HAT_CONFIG_DIR", str(tmp_path))
    sm = StateManager()
    sm.write_env({"FOO": "bar"})
    sm.clear_env()
    env_file = tmp_path / "state.env"
    assert not env_file.exists() or env_file.read_text() == ""
