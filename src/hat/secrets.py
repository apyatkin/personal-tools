from __future__ import annotations

import subprocess
from typing import Any


def parse_secret_ref(ref: str) -> tuple[str, str]:
    if ":" not in ref:
        raise ValueError(f"Invalid secret ref (expected 'backend:path'): {ref}")
    backend, _, path = ref.partition(":")
    if backend not in ("keychain", "bitwarden"):
        raise ValueError(f"Unknown secret backend: {backend}")
    return backend, path


class SecretResolver:
    def __init__(self):
        self._cache: dict[str, str] = {}
        self._bw_session: str | None = None

    def _find_refs(self, obj: Any, refs: list[str] | None = None) -> list[str]:
        if refs is None:
            refs = []
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key.endswith("_ref") and isinstance(value, str):
                    refs.append(value)
                else:
                    self._find_refs(value, refs)
        elif isinstance(obj, list):
            for item in obj:
                self._find_refs(item, refs)
        return refs

    def resolve_refs(self, config: dict) -> dict[str, str]:
        refs = self._find_refs(config)
        secrets = {}
        for ref in refs:
            if ref in self._cache:
                secrets[ref] = self._cache[ref]
            else:
                value = self._resolve_one(ref)
                self._cache[ref] = value
                secrets[ref] = value
        return secrets

    def _resolve_one(self, ref: str) -> str:
        backend, path = parse_secret_ref(ref)
        if backend == "keychain":
            return self._resolve_keychain(path)
        return self._resolve_bitwarden(path)

    def _resolve_keychain(self, service: str) -> str:
        import base64

        from hat.platform import get_secret

        raw = get_secret(service)
        if raw is None:
            raise RuntimeError(
                f"Failed to read secret '{service}' from credential store"
            )
        try:
            return base64.b64decode(raw).decode()
        except Exception:
            return raw

    def _resolve_bitwarden(self, path: str) -> str:
        if self._bw_session is None:
            self._bw_session = self._unlock_bitwarden()
        parts = path.split("/")
        item_name = parts[0]
        if len(parts) == 1:
            field = "password"
        elif len(parts) == 2:
            field = parts[1]
        elif len(parts) == 3 and parts[1] == "field":
            field = parts[2]
        else:
            raise ValueError(f"Invalid bitwarden path: {path}")

        if field in ("password", "notes"):
            result = subprocess.run(
                ["bw", "get", field, item_name, "--session", self._bw_session],
                capture_output=True,
                text=True,
            )
        else:
            result = subprocess.run(
                ["bw", "get", "item", item_name, "--session", self._bw_session],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                import json

                item = json.loads(result.stdout)
                for f in item.get("fields", []):
                    if f["name"] == field:
                        return f["value"]
                raise RuntimeError(
                    f"Field '{field}' not found in bitwarden item '{item_name}'"
                )

        if result.returncode != 0:
            raise RuntimeError(
                f"Failed to read bitwarden secret '{path}': {result.stderr.strip()}"
            )
        return result.stdout.strip()

    def _unlock_bitwarden(self) -> str:
        import os

        session = os.environ.get("BW_SESSION")
        if session:
            return session
        result = subprocess.run(
            ["bw", "unlock", "--raw"],
            capture_output=False,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError("Failed to unlock Bitwarden vault")
        return result.stdout.strip()

    def clear(self):
        self._cache.clear()
        self._bw_session = None
