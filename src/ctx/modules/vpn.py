from __future__ import annotations

import subprocess

import click

from ctx.modules import Module, ModuleStatus


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
            cmd = ["sudo", "wg-quick", "up", self._config_path]
        elif self._provider == "amnezia":
            cmd = ["sudo", "amnezia-cli", "connect", self._config_path]
        elif self._provider == "tailscale":
            cmd = ["sudo", "tailscale", "up"]
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
            cmd = ["sudo", "wg-quick", "down", interface]
        elif self._provider == "amnezia":
            cmd = ["sudo", "amnezia-cli", "disconnect"]
        elif self._provider == "tailscale":
            cmd = ["sudo", "tailscale", "down"]
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
