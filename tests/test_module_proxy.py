from ctx.modules.proxy import ProxyModule


def test_proxy_activate(tmp_path, monkeypatch):
    monkeypatch.setenv("CTX_CONFIG_DIR", str(tmp_path))
    mod = ProxyModule()
    config = {
        "http": "http://proxy.acme.com:3128",
        "https": "http://proxy.acme.com:3128",
        "no_proxy": "*.acme.internal,10.0.0.0/8",
    }
    mod.activate(config, secrets={})
    env_file = tmp_path / "state.env"
    content = env_file.read_text()
    assert "HTTP_PROXY" in content
    assert "HTTPS_PROXY" in content
    assert "NO_PROXY" in content
    assert mod.status().active


def test_proxy_deactivate(tmp_path, monkeypatch):
    monkeypatch.setenv("CTX_CONFIG_DIR", str(tmp_path))
    mod = ProxyModule()
    config = {"http": "http://proxy.acme.com:3128"}
    mod.activate(config, secrets={})
    mod.deactivate()
    assert not mod.status().active


def test_proxy_no_config():
    mod = ProxyModule()
    mod.activate({}, secrets={})
    assert not mod.status().active
