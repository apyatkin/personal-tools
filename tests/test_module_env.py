from ctx.modules.env import EnvModule


def test_env_activate(tmp_path, monkeypatch):
    monkeypatch.setenv("CTX_CONFIG_DIR", str(tmp_path))
    mod = EnvModule()
    mod.activate({"FOO": "bar", "BAZ": "qux"}, secrets={})
    st = mod.status()
    assert st.active
    assert "FOO" in st.details

    env_file = tmp_path / "state.env"
    assert env_file.exists()
    content = env_file.read_text()
    assert 'export FOO="bar"' in content
    assert 'export BAZ="qux"' in content


def test_env_deactivate(tmp_path, monkeypatch):
    monkeypatch.setenv("CTX_CONFIG_DIR", str(tmp_path))
    mod = EnvModule()
    mod.activate({"FOO": "bar"}, secrets={})
    mod.deactivate()
    assert not mod.status().active
    env_file = tmp_path / "state.env"
    assert not env_file.exists() or env_file.read_text() == ""


def test_env_empty_config(tmp_path, monkeypatch):
    monkeypatch.setenv("CTX_CONFIG_DIR", str(tmp_path))
    mod = EnvModule()
    mod.activate({}, secrets={})
    assert not mod.status().active
