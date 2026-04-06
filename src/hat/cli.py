from __future__ import annotations

import click
import yaml

from hat.config import get_config_dir, load_company_config, list_companies, save_company_config, set_nested
from hat.modules import Orchestrator
from hat.modules.tools import ToolsModule
from hat.modules.vpn import VPNModule
from hat.modules.dns import DNSModule
from hat.modules.hosts import HostsModule
from hat.modules.ssh import SSHModule
from hat.modules.git import GitModule
from hat.modules.cloud import CloudModule
from hat.modules.env import EnvModule
from hat.modules.docker import DockerModule
from hat.modules.proxy import ProxyModule
from hat.modules.browser import BrowserModule
from hat.modules.apps import AppsModule
from hat.secrets import SecretResolver
from hat.shell import generate_shell_init
from hat.state import StateManager
from hat.repos import clone_repos, pull_repos, get_repos_dir, list_remote_repos


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


MODULE_NAMES = frozenset({
    "tools", "vpn", "dns", "hosts", "ssh", "git",
    "cloud", "env", "docker", "proxy", "browser", "apps",
})


@click.group()
@click.version_option(version="1.0.1")
def main():
    """Company context switcher."""


@main.command("on")
@click.argument("company")
@click.option("--check-tools", is_flag=True, help="Force tool update check")
def on_cmd(company: str, check_tools: bool):
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

    module_config = {k: v for k, v in config.items() if k in MODULE_NAMES}

    # Tools come from ~/projects/common/tools.yaml, not per-company
    from hat.common import load_common_tools
    common_tools = load_common_tools()
    if common_tools:
        module_config["tools"] = common_tools

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
        click.echo("No companies configured. Use 'hat init <name>' to create one.")
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
    }
    config_file.write_text(yaml.dump(template, default_flow_style=False, sort_keys=False))
    click.echo(f"Created {config_file}")
    click.echo("Edit the config to add your company settings.")


@main.command("shell-init")
@click.argument("shell")
def shell_init(shell: str):
    """Output shell integration code."""
    click.echo(generate_shell_init(shell))


@main.command("run")
@click.argument("company")
@click.argument("command", nargs=-1, type=click.UNPROCESSED)
def run_cmd(company: str, command: tuple[str, ...]):
    """Run a command in a company's environment without switching context."""
    import os
    import subprocess
    from hat.env_builder import build_company_env

    if not command:
        click.echo("No command specified. Usage: hat run <company> -- <command>")
        return

    env = {**os.environ, **build_company_env(company)}
    result = subprocess.run(list(command), env=env)
    raise SystemExit(result.returncode)


@main.command("env")
@click.argument("company")
@click.option("--export", "export_format", is_flag=True, help="Output in export format")
def env_cmd(company: str, export_format: bool):
    """Show env vars that would be set for a company (dry run)."""
    from hat.env_builder import build_company_env
    env = build_company_env(company)
    if not env:
        click.echo("No env vars configured.")
        return
    for k, v in sorted(env.items()):
        if export_format:
            click.echo(f'export {k}="{v}"')
        else:
            click.echo(f"{k}={v}")


@main.command("shell")
@click.argument("company")
def shell_cmd(company: str):
    """Spawn a new shell with a company's environment."""
    import os
    from hat.env_builder import build_company_env
    env = {**os.environ, **build_company_env(company)}
    env["HAT_ACTIVE"] = company
    shell = os.environ.get("SHELL", "/bin/zsh")
    click.echo(f"Entering {company} shell. Type 'exit' to leave.")
    os.execve(shell, [shell], env)


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

@main.group("secret")
def secret_group():
    """Manage secrets."""


@secret_group.command("set")
@click.argument("ref")
@click.option("--file", "-f", "file_path", type=click.Path(exists=True), help="Read value from file")
def secret_set(ref: str, file_path: str | None):
    """Store a secret. Use -f for multiline values (SSH keys, certs)."""
    from hat.secrets import parse_secret_ref
    import base64
    import subprocess
    backend, path = parse_secret_ref(ref)

    if file_path:
        value = open(file_path).read()
    else:
        click.echo("Enter secret value (paste multiline, then Ctrl-D when done):")
        import sys
        value = sys.stdin.read()

    if backend == "keychain":
        encoded = base64.b64encode(value.encode()).decode()
        subprocess.run(
            ["security", "add-generic-password", "-s", path, "-a", path,
             "-w", encoded, "-U"],
            check=True,
        )
        click.echo(f"Stored in keychain: {path}")
    elif backend == "bitwarden":
        click.echo("Bitwarden secrets must be stored via the bw CLI or web vault.")


@secret_group.command("get")
@click.argument("ref")
def secret_get(ref: str):
    """Display a secret value."""
    from hat.secrets import SecretResolver
    resolver = SecretResolver()
    value = resolver._resolve_one(ref)
    click.echo(value)


# --- Config command ---

@main.group("config")
def config_group():
    """Modify company configs without editing YAML."""


@config_group.command("set")
@click.argument("company")
@click.argument("path")
@click.argument("value")
def config_set(company: str, path: str, value: str):
    """Set a config value. Use dotted paths (e.g. cloud.nomad.addr)."""
    config = load_company_config(company)
    set_nested(config, path, value)
    save_company_config(company, config)
    click.echo(f"{company}: {path} = {value}")


@config_group.command("add-ssh")
@click.argument("company")
@click.argument("keychain_name")
@click.option("--file", "-f", "file_path", type=click.Path(exists=True), help="Read key from file")
def config_add_ssh(company: str, keychain_name: str, file_path: str | None):
    """Store SSH key in Keychain and add ref to company config.

    Examples:

      hat config add-ssh acme acme-sshkey -f ~/.ssh/acme_ed25519

      hat config add-ssh acme acme-sshkey
      (paste key, Ctrl-D)
    """
    import base64
    import subprocess

    if file_path:
        value = open(file_path).read()
    else:
        click.echo("Paste SSH private key (Ctrl-D when done):")
        import sys
        value = sys.stdin.read()

    encoded = base64.b64encode(value.encode()).decode()
    subprocess.run(
        ["security", "add-generic-password", "-s", keychain_name, "-a", keychain_name,
         "-w", encoded, "-U"],
        check=True,
    )

    config = load_company_config(company)
    set_nested(config, "ssh.keys[+]", f"keychain:{keychain_name}")
    save_company_config(company, config)
    click.echo(f"Stored in keychain: {keychain_name}")
    click.echo(f"{company}: added keychain:{keychain_name} to ssh.keys")


@config_group.command("add-secret")
@click.argument("company")
@click.argument("config_path")
@click.argument("keychain_name")
@click.option("--file", "-f", "file_path", type=click.Path(exists=True), help="Read value from file")
def config_add_secret(company: str, config_path: str, keychain_name: str, file_path: str | None):
    """Store secret in keychain and add ref to company config.

    Examples:

      hat config add-secret acme cloud.nomad.token_ref acme-nomad-token

      hat config add-secret acme git.identity.ssh_key acme-sshkey -f ~/.ssh/key
    """
    import base64
    import subprocess

    if file_path:
        value = open(file_path).read()
    else:
        click.echo("Enter secret value (paste multiline, then Ctrl-D when done):")
        import sys
        value = sys.stdin.read()

    encoded = base64.b64encode(value.encode()).decode()
    subprocess.run(
        ["security", "add-generic-password", "-s", keychain_name, "-a", keychain_name,
         "-w", encoded, "-U"],
        check=True,
    )

    config = load_company_config(company)
    set_nested(config, config_path, f"keychain:{keychain_name}")
    save_company_config(company, config)
    click.echo(f"Stored in keychain: {keychain_name}")
    click.echo(f"{company}: {config_path} = keychain:{keychain_name}")


# --- Tools command ---

@main.group("tools")
def tools_group():
    """Manage company tools."""


@tools_group.command("check")
def tools_check():
    """Check and install/update tools from ~/projects/common/tools.yaml."""
    from hat.common import load_common_tools
    tools_config = load_common_tools()
    if not tools_config:
        click.echo("No tools configured. Run 'hat tools init' first.")
        return
    from hat.modules.tools import ToolsModule
    mod = ToolsModule()
    mod.activate(tools_config, secrets={})


@tools_group.command("init")
def tools_init():
    """Generate ~/projects/common/tools.yaml with default tools."""
    from hat.common import generate_tools_config
    path = generate_tools_config()
    click.echo(f"Generated {path}")
    click.echo("Edit the file to customize your tools list.")


# --- Aliases command ---

@main.group()
def aliases():
    """Manage shell aliases."""


@aliases.command("generate")
def aliases_generate():
    """Generate ~/projects/common/aliases.sh."""
    from hat.common import generate_aliases
    path = generate_aliases()
    click.echo(f"Generated {path}")


# --- Completions command ---

@main.group()
def completions():
    """Manage shell completions."""


@completions.command("generate")
def completions_generate():
    """Generate ~/projects/common/completions.sh."""
    from hat.common import generate_completions
    path = generate_completions()
    click.echo(f"Generated {path}")


# --- Skills command ---

@main.group()
def skills():
    """Manage Claude Code skills."""


@skills.command("deploy")
def skills_deploy():
    """Deploy skills to ~/projects/.claude/skills/ as symlinks."""
    from hat.skills import get_skills_source, deploy_skills
    source = get_skills_source()
    if not source.exists():
        click.echo(f"Skills source not found: {source}")
        return
    deployed = deploy_skills(source)
    if deployed:
        click.echo(f"Deployed {len(deployed)} skills: {', '.join(deployed)}")
    else:
        click.echo("All skills already deployed.")
