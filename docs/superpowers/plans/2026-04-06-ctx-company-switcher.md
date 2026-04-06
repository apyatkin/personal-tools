# ctx — Company Context Switcher Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python CLI tool (`ctx`) that switches between company environments — managing VPN, SSH keys, cloud credentials, env vars, DNS, git identity, docker registries, browser profiles, tool installation, and git repo cloning.

**Architecture:** Modular plugin system where each concern (vpn, ssh, dns, etc.) is a module with activate/deactivate/status methods. A central orchestrator runs modules in defined order. Company configs are declarative YAML files. State is tracked in JSON so operations survive shell restarts.

**Tech Stack:** Python 3.11+, click (CLI), pyyaml (config), keyring (macOS Keychain), httpx (API calls), pytest (tests)

---

### Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `src/ctx/__init__.py`
- Create: `src/ctx/cli.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "ctx-switch"
version = "0.1.0"
description = "Company context switcher"
requires-python = ">=3.11"
dependencies = [
    "click>=8.1",
    "pyyaml>=6.0",
    "keyring>=25.0",
    "httpx>=0.27",
]

[project.scripts]
ctx = "ctx.cli:main"

[tool.hatch.build.targets.wheel]
packages = ["src/ctx"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

- [ ] **Step 2: Create src/ctx/__init__.py**

```python
"""ctx — Company context switcher."""
```

- [ ] **Step 3: Create src/ctx/cli.py with root group**

```python
import click


@click.group()
@click.version_option(version="0.1.0")
def main():
    """Company context switcher."""


@main.command()
def status():
    """Show active company and module states."""
    click.echo("No active context.")
```

- [ ] **Step 4: Install in dev mode and verify CLI works**

Run: `cd /Users/alex/work/personal-tools/personal-tools && uv venv && uv pip install -e ".[dev]" 2>/dev/null; uv pip install -e . && uv run ctx --version`
Expected: `ctx-switch, version 0.1.0`

Run: `uv run ctx status`
Expected: `No active context.`

- [ ] **Step 5: Create test scaffold**

Create `tests/__init__.py` (empty) and `tests/test_cli.py`:

```python
from click.testing import CliRunner

from ctx.cli import main


def test_version():
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_status_no_context():
    runner = CliRunner()
    result = runner.invoke(main, ["status"])
    assert result.exit_code == 0
    assert "No active context" in result.output
```

- [ ] **Step 6: Run tests**

Run: `uv pip install pytest && uv run pytest tests/test_cli.py -v`
Expected: 2 passed

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml src/ tests/
git commit -m "feat: project scaffolding with basic CLI"
```

---

### Task 2: Config Loading

**Files:**
- Create: `src/ctx/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write failing tests for config loading**

```python
import os
import textwrap

import pytest

from ctx.config import load_company_config, list_companies, get_config_dir


def test_get_config_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("CTX_CONFIG_DIR", str(tmp_path))
    assert get_config_dir() == tmp_path


def test_get_config_dir_default(monkeypatch):
    monkeypatch.delenv("CTX_CONFIG_DIR", raising=False)
    result = get_config_dir()
    assert str(result).endswith(".config/ctx")


def test_load_company_config(tmp_path, monkeypatch):
    monkeypatch.setenv("CTX_CONFIG_DIR", str(tmp_path))
    company_dir = tmp_path / "companies" / "acme"
    company_dir.mkdir(parents=True)
    config_file = company_dir / "config.yaml"
    config_file.write_text(textwrap.dedent("""\
        name: acme
        description: "Acme Corp"
        env:
          FOO: bar
    """))
    config = load_company_config("acme")
    assert config["name"] == "acme"
    assert config["env"]["FOO"] == "bar"


def test_load_company_config_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("CTX_CONFIG_DIR", str(tmp_path))
    with pytest.raises(FileNotFoundError):
        load_company_config("nonexistent")


def test_list_companies(tmp_path, monkeypatch):
    monkeypatch.setenv("CTX_CONFIG_DIR", str(tmp_path))
    companies_dir = tmp_path / "companies"
    companies_dir.mkdir()
    (companies_dir / "acme").mkdir()
    (companies_dir / "acme" / "config.yaml").write_text("name: acme\n")
    (companies_dir / "globex").mkdir()
    (companies_dir / "globex" / "config.yaml").write_text("name: globex\n")
    result = list_companies()
    assert set(result) == {"acme", "globex"}


def test_list_companies_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("CTX_CONFIG_DIR", str(tmp_path))
    result = list_companies()
    assert result == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ctx.config'`

- [ ] **Step 3: Implement config.py**

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def get_config_dir() -> Path:
    import os

    env = os.environ.get("CTX_CONFIG_DIR")
    if env:
        return Path(env)
    return Path.home() / ".config" / "ctx"


def load_company_config(name: str) -> dict[str, Any]:
    config_file = get_config_dir() / "companies" / name / "config.yaml"
    if not config_file.exists():
        raise FileNotFoundError(f"Company config not found: {config_file}")
    with open(config_file) as f:
        return yaml.safe_load(f)


def list_companies() -> list[str]:
    companies_dir = get_config_dir() / "companies"
    if not companies_dir.exists():
        return []
    return sorted(
        d.name
        for d in companies_dir.iterdir()
        if d.is_dir() and (d / "config.yaml").exists()
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_config.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/ctx/config.py tests/test_config.py
git commit -m "feat: config loading and company listing"
```

---

### Task 3: State Management

**Files:**
- Create: `src/ctx/state.py`
- Create: `tests/test_state.py`

- [ ] **Step 1: Write failing tests**

```python
import json
import textwrap

from ctx.state import StateManager


def test_load_empty_state(tmp_path, monkeypatch):
    monkeypatch.setenv("CTX_CONFIG_DIR", str(tmp_path))
    sm = StateManager()
    assert sm.active_company is None
    assert sm.activated_modules == []


def test_save_and_load_state(tmp_path, monkeypatch):
    monkeypatch.setenv("CTX_CONFIG_DIR", str(tmp_path))
    sm = StateManager()
    sm.set_active("acme", ["secrets", "vpn", "env"])
    sm.save()

    sm2 = StateManager()
    assert sm2.active_company == "acme"
    assert sm2.activated_modules == ["secrets", "vpn", "env"]
    assert sm2.activated_at is not None


def test_clear_state(tmp_path, monkeypatch):
    monkeypatch.setenv("CTX_CONFIG_DIR", str(tmp_path))
    sm = StateManager()
    sm.set_active("acme", ["env"])
    sm.save()
    sm.clear()
    sm.save()
    assert sm.active_company is None

    sm2 = StateManager()
    assert sm2.active_company is None


def test_write_env_file(tmp_path, monkeypatch):
    monkeypatch.setenv("CTX_CONFIG_DIR", str(tmp_path))
    sm = StateManager()
    sm.write_env({"FOO": "bar", "BAZ": "qux with spaces"})
    env_file = tmp_path / "state.env"
    assert env_file.exists()
    content = env_file.read_text()
    assert 'export FOO="bar"' in content
    assert 'export BAZ="qux with spaces"' in content


def test_clear_env_file(tmp_path, monkeypatch):
    monkeypatch.setenv("CTX_CONFIG_DIR", str(tmp_path))
    sm = StateManager()
    sm.write_env({"FOO": "bar"})
    sm.clear_env()
    env_file = tmp_path / "state.env"
    assert not env_file.exists() or env_file.read_text() == ""
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_state.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ctx.state'`

- [ ] **Step 3: Implement state.py**

```python
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ctx.config import get_config_dir


class StateManager:
    def __init__(self):
        self._dir = get_config_dir()
        self._state_file = self._dir / "state.json"
        self._env_file = self._dir / "state.env"
        self.active_company: str | None = None
        self.activated_modules: list[str] = []
        self.activated_at: str | None = None
        self._load()

    def _load(self):
        if self._state_file.exists():
            data = json.loads(self._state_file.read_text())
            self.active_company = data.get("active_company")
            self.activated_modules = data.get("activated_modules", [])
            self.activated_at = data.get("activated_at")

    def set_active(self, company: str, modules: list[str]):
        self.active_company = company
        self.activated_modules = modules
        self.activated_at = datetime.now(timezone.utc).isoformat()

    def clear(self):
        self.active_company = None
        self.activated_modules = []
        self.activated_at = None

    def save(self):
        self._dir.mkdir(parents=True, exist_ok=True)
        data = {
            "active_company": self.active_company,
            "activated_modules": self.activated_modules,
            "activated_at": self.activated_at,
        }
        self._state_file.write_text(json.dumps(data, indent=2) + "\n")

    def write_env(self, env_vars: dict[str, str]):
        self._dir.mkdir(parents=True, exist_ok=True)
        lines = [f'export {k}="{v}"' for k, v in sorted(env_vars.items())]
        self._env_file.write_text("\n".join(lines) + "\n")

    def clear_env(self):
        if self._env_file.exists():
            self._env_file.unlink()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_state.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/ctx/state.py tests/test_state.py
git commit -m "feat: state management for active context and env file"
```

---

### Task 4: Module Base Class and Orchestrator

**Files:**
- Create: `src/ctx/modules/__init__.py`
- Create: `tests/test_modules_base.py`

- [ ] **Step 1: Write failing tests**

```python
from ctx.modules import Module, ModuleStatus, Orchestrator


class FakeModuleA(Module):
    name = "a"
    order = 0

    def __init__(self):
        self.activated = False
        self.deactivated = False

    def activate(self, config, secrets):
        self.activated = True

    def deactivate(self):
        self.deactivated = True

    def status(self):
        return ModuleStatus(active=self.activated, details="fake a")


class FakeModuleB(Module):
    name = "b"
    order = 1

    def __init__(self):
        self.activated = False
        self.deactivated = False

    def activate(self, config, secrets):
        self.activated = True

    def deactivate(self):
        self.deactivated = True

    def status(self):
        return ModuleStatus(active=self.activated, details="fake b")


def test_orchestrator_activate_order():
    a = FakeModuleA()
    b = FakeModuleB()
    orch = Orchestrator([b, a])  # pass in wrong order
    activated = orch.activate(config={}, secrets={})
    assert activated == ["a", "b"]  # sorted by order
    assert a.activated
    assert b.activated


def test_orchestrator_deactivate_reverse_order():
    a = FakeModuleA()
    b = FakeModuleB()
    orch = Orchestrator([a, b])
    orch.activate(config={}, secrets={})
    deactivated = orch.deactivate(["a", "b"])
    assert deactivated == ["b", "a"]  # reverse order
    assert a.deactivated
    assert b.deactivated


def test_orchestrator_skips_unconfigured():
    a = FakeModuleA()
    b = FakeModuleB()
    orch = Orchestrator([a, b])
    # config only has section for "a"
    config = {"a": {"key": "val"}}
    activated = orch.activate(config=config, secrets={}, only_configured=True)
    assert activated == ["a"]
    assert a.activated
    assert not b.activated


def test_orchestrator_status():
    a = FakeModuleA()
    b = FakeModuleB()
    orch = Orchestrator([a, b])
    orch.activate(config={}, secrets={})
    statuses = orch.status()
    assert statuses["a"].active is True
    assert statuses["b"].active is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_modules_base.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement modules/__init__.py**

```python
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
        self._modules = {m.name: m for m in modules}
        self._sorted = sorted(modules, key=lambda m: m.order)

    def activate(
        self, config: dict, secrets: dict, only_configured: bool = False
    ) -> list[str]:
        activated = []
        for mod in self._sorted:
            if only_configured and mod.name not in config:
                continue
            mod_config = config.get(mod.name, {})
            mod.activate(mod_config, secrets)
            activated.append(mod.name)
        return activated

    def deactivate(self, module_names: list[str]) -> list[str]:
        reverse = [m for m in reversed(self._sorted) if m.name in module_names]
        deactivated = []
        for mod in reverse:
            mod.deactivate()
            deactivated.append(mod.name)
        return deactivated

    def status(self) -> dict[str, ModuleStatus]:
        return {m.name: m.status() for m in self._sorted}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_modules_base.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/ctx/modules/__init__.py tests/test_modules_base.py
git commit -m "feat: module base class and orchestrator"
```

---

### Task 5: Secret Resolution

**Files:**
- Create: `src/ctx/secrets.py`
- Create: `tests/test_secrets.py`

- [ ] **Step 1: Write failing tests**

```python
import pytest

from ctx.secrets import SecretResolver, parse_secret_ref


def test_parse_keychain_ref():
    backend, path = parse_secret_ref("keychain:acme-gitlab-token")
    assert backend == "keychain"
    assert path == "acme-gitlab-token"


def test_parse_bitwarden_ref():
    backend, path = parse_secret_ref("bitwarden:acme-vault/password")
    assert backend == "bitwarden"
    assert path == "acme-vault/password"


def test_parse_invalid_ref():
    with pytest.raises(ValueError, match="Invalid secret ref"):
        parse_secret_ref("plaintext-value")


def test_resolve_refs_in_config():
    resolver = SecretResolver()
    resolver._cache = {
        "keychain:acme-token": "secret123",
        "bitwarden:acme-vault/password": "vaultpass",
    }
    config = {
        "cloud": {
            "nomad": {
                "addr": "https://nomad.acme.com",
                "token_ref": "keychain:acme-token",
            },
            "vault": {
                "token_ref": "bitwarden:acme-vault/password",
            },
        },
        "env": {"FOO": "bar"},
    }
    secrets = resolver.resolve_refs(config)
    assert secrets["keychain:acme-token"] == "secret123"
    assert secrets["bitwarden:acme-vault/password"] == "vaultpass"


def test_find_all_refs():
    config = {
        "docker": {
            "registries": [
                {
                    "host": "reg.acme.com",
                    "username_ref": "keychain:reg-user",
                    "password_ref": "keychain:reg-pass",
                }
            ]
        },
        "cloud": {"hetzner": {"token_ref": "bitwarden:hcloud"}},
    }
    resolver = SecretResolver()
    refs = resolver._find_refs(config)
    assert set(refs) == {"keychain:reg-user", "keychain:reg-pass", "bitwarden:hcloud"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_secrets.py -v`
Expected: FAIL

- [ ] **Step 3: Implement secrets.py**

```python
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
        elif backend == "bitwarden":
            return self._resolve_bitwarden(path)
        raise ValueError(f"Unknown backend: {backend}")

    def _resolve_keychain(self, service: str) -> str:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", service, "-w"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Failed to read keychain secret '{service}': {result.stderr.strip()}")
        return result.stdout.strip()

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

        if field == "password":
            result = subprocess.run(
                ["bw", "get", "password", item_name, "--session", self._bw_session],
                capture_output=True,
                text=True,
            )
        elif field == "notes":
            result = subprocess.run(
                ["bw", "get", "notes", item_name, "--session", self._bw_session],
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
                raise RuntimeError(f"Field '{field}' not found in bitwarden item '{item_name}'")

        if result.returncode != 0:
            raise RuntimeError(f"Failed to read bitwarden secret '{path}': {result.stderr.strip()}")
        return result.stdout.strip()

    def _unlock_bitwarden(self) -> str:
        # Check if already unlocked via BW_SESSION env var
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_secrets.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/ctx/secrets.py tests/test_secrets.py
git commit -m "feat: secret resolution for keychain and bitwarden"
```

---

### Task 6: Env Module

**Files:**
- Create: `src/ctx/modules/env.py`
- Create: `tests/test_module_env.py`

- [ ] **Step 1: Write failing tests**

```python
from ctx.modules.env import EnvModule


def test_env_activate(tmp_path, monkeypatch):
    monkeypatch.setenv("CTX_CONFIG_DIR", str(tmp_path))
    mod = EnvModule()
    mod.activate({"FOO": "bar", "BAZ": "qux"}, secrets={})
    st = mod.status()
    assert st.active
    assert "FOO" in st.details

    env_file = tmp_path / "state.env"
    assert env_file.exists()
    content = env_file.read_text()
    assert 'export FOO="bar"' in content
    assert 'export BAZ="qux"' in content


def test_env_deactivate(tmp_path, monkeypatch):
    monkeypatch.setenv("CTX_CONFIG_DIR", str(tmp_path))
    mod = EnvModule()
    mod.activate({"FOO": "bar"}, secrets={})
    mod.deactivate()
    assert not mod.status().active
    env_file = tmp_path / "state.env"
    assert not env_file.exists() or env_file.read_text() == ""


def test_env_empty_config(tmp_path, monkeypatch):
    monkeypatch.setenv("CTX_CONFIG_DIR", str(tmp_path))
    mod = EnvModule()
    mod.activate({}, secrets={})
    assert not mod.status().active
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_module_env.py -v`
Expected: FAIL

- [ ] **Step 3: Implement env module**

```python
from __future__ import annotations

from ctx.modules import Module, ModuleStatus
from ctx.state import StateManager


class EnvModule(Module):
    name = "env"
    order = 8

    def __init__(self):
        self._vars: dict[str, str] = {}

    def activate(self, config: dict, secrets: dict) -> None:
        if not config:
            return
        self._vars = dict(config)
        sm = StateManager()
        sm.write_env(self._vars)

    def deactivate(self) -> None:
        self._vars = {}
        sm = StateManager()
        sm.clear_env()

    def status(self) -> ModuleStatus:
        if not self._vars:
            return ModuleStatus(active=False)
        var_names = ", ".join(sorted(self._vars.keys()))
        return ModuleStatus(active=True, details=var_names)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_module_env.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/ctx/modules/env.py tests/test_module_env.py
git commit -m "feat: env module for arbitrary environment variables"
```

---

### Task 7: Git Module

**Files:**
- Create: `src/ctx/modules/git.py`
- Create: `tests/test_module_git.py`

- [ ] **Step 1: Write failing tests**

```python
from ctx.modules.git import GitModule


def test_git_activate(tmp_path, monkeypatch):
    monkeypatch.setenv("CTX_CONFIG_DIR", str(tmp_path))
    mod = GitModule()
    config = {"identity": {"name": "Alex", "email": "alex@acme.com"}}
    mod.activate(config, secrets={})
    st = mod.status()
    assert st.active
    assert "Alex" in st.details

    # Check that env vars were written to state.env
    env_file = tmp_path / "state.env"
    content = env_file.read_text()
    assert "GIT_AUTHOR_NAME" in content
    assert "GIT_COMMITTER_NAME" in content


def test_git_deactivate(tmp_path, monkeypatch):
    monkeypatch.setenv("CTX_CONFIG_DIR", str(tmp_path))
    mod = GitModule()
    config = {"identity": {"name": "Alex", "email": "alex@acme.com"}}
    mod.activate(config, secrets={})
    mod.deactivate()
    assert not mod.status().active


def test_git_no_identity(tmp_path, monkeypatch):
    monkeypatch.setenv("CTX_CONFIG_DIR", str(tmp_path))
    mod = GitModule()
    mod.activate({}, secrets={})
    assert not mod.status().active
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_module_git.py -v`
Expected: FAIL

- [ ] **Step 3: Implement git module**

```python
from __future__ import annotations

from ctx.modules import Module, ModuleStatus
from ctx.state import StateManager


class GitModule(Module):
    name = "git"
    order = 6

    def __init__(self):
        self._identity: dict[str, str] | None = None

    def activate(self, config: dict, secrets: dict) -> None:
        identity = config.get("identity")
        if not identity:
            return
        self._identity = identity
        env_vars = {
            "GIT_AUTHOR_NAME": identity["name"],
            "GIT_AUTHOR_EMAIL": identity["email"],
            "GIT_COMMITTER_NAME": identity["name"],
            "GIT_COMMITTER_EMAIL": identity["email"],
        }
        sm = StateManager()
        # Read existing env, merge git vars in
        existing = {}
        env_file = sm._env_file
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("export "):
                    key, _, val = line[7:].partition("=")
                    existing[key] = val.strip('"')
        existing.update(env_vars)
        sm.write_env(existing)

    def deactivate(self) -> None:
        self._identity = None

    def status(self) -> ModuleStatus:
        if not self._identity:
            return ModuleStatus(active=False)
        return ModuleStatus(
            active=True,
            details=f"{self._identity['name']} <{self._identity['email']}>",
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_module_git.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/ctx/modules/git.py tests/test_module_git.py
git commit -m "feat: git identity module"
```

---

### Task 8: SSH Module

**Files:**
- Create: `src/ctx/modules/ssh.py`
- Create: `tests/test_module_ssh.py`

- [ ] **Step 1: Write failing tests**

```python
from unittest.mock import patch, call

from ctx.modules.ssh import SSHModule


def test_ssh_activate_adds_keys():
    mod = SSHModule()
    config = {"keys": ["~/.ssh/acme_ed25519", "~/.ssh/acme_bastion"]}
    with patch("ctx.modules.ssh.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mod.activate(config, secrets={})
    expected_calls = [
        call(["ssh-add", "~/.ssh/acme_ed25519"], capture_output=True, text=True),
        call(["ssh-add", "~/.ssh/acme_bastion"], capture_output=True, text=True),
    ]
    assert mock_run.call_args_list == expected_calls
    assert mod.status().active


def test_ssh_deactivate_removes_keys():
    mod = SSHModule()
    config = {"keys": ["~/.ssh/acme_ed25519"]}
    with patch("ctx.modules.ssh.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mod.activate(config, secrets={})
        mod.deactivate()
    # Last call should be ssh-add -d
    last_call = mock_run.call_args_list[-1]
    assert last_call == call(
        ["ssh-add", "-d", "~/.ssh/acme_ed25519"], capture_output=True, text=True
    )


def test_ssh_no_keys():
    mod = SSHModule()
    mod.activate({}, secrets={})
    assert not mod.status().active
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_module_ssh.py -v`
Expected: FAIL

- [ ] **Step 3: Implement ssh module**

```python
from __future__ import annotations

import subprocess

from ctx.modules import Module, ModuleStatus


class SSHModule(Module):
    name = "ssh"
    order = 5

    def __init__(self):
        self._keys: list[str] = []
        self._config_snippet: str | None = None

    def activate(self, config: dict, secrets: dict) -> None:
        self._keys = config.get("keys", [])
        self._config_snippet = config.get("config")

        for key in self._keys:
            subprocess.run(["ssh-add", key], capture_output=True, text=True)

    def deactivate(self) -> None:
        for key in self._keys:
            subprocess.run(["ssh-add", "-d", key], capture_output=True, text=True)
        self._keys = []
        self._config_snippet = None

    def status(self) -> ModuleStatus:
        if not self._keys:
            return ModuleStatus(active=False)
        return ModuleStatus(
            active=True,
            details=f"{len(self._keys)} key(s) loaded",
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_module_ssh.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/ctx/modules/ssh.py tests/test_module_ssh.py
git commit -m "feat: ssh module for key loading"
```

---

### Task 9: VPN Module

**Files:**
- Create: `src/ctx/modules/vpn.py`
- Create: `tests/test_module_vpn.py`

- [ ] **Step 1: Write failing tests**

```python
from unittest.mock import patch, call

from ctx.modules.vpn import VPNModule


def test_vpn_wireguard_activate():
    mod = VPNModule()
    config = {
        "provider": "wireguard",
        "config": "/etc/wireguard/wg-acme.conf",
        "interface": "wg-acme",
    }
    with patch("ctx.modules.vpn.subprocess.run") as mock_run, \
         patch("ctx.modules.vpn.click.confirm"):
        mock_run.return_value.returncode = 0
        mod.activate(config, secrets={})
    mock_run.assert_called_once_with(
        ["sudo", "wg-quick", "up", "/etc/wireguard/wg-acme.conf"],
        check=True,
    )


def test_vpn_tailscale_activate():
    mod = VPNModule()
    config = {"provider": "tailscale"}
    with patch("ctx.modules.vpn.subprocess.run") as mock_run, \
         patch("ctx.modules.vpn.click.confirm"):
        mock_run.return_value.returncode = 0
        mod.activate(config, secrets={})
    mock_run.assert_called_once_with(
        ["sudo", "tailscale", "up"],
        check=True,
    )


def test_vpn_deactivate_wireguard():
    mod = VPNModule()
    config = {
        "provider": "wireguard",
        "config": "/etc/wireguard/wg-acme.conf",
        "interface": "wg-acme",
    }
    with patch("ctx.modules.vpn.subprocess.run") as mock_run, \
         patch("ctx.modules.vpn.click.confirm"):
        mock_run.return_value.returncode = 0
        mod.activate(config, secrets={})
        mod.deactivate()
    last_call = mock_run.call_args_list[-1]
    assert last_call == call(
        ["sudo", "wg-quick", "down", "wg-acme"], check=True,
    )


def test_vpn_no_config():
    mod = VPNModule()
    mod.activate({}, secrets={})
    assert not mod.status().active
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_module_vpn.py -v`
Expected: FAIL

- [ ] **Step 3: Implement vpn module**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_module_vpn.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/ctx/modules/vpn.py tests/test_module_vpn.py
git commit -m "feat: vpn module for wireguard, amnezia, tailscale"
```

---

### Task 10: DNS Module

**Files:**
- Create: `src/ctx/modules/dns.py`
- Create: `tests/test_module_dns.py`

- [ ] **Step 1: Write failing tests**

```python
from unittest.mock import patch

from ctx.modules.dns import DNSModule


def test_dns_activate(tmp_path):
    mod = DNSModule()
    config = {
        "resolvers": ["10.0.0.53", "10.0.0.54"],
        "search_domains": ["acme.internal"],
    }
    with patch("ctx.modules.dns.RESOLVER_DIR", tmp_path), \
         patch("ctx.modules.dns.click.confirm"):
        mod.activate(config, secrets={})

    resolver_file = tmp_path / "acme.internal"
    assert resolver_file.exists()
    content = resolver_file.read_text()
    assert "nameserver 10.0.0.53" in content
    assert "nameserver 10.0.0.54" in content


def test_dns_deactivate(tmp_path):
    mod = DNSModule()
    config = {
        "resolvers": ["10.0.0.53"],
        "search_domains": ["acme.internal", "acme.corp"],
    }
    with patch("ctx.modules.dns.RESOLVER_DIR", tmp_path), \
         patch("ctx.modules.dns.click.confirm"):
        mod.activate(config, secrets={})
        mod.deactivate()

    assert not (tmp_path / "acme.internal").exists()
    assert not (tmp_path / "acme.corp").exists()


def test_dns_no_config():
    mod = DNSModule()
    mod.activate({}, secrets={})
    assert not mod.status().active
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_module_dns.py -v`
Expected: FAIL

- [ ] **Step 3: Implement dns module**

```python
from __future__ import annotations

import subprocess
from pathlib import Path

import click

from ctx.modules import Module, ModuleStatus

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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_module_dns.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/ctx/modules/dns.py tests/test_module_dns.py
git commit -m "feat: dns resolver module for macOS"
```

---

### Task 11: Hosts Module

**Files:**
- Create: `src/ctx/modules/hosts.py`
- Create: `tests/test_module_hosts.py`

- [ ] **Step 1: Write failing tests**

```python
from ctx.modules.hosts import HostsModule, MARKER_START, MARKER_END


def test_hosts_activate(tmp_path):
    hosts_file = tmp_path / "hosts"
    hosts_file.write_text("127.0.0.1 localhost\n")
    mod = HostsModule(hosts_path=hosts_file)
    config = {
        "entries": [
            "10.0.1.10 grafana.acme.internal",
            "10.0.1.11 vault.acme.internal",
        ]
    }
    mod.activate(config, secrets={})
    content = hosts_file.read_text()
    assert "127.0.0.1 localhost" in content
    assert MARKER_START in content
    assert "10.0.1.10 grafana.acme.internal" in content
    assert MARKER_END in content


def test_hosts_deactivate(tmp_path):
    hosts_file = tmp_path / "hosts"
    hosts_file.write_text("127.0.0.1 localhost\n")
    mod = HostsModule(hosts_path=hosts_file)
    config = {"entries": ["10.0.1.10 grafana.acme.internal"]}
    mod.activate(config, secrets={})
    mod.deactivate()
    content = hosts_file.read_text()
    assert "127.0.0.1 localhost" in content
    assert MARKER_START not in content
    assert "grafana.acme.internal" not in content


def test_hosts_replaces_existing_block(tmp_path):
    hosts_file = tmp_path / "hosts"
    hosts_file.write_text(
        f"127.0.0.1 localhost\n{MARKER_START}\nold entry\n{MARKER_END}\n"
    )
    mod = HostsModule(hosts_path=hosts_file)
    config = {"entries": ["10.0.1.10 new.acme.internal"]}
    mod.activate(config, secrets={})
    content = hosts_file.read_text()
    assert "old entry" not in content
    assert "10.0.1.10 new.acme.internal" in content


def test_hosts_no_config(tmp_path):
    hosts_file = tmp_path / "hosts"
    hosts_file.write_text("127.0.0.1 localhost\n")
    mod = HostsModule(hosts_path=hosts_file)
    mod.activate({}, secrets={})
    assert not mod.status().active
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_module_hosts.py -v`
Expected: FAIL

- [ ] **Step 3: Implement hosts module**

```python
from __future__ import annotations

from pathlib import Path

import click

from ctx.modules import Module, ModuleStatus

MARKER_START = "# >>> ctx-managed >>>"
MARKER_END = "# <<< ctx-managed <<<"
DEFAULT_HOSTS_PATH = Path("/etc/hosts")


class HostsModule(Module):
    name = "hosts"
    order = 4

    def __init__(self, hosts_path: Path | None = None):
        self._hosts_path = hosts_path or DEFAULT_HOSTS_PATH
        self._entries: list[str] = []

    def activate(self, config: dict, secrets: dict) -> None:
        entries = config.get("entries", [])
        if not entries:
            return
        self._entries = entries

        block = f"{MARKER_START}\n" + "\n".join(entries) + f"\n{MARKER_END}\n"
        content = self._hosts_path.read_text()
        content = self._remove_block(content)

        if self._hosts_path == DEFAULT_HOSTS_PATH:
            click.confirm(
                f"Will add {len(entries)} entries to /etc/hosts\nProceed?",
                default=True,
                abort=True,
            )

        self._hosts_path.write_text(content.rstrip("\n") + "\n" + block)

    def deactivate(self) -> None:
        if not self._entries:
            return
        content = self._hosts_path.read_text()
        content = self._remove_block(content)
        self._hosts_path.write_text(content)
        self._entries = []

    def _remove_block(self, content: str) -> str:
        lines = content.splitlines(keepends=True)
        result = []
        in_block = False
        for line in lines:
            if line.strip() == MARKER_START:
                in_block = True
                continue
            if line.strip() == MARKER_END:
                in_block = False
                continue
            if not in_block:
                result.append(line)
        return "".join(result)

    def status(self) -> ModuleStatus:
        if not self._entries:
            return ModuleStatus(active=False)
        return ModuleStatus(
            active=True,
            details=f"{len(self._entries)} entries",
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_module_hosts.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/ctx/modules/hosts.py tests/test_module_hosts.py
git commit -m "feat: hosts module with marker-based /etc/hosts management"
```

---

### Task 12: Cloud Module

**Files:**
- Create: `src/ctx/modules/cloud.py`
- Create: `tests/test_module_cloud.py`

- [ ] **Step 1: Write failing tests**

```python
from unittest.mock import patch, call

from ctx.modules.cloud import CloudModule


def test_cloud_env_vars(tmp_path, monkeypatch):
    monkeypatch.setenv("CTX_CONFIG_DIR", str(tmp_path))
    mod = CloudModule()
    config = {
        "nomad": {
            "addr": "https://nomad.acme.com:4646",
            "token_ref": "keychain:nomad-token",
        },
        "vault": {"addr": "https://vault.acme.com:8200"},
        "consul": {"addr": "https://consul.acme.com:8500"},
        "hetzner": {"token_ref": "keychain:hcloud-token"},
        "kubernetes": {"kubeconfig": "~/.config/ctx/companies/acme/kubeconfig"},
    }
    secrets = {
        "keychain:nomad-token": "s3cret",
        "keychain:hcloud-token": "hetzner123",
    }
    with patch("ctx.modules.cloud.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mod.activate(config, secrets)

    env_file = tmp_path / "state.env"
    content = env_file.read_text()
    assert 'NOMAD_ADDR="https://nomad.acme.com:4646"' in content
    assert 'NOMAD_TOKEN="s3cret"' in content
    assert 'VAULT_ADDR="https://vault.acme.com:8200"' in content
    assert 'CONSUL_HTTP_ADDR="https://consul.acme.com:8500"' in content
    assert 'HCLOUD_TOKEN="hetzner123"' in content
    assert "KUBECONFIG" in content


def test_cloud_yandex_profile():
    mod = CloudModule()
    config = {"yandex": {"profile": "acme"}}
    with patch("ctx.modules.cloud.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mod.activate(config, secrets={})
    mock_run.assert_any_call(
        ["yc", "config", "profile", "activate", "acme"],
        capture_output=True, text=True,
    )


def test_cloud_digitalocean_context():
    mod = CloudModule()
    config = {"digitalocean": {"context": "acme"}}
    with patch("ctx.modules.cloud.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mod.activate(config, secrets={})
    mock_run.assert_any_call(
        ["doctl", "auth", "switch", "--context", "acme"],
        capture_output=True, text=True,
    )


def test_cloud_aws_sso():
    mod = CloudModule()
    config = {"aws": {"profile": "acme-prod", "sso": True}}
    with patch("ctx.modules.cloud.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mod.activate(config, secrets={})
    mock_run.assert_any_call(
        ["aws", "sso", "login", "--profile", "acme-prod"],
        capture_output=True, text=True,
    )


def test_cloud_no_config():
    mod = CloudModule()
    mod.activate({}, secrets={})
    assert not mod.status().active
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_module_cloud.py -v`
Expected: FAIL

- [ ] **Step 3: Implement cloud module**

```python
from __future__ import annotations

import subprocess
from pathlib import Path

from ctx.modules import Module, ModuleStatus
from ctx.state import StateManager


class CloudModule(Module):
    name = "cloud"
    order = 7

    def __init__(self):
        self._active_providers: list[str] = []
        self._env_vars: dict[str, str] = {}

    def activate(self, config: dict, secrets: dict) -> None:
        if not config:
            return

        env_vars: dict[str, str] = {}

        if "aws" in config:
            aws = config["aws"]
            env_vars["AWS_PROFILE"] = aws["profile"]
            if aws.get("sso"):
                subprocess.run(
                    ["aws", "sso", "login", "--profile", aws["profile"]],
                    capture_output=True, text=True,
                )
            self._active_providers.append("aws")

        if "kubernetes" in config:
            k8s = config["kubernetes"]
            kubeconfig = k8s.get("kubeconfig", "")
            env_vars["KUBECONFIG"] = str(Path(kubeconfig).expanduser())
            refresh = k8s.get("refresh")
            if refresh:
                self._refresh_kubeconfig(refresh)
            self._active_providers.append("kubernetes")

        if "nomad" in config:
            nomad = config["nomad"]
            env_vars["NOMAD_ADDR"] = nomad["addr"]
            token_ref = nomad.get("token_ref")
            if token_ref and token_ref in secrets:
                env_vars["NOMAD_TOKEN"] = secrets[token_ref]
            cacert = nomad.get("cacert")
            if cacert:
                env_vars["NOMAD_CACERT"] = str(Path(cacert).expanduser())
            self._active_providers.append("nomad")

        if "vault" in config:
            vault = config["vault"]
            env_vars["VAULT_ADDR"] = vault["addr"]
            token_ref = vault.get("token_ref")
            if token_ref and token_ref in secrets:
                env_vars["VAULT_TOKEN"] = secrets[token_ref]
            self._active_providers.append("vault")

        if "consul" in config:
            consul = config["consul"]
            env_vars["CONSUL_HTTP_ADDR"] = consul["addr"]
            token_ref = consul.get("token_ref")
            if token_ref and token_ref in secrets:
                env_vars["CONSUL_HTTP_TOKEN"] = secrets[token_ref]
            self._active_providers.append("consul")

        if "yandex" in config:
            yc = config["yandex"]
            subprocess.run(
                ["yc", "config", "profile", "activate", yc["profile"]],
                capture_output=True, text=True,
            )
            self._active_providers.append("yandex")

        if "digitalocean" in config:
            do = config["digitalocean"]
            subprocess.run(
                ["doctl", "auth", "switch", "--context", do["context"]],
                capture_output=True, text=True,
            )
            self._active_providers.append("digitalocean")

        if "hetzner" in config:
            hz = config["hetzner"]
            token_ref = hz.get("token_ref")
            if token_ref and token_ref in secrets:
                env_vars["HCLOUD_TOKEN"] = secrets[token_ref]
            self._active_providers.append("hetzner")

        if "terraform" in config:
            tf = config["terraform"]
            for var_name, var_value in tf.get("vars", {}).items():
                env_vars[f"TF_VAR_{var_name}"] = var_value
            self._active_providers.append("terraform")

        self._env_vars = env_vars
        if env_vars:
            sm = StateManager()
            existing = {}
            if sm._env_file.exists():
                for line in sm._env_file.read_text().splitlines():
                    if line.startswith("export "):
                        key, _, val = line[7:].partition("=")
                        existing[key] = val.strip('"')
            existing.update(env_vars)
            sm.write_env(existing)

    def _refresh_kubeconfig(self, refresh: dict) -> None:
        provider = refresh.get("provider")
        cluster = refresh.get("cluster", "")
        if provider == "yandex":
            subprocess.run(
                ["yc", "managed-kubernetes", "cluster", "get-credentials",
                 cluster, "--external", "--force"],
                capture_output=True, text=True,
            )
        elif provider == "aws":
            subprocess.run(
                ["aws", "eks", "update-kubeconfig", "--name", cluster],
                capture_output=True, text=True,
            )
        elif provider == "digitalocean":
            subprocess.run(
                ["doctl", "kubernetes", "cluster", "kubeconfig", "save", cluster],
                capture_output=True, text=True,
            )

    def deactivate(self) -> None:
        self._active_providers = []
        self._env_vars = {}

    def status(self) -> ModuleStatus:
        if not self._active_providers:
            return ModuleStatus(active=False)
        return ModuleStatus(
            active=True,
            details=", ".join(self._active_providers),
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_module_cloud.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/ctx/modules/cloud.py tests/test_module_cloud.py
git commit -m "feat: cloud module for AWS, K8s, Nomad, Vault, Consul, YC, DO, Hetzner, TF"
```

---

### Task 13: Docker Module

**Files:**
- Create: `src/ctx/modules/docker.py`
- Create: `tests/test_module_docker.py`

- [ ] **Step 1: Write failing tests**

```python
from unittest.mock import patch, call

from ctx.modules.docker import DockerModule


def test_docker_activate():
    mod = DockerModule()
    config = {
        "registries": [
            {
                "host": "registry.acme.com",
                "username_ref": "keychain:reg-user",
                "password_ref": "keychain:reg-pass",
            }
        ]
    }
    secrets = {
        "keychain:reg-user": "admin",
        "keychain:reg-pass": "s3cret",
    }
    with patch("ctx.modules.docker.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mod.activate(config, secrets)
    mock_run.assert_called_once_with(
        ["docker", "login", "registry.acme.com",
         "-u", "admin", "--password-stdin"],
        input="s3cret",
        capture_output=True,
        text=True,
    )


def test_docker_deactivate():
    mod = DockerModule()
    config = {
        "registries": [{"host": "registry.acme.com", "username_ref": "keychain:u", "password_ref": "keychain:p"}]
    }
    secrets = {"keychain:u": "a", "keychain:p": "b"}
    with patch("ctx.modules.docker.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mod.activate(config, secrets)
        mod.deactivate()
    last_call = mock_run.call_args_list[-1]
    assert last_call == call(
        ["docker", "logout", "registry.acme.com"],
        capture_output=True, text=True,
    )


def test_docker_no_config():
    mod = DockerModule()
    mod.activate({}, secrets={})
    assert not mod.status().active
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_module_docker.py -v`
Expected: FAIL

- [ ] **Step 3: Implement docker module**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_module_docker.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/ctx/modules/docker.py tests/test_module_docker.py
git commit -m "feat: docker registry login/logout module"
```

---

### Task 14: Proxy Module

**Files:**
- Create: `src/ctx/modules/proxy.py`
- Create: `tests/test_module_proxy.py`

- [ ] **Step 1: Write failing tests**

```python
from ctx.modules.proxy import ProxyModule


def test_proxy_activate(tmp_path, monkeypatch):
    monkeypatch.setenv("CTX_CONFIG_DIR", str(tmp_path))
    mod = ProxyModule()
    config = {
        "http": "http://proxy.acme.com:3128",
        "https": "http://proxy.acme.com:3128",
        "no_proxy": "*.acme.internal,10.0.0.0/8",
    }
    mod.activate(config, secrets={})
    env_file = tmp_path / "state.env"
    content = env_file.read_text()
    assert "HTTP_PROXY" in content
    assert "HTTPS_PROXY" in content
    assert "NO_PROXY" in content
    assert mod.status().active


def test_proxy_deactivate(tmp_path, monkeypatch):
    monkeypatch.setenv("CTX_CONFIG_DIR", str(tmp_path))
    mod = ProxyModule()
    config = {"http": "http://proxy.acme.com:3128"}
    mod.activate(config, secrets={})
    mod.deactivate()
    assert not mod.status().active


def test_proxy_no_config():
    mod = ProxyModule()
    mod.activate({}, secrets={})
    assert not mod.status().active
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_module_proxy.py -v`
Expected: FAIL

- [ ] **Step 3: Implement proxy module**

```python
from __future__ import annotations

from ctx.modules import Module, ModuleStatus
from ctx.state import StateManager


class ProxyModule(Module):
    name = "proxy"
    order = 10

    def __init__(self):
        self._active = False

    def activate(self, config: dict, secrets: dict) -> None:
        if not config:
            return

        env_vars: dict[str, str] = {}
        if "http" in config:
            env_vars["HTTP_PROXY"] = config["http"]
            env_vars["http_proxy"] = config["http"]
        if "https" in config:
            env_vars["HTTPS_PROXY"] = config["https"]
            env_vars["https_proxy"] = config["https"]
        if "no_proxy" in config:
            env_vars["NO_PROXY"] = config["no_proxy"]
            env_vars["no_proxy"] = config["no_proxy"]

        if env_vars:
            self._active = True
            sm = StateManager()
            existing = {}
            if sm._env_file.exists():
                for line in sm._env_file.read_text().splitlines():
                    if line.startswith("export "):
                        key, _, val = line[7:].partition("=")
                        existing[key] = val.strip('"')
            existing.update(env_vars)
            sm.write_env(existing)

    def deactivate(self) -> None:
        self._active = False

    def status(self) -> ModuleStatus:
        if not self._active:
            return ModuleStatus(active=False)
        return ModuleStatus(active=True, details="proxy configured")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_module_proxy.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/ctx/modules/proxy.py tests/test_module_proxy.py
git commit -m "feat: proxy module for HTTP/HTTPS/SOCKS proxy env vars"
```

---

### Task 15: Browser Module

**Files:**
- Create: `src/ctx/modules/browser.py`
- Create: `tests/test_module_browser.py`

- [ ] **Step 1: Write failing tests**

```python
from unittest.mock import patch

from ctx.modules.browser import BrowserModule


def test_browser_activate():
    mod = BrowserModule()
    config = {"profile": "Acme", "app": "google-chrome"}
    with patch("ctx.modules.browser.subprocess.Popen") as mock_popen:
        mod.activate(config, secrets={})
    mock_popen.assert_called_once_with(
        ["open", "-a", "Google Chrome", "--args", "--profile-directory=Acme"],
    )
    assert mod.status().active


def test_browser_no_config():
    mod = BrowserModule()
    mod.activate({}, secrets={})
    assert not mod.status().active


def test_browser_deactivate():
    mod = BrowserModule()
    config = {"profile": "Acme", "app": "google-chrome"}
    with patch("ctx.modules.browser.subprocess.Popen"):
        mod.activate(config, secrets={})
    mod.deactivate()
    assert not mod.status().active
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_module_browser.py -v`
Expected: FAIL

- [ ] **Step 3: Implement browser module**

```python
from __future__ import annotations

import subprocess

from ctx.modules import Module, ModuleStatus

APP_MAP = {
    "google-chrome": "Google Chrome",
    "firefox": "Firefox",
    "arc": "Arc",
}


class BrowserModule(Module):
    name = "browser"
    order = 11

    def __init__(self):
        self._profile: str | None = None
        self._app: str | None = None

    def activate(self, config: dict, secrets: dict) -> None:
        profile = config.get("profile")
        app = config.get("app")
        if not profile or not app:
            return

        self._profile = profile
        self._app = app
        app_name = APP_MAP.get(app, app)
        subprocess.Popen(
            ["open", "-a", app_name, "--args", f"--profile-directory={profile}"],
        )

    def deactivate(self) -> None:
        self._profile = None
        self._app = None

    def status(self) -> ModuleStatus:
        if not self._profile:
            return ModuleStatus(active=False)
        return ModuleStatus(active=True, details=f"{self._app} ({self._profile})")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_module_browser.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/ctx/modules/browser.py tests/test_module_browser.py
git commit -m "feat: browser module to open with company profile"
```

---

### Task 16: Apps Module

**Files:**
- Create: `src/ctx/modules/apps.py`
- Create: `tests/test_module_apps.py`

- [ ] **Step 1: Write failing tests**

```python
from unittest.mock import patch

from ctx.modules.apps import AppsModule


def test_apps_activate_slack():
    mod = AppsModule()
    config = {"slack": {"workspace": "acme-corp"}}
    with patch("ctx.modules.apps.subprocess.Popen") as mock_popen:
        mod.activate(config, secrets={})
    mock_popen.assert_called_once_with(
        ["open", "slack://channel?team=acme-corp"],
    )
    assert mod.status().active


def test_apps_no_config():
    mod = AppsModule()
    mod.activate({}, secrets={})
    assert not mod.status().active
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_module_apps.py -v`
Expected: FAIL

- [ ] **Step 3: Implement apps module**

```python
from __future__ import annotations

import subprocess

from ctx.modules import Module, ModuleStatus


class AppsModule(Module):
    name = "apps"
    order = 12

    def __init__(self):
        self._launched: list[str] = []

    def activate(self, config: dict, secrets: dict) -> None:
        if not config:
            return

        if "slack" in config:
            workspace = config["slack"]["workspace"]
            subprocess.Popen(["open", f"slack://channel?team={workspace}"])
            self._launched.append(f"slack:{workspace}")

    def deactivate(self) -> None:
        self._launched = []

    def status(self) -> ModuleStatus:
        if not self._launched:
            return ModuleStatus(active=False)
        return ModuleStatus(active=True, details=", ".join(self._launched))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_module_apps.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add src/ctx/modules/apps.py tests/test_module_apps.py
git commit -m "feat: apps module for launching Slack etc"
```

---

### Task 17: Tools Module

**Files:**
- Create: `src/ctx/modules/tools.py`
- Create: `tests/test_module_tools.py`

- [ ] **Step 1: Write failing tests**

```python
import json
import time
from unittest.mock import patch, MagicMock

from ctx.modules.tools import ToolsModule


def test_tools_installs_missing_brew(tmp_path, monkeypatch):
    monkeypatch.setenv("CTX_CONFIG_DIR", str(tmp_path))
    mod = ToolsModule()
    config = {"brew": ["kubectl", "helm"], "pipx": []}

    def fake_which(name):
        return None  # nothing installed

    with patch("ctx.modules.tools.shutil.which", side_effect=fake_which), \
         patch("ctx.modules.tools.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        mod.activate(config, secrets={})

    brew_calls = [
        c for c in mock_run.call_args_list
        if c.args[0][0] == "brew" and c.args[0][1] == "install"
    ]
    assert len(brew_calls) == 2


def test_tools_installs_missing_pipx(tmp_path, monkeypatch):
    monkeypatch.setenv("CTX_CONFIG_DIR", str(tmp_path))
    mod = ToolsModule()
    config = {"brew": [], "pipx": ["ansible", "ruff"]}

    with patch("ctx.modules.tools.shutil.which", return_value=None), \
         patch("ctx.modules.tools.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        mod.activate(config, secrets={})

    uv_calls = [
        c for c in mock_run.call_args_list
        if c.args[0][:3] == ["uv", "tool", "install"]
    ]
    assert len(uv_calls) == 2


def test_tools_skips_installed(tmp_path, monkeypatch):
    monkeypatch.setenv("CTX_CONFIG_DIR", str(tmp_path))
    # Pre-populate tools_state.json with recent timestamps
    state_file = tmp_path / "tools_state.json"
    now = time.time()
    state_file.write_text(json.dumps({"kubectl": now, "helm": now}))

    mod = ToolsModule()
    config = {"brew": ["kubectl", "helm"], "pipx": []}

    with patch("ctx.modules.tools.shutil.which", return_value="/usr/local/bin/kubectl"), \
         patch("ctx.modules.tools.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        mod.activate(config, secrets={})

    # No install or upgrade calls expected
    install_calls = [
        c for c in mock_run.call_args_list
        if len(c.args[0]) > 1 and c.args[0][1] in ("install", "upgrade")
    ]
    assert len(install_calls) == 0


def test_tools_no_config():
    mod = ToolsModule()
    mod.activate({}, secrets={})
    assert not mod.status().active
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_module_tools.py -v`
Expected: FAIL

- [ ] **Step 3: Implement tools module**

```python
from __future__ import annotations

import json
import shutil
import subprocess
import time
from pathlib import Path

import click

from ctx.config import get_config_dir
from ctx.modules import Module, ModuleStatus

THROTTLE_SECONDS = 86400  # 24 hours


class ToolsModule(Module):
    name = "tools"
    order = 0

    def __init__(self):
        self._installed: list[str] = []
        self._updated: list[str] = []
        self._already_ok: list[str] = []

    def activate(self, config: dict, secrets: dict) -> None:
        brew_tools = config.get("brew", [])
        pipx_tools = config.get("pipx", [])
        if not brew_tools and not pipx_tools:
            return

        state = self._load_state()
        now = time.time()

        for tool in brew_tools:
            self._ensure_brew(tool, state, now)

        for tool in pipx_tools:
            self._ensure_pipx(tool, state, now)

        self._save_state(state)

        parts = []
        if self._installed:
            parts.append(f"installed {len(self._installed)}")
        if self._updated:
            parts.append(f"updated {len(self._updated)}")
        if self._already_ok:
            parts.append(f"{len(self._already_ok)} up to date")
        if parts:
            click.echo(f"Tools: {', '.join(parts)}")

    def _ensure_brew(self, tool: str, state: dict, now: float) -> None:
        if shutil.which(tool) is None:
            subprocess.run(["brew", "install", tool], capture_output=True, text=True)
            self._installed.append(tool)
            state[tool] = now
        elif self._should_check(tool, state, now):
            result = subprocess.run(
                ["brew", "outdated", "--quiet"],
                capture_output=True, text=True,
            )
            if tool in result.stdout.split():
                subprocess.run(["brew", "upgrade", tool], capture_output=True, text=True)
                self._updated.append(tool)
            else:
                self._already_ok.append(tool)
            state[tool] = now
        else:
            self._already_ok.append(tool)

    def _ensure_pipx(self, tool: str, state: dict, now: float) -> None:
        if shutil.which(tool) is None:
            subprocess.run(
                ["uv", "tool", "install", tool],
                capture_output=True, text=True,
            )
            self._installed.append(tool)
            state[tool] = now
        elif self._should_check(tool, state, now):
            result = subprocess.run(
                ["uv", "tool", "upgrade", tool],
                capture_output=True, text=True,
            )
            if "already" not in result.stdout.lower():
                self._updated.append(tool)
            else:
                self._already_ok.append(tool)
            state[tool] = now
        else:
            self._already_ok.append(tool)

    def _should_check(self, tool: str, state: dict, now: float) -> bool:
        last_check = state.get(tool, 0)
        return (now - last_check) > THROTTLE_SECONDS

    def _load_state(self) -> dict:
        state_file = get_config_dir() / "tools_state.json"
        if state_file.exists():
            return json.loads(state_file.read_text())
        return {}

    def _save_state(self, state: dict) -> None:
        state_file = get_config_dir() / "tools_state.json"
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(json.dumps(state, indent=2) + "\n")

    def deactivate(self) -> None:
        pass  # no-op: don't uninstall tools

    def status(self) -> ModuleStatus:
        total = len(self._installed) + len(self._updated) + len(self._already_ok)
        if total == 0:
            return ModuleStatus(active=False)
        return ModuleStatus(active=True, details=f"{total} tools managed")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_module_tools.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/ctx/modules/tools.py tests/test_module_tools.py
git commit -m "feat: tools module for brew and uv tool install/upgrade"
```

---

### Task 18: Shell Integration

**Files:**
- Create: `src/ctx/shell.py`
- Create: `tests/test_shell.py`

- [ ] **Step 1: Write failing tests**

```python
from ctx.shell import generate_shell_init


def test_generate_zsh_init():
    output = generate_shell_init("zsh")
    assert "precmd" in output
    assert "state.env" in output
    assert "CTX_ACTIVE" in output


def test_generate_unknown_shell():
    import pytest
    with pytest.raises(ValueError, match="Unsupported shell"):
        generate_shell_init("fish")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_shell.py -v`
Expected: FAIL

- [ ] **Step 3: Implement shell.py**

```python
from __future__ import annotations


def generate_shell_init(shell: str) -> str:
    if shell != "zsh":
        raise ValueError(f"Unsupported shell: {shell}")

    return """\
# ctx shell integration
_ctx_precmd() {
  local env_file="${CTX_CONFIG_DIR:-$HOME/.config/ctx}/state.env"
  if [[ -f "$env_file" ]]; then
    source "$env_file"
  fi
  # Read active company for prompt
  local state_file="${CTX_CONFIG_DIR:-$HOME/.config/ctx}/state.json"
  if [[ -f "$state_file" ]]; then
    export CTX_ACTIVE=$(python3 -c "import json,sys;d=json.load(open('$state_file'));print(d.get('active_company',''))" 2>/dev/null)
  else
    unset CTX_ACTIVE
  fi
}
autoload -Uz add-zsh-hook
add-zsh-hook precmd _ctx_precmd

# Prompt indicator
if [[ -n "$CTX_ACTIVE" ]]; then
  RPROMPT="[${CTX_ACTIVE}] ${RPROMPT}"
fi
"""
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_shell.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add src/ctx/shell.py tests/test_shell.py
git commit -m "feat: shell integration for zsh with prompt indicator"
```

---

### Task 19: Repo Management

**Files:**
- Create: `src/ctx/repos.py`
- Create: `tests/test_repos.py`

- [ ] **Step 1: Write failing tests**

```python
import json
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

from ctx.repos import (
    list_remote_repos,
    clone_repos,
    pull_repos,
    get_repos_dir,
)


def test_get_repos_dir():
    path = get_repos_dir("acme")
    assert path == Path.home() / "projects" / "acme" / "repos"


def test_list_remote_gitlab():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"path_with_namespace": "infrastructure/deploy/charts", "ssh_url_to_repo": "git@gitlab.acme.com:infrastructure/deploy/charts.git"},
        {"path_with_namespace": "infrastructure/terraform-modules", "ssh_url_to_repo": "git@gitlab.acme.com:infrastructure/terraform-modules.git"},
    ]
    mock_response.headers = {}

    source = {
        "provider": "gitlab",
        "host": "gitlab.acme.com",
        "group": "infrastructure",
        "token_ref": "keychain:token",
    }
    secrets = {"keychain:token": "glpat-123"}

    with patch("ctx.repos.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value = mock_client
        repos = list_remote_repos(source, secrets)

    assert len(repos) == 2
    assert repos[0]["relative_path"] == "deploy/charts"
    assert repos[1]["relative_path"] == "terraform-modules"


def test_list_remote_github():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"name": "api-server", "ssh_url": "git@github.com:acme-oss/api-server.git"},
        {"name": "docs", "ssh_url": "git@github.com:acme-oss/docs.git"},
    ]
    mock_response.headers = {}

    source = {
        "provider": "github",
        "org": "acme-oss",
        "token_ref": "keychain:gh-token",
    }
    secrets = {"keychain:gh-token": "ghp_123"}

    with patch("ctx.repos.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value = mock_client
        repos = list_remote_repos(source, secrets)

    assert len(repos) == 2
    assert repos[0]["relative_path"] == "api-server"


def test_pull_repos_skips_dirty(tmp_path):
    # Create a fake repo with uncommitted changes
    repo_dir = tmp_path / "acme" / "repos" / "dirty-repo"
    repo_dir.mkdir(parents=True)
    (repo_dir / ".git").mkdir()

    with patch("ctx.repos.subprocess.run") as mock_run:
        # git status --porcelain returns non-empty = dirty
        mock_run.return_value = MagicMock(returncode=0, stdout="M file.txt\n")
        results = pull_repos(tmp_path / "acme" / "repos")

    assert results[0]["status"] == "skipped"
    assert "uncommitted" in results[0]["reason"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_repos.py -v`
Expected: FAIL

- [ ] **Step 3: Implement repos.py**

```python
from __future__ import annotations

import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import httpx


def get_repos_dir(company: str) -> Path:
    return Path.home() / "projects" / company / "repos"


def list_remote_repos(source: dict, secrets: dict) -> list[dict]:
    provider = source["provider"]
    if provider == "gitlab":
        return _list_gitlab(source, secrets)
    elif provider == "github":
        return _list_github(source, secrets)
    else:
        raise ValueError(f"Unknown git provider: {provider}")


def _list_gitlab(source: dict, secrets: dict) -> list[dict]:
    host = source["host"]
    group = source["group"]
    token = secrets.get(source.get("token_ref", ""), "")
    base_url = f"https://{host}/api/v4"

    repos = []
    page = 1
    with httpx.Client() as client:
        while True:
            resp = client.get(
                f"{base_url}/groups/{group}/projects",
                params={"include_subgroups": "true", "per_page": 100, "page": page},
                headers={"PRIVATE-TOKEN": token},
            )
            resp.raise_for_status()
            projects = resp.json()
            if not projects:
                break

            for proj in projects:
                full_path = proj["path_with_namespace"]
                # Strip the group prefix to get relative path
                prefix = group + "/"
                if full_path.startswith(prefix):
                    relative = full_path[len(prefix):]
                else:
                    relative = full_path.rsplit("/", 1)[-1]

                repos.append({
                    "relative_path": relative,
                    "clone_url": proj["ssh_url_to_repo"],
                })

            next_page = resp.headers.get("x-next-page", "")
            if not next_page:
                break
            page = int(next_page)

    return repos


def _list_github(source: dict, secrets: dict) -> list[dict]:
    org = source["org"]
    token = secrets.get(source.get("token_ref", ""), "")

    repos = []
    page = 1
    with httpx.Client() as client:
        while True:
            resp = client.get(
                f"https://api.github.com/orgs/{org}/repos",
                params={"per_page": 100, "page": page},
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            items = resp.json()
            if not items:
                break

            for repo in items:
                repos.append({
                    "relative_path": repo["name"],
                    "clone_url": repo["ssh_url"],
                })

            page += 1

    return repos


def clone_repos(
    company: str,
    sources: list[dict],
    secrets: dict,
    git_identity: dict | None = None,
    concurrency: int = 4,
) -> list[dict]:
    repos_dir = get_repos_dir(company)
    repos_dir.mkdir(parents=True, exist_ok=True)

    all_repos = []
    for source in sources:
        remote_repos = list_remote_repos(source, secrets)
        all_repos.extend(remote_repos)

    results = []

    def _clone_one(repo: dict) -> dict:
        target = repos_dir / repo["relative_path"]
        if target.exists():
            return {"path": str(target), "status": "exists"}
        target.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            ["git", "clone", repo["clone_url"], str(target)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return {"path": str(target), "status": "failed", "reason": result.stderr.strip()}

        # Set git identity
        if git_identity:
            subprocess.run(
                ["git", "config", "user.name", git_identity["name"]],
                cwd=str(target), capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", git_identity["email"]],
                cwd=str(target), capture_output=True,
            )

        return {"path": str(target), "status": "cloned"}

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = {pool.submit(_clone_one, r): r for r in all_repos}
        for future in as_completed(futures):
            results.append(future.result())

    return results


def pull_repos(repos_dir: Path, concurrency: int = 4) -> list[dict]:
    if not repos_dir.exists():
        return []

    git_dirs = [
        p.parent for p in repos_dir.rglob(".git")
        if p.is_dir()
    ]

    results = []

    def _pull_one(repo_path: Path) -> dict:
        # Check for uncommitted changes
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(repo_path),
            capture_output=True,
            text=True,
        )
        if status_result.stdout.strip():
            return {
                "path": str(repo_path),
                "status": "skipped",
                "reason": "uncommitted changes",
            }

        pull_result = subprocess.run(
            ["git", "pull", "--ff-only"],
            cwd=str(repo_path),
            capture_output=True,
            text=True,
        )
        if pull_result.returncode != 0:
            return {
                "path": str(repo_path),
                "status": "failed",
                "reason": pull_result.stderr.strip(),
            }
        return {"path": str(repo_path), "status": "updated"}

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = {pool.submit(_pull_one, d): d for d in git_dirs}
        for future in as_completed(futures):
            results.append(future.result())

    return results
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_repos.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/ctx/repos.py tests/test_repos.py
git commit -m "feat: repo management — clone, pull, list for GitLab and GitHub"
```

---

### Task 20: Full CLI Wiring

**Files:**
- Modify: `src/ctx/cli.py`
- Create: `tests/test_cli_full.py`

This task replaces the placeholder CLI with the full command set, wiring together all modules.

- [ ] **Step 1: Write failing tests for key CLI commands**

```python
import json
import textwrap

from click.testing import CliRunner

from ctx.cli import main


def _setup_company(tmp_path, name="acme"):
    company_dir = tmp_path / "companies" / name
    company_dir.mkdir(parents=True)
    config = {
        "name": name,
        "description": f"{name} corp",
        "env": {"FOO": "bar"},
        "git": {"identity": {"name": "Alex", "email": "alex@acme.com"}},
    }
    import yaml
    (company_dir / "config.yaml").write_text(yaml.dump(config))
    return company_dir


def test_ctx_list(tmp_path, monkeypatch):
    monkeypatch.setenv("CTX_CONFIG_DIR", str(tmp_path))
    _setup_company(tmp_path, "acme")
    _setup_company(tmp_path, "globex")
    runner = CliRunner()
    result = runner.invoke(main, ["list"])
    assert result.exit_code == 0
    assert "acme" in result.output
    assert "globex" in result.output


def test_ctx_init(tmp_path, monkeypatch):
    monkeypatch.setenv("CTX_CONFIG_DIR", str(tmp_path))
    runner = CliRunner()
    result = runner.invoke(main, ["init", "newcorp"])
    assert result.exit_code == 0
    assert (tmp_path / "companies" / "newcorp" / "config.yaml").exists()


def test_ctx_status_no_active(tmp_path, monkeypatch):
    monkeypatch.setenv("CTX_CONFIG_DIR", str(tmp_path))
    runner = CliRunner()
    result = runner.invoke(main, ["status"])
    assert result.exit_code == 0
    assert "No active context" in result.output


def test_ctx_use_and_status(tmp_path, monkeypatch):
    monkeypatch.setenv("CTX_CONFIG_DIR", str(tmp_path))
    _setup_company(tmp_path, "acme")
    runner = CliRunner()
    result = runner.invoke(main, ["use", "acme"])
    assert result.exit_code == 0

    # Check state was written
    state_file = tmp_path / "state.json"
    assert state_file.exists()
    state = json.loads(state_file.read_text())
    assert state["active_company"] == "acme"

    # Check status shows active
    result = runner.invoke(main, ["status"])
    assert "acme" in result.output


def test_ctx_off(tmp_path, monkeypatch):
    monkeypatch.setenv("CTX_CONFIG_DIR", str(tmp_path))
    _setup_company(tmp_path, "acme")
    runner = CliRunner()
    runner.invoke(main, ["use", "acme"])
    result = runner.invoke(main, ["off"])
    assert result.exit_code == 0

    result = runner.invoke(main, ["status"])
    assert "No active context" in result.output
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_cli_full.py -v`
Expected: FAIL

- [ ] **Step 3: Implement full cli.py**

```python
from __future__ import annotations

import click
import yaml

from ctx.config import get_config_dir, load_company_config, list_companies
from ctx.modules import Orchestrator
from ctx.modules.tools import ToolsModule
from ctx.modules.vpn import VPNModule
from ctx.modules.dns import DNSModule
from ctx.modules.hosts import HostsModule
from ctx.modules.ssh import SSHModule
from ctx.modules.git import GitModule
from ctx.modules.cloud import CloudModule
from ctx.modules.env import EnvModule
from ctx.modules.docker import DockerModule
from ctx.modules.proxy import ProxyModule
from ctx.modules.browser import BrowserModule
from ctx.modules.apps import AppsModule
from ctx.secrets import SecretResolver
from ctx.shell import generate_shell_init
from ctx.state import StateManager
from ctx.repos import clone_repos, pull_repos, get_repos_dir, list_remote_repos


def _build_orchestrator() -> Orchestrator:
    return Orchestrator([
        ToolsModule(),
        VPNModule(),
        DNSModule(),
        HostsModule(),
        SSHModule(),
        GitModule(),
        CloudModule(),
        EnvModule(),
        DockerModule(),
        ProxyModule(),
        BrowserModule(),
        AppsModule(),
    ])


# Map config top-level keys to module names
CONFIG_KEY_TO_MODULE = {
    "tools": "tools",
    "vpn": "vpn",
    "dns": "dns",
    "hosts": "hosts",
    "ssh": "ssh",
    "git": "git",
    "cloud": "cloud",
    "env": "env",
    "docker": "docker",
    "proxy": "proxy",
    "browser": "browser",
    "apps": "apps",
}


@click.group()
@click.version_option(version="0.1.0")
def main():
    """Company context switcher."""


@main.command()
@click.argument("company")
@click.option("--check-tools", is_flag=True, help="Force tool update check")
def use(company: str, check_tools: bool):
    """Switch context to a company."""
    config = load_company_config(company)
    sm = StateManager()

    # Deactivate current context if any
    if sm.active_company:
        click.echo(f"Deactivating {sm.active_company}...")
        orch = _build_orchestrator()
        orch.deactivate(sm.activated_modules)
        sm.clear()
        sm.clear_env()
        sm.save()

    # Resolve secrets
    resolver = SecretResolver()
    secrets = resolver.resolve_refs(config)

    # Build module config mapping
    module_config = {}
    for config_key, module_name in CONFIG_KEY_TO_MODULE.items():
        if config_key in config:
            module_config[module_name] = config[config_key]

    # Activate
    click.echo(f"Activating {company}...")
    orch = _build_orchestrator()
    activated = orch.activate(
        config=module_config, secrets=secrets, only_configured=True
    )

    sm.set_active(company, activated)
    sm.save()
    click.echo(f"Context switched to {company}.")


@main.command()
def off():
    """Deactivate current context."""
    sm = StateManager()
    if not sm.active_company:
        click.echo("No active context.")
        return

    click.echo(f"Deactivating {sm.active_company}...")
    orch = _build_orchestrator()
    orch.deactivate(sm.activated_modules)
    sm.clear()
    sm.clear_env()
    sm.save()
    click.echo("Context deactivated.")


@main.command()
def status():
    """Show active company and module states."""
    sm = StateManager()
    if not sm.active_company:
        click.echo("No active context.")
        return

    click.echo(f"Active: {sm.active_company}")
    click.echo(f"Since:  {sm.activated_at}")
    click.echo(f"Modules: {', '.join(sm.activated_modules)}")


@main.command("list")
def list_cmd():
    """List configured companies."""
    companies = list_companies()
    if not companies:
        click.echo("No companies configured. Use 'ctx init <name>' to create one.")
        return
    sm = StateManager()
    for name in companies:
        marker = " (active)" if name == sm.active_company else ""
        click.echo(f"  {name}{marker}")


@main.command()
@click.argument("company")
def init(company: str):
    """Scaffold a new company config."""
    config_dir = get_config_dir() / "companies" / company
    config_file = config_dir / "config.yaml"
    if config_file.exists():
        click.echo(f"Company '{company}' already exists.")
        return

    config_dir.mkdir(parents=True, exist_ok=True)
    template = {
        "name": company,
        "description": "",
        "git": {
            "identity": {"name": "", "email": ""},
            "sources": [],
        },
        "env": {},
        "ssh": {"keys": []},
        "vpn": {},
        "dns": {},
        "hosts": {"entries": []},
        "cloud": {},
        "docker": {"registries": []},
        "proxy": {},
        "browser": {},
        "apps": {},
        "tools": {"brew": [], "pipx": []},
    }
    config_file.write_text(yaml.dump(template, default_flow_style=False, sort_keys=False))
    click.echo(f"Created {config_file}")
    click.echo("Edit the config to add your company settings.")


@main.command("shell-init")
@click.argument("shell")
def shell_init(shell: str):
    """Output shell integration code."""
    click.echo(generate_shell_init(shell))


# --- Repos subgroup ---

@main.group()
def repos():
    """Manage company git repositories."""


@repos.command("clone")
@click.argument("company")
@click.option("--concurrency", "-j", default=4, help="Parallel clone workers")
def repos_clone(company: str, concurrency: int):
    """Clone all repos from configured git sources."""
    config = load_company_config(company)
    sources = config.get("git", {}).get("sources", [])
    if not sources:
        click.echo("No git sources configured.")
        return

    resolver = SecretResolver()
    secrets = resolver.resolve_refs(config)
    identity = config.get("git", {}).get("identity")

    click.echo(f"Cloning repos for {company}...")
    results = clone_repos(company, sources, secrets, identity, concurrency)

    cloned = [r for r in results if r["status"] == "cloned"]
    exists = [r for r in results if r["status"] == "exists"]
    failed = [r for r in results if r["status"] == "failed"]

    click.echo(f"Done: {len(cloned)} cloned, {len(exists)} already existed, {len(failed)} failed")
    for f in failed:
        click.echo(f"  FAIL: {f['path']} — {f['reason']}")


@repos.command("pull")
@click.argument("company", required=False)
@click.option("--all", "pull_all", is_flag=True, help="Pull all companies")
def repos_pull(company: str | None, pull_all: bool):
    """Pull updates for company repos."""
    if pull_all:
        companies = list_companies()
    elif company:
        companies = [company]
    else:
        click.echo("Specify a company or --all")
        return

    for name in companies:
        repos_dir = get_repos_dir(name)
        if not repos_dir.exists():
            click.echo(f"{name}: no repos directory")
            continue
        click.echo(f"Pulling {name}...")
        results = pull_repos(repos_dir)
        updated = [r for r in results if r["status"] == "updated"]
        skipped = [r for r in results if r["status"] == "skipped"]
        failed = [r for r in results if r["status"] == "failed"]
        click.echo(f"  {len(updated)} updated, {len(skipped)} skipped, {len(failed)} failed")
        for s in skipped:
            click.echo(f"  SKIP: {s['path']} — {s['reason']}")
        for f in failed:
            click.echo(f"  FAIL: {f['path']} — {f['reason']}")


@repos.command("list")
@click.argument("company")
def repos_list(company: str):
    """List local vs remote repos."""
    config = load_company_config(company)
    sources = config.get("git", {}).get("sources", [])
    if not sources:
        click.echo("No git sources configured.")
        return

    resolver = SecretResolver()
    secrets = resolver.resolve_refs(config)
    repos_dir = get_repos_dir(company)

    for source in sources:
        remote_repos = list_remote_repos(source, secrets)
        provider = source.get("provider")
        group = source.get("group") or source.get("org")
        click.echo(f"\n{provider}: {group}")
        for repo in remote_repos:
            local_path = repos_dir / repo["relative_path"]
            marker = "  [cloned]" if local_path.exists() else "  [missing]"
            click.echo(f"  {repo['relative_path']}{marker}")


# --- Secret command ---

@main.command("secret")
@click.argument("action", type=click.Choice(["set"]))
@click.argument("ref")
def secret_cmd(action: str, ref: str):
    """Manage secrets."""
    from ctx.secrets import parse_secret_ref
    backend, path = parse_secret_ref(ref)
    value = click.prompt("Enter secret value", hide_input=True)

    if backend == "keychain":
        import subprocess
        subprocess.run(
            ["security", "add-generic-password", "-s", path, "-a", path,
             "-w", value, "-U"],
            check=True,
        )
        click.echo(f"Stored in keychain: {path}")
    elif backend == "bitwarden":
        click.echo("Bitwarden secrets must be stored via the bw CLI or web vault.")


# --- Tools command ---

@main.group("tools")
def tools_group():
    """Manage company tools."""


@tools_group.command("check")
@click.argument("company")
def tools_check(company: str):
    """Check and install/update tools without switching context."""
    config = load_company_config(company)
    tools_config = config.get("tools", {})
    if not tools_config:
        click.echo("No tools configured.")
        return
    mod = ToolsModule()
    mod.activate(tools_config, secrets={})
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_cli_full.py -v`
Expected: 5 passed

- [ ] **Step 5: Run all tests**

Run: `uv run pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 6: Commit**

```bash
git add src/ctx/cli.py tests/test_cli_full.py
git commit -m "feat: full CLI wiring — use, off, status, list, init, repos, secret, tools, shell-init"
```

---

### Task 21: Final Integration Test

**Files:**
- Create: `tests/test_integration.py`

An end-to-end test that exercises the full flow: init a company, configure it, use it, check status, switch off.

- [ ] **Step 1: Write integration test**

```python
import json
import textwrap

import yaml
from click.testing import CliRunner

from ctx.cli import main


def test_full_lifecycle(tmp_path, monkeypatch):
    monkeypatch.setenv("CTX_CONFIG_DIR", str(tmp_path))

    runner = CliRunner()

    # Init a company
    result = runner.invoke(main, ["init", "acme"])
    assert result.exit_code == 0

    # Write a real config
    config = {
        "name": "acme",
        "description": "Acme Corp",
        "env": {"ACME_ENV": "production", "API_URL": "https://api.acme.com"},
        "git": {
            "identity": {"name": "Alex Pyatkin", "email": "alex@acme.com"},
        },
    }
    config_file = tmp_path / "companies" / "acme" / "config.yaml"
    config_file.write_text(yaml.dump(config))

    # List — should show acme
    result = runner.invoke(main, ["list"])
    assert "acme" in result.output

    # Use acme
    result = runner.invoke(main, ["use", "acme"])
    assert result.exit_code == 0
    assert "Activating acme" in result.output

    # Check state.json
    state = json.loads((tmp_path / "state.json").read_text())
    assert state["active_company"] == "acme"

    # Check state.env has our env vars
    env_content = (tmp_path / "state.env").read_text()
    assert "ACME_ENV" in env_content
    assert "GIT_AUTHOR_NAME" in env_content

    # Status
    result = runner.invoke(main, ["status"])
    assert "acme" in result.output
    assert "env" in result.output

    # Init second company
    runner.invoke(main, ["init", "globex"])
    config2 = {
        "name": "globex",
        "description": "Globex Corp",
        "env": {"GLOBEX_KEY": "abc123"},
    }
    config_file2 = tmp_path / "companies" / "globex" / "config.yaml"
    config_file2.write_text(yaml.dump(config2))

    # Switch to globex — should deactivate acme first
    result = runner.invoke(main, ["use", "globex"])
    assert "Deactivating acme" in result.output
    assert "Activating globex" in result.output

    state = json.loads((tmp_path / "state.json").read_text())
    assert state["active_company"] == "globex"

    # Off
    result = runner.invoke(main, ["off"])
    assert "Deactivating globex" in result.output

    result = runner.invoke(main, ["status"])
    assert "No active context" in result.output
```

- [ ] **Step 2: Run integration test**

Run: `uv run pytest tests/test_integration.py -v`
Expected: 1 passed

- [ ] **Step 3: Run full test suite**

Run: `uv run pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 4: Commit**

```bash
git add tests/test_integration.py
git commit -m "feat: integration test for full ctx lifecycle"
```

---

### Task 22: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update CLAUDE.md with project-specific info**

Replace the contents of `CLAUDE.md` with:

```markdown
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

`ctx` is a Python CLI tool for switching between multiple company environments. It manages VPN connections, SSH keys, cloud credentials (AWS, K8s, Nomad, Vault, etc.), env vars, DNS, git identity, docker registries, browser profiles, and tool installation.

## Development

```bash
uv venv && uv pip install -e .     # install in dev mode
uv run ctx --version               # verify CLI works
uv run pytest tests/ -v            # run all tests
uv run pytest tests/test_foo.py -v # run single test file
```

## Architecture

- `src/ctx/cli.py` — Click command definitions, wires everything together
- `src/ctx/config.py` — YAML config loading from `~/.config/ctx/companies/<name>/config.yaml`
- `src/ctx/state.py` — State management (`state.json` + `state.env`)
- `src/ctx/secrets.py` — Secret resolution from macOS Keychain and Bitwarden
- `src/ctx/shell.py` — Shell integration code generation for zsh
- `src/ctx/repos.py` — Git repo cloning/pulling via GitLab/GitHub APIs
- `src/ctx/modules/` — Each module has `activate()`, `deactivate()`, `status()` methods:
  - Activation order: tools(0) → secrets(1) → vpn(2) → dns(3) → hosts(4) → ssh(5) → git(6) → cloud(7) → env(8) → docker(9) → proxy(10) → browser(11) → apps(12)
  - Deactivation runs in reverse order

## Key Design Decisions

- Hard switch only — one active company at a time
- All config sections are optional
- Secrets referenced via `*_ref` fields using `keychain:<name>` or `bitwarden:<path>` syntax
- Privileged operations (vpn, dns, hosts) prompt before running `sudo`
- Tool update checks throttled to once per 24 hours
- GitLab repos preserve nested subgroup structure
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md with project architecture"
```
