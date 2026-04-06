from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from hat.config import get_config_dir


class StateManager:
    def __init__(self):
        self._dir = get_config_dir()
        self._state_file = self._dir / "state.json"
        self._env_file = self._dir / "state.env"
        self.active_company: str | None = None
        self.activated_modules: list[str] = []
        self.activated_at: str | None = None
        self._load()

    def _load(self):
        if self._state_file.exists():
            data = json.loads(self._state_file.read_text())
            self.active_company = data.get("active_company")
            self.activated_modules = data.get("activated_modules", [])
            self.activated_at = data.get("activated_at")

    def set_active(self, company: str, modules: list[str]):
        self.active_company = company
        self.activated_modules = modules
        self.activated_at = datetime.now(timezone.utc).isoformat()

    def clear(self):
        self.active_company = None
        self.activated_modules = []
        self.activated_at = None

    def _atomic_write(self, path: Path, content: str):
        """Write atomically: write to temp file, set permissions, rename."""
        tmp_path = path.with_suffix(".tmp")
        tmp_path.write_text(content)
        os.chmod(tmp_path, 0o600)
        os.replace(tmp_path, path)

    def save(self):
        self._dir.mkdir(parents=True, exist_ok=True)
        data = {
            "active_company": self.active_company,
            "activated_modules": self.activated_modules,
            "activated_at": self.activated_at,
        }
        self._atomic_write(self._state_file, json.dumps(data, indent=2) + "\n")
        self.write_active_file()

    def write_env(self, env_vars: dict[str, str]):
        self._dir.mkdir(parents=True, exist_ok=True)
        lines = [f'export {k}="{v}"' for k, v in sorted(env_vars.items())]
        self._atomic_write(self._env_file, "\n".join(lines) + "\n")

    def write_active_file(self):
        """Write active company name to a flat file for fast shell hook reading."""
        active_file = self._dir / "active"
        if self.active_company:
            self._atomic_write(active_file, self.active_company + "\n")
        elif active_file.exists():
            active_file.unlink()

    def merge_env(self, env_vars: dict[str, str]):
        existing = self.read_env()
        existing.update(env_vars)
        self.write_env(existing)

    def read_env(self) -> dict[str, str]:
        if not self._env_file.exists():
            return {}
        result = {}
        for line in self._env_file.read_text().splitlines():
            if line.startswith("export "):
                key, _, val = line[7:].partition("=")
                result[key] = val.strip('"')
        return result

    def clear_env(self):
        if self._env_file.exists():
            self._env_file.unlink()
