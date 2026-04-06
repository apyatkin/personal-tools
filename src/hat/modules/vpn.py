from __future__ import annotations

import subprocess
from pathlib import Path

import click

from hat.modules import Module, ModuleStatus
from hat.utils import find_binary, sudo_env


class VPNModule(Module):
    name = "vpn"
    order = 2

    def __init__(self):
        self._provider: str | None = None
        self._config_path: str | None = None
        self._interface: str | None = None

    def _is_already_connected(self) -> bool:
        if self._provider == "wireguard":
            result = subprocess.run(
                ["sudo", find_binary("wg"), "show"],
                capture_output=True,
                text=True,
                env=sudo_env(),
            )
            return result.returncode == 0 and len(result.stdout.strip()) > 0
        elif self._provider == "tailscale":
            result = subprocess.run(
                [find_binary("tailscale"), "status"],
                capture_output=True,
                text=True,
            )
            return result.returncode == 0 and "stopped" not in result.stdout.lower()
        return False

    def activate(self, config: dict, secrets: dict) -> None:
        self._provider = config.get("provider")
        if not self._provider:
            return

        self._config_path = config.get("config")
        self._interface = config.get("interface")

        if self._is_already_connected():
            click.echo("    (already connected)")
            return

        if self._config_path:
            p = Path(self._config_path).expanduser()
            if not p.exists():
                raise FileNotFoundError(f"VPN config not found: {p}")

        if self._provider == "wireguard":
            cmd = ["sudo", find_binary("wg-quick"), "up", self._config_path]
        elif self._provider == "amnezia":
            cmd = ["sudo", find_binary("amnezia-cli"), "connect", self._config_path]
        elif self._provider == "tailscale":
            cmd = ["sudo", find_binary("tailscale"), "up"]
        else:
            raise ValueError(f"Unknown VPN provider: {self._provider}")

        click.confirm(f"Will run: {' '.join(cmd)}\nProceed?", default=True, abort=True)
        subprocess.run(cmd, check=True, env=sudo_env())

    def deactivate(self) -> None:
        if not self._provider:
            return

        if self._provider == "wireguard":
            interface = self._interface or self._config_path
            cmd = ["sudo", find_binary("wg-quick"), "down", interface]
        elif self._provider == "amnezia":
            cmd = ["sudo", find_binary("amnezia-cli"), "disconnect"]
        elif self._provider == "tailscale":
            cmd = ["sudo", find_binary("tailscale"), "down"]
        else:
            return

        subprocess.run(cmd, check=True, env=sudo_env())
        self._provider = None
        self._config_path = None
        self._interface = None

    def status(self) -> ModuleStatus:
        if not self._provider:
            return ModuleStatus(active=False)
        return ModuleStatus(active=True, details=f"{self._provider}")
