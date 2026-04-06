"""Plugin system for custom modules."""

from __future__ import annotations

import importlib.util

from hat.config import get_config_dir
from hat.modules import Module


PLUGINS_DIR = get_config_dir() / "plugins"


def load_plugins() -> list[Module]:
    """Load custom modules from ~/Library/hat/plugins/."""
    if not PLUGINS_DIR.exists():
        return []

    modules = []
    for py_file in sorted(PLUGINS_DIR.glob("*.py")):
        try:
            spec = importlib.util.spec_from_file_location(py_file.stem, py_file)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            # Find Module subclasses
            for attr_name in dir(mod):
                attr = getattr(mod, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, Module)
                    and attr is not Module
                ):
                    modules.append(attr())
        except Exception as e:
            import click

            click.echo(f"Plugin load error ({py_file.name}): {e}")

    return modules
