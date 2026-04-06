from hat.doctor import run_checks, _check_tools


def test_doctor_valid_config(tmp_path, monkeypatch):
    monkeypatch.setenv("HAT_CONFIG_DIR", str(tmp_path))
    company_dir = tmp_path / "companies" / "acme"
    company_dir.mkdir(parents=True)
    (company_dir / "config.yaml").write_text("name: acme\nenv:\n  FOO: bar\n")
    results = run_checks("acme")
    assert any(r.level == "ok" and "config" in r.name.lower() for r in results)


def test_doctor_missing_config(tmp_path, monkeypatch):
    monkeypatch.setenv("HAT_CONFIG_DIR", str(tmp_path))
    results = run_checks("nonexistent")
    assert any(r.level == "error" for r in results)


def test_check_tools_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("HAT_CONFIG_DIR", str(tmp_path))
    results = _check_tools()
    assert any("tools" in r.name for r in results)
