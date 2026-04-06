from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def get_config_dir() -> Path:
    import os

    env = os.environ.get("CTX_CONFIG_DIR")
    if env:
        return Path(env)
    return Path.home() / ".config" / "ctx"


def load_company_config(name: str) -> dict[str, Any]:
    config_file = get_config_dir() / "companies" / name / "config.yaml"
    if not config_file.exists():
        raise FileNotFoundError(f"Company config not found: {config_file}")
    with open(config_file) as f:
        return yaml.safe_load(f)


def list_companies() -> list[str]:
    companies_dir = get_config_dir() / "companies"
    if not companies_dir.exists():
        return []
    return sorted(
        d.name
        for d in companies_dir.iterdir()
        if d.is_dir() and (d / "config.yaml").exists()
    )
