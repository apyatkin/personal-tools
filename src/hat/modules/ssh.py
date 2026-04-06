from __future__ import annotations

import os
import subprocess
import tempfile

from hat.modules import Module, ModuleStatus


class SSHModule(Module):
    name = "ssh"
    order = 5

    def __init__(self):
        self._keys: list[str] = []
        self._temp_files: list[str] = []
        self._config_snippet: str | None = None

    def activate(self, config: dict, secrets: dict) -> None:
        self._keys = config.get("keys", [])
        self._config_snippet = config.get("config")

        for key in self._keys:
            if key.startswith("keychain:") or key.startswith("bitwarden:"):
                path = self._extract_key(key, secrets)
                subprocess.run(["ssh-add", path], capture_output=True, text=True)
            else:
                subprocess.run(["ssh-add", key], capture_output=True, text=True)

    def _extract_key(self, ref: str, secrets: dict) -> str:
        if ref in secrets:
            key_data = secrets[ref]
        else:
            from hat.secrets import SecretResolver
            resolver = SecretResolver()
            key_data = resolver._resolve_one(ref)

        fd, path = tempfile.mkstemp(prefix="hat-ssh-", suffix=".key")
        os.write(fd, key_data.encode())
        os.close(fd)
        os.chmod(path, 0o600)
        self._temp_files.append(path)
        return path

    def deactivate(self) -> None:
        for key in self._keys:
            if key.startswith("keychain:") or key.startswith("bitwarden:"):
                continue  # temp files already cleaned up
            subprocess.run(["ssh-add", "-d", key], capture_output=True, text=True)

        for path in self._temp_files:
            subprocess.run(["ssh-add", "-d", path], capture_output=True, text=True)
            if os.path.exists(path):
                os.unlink(path)

        self._keys = []
        self._temp_files = []
        self._config_snippet = None

    def status(self) -> ModuleStatus:
        if not self._keys:
            return ModuleStatus(active=False)
        return ModuleStatus(
            active=True,
            details=f"{len(self._keys)} key(s) loaded",
        )
