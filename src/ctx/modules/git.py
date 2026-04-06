from __future__ import annotations

from ctx.modules import Module, ModuleStatus
from ctx.state import StateManager


class GitModule(Module):
    name = "git"
    order = 6

    def __init__(self):
        self._identity: dict[str, str] | None = None

    def activate(self, config: dict, secrets: dict) -> None:
        identity = config.get("identity")
        if not identity:
            return
        self._identity = identity
        env_vars = {
            "GIT_AUTHOR_NAME": identity["name"],
            "GIT_AUTHOR_EMAIL": identity["email"],
            "GIT_COMMITTER_NAME": identity["name"],
            "GIT_COMMITTER_EMAIL": identity["email"],
        }
        sm = StateManager()
        existing = {}
        env_file = sm._env_file
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("export "):
                    key, _, val = line[7:].partition("=")
                    existing[key] = val.strip('"')
        existing.update(env_vars)
        sm.write_env(existing)

    def deactivate(self) -> None:
        self._identity = None

    def status(self) -> ModuleStatus:
        if not self._identity:
            return ModuleStatus(active=False)
        return ModuleStatus(
            active=True,
            details=f"{self._identity['name']} <{self._identity['email']}>",
        )
