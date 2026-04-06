from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ValidationError:
    path: str
    level: str  # "error" or "warn"
    message: str


VALID_TOP_KEYS = {
    "name",
    "description",
    "tags",
    "git",
    "env",
    "ssh",
    "vpn",
    "dns",
    "hosts",
    "cloud",
    "docker",
    "proxy",
    "browser",
    "apps",
}

VALID_CLOUD_KEYS = {
    "aws",
    "kubernetes",
    "nomad",
    "vault",
    "consul",
    "yandex",
    "digitalocean",
    "hetzner",
    "terraform",
}


def validate_config(config: dict) -> list[ValidationError]:
    errors = []

    if not isinstance(config, dict):
        return [ValidationError("", "error", "Config is not a dict")]

    # Required fields
    if "name" not in config:
        errors.append(ValidationError("name", "error", "Missing required field 'name'"))

    # Unknown top-level keys
    for key in config:
        if key not in VALID_TOP_KEYS:
            errors.append(
                ValidationError(key, "warn", f"Unknown top-level key '{key}'")
            )

    # Type checks
    if "git" in config and not isinstance(config["git"], dict):
        errors.append(ValidationError("git", "error", "Expected dict"))
    if "env" in config and not isinstance(config["env"], dict):
        errors.append(ValidationError("env", "error", "Expected dict"))
    if "ssh" in config and not isinstance(config["ssh"], dict):
        errors.append(ValidationError("ssh", "error", "Expected dict"))
    if "hosts" in config:
        entries = config["hosts"].get("entries", [])
        if not isinstance(entries, list):
            errors.append(ValidationError("hosts.entries", "error", "Expected list"))
    if "cloud" in config and isinstance(config["cloud"], dict):
        for key in config["cloud"]:
            if key not in VALID_CLOUD_KEYS:
                errors.append(
                    ValidationError(
                        f"cloud.{key}", "warn", f"Unknown cloud provider '{key}'"
                    )
                )

    # Validate *_ref format
    _check_refs(config, "", errors)

    return errors


def _check_refs(obj, path: str, errors: list[ValidationError]) -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            full_path = f"{path}.{key}" if path else key
            if key.endswith("_ref") and isinstance(value, str):
                if ":" not in value:
                    errors.append(
                        ValidationError(
                            full_path, "error", f"Invalid ref format: {value}"
                        )
                    )
                else:
                    backend = value.split(":")[0]
                    if backend not in ("keychain", "bitwarden"):
                        errors.append(
                            ValidationError(
                                full_path, "error", f"Unknown backend: {backend}"
                            )
                        )
            else:
                _check_refs(value, full_path, errors)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            _check_refs(item, f"{path}[{i}]", errors)
