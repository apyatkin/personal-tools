from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ctx.config import get_config_dir


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

    def save(self):
        self._dir.mkdir(parents=True, exist_ok=True)
        data = {
            "active_company": self.active_company,
            "activated_modules": self.activated_modules,
            "activated_at": self.activated_at,
        }
        self._state_file.write_text(json.dumps(data, indent=2) + "\n")

    def write_env(self, env_vars: dict[str, str]):
        self._dir.mkdir(parents=True, exist_ok=True)
        lines = [f'export {k}="{v}"' for k, v in sorted(env_vars.items())]
        self._env_file.write_text("\n".join(lines) + "\n")

    def clear_env(self):
        if self._env_file.exists():
            self._env_file.unlink()
