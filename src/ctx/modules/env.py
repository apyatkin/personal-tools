from __future__ import annotations

from ctx.modules import Module, ModuleStatus
from ctx.state import StateManager


class EnvModule(Module):
    name = "env"
    order = 8

    def __init__(self):
        self._vars: dict[str, str] = {}

    def activate(self, config: dict, secrets: dict) -> None:
        if not config:
            return
        self._vars = dict(config)
        sm = StateManager()
        sm.write_env(self._vars)

    def deactivate(self) -> None:
        self._vars = {}
        sm = StateManager()
        sm.clear_env()

    def status(self) -> ModuleStatus:
        if not self._vars:
            return ModuleStatus(active=False)
        var_names = ", ".join(sorted(self._vars.keys()))
        return ModuleStatus(active=True, details=var_names)
