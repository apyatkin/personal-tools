from pathlib import Path

import pytest
import yaml


SKILLS_DIR = Path(__file__).parent.parent / "skills"

EXPECTED_SKILLS = [
    "ansible",
    "consul",
    "docker",
    "favro",
    "github",
    "gitlab",
    "helm",
    "jira",
    "kubernetes",
    "nomad",
    "terraform",
    "vault",
]


def test_all_skills_exist():
    for name in EXPECTED_SKILLS:
        skill_file = SKILLS_DIR / name / "SKILL.md"
        assert skill_file.exists(), f"Missing skill: {name}"


@pytest.mark.parametrize("skill_name", EXPECTED_SKILLS)
def test_skill_has_valid_frontmatter(skill_name):
    skill_file = SKILLS_DIR / skill_name / "SKILL.md"
    content = skill_file.read_text()

    assert content.startswith("---"), f"{skill_name}: missing frontmatter"

    parts = content.split("---", 2)
    assert len(parts) >= 3, f"{skill_name}: invalid frontmatter format"

    fm = yaml.safe_load(parts[1])
    assert "name" in fm, f"{skill_name}: missing 'name' in frontmatter"
    assert "description" in fm, f"{skill_name}: missing 'description' in frontmatter"
    assert fm["name"] == skill_name, f"{skill_name}: name mismatch"


@pytest.mark.parametrize("skill_name", EXPECTED_SKILLS)
def test_skill_has_required_sections(skill_name):
    skill_file = SKILLS_DIR / skill_name / "SKILL.md"
    content = skill_file.read_text()

    assert "## Company Context" in content, (
        f"{skill_name}: missing Company Context section"
    )
    assert "## Commands" in content, f"{skill_name}: missing Commands section"
    assert "## Runbooks" in content, f"{skill_name}: missing Runbooks section"
    assert "active_company" in content, (
        f"{skill_name}: missing ctx config reading instructions"
    )
