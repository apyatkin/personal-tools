from __future__ import annotations

import click

from hat.modules import Module, ModuleStatus


class DNSModule(Module):
    name = "dns"
    order = 3

    def __init__(self):
        self._domains: list[str] = []

    def activate(self, config: dict, secrets: dict) -> None:
        from hat.platform import configure_dns, get_resolver_dir

        resolvers = config.get("resolvers", [])
        domains = config.get("search_domains", [])
        if not resolvers or not domains:
            return

        self._domains = domains
        resolver_dir = get_resolver_dir()
        location = str(resolver_dir) if resolver_dir else "system DNS"

        click.confirm(
            f"Will configure DNS in {location} for: {', '.join(domains)}\nProceed?",
            default=True,
            abort=True,
        )

        configure_dns(resolvers, domains)

    def deactivate(self) -> None:
        from hat.platform import unconfigure_dns

        unconfigure_dns(self._domains)
        self._domains = []

    def status(self) -> ModuleStatus:
        if not self._domains:
            return ModuleStatus(active=False)
        return ModuleStatus(active=True, details=", ".join(self._domains))
