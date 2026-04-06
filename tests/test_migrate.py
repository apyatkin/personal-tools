from hat.migrate import migrate_from_ctx


def test_migrate_nothing(tmp_path, monkeypatch):
    monkeypatch.setenv("HAT_CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr("hat.migrate.Path.home", lambda: tmp_path)
    actions = migrate_from_ctx()
    assert any("Nothing to migrate" in a for a in actions)


def test_migrate_copies_company(tmp_path, monkeypatch):
    monkeypatch.setenv("HAT_CONFIG_DIR", str(tmp_path / "hat"))
    # Create old config
    old_dir = tmp_path / ".config" / "ctx" / "companies" / "acme"
    old_dir.mkdir(parents=True)
    (old_dir / "config.yaml").write_text("name: acme\ntools:\n  brew:\n    - kubectl\n")
    monkeypatch.setattr("hat.migrate.Path.home", lambda: tmp_path)

    actions = migrate_from_ctx()
    assert any("Copied acme" in a for a in actions)
    assert any("tools" in a.lower() for a in actions)

    # Check tools section removed
    import yaml

    new_config = yaml.safe_load(
        (tmp_path / "hat" / "companies" / "acme" / "config.yaml").read_text()
    )
    assert "tools" not in new_config
