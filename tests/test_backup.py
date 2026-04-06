from pathlib import Path
from hat.backup import create_backup, restore_backup


def test_create_backup(tmp_path, monkeypatch):
    monkeypatch.setenv("HAT_CONFIG_DIR", str(tmp_path / "hat"))
    config_dir = tmp_path / "hat" / "companies" / "acme"
    config_dir.mkdir(parents=True)
    (config_dir / "config.yaml").write_text("name: acme\n")
    (tmp_path / "hat" / "state.json").write_text("{}")  # should be excluded

    output = create_backup(tmp_path / "backups")
    assert output.exists()
    assert "hat-backup-" in output.name

    import tarfile
    with tarfile.open(output) as tar:
        names = tar.getnames()
        assert any("acme" in n for n in names)
        assert not any("state.json" in n for n in names)


def test_restore_backup(tmp_path, monkeypatch):
    # Create a backup first
    monkeypatch.setenv("HAT_CONFIG_DIR", str(tmp_path / "hat"))
    config_dir = tmp_path / "hat" / "companies" / "acme"
    config_dir.mkdir(parents=True)
    (config_dir / "config.yaml").write_text("name: acme\n")
    output = create_backup(tmp_path)

    # Wipe and restore
    import shutil
    shutil.rmtree(tmp_path / "hat")
    actions = restore_backup(output)
    assert (tmp_path / "hat" / "companies" / "acme" / "config.yaml").exists()
