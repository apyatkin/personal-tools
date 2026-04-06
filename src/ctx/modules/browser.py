from __future__ import annotations

import subprocess

from ctx.modules import Module, ModuleStatus

APP_MAP = {
    "google-chrome": "Google Chrome",
    "firefox": "Firefox",
    "arc": "Arc",
}


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
        app_name = APP_MAP.get(app, app)
        subprocess.Popen(
            ["open", "-a", app_name, "--args", f"--profile-directory={profile}"],
        )

    def deactivate(self) -> None:
        self._profile = None
        self._app = None

    def status(self) -> ModuleStatus:
        if not self._profile:
            return ModuleStatus(active=False)
        return ModuleStatus(active=True, details=f"{self._app} ({self._profile})")
