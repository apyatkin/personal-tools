from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ModuleStatus:
    active: bool
    details: str = ""


class Module(ABC):
    name: str
    order: int

    @abstractmethod
    def activate(self, config: dict, secrets: dict) -> None: ...

    @abstractmethod
    def deactivate(self) -> None: ...

    @abstractmethod
    def status(self) -> ModuleStatus: ...


class Orchestrator:
    def __init__(self, modules: list[Module]):
        self._sorted = sorted(modules, key=lambda m: m.order)

    def activate(
        self,
        config: dict,
        secrets: dict,
        only_configured: bool = False,
        on_activate: callable | None = None,
    ) -> list[str]:
        activated = []
        for mod in self._sorted:
            if only_configured and mod.name not in config:
                continue
            mod_config = config.get(mod.name, {})
            if on_activate:
                on_activate(mod.name)
            try:
                mod.activate(mod_config, secrets)
                activated.append(mod.name)
            except Exception as e:
                # Rollback already-activated modules in reverse order
                self.deactivate(activated)
                raise RuntimeError(
                    f"Module '{mod.name}' failed: {e}. "
                    f"Rolled back: {', '.join(activated) or 'none'}"
                ) from e
        return activated

    def deactivate(self, module_names: list[str]) -> list[str]:
        reverse = [m for m in reversed(self._sorted) if m.name in module_names]
        deactivated = []
        errors = []
        for mod in reverse:
            try:
                mod.deactivate()
                deactivated.append(mod.name)
            except Exception as e:
                errors.append(f"{mod.name}: {e}")
                deactivated.append(mod.name)  # still mark as attempted
        if errors:
            import click

            for err in errors:
                click.echo(f"  deactivate warning: {err}")
        return deactivated

    def status(self) -> dict[str, ModuleStatus]:
        return {m.name: m.status() for m in self._sorted}
