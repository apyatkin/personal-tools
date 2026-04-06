"""Registry of hat-managed secrets. Tracks what hat has stored in Keychain/Bitwarden."""

from __future__ import annotations

import json
import os
from pathlib import Path

from hat.config import get_config_dir


def _registry_path() -> Path:
    return get_config_dir() / "secrets.json"


def register(ref: str) -> None:
    entries = load()
    if ref not in entries:
        entries.append(ref)
        entries.sort()
        path = _registry_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(entries, indent=2) + "\n")
        os.chmod(path, 0o600)


def unregister(ref: str) -> None:
    entries = load()
    if ref in entries:
        entries.remove(ref)
        path = _registry_path()
        path.write_text(json.dumps(entries, indent=2) + "\n")
        os.chmod(path, 0o600)


def load() -> list[str]:
    path = _registry_path()
    if not path.exists():
        return []
    return json.loads(path.read_text())
