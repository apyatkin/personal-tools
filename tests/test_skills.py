from pathlib import Path
from unittest.mock import patch

import pytest

from ctx.skills import deploy_skills, get_skills_source


def test_get_skills_source(tmp_path, monkeypatch):
    monkeypatch.setenv("CTX_CONFIG_DIR", str(tmp_path))
    config_file = tmp_path / "config.yaml"
    config_file.write_text("skills_source: /path/to/skills\n")
    assert get_skills_source() == Path("/path/to/skills")


def test_get_skills_source_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("CTX_CONFIG_DIR", str(tmp_path))
    with pytest.raises(FileNotFoundError):
        get_skills_source()


def test_deploy_skills(tmp_path, monkeypatch):
    source_dir = tmp_path / "source" / "skills"
    (source_dir / "gitlab").mkdir(parents=True)
    (source_dir / "gitlab" / "SKILL.md").write_text("---\nname: gitlab\n---\n")
    (source_dir / "github").mkdir(parents=True)
    (source_dir / "github" / "SKILL.md").write_text("---\nname: github\n---\n")

    target_dir = tmp_path / "projects"
    target_dir.mkdir()

    results = deploy_skills(source_dir, target_dir)

    assert (target_dir / ".claude" / "skills" / "gitlab").is_symlink()
    assert (target_dir / ".claude" / "skills" / "github").is_symlink()
    assert (target_dir / "CLAUDE.md").exists()
    assert "skills" in (target_dir / "CLAUDE.md").read_text().lower()
    assert len(results) == 2


def test_deploy_skills_updates_existing(tmp_path):
    source_dir = tmp_path / "source" / "skills"
    (source_dir / "gitlab").mkdir(parents=True)
    (source_dir / "gitlab" / "SKILL.md").write_text("---\nname: gitlab\n---\n")

    target_dir = tmp_path / "projects"
    target_dir.mkdir()

    deploy_skills(source_dir, target_dir)
    results = deploy_skills(source_dir, target_dir)
    assert len(results) == 1
    assert (target_dir / ".claude" / "skills" / "gitlab").is_symlink()


from click.testing import CliRunner
from ctx.cli import main


def test_skills_deploy_cli(tmp_path, monkeypatch):
    monkeypatch.setenv("CTX_CONFIG_DIR", str(tmp_path))

    config_file = tmp_path / "config.yaml"
    source_dir = tmp_path / "skills_src"
    (source_dir / "gitlab").mkdir(parents=True)
    (source_dir / "gitlab" / "SKILL.md").write_text("---\nname: gitlab\n---\n")
    config_file.write_text(f"skills_source: {source_dir}\n")

    target = tmp_path / "projects"
    target.mkdir()
    monkeypatch.setattr("ctx.skills.PROJECTS_DIR", target)

    runner = CliRunner()
    result = runner.invoke(main, ["skills", "deploy"])
    assert result.exit_code == 0
    assert "Deployed 1 skills" in result.output
    assert (target / ".claude" / "skills" / "gitlab").is_symlink()
