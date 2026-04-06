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
    from ctx.modules.tools import ToolsModule
    mod = ToolsModule()
    mod.activate(tools_config, secrets={})


# --- Skills command ---

@main.group()
def skills():
    """Manage Claude Code skills."""


@skills.command("deploy")
def skills_deploy():
    """Deploy skills to ~/projects/.claude/skills/ as symlinks."""
    from ctx.skills import get_skills_source, deploy_skills
    source = get_skills_source()
    if not source.exists():
        click.echo(f"Skills source not found: {source}")
        return
    deployed = deploy_skills(source)
    if deployed:
        click.echo(f"Deployed {len(deployed)} skills: {', '.join(deployed)}")
    else:
        click.echo("All skills already deployed.")
