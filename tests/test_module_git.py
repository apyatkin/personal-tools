from ctx.modules.git import GitModule


def test_git_activate(tmp_path, monkeypatch):
    monkeypatch.setenv("CTX_CONFIG_DIR", str(tmp_path))
    mod = GitModule()
    config = {"identity": {"name": "Alex", "email": "alex@acme.com"}}
    mod.activate(config, secrets={})
    st = mod.status()
    assert st.active
    assert "Alex" in st.details

    env_file = tmp_path / "state.env"
    content = env_file.read_text()
    assert "GIT_AUTHOR_NAME" in content
    assert "GIT_COMMITTER_NAME" in content


def test_git_deactivate(tmp_path, monkeypatch):
    monkeypatch.setenv("CTX_CONFIG_DIR", str(tmp_path))
    mod = GitModule()
    config = {"identity": {"name": "Alex", "email": "alex@acme.com"}}
    mod.activate(config, secrets={})
    mod.deactivate()
    assert not mod.status().active


def test_git_no_identity(tmp_path, monkeypatch):
    monkeypatch.setenv("CTX_CONFIG_DIR", str(tmp_path))
    mod = GitModule()
    mod.activate({}, secrets={})
    assert not mod.status().active
