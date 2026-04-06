from __future__ import annotations

import subprocess

from ctx.modules import Module, ModuleStatus


class DockerModule(Module):
    name = "docker"
    order = 9

    def __init__(self):
        self._hosts: list[str] = []

    def activate(self, config: dict, secrets: dict) -> None:
        registries = config.get("registries", [])
        if not registries:
            return

        for reg in registries:
            host = reg["host"]
            username = secrets.get(reg.get("username_ref", ""), "")
            password = secrets.get(reg.get("password_ref", ""), "")
            subprocess.run(
                ["docker", "login", host, "-u", username, "--password-stdin"],
                input=password,
                capture_output=True,
                text=True,
            )
            self._hosts.append(host)

    def deactivate(self) -> None:
        for host in self._hosts:
            subprocess.run(
                ["docker", "logout", host],
                capture_output=True, text=True,
            )
        self._hosts = []

    def status(self) -> ModuleStatus:
        if not self._hosts:
            return ModuleStatus(active=False)
        return ModuleStatus(active=True, details=", ".join(self._hosts))
