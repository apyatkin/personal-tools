from __future__ import annotations

from hat.modules import Module, ModuleStatus


class AppsModule(Module):
    name = "apps"
    order = 12

    def __init__(self):
        self._launched: list[str] = []

    def activate(self, config: dict, secrets: dict) -> None:
        if not config:
            return

        if "slack" in config:
            workspace = config["slack"]["workspace"]
            from hat.platform import open_url

            open_url(f"slack://channel?team={workspace}")
            self._launched.append(f"slack:{workspace}")

    def deactivate(self) -> None:
        self._launched = []

    def status(self) -> ModuleStatus:
        if not self._launched:
            return ModuleStatus(active=False)
        return ModuleStatus(active=True, details=", ".join(self._launched))
