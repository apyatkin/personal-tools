from __future__ import annotations

import shutil
from dataclasses import dataclass

from hat.config import load_company_config, list_companies
from hat.common import load_common_tools
from hat.secrets import SecretResolver


@dataclass
class CheckResult:
    name: str
    level: str  # "ok", "warn", "error"
    message: str


def run_checks(company: str | None = None) -> list[CheckResult]:
    results = []
    companies = [company] if company else list_companies()

    for name in companies:
        results.extend(_check_company(name))

    results.extend(_check_tools())
    return results


def _check_company(name: str) -> list[CheckResult]:
    results = []

    # Config parseable
    try:
        config = load_company_config(name)
        results.append(CheckResult(f"{name}/config", "ok", "Config loaded"))
    except Exception as e:
        results.append(CheckResult(f"{name}/config", "error", str(e)))
        return results

    # Required fields
    if not config.get("name"):
        results.append(CheckResult(f"{name}/name", "warn", "Missing 'name' field"))

    # Secrets accessible
    resolver = SecretResolver()
    refs = resolver._find_refs(config)
    for ref in refs:
        try:
            resolver._resolve_one(ref)
            results.append(CheckResult(f"{name}/secret/{ref}", "ok", "Accessible"))
        except Exception as e:
            results.append(CheckResult(f"{name}/secret/{ref}", "error", str(e)))

    return results


def fix_issues() -> list[str]:
    """Auto-fix common issues."""
    from pathlib import Path
    import os
    fixed = []

    # Fix directory structure
    projects = Path.home() / "projects"
    if not projects.exists():
        projects.mkdir(parents=True)
        fixed.append("Created ~/projects/")
    common = projects / "common"
    if not common.exists():
        common.mkdir()
        fixed.append("Created ~/projects/common/")

    # Fix file permissions
    from hat.config import get_config_dir
    config_dir = get_config_dir()
    for name in ["state.json", "state.env", "secrets.json", "active"]:
        path = config_dir / name
        if path.exists():
            mode = oct(path.stat().st_mode)[-3:]
            if mode != "600":
                os.chmod(path, 0o600)
                fixed.append(f"Fixed permissions on {name}")

    # Install missing tools
    tools = load_common_tools()
    if tools:
        import shutil
        from hat.modules.tools import _brew_bin_name, _npm_bin_name
        missing = []
        for tool in tools.get("brew", []):
            if not shutil.which(_brew_bin_name(tool)):
                missing.append(f"{tool} (brew)")
        for tool in tools.get("pipx", []):
            if not shutil.which(tool):
                missing.append(f"{tool} (pipx)")
        for tool in tools.get("npm", []):
            if not shutil.which(_npm_bin_name(tool)):
                missing.append(f"{tool} (npm)")
        if missing:
            fixed.append(f"Missing tools: {', '.join(missing)} — run 'hat tools install'")

    return fixed


def _check_tools() -> list[CheckResult]:
    results = []
    tools = load_common_tools()
    if not tools:
        results.append(CheckResult("tools/config", "warn", "No tools.yaml found"))
        return results

    for tool in tools.get("brew", []) + tools.get("pipx", []):
        if shutil.which(tool):
            results.append(CheckResult(f"tools/{tool}", "ok", "Installed"))
        else:
            results.append(CheckResult(f"tools/{tool}", "warn", f"Not installed"))

    return results
