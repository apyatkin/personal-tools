from __future__ import annotations

import shutil
from pathlib import Path

import yaml

from hat.config import get_config_dir


def migrate_from_ctx() -> list[str]:
    old_dir = Path.home() / ".config" / "ctx"
    new_dir = get_config_dir()
    actions = []

    if not old_dir.exists():
        return ["Nothing to migrate: ~/.config/ctx/ does not exist"]

    # Copy companies
    old_companies = old_dir / "companies"
    if old_companies.exists():
        new_companies = new_dir / "companies"
        new_companies.mkdir(parents=True, exist_ok=True)
        for company_dir in old_companies.iterdir():
            if company_dir.is_dir():
                target = new_companies / company_dir.name
                if target.exists():
                    actions.append(f"Skipped {company_dir.name} (already exists)")
                else:
                    shutil.copytree(company_dir, target)
                    actions.append(f"Copied {company_dir.name}")
                    # Strip tools section
                    config_file = target / "config.yaml"
                    if config_file.exists():
                        config = yaml.safe_load(config_file.read_text())
                        if config and "tools" in config:
                            del config["tools"]
                            config_file.write_text(
                                yaml.dump(
                                    config, default_flow_style=False, sort_keys=False
                                )
                            )
                            actions.append(
                                f"  Removed 'tools' section from {company_dir.name}"
                            )

    # Copy global config
    old_config = old_dir / "config.yaml"
    if old_config.exists():
        new_config = new_dir / "config.yaml"
        if not new_config.exists():
            shutil.copy2(old_config, new_config)
            actions.append("Copied global config.yaml")

    # Copy state
    old_state = old_dir / "state.json"
    if old_state.exists():
        new_state = new_dir / "state.json"
        if not new_state.exists():
            shutil.copy2(old_state, new_state)
            actions.append("Copied state.json")

    actions.append("")
    actions.append("Migration complete. Update your ~/.zshrc:")
    actions.append('  Replace: eval "$(ctx shell-init zsh)"')
    actions.append('  With:    eval "$(hat shell-init zsh)"')

    return actions
