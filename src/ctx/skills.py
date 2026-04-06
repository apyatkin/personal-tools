from __future__ import annotations

from pathlib import Path

import yaml

from ctx.config import get_config_dir

PROJECTS_DIR = Path.home() / "projects"

CLAUDE_MD_CONTENT = """\
# Projects

Skills in `.claude/skills/` are available for all company work.
Active company config is at `~/.config/ctx/companies/<name>/config.yaml`.
"""


def get_skills_source() -> Path:
    config_file = get_config_dir() / "config.yaml"
    if not config_file.exists():
        raise FileNotFoundError(
            f"Global config not found: {config_file}\n"
            f"Create it with:\n  skills_source: /path/to/your/skills"
        )
    with open(config_file) as f:
        config = yaml.safe_load(f)
    source = config.get("skills_source")
    if not source:
        raise FileNotFoundError("skills_source not set in global config")
    return Path(source)


def deploy_skills(
    source_dir: Path,
    target_dir: Path | None = None,
) -> list[str]:
    if target_dir is None:
        target_dir = PROJECTS_DIR

    skills_target = target_dir / ".claude" / "skills"
    skills_target.mkdir(parents=True, exist_ok=True)

    claude_md = target_dir / "CLAUDE.md"
    if not claude_md.exists():
        claude_md.write_text(CLAUDE_MD_CONTENT)

    deployed = []
    for skill_dir in sorted(source_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        if not (skill_dir / "SKILL.md").exists():
            continue

        link = skills_target / skill_dir.name
        if link.is_symlink():
            link.unlink()
        elif link.exists():
            continue

        link.symlink_to(skill_dir)
        deployed.append(skill_dir.name)

    return deployed
