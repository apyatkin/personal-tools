from __future__ import annotations

import os
import shutil
import subprocess

import click

from hat.modules import Module, ModuleStatus


def _find_binary(name: str) -> str:
    path = shutil.which(name)
    if path:
        return path
    for prefix in ["/opt/homebrew/bin", "/usr/local/bin"]:
        candidate = f"{prefix}/{name}"
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return name


class VPNModule(Module):
    name = "vpn"
    order = 2

    def __init__(self):
        self._provider: str | None = None
        self._config_path: str | None = None
        self._interface: str | None = None

    def activate(self, config: dict, secrets: dict) -> None:
        self._provider = config.get("provider")
        if not self._provider:
            return

        self._config_path = config.get("config")
        self._interface = config.get("interface")

        if self._provider == "wireguard":
            cmd = ["sudo", _find_binary("wg-quick"), "up", self._config_path]
        elif self._provider == "amnezia":
            cmd = ["sudo", _find_binary("amnezia-cli"), "connect", self._config_path]
        elif self._provider == "tailscale":
            cmd = ["sudo", _find_binary("tailscale"), "up"]
        else:
            raise ValueError(f"Unknown VPN provider: {self._provider}")

        click.confirm(
            f"Will run: {' '.join(cmd)}\nProceed?", default=True, abort=True
        )
        subprocess.run(cmd, check=True)

    def deactivate(self) -> None:
        if not self._provider:
            return

        if self._provider == "wireguard":
            interface = self._interface or self._config_path
            cmd = ["sudo", _find_binary("wg-quick"), "down", interface]
        elif self._provider == "amnezia":
            cmd = ["sudo", _find_binary("amnezia-cli"), "disconnect"]
        elif self._provider == "tailscale":
            cmd = ["sudo", _find_binary("tailscale"), "down"]
        else:
            return

        subprocess.run(cmd, check=True)
        self._provider = None
        self._config_path = None
        self._interface = None

    def status(self) -> ModuleStatus:
        if not self._provider:
            return ModuleStatus(active=False)
        return ModuleStatus(active=True, details=f"{self._provider}")
