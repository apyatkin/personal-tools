from __future__ import annotations

from pathlib import Path

import click

from hat.modules import Module, ModuleStatus

RESOLVER_DIR = Path("/etc/resolver")


class DNSModule(Module):
    name = "dns"
    order = 3

    def __init__(self):
        self._domains: list[str] = []

    def activate(self, config: dict, secrets: dict) -> None:
        resolvers = config.get("resolvers", [])
        domains = config.get("search_domains", [])
        if not resolvers or not domains:
            return

        self._domains = domains
        content = "\n".join(f"nameserver {r}" for r in resolvers) + "\n"

        click.confirm(
            f"Will create resolver files in {RESOLVER_DIR} for: {', '.join(domains)}\nProceed?",
            default=True,
            abort=True,
        )

        RESOLVER_DIR.mkdir(parents=True, exist_ok=True)
        for domain in domains:
            resolver_file = RESOLVER_DIR / domain
            resolver_file.write_text(content)

    def deactivate(self) -> None:
        for domain in self._domains:
            resolver_file = RESOLVER_DIR / domain
            if resolver_file.exists():
                resolver_file.unlink()
        self._domains = []

    def status(self) -> ModuleStatus:
        if not self._domains:
            return ModuleStatus(active=False)
        return ModuleStatus(active=True, details=", ".join(self._domains))
