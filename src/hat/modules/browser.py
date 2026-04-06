from __future__ import annotations

from hat.modules import Module, ModuleStatus


class BrowserModule(Module):
    name = "browser"
    order = 11

    def __init__(self):
        self._profile: str | None = None
        self._app: str | None = None

    def activate(self, config: dict, secrets: dict) -> None:
        profile = config.get("profile")
        app = config.get("app")
        if not profile or not app:
            return

        self._profile = profile
        self._app = app
        from hat.platform import open_browser_with_profile

        open_browser_with_profile(app, profile)

    def deactivate(self) -> None:
        self._profile = None
        self._app = None

    def status(self) -> ModuleStatus:
        if not self._profile:
            return ModuleStatus(active=False)
        return ModuleStatus(active=True, details=f"{self._app} ({self._profile})")
