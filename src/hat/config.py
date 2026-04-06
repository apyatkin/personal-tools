from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def get_config_dir() -> Path:
    import os

    env = os.environ.get("HAT_CONFIG_DIR")
    if env:
        return Path(env)
    return Path.home() / "Library" / "hat"


def load_company_config(name: str) -> dict[str, Any]:
    config_file = get_config_dir() / "companies" / name / "config.yaml"
    if not config_file.exists():
        raise FileNotFoundError(f"Company config not found: {config_file}")
    with open(config_file) as f:
        return yaml.safe_load(f)


def save_company_config(name: str, config: dict[str, Any]) -> None:
    config_file = get_config_dir() / "companies" / name / "config.yaml"
    config_file.parent.mkdir(parents=True, exist_ok=True)
    with open(config_file, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)


def set_nested(config: dict, path: str, value: Any) -> None:
    """Set a value at a dotted path. Use [+] to append to a list."""
    parts = path.split(".")
    obj = config
    for part in parts[:-1]:
        if part not in obj:
            obj[part] = {}
        obj = obj[part]
    last = parts[-1]
    if last.endswith("[+]"):
        key = last[:-3]
        if key not in obj:
            obj[key] = []
        obj[key].append(value)
    else:
        obj[last] = value


def list_companies(tag: str | None = None) -> list[str]:
    companies_dir = get_config_dir() / "companies"
    if not companies_dir.exists():
        return []
    names = sorted(
        d.name
        for d in companies_dir.iterdir()
        if d.is_dir() and (d / "config.yaml").exists()
    )
    if tag is None:
        return names
    result = []
    for name in names:
        config = load_company_config(name)
        if tag in config.get("tags", []):
            result.append(name)
    return result


def _clear_refs(obj: Any) -> None:
    if isinstance(obj, dict):
        for key in list(obj.keys()):
            if key.endswith("_ref"):
                obj[key] = ""
            else:
                _clear_refs(obj[key])
    elif isinstance(obj, list):
        for item in obj:
            _clear_refs(item)


def clone_company_config(source: str, target: str) -> Path:
    config = load_company_config(source)
    config["name"] = target
    # Clear secrets
    _clear_refs(config)
    if "ssh" in config:
        config["ssh"]["keys"] = []
    save_company_config(target, config)
    return get_config_dir() / "companies" / target / "config.yaml"
