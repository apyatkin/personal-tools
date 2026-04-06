from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

VALID_NAME_RE = re.compile(r"^[a-zA-Z0-9_-]+$")


def validate_company_name(name: str) -> None:
    if not VALID_NAME_RE.match(name):
        raise ValueError(
            f"Invalid company name '{name}'. Use only letters, numbers, hyphens, underscores."
        )


def get_config_dir() -> Path:
    import os

    env = os.environ.get("HAT_CONFIG_DIR")
    if env:
        return Path(env)
    from hat.platform import get_default_config_dir

    return get_default_config_dir()


def _deep_merge(base: dict, override: dict) -> dict:
    """Deep merge override into base. Override values win."""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_company_config(name: str) -> dict[str, Any]:
    """Load company config. Supports profiles: 'acme/staging'."""
    validate_company_name(name.split("/")[0])

    config_dir = get_config_dir() / "companies"

    if "/" in name:
        company, profile = name.split("/", 1)
        base_file = config_dir / company / "config.yaml"
        profile_file = config_dir / company / f"{profile}.yaml"

        if not base_file.exists():
            raise FileNotFoundError(f"Company config not found: {base_file}")

        with open(base_file) as f:
            config = yaml.safe_load(f) or {}

        # Handle inheritance on base config
        extends = config.get("extends")
        if extends:
            base_config = load_company_config(extends)
            base_config.pop("extends", None)
            base_config.pop("name", None)
            config = _deep_merge(base_config, config)

        if profile_file.exists():
            with open(profile_file) as f:
                profile_config = yaml.safe_load(f) or {}
            config = _deep_merge(config, profile_config)
        else:
            raise FileNotFoundError(f"Profile not found: {profile_file}")

        return config

    config_file = config_dir / name / "config.yaml"
    if not config_file.exists():
        raise FileNotFoundError(f"Company config not found: {config_file}")
    with open(config_file) as f:
        config = yaml.safe_load(f) or {}

    # Handle inheritance
    extends = config.get("extends")
    if extends:
        base_config = load_company_config(extends)
        base_config.pop("extends", None)
        base_config.pop("name", None)
        config = _deep_merge(base_config, config)

    return config


def save_company_config(name: str, config: dict[str, Any]) -> None:
    validate_company_name(name)
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
    validate_company_name(source)
    validate_company_name(target)
    config = load_company_config(source)
    config["name"] = target
    # Clear secrets
    _clear_refs(config)
    if "ssh" in config:
        config["ssh"]["keys"] = []
    save_company_config(target, config)
    return get_config_dir() / "companies" / target / "config.yaml"
