"""Per-company Python virtualenv module.

Creates (and maintains) a dedicated venv under the company's projects
directory and activates it by exporting VIRTUAL_ENV. The shell hook is
responsible for prepending VIRTUAL_ENV/bin to PATH on the next prompt
and restoring the original PATH after `hat off`.

Config shape:

    venv:
      enabled: true                 # optional, default true when section present
      path: ~/projects/acme/venv    # optional, default ~/projects/<company>/venv
      python: python3               # optional, default python3 (or uv if available)
      packages:
        - ansible
        - ansible-lint

If the `venv` section is absent, the module does nothing (backward compat).
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import click

from hat.modules import Module, ModuleStatus
from hat.state import StateManager


DEFAULT_PACKAGES: list[str] = ["ansible"]


class VenvModule(Module):
    name = "venv"
    order = 1  # Before env (8) and tools (0), so $VIRTUAL_ENV exists when tools run

    def __init__(self):
        self._venv_path: Path | None = None
        self._company: str | None = None

    # ─── Helpers ──────────────────────────────────────────────────────────

    def _resolve_path(self, config: dict, company: str) -> Path:
        raw = config.get("path")
        if raw:
            return Path(str(raw)).expanduser().resolve()
        return (Path.home() / "projects" / company / "venv").resolve()

    def _ensure_venv(self, venv_path: Path, python_bin: str) -> None:
        if (venv_path / "bin" / "python").exists():
            return
        venv_path.parent.mkdir(parents=True, exist_ok=True)
        click.echo(f"  venv: creating {venv_path}")
        # Prefer `uv venv` (much faster) if available
        uv = shutil.which("uv")
        if uv:
            subprocess.run(
                [uv, "venv", "--python", python_bin, str(venv_path)],
                check=True,
                capture_output=True,
                text=True,
            )
            return
        subprocess.run(
            [python_bin, "-m", "venv", str(venv_path)],
            check=True,
            capture_output=True,
            text=True,
        )

    def _installed_packages(self, venv_path: Path) -> set[str]:
        """Return the set of installed dist names in the venv (lowercased)."""
        python = venv_path / "bin" / "python"
        if not python.exists():
            return set()
        # `uv venv` doesn't ship pip, so query via importlib.metadata which
        # works regardless of whether pip is installed.
        try:
            result = subprocess.run(
                [
                    str(python),
                    "-c",
                    "import importlib.metadata as m; "
                    "print('\\n'.join(d.metadata['Name'] for d in m.distributions()))",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError:
            return set()
        return {
            line.strip().lower() for line in result.stdout.splitlines() if line.strip()
        }

    def _install_packages(self, venv_path: Path, packages: list[str]) -> None:
        if not packages:
            return
        installed = self._installed_packages(venv_path)
        missing = [p for p in packages if p.split("[", 1)[0].lower() not in installed]
        if not missing:
            return
        click.echo(f"  venv: installing {', '.join(missing)}")
        uv = shutil.which("uv")
        if uv:
            subprocess.run(
                [
                    uv,
                    "pip",
                    "install",
                    "--python",
                    str(venv_path / "bin" / "python"),
                    *missing,
                ],
                check=True,
            )
            return
        subprocess.run(
            [str(venv_path / "bin" / "pip"), "install", *missing],
            check=True,
        )

    # ─── Module lifecycle ─────────────────────────────────────────────────

    def activate(self, config: dict, secrets: dict) -> None:
        if not config:
            return
        if config.get("enabled", True) is False:
            return

        company = StateManager().active_company or os.environ.get("HAT_COMPANY", "")
        # StateManager().active_company is set AFTER orchestrator.activate()
        # completes, so fall back to reading companies/ for the loading cfg.
        # We receive the company name via a side channel: cli.py's on_cmd
        # passes it through the env vars it sets just before activation, so
        # also check HAT_ACTIVATING_COMPANY.
        company = company or os.environ.get("HAT_ACTIVATING_COMPANY", "") or "default"

        venv_path = self._resolve_path(config, company)
        python_bin = config.get("python", "python3")

        raw_packages = config.get("packages")
        if raw_packages is None:
            packages = list(DEFAULT_PACKAGES)
        elif isinstance(raw_packages, str):
            raise RuntimeError(
                f"venv.packages must be a list, got string: {raw_packages!r}. "
                "Use YAML list syntax, e.g. `packages: [ansible]` or one item per line."
            )
        elif not isinstance(raw_packages, list):
            raise RuntimeError(
                f"venv.packages must be a list of strings, got {type(raw_packages).__name__}"
            )
        else:
            packages = [str(p) for p in raw_packages if p]

        try:
            self._ensure_venv(venv_path, python_bin)
            self._install_packages(venv_path, packages)
        except subprocess.CalledProcessError as e:
            stderr = (e.stderr or "").strip() if hasattr(e, "stderr") else ""
            raise RuntimeError(f"venv setup failed: {stderr or e}") from e

        self._venv_path = venv_path
        self._company = company

        # Export VIRTUAL_ENV. The shell hook handles PATH injection and
        # restoration so sourcing state.env multiple times is idempotent.
        StateManager().merge_env({"VIRTUAL_ENV": str(venv_path)})

    def deactivate(self) -> None:
        self._venv_path = None
        self._company = None
        # Env cleanup is handled by StateManager.clear_env() called from
        # the global deactivate path; we don't need to remove VIRTUAL_ENV
        # specifically.

    def status(self) -> ModuleStatus:
        if not self._venv_path:
            return ModuleStatus(active=False)
        return ModuleStatus(active=True, details=str(self._venv_path))
