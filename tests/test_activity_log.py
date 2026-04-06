from hat.activity_log import log_event, read_log


def test_log_and_read(tmp_path, monkeypatch):
    monkeypatch.setenv("HAT_CONFIG_DIR", str(tmp_path))
    log_event("on", "acme", ["env", "git"])
    log_event("off", "acme")
    entries = read_log()
    assert len(entries) == 2
    assert entries[0]["action"] == "on"
    assert entries[1]["action"] == "off"


def test_log_filter_company(tmp_path, monkeypatch):
    monkeypatch.setenv("HAT_CONFIG_DIR", str(tmp_path))
    log_event("on", "acme")
    log_event("on", "globex")
    entries = read_log(company="acme")
    assert len(entries) == 1
    assert entries[0]["company"] == "acme"


def test_log_limit(tmp_path, monkeypatch):
    monkeypatch.setenv("HAT_CONFIG_DIR", str(tmp_path))
    for i in range(10):
        log_event("on", f"company-{i}")
    entries = read_log(limit=3)
    assert len(entries) == 3
