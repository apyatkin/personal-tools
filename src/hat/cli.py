from __future__ import annotations

import click
import yaml

from hat.config import get_config_dir, load_company_config, list_companies
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


def _complete_company(ctx, param, incomplete):
    return [c for c in list_companies() if c.startswith(incomplete)]


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


@main.command("ssh")
@click.argument("company")
@click.argument("host")
@click.option("-u", "--user", default=None, help="SSH user")
def ssh_cmd(company: str, host: str, user: str | None):
    """SSH into a host through company's jump host."""
    import os
    import tempfile

    config = load_company_config(company)
    ssh_config = config.get("ssh", {})
    jump_host = ssh_config.get("jump_host")

    if not jump_host:
        click.echo(f"No jump_host configured for {company}.")
        return

    cmd = ["ssh"]
    jump_user = ssh_config.get("jump_user")
    jump = f"{jump_user}@{jump_host}" if jump_user else jump_host
    cmd.extend(["-J", jump])

    jump_key_ref = ssh_config.get("jump_key_ref")
    if jump_key_ref:
        resolver = SecretResolver()
        secrets = resolver.resolve_refs(config)
        key_data = secrets.get(jump_key_ref) or resolver._resolve_one(jump_key_ref)
        fd, key_path = tempfile.mkstemp(prefix="hat-ssh-", suffix=".key")
        os.write(fd, key_data.encode())
        os.close(fd)
        os.chmod(key_path, 0o600)
        cmd.extend(["-i", key_path])

    if user:
        cmd.extend(["-l", user])
    cmd.append(host)
    os.execvp("ssh", cmd)


@main.command()
@click.argument("company", required=False)
def doctor(company: str | None):
    """Health check — validate configs, secrets, tools."""
    from hat.doctor import run_checks
    results = run_checks(company)
    for r in results:
        if r.level == "ok":
            icon = click.style("OK", fg="green")
        elif r.level == "warn":
            icon = click.style("WARN", fg="yellow")
        else:
            icon = click.style("FAIL", fg="red")
        click.echo(f"  [{icon}] {r.name}: {r.message}")
    errors = [r for r in results if r.level == "error"]
    if errors:
        click.echo(f"\n{len(errors)} error(s) found.")
    else:
        click.echo("\nAll checks passed.")


@main.command()
def migrate():
    """Migrate config from ~/.config/ctx/ to ~/Library/hat/."""
    from hat.migrate import migrate_from_ctx
    actions = migrate_from_ctx()
    for action in actions:
        click.echo(action)


@main.group("tunnel")
def tunnel_group():
    """Manage SSH tunnels and SOCKS proxies."""


@tunnel_group.command("start")
@click.argument("company", shell_complete=_complete_company)
def tunnel_start(company: str):
    """Start tunnels for a company."""
    from hat.tunnel import start_tunnels
    results = start_tunnels(company)
    if not results:
        click.echo("No tunnels configured. Add ssh.tunnels to company config.")
        return
    for r in results:
        click.echo(f"  {r['type']} :{r['local_port']} (pid {r['pid']})")
    # Save PIDs to state
    sm = StateManager()
    sm._dir.mkdir(parents=True, exist_ok=True)
    import json
    pids_file = sm._dir / "tunnel_pids.json"
    pids_file.write_text(json.dumps([r["pid"] for r in results]))


@tunnel_group.command("stop")
def tunnel_stop():
    """Stop all running tunnels."""
    from hat.tunnel import stop_tunnels
    import json
    sm = StateManager()
    pids_file = sm._dir / "tunnel_pids.json"
    if not pids_file.exists():
        click.echo("No tunnels running.")
        return
    pids = json.loads(pids_file.read_text())
    results = stop_tunnels(pids)
    pids_file.unlink()
    for r in results:
        click.echo(f"  pid {r['pid']}: {r['status']}")


from hat.cli_repos import repos
from hat.cli_secret import secret_group
from hat.cli_config import config_group
from hat.cli_tools import tools_group, aliases, completions, skills

main.add_command(repos)
main.add_command(secret_group)
main.add_command(config_group)
main.add_command(tools_group)
main.add_command(aliases)
main.add_command(completions)
main.add_command(skills)
