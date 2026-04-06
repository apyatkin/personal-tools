from __future__ import annotations

import click
import yaml

from hat.config import get_config_dir, load_company_config, list_companies, validate_company_name
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
@click.version_option(package_name="hatctl")
def main():
    """Company context switcher."""


@main.command("on")
@click.argument("company", shell_complete=_complete_company)
@click.option("--check-tools", is_flag=True, help="Force tool update check")
@click.option("--no-vpn", is_flag=True, help="Skip VPN connection")
def on_cmd(company: str, check_tools: bool, no_vpn: bool):
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

    if no_vpn:
        module_config.pop("vpn", None)

    # Activate
    click.echo(f"Activating {company}...")
    try:
        orch = _build_orchestrator()
        activated = orch.activate(
            config=module_config, secrets=secrets, only_configured=True,
            on_activate=lambda name: click.echo(f"  {name}..."),
        )
    except RuntimeError as e:
        click.echo(click.style(f"Activation failed: {e}", fg="red"))
        return

    sm.set_active(company, activated)
    sm.save()
    click.echo(f"Context switched to {company}.")
    from hat.activity_log import log_event
    log_event("on", company, activated)
    from hat.notify import send_notification
    send_notification("hat", f"Put on {company} hat")


@main.command()
@click.argument("company", required=False)
def off(company: str | None):
    """Deactivate current context and disconnect VPN."""
    sm = StateManager()
    if not sm.active_company:
        click.echo("No active context.")
        return

    company_name = sm.active_company
    click.echo(f"Deactivating {company_name}...")

    # Disconnect VPN if it was activated
    if "vpn" in sm.activated_modules:
        try:
            config = load_company_config(company_name)
            vpn_config = config.get("vpn", {})
            provider = vpn_config.get("provider")
            if provider:
                import subprocess
                from hat.utils import find_binary, sudo_env
                if provider == "wireguard":
                    interface = vpn_config.get("interface") or vpn_config.get("config")
                    cmd = ["sudo", find_binary("wg-quick"), "down", interface]
                elif provider == "amnezia":
                    cmd = ["sudo", find_binary("amnezia-cli"), "disconnect"]
                elif provider == "tailscale":
                    cmd = ["sudo", find_binary("tailscale"), "down"]
                else:
                    cmd = None
                if cmd:
                    click.echo(f"  vpn down ({provider})...")
                    subprocess.run(cmd, env=sudo_env())
        except Exception as e:
            click.echo(f"  vpn disconnect warning: {e}")

    orch = _build_orchestrator()
    orch.deactivate(sm.activated_modules)
    sm.clear()
    sm.clear_env()
    sm.save()
    click.echo("Context deactivated.")
    from hat.activity_log import log_event
    log_event("off", company_name)
    from hat.notify import send_notification
    send_notification("hat", f"Took off {company_name} hat")


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
@click.option("--tag", default=None, help="Filter by tag")
def list_cmd(tag: str | None):
    """List configured companies."""
    companies = list_companies(tag=tag)
    if not companies:
        click.echo("No companies configured. Use 'hat init <name>' to create one.")
        return
    sm = StateManager()
    for name in companies:
        marker = " (active)" if name == sm.active_company else ""
        click.echo(f"  {name}{marker}")


@main.command()
@click.argument("company", shell_complete=_complete_company)
def init(company: str):
    """Scaffold a new company config."""
    validate_company_name(company)
    config_dir = get_config_dir() / "companies" / company
    config_file = config_dir / "config.yaml"
    if config_file.exists():
        click.echo(f"Company '{company}' already exists.")
        return

    config_dir.mkdir(parents=True, exist_ok=True)

    # Create project directory
    from pathlib import Path
    projects_dir = Path.home() / "projects" / company
    projects_dir.mkdir(parents=True, exist_ok=True)
    (projects_dir / "repos").mkdir(exist_ok=True)

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
    click.echo(f"Created {projects_dir}/")
    click.echo("Next steps:")
    click.echo(f"  hat ssh config {company} --default-user <user>")
    click.echo(f"  hat vpn config {company} --provider wireguard --config-file {projects_dir}/wg0.conf")
    click.echo(f"  hat config set {company} git.identity.name 'Your Name'")


@main.command("shell-init")
@click.argument("shell")
def shell_init(shell: str):
    """Output shell integration code."""
    click.echo(generate_shell_init(shell))


@main.command("run")
@click.argument("company", shell_complete=_complete_company)
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
    from hat.activity_log import log_event
    log_event("run", company, list(command))
    result = subprocess.run(list(command), env=env)
    raise SystemExit(result.returncode)


@main.command("env")
@click.argument("company", shell_complete=_complete_company)
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
@click.argument("company", shell_complete=_complete_company)
def shell_cmd(company: str):
    """Spawn a new shell with a company's environment."""
    import os
    from hat.env_builder import build_company_env
    env = {**os.environ, **build_company_env(company)}
    env["HAT_ACTIVE"] = company
    shell = os.environ.get("SHELL", "/bin/zsh")
    click.echo(f"Entering {company} shell. Type 'exit' to leave.")
    os.execve(shell, [shell], env)




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


@main.command()
@click.option("-o", "--output", "output_dir", type=click.Path(), default=None, help="Output directory")
def backup(output_dir: str | None):
    """Backup configs to a tarball."""
    from hat.backup import create_backup
    from pathlib import Path
    path = create_backup(Path(output_dir) if output_dir else None)
    click.echo(f"Backup created: {path}")


@main.command()
@click.argument("archive", type=click.Path(exists=True))
def restore(archive: str):
    """Restore configs from a backup tarball."""
    from hat.backup import restore_backup
    from pathlib import Path
    click.confirm("This will overwrite existing configs. Continue?", abort=True)
    actions = restore_backup(Path(archive))
    for a in actions:
        click.echo(a)


@main.command()
@click.argument("company", shell_complete=_complete_company)
@click.option("--from", "from_company", required=True, help="Source company to copy from")
def template(company: str, from_company: str):
    """Create a new company config based on an existing one."""
    from hat.config import clone_company_config
    path = clone_company_config(from_company, company)
    click.echo(f"Created {path} (based on {from_company})")
    click.echo("Secrets have been cleared — add them with 'hat config add-secret'.")


@main.group()
def kubeconfig():
    """Manage Kubernetes configs."""


@kubeconfig.command("merge")
def kubeconfig_merge():
    """Merge all company kubeconfigs into one."""
    from hat.kubeconfig import merge_kubeconfigs
    path = merge_kubeconfigs()
    click.echo(f"Merged kubeconfig: {path}")
    click.echo(f"export KUBECONFIG={path}")


@main.command("diff")
@click.argument("company1", shell_complete=_complete_company)
@click.argument("company2", shell_complete=_complete_company)
def diff_cmd(company1: str, company2: str):
    """Compare two company configs."""
    import difflib
    config1 = load_company_config(company1)
    config2 = load_company_config(company2)
    yaml1 = yaml.dump(config1, default_flow_style=False, sort_keys=True).splitlines(keepends=True)
    yaml2 = yaml.dump(config2, default_flow_style=False, sort_keys=True).splitlines(keepends=True)
    diff = difflib.unified_diff(yaml1, yaml2, fromfile=company1, tofile=company2)
    output = "".join(diff)
    if not output:
        click.echo("Configs are identical.")
    else:
        click.echo(output)


@main.command("log")
@click.option("--company", default=None, help="Filter by company")
@click.option("--limit", "-n", default=20, help="Number of entries")
def log_cmd(company: str | None, limit: int):
    """Show activity log."""
    from hat.activity_log import read_log
    entries = read_log(company, limit)
    if not entries:
        click.echo("No log entries.")
        return
    for e in entries:
        ts = e["timestamp"][:19].replace("T", " ")
        modules = ", ".join(e.get("modules", []))
        suffix = f" [{modules}]" if modules else ""
        click.echo(f"  {ts}  {e['action']:3}  {e['company']}{suffix}")


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


@main.command("completion")
@click.argument("shell", default="zsh")
def completion_cmd(shell: str):
    """Output shell completion code."""
    if shell == "zsh":
        click.echo('eval "$(_HAT_COMPLETE=zsh_source hat)"')
    elif shell == "bash":
        click.echo('eval "$(_HAT_COMPLETE=bash_source hat)"')
    else:
        click.echo(f"Unsupported shell: {shell}")


@main.command()
def setup():
    """First-time setup — configure shell, Touch ID, directories.

    \b
    Run this once after installing hat. It will:
      1. Create ~/projects/ directory
      2. Enable Touch ID for sudo (optional)
      3. Generate shell aliases and completions
      4. Show next steps
    """
    from pathlib import Path
    import subprocess

    click.echo("hat setup\n")

    # 1. Create projects dir
    projects = Path.home() / "projects"
    projects.mkdir(exist_ok=True)
    (projects / "common").mkdir(exist_ok=True)
    click.echo(f"  [OK] {projects}/")

    # 2. Touch ID for sudo
    pam_file = Path("/etc/pam.d/sudo_local")
    if pam_file.exists() and "pam_tid.so" in pam_file.read_text():
        click.echo("  [OK] Touch ID for sudo (already enabled)")
    else:
        if click.confirm("\n  Enable Touch ID for sudo? (uses fingerprint instead of password)", default=True):
            result = subprocess.run(
                ["sudo", "sh", "-c", 'echo "auth       sufficient     pam_tid.so" > /etc/pam.d/sudo_local'],
                capture_output=False,
            )
            if result.returncode == 0:
                click.echo("  [OK] Touch ID for sudo enabled")
            else:
                click.echo("  [SKIP] Could not enable Touch ID")
        else:
            click.echo("  [SKIP] Touch ID for sudo")

    # 3. Generate aliases and completions
    from hat.common import generate_aliases, generate_completions
    generate_aliases()
    click.echo("  [OK] ~/projects/common/aliases.sh")
    generate_completions()
    click.echo("  [OK] ~/projects/common/completions.sh")

    # 4. Shell integration check
    click.echo("\n  Add to ~/.zshrc (if not already there):")
    click.echo('    eval "$(hat shell-init zsh)"')
    click.echo('    eval "$(_HAT_COMPLETE=zsh_source hat)"')

    click.echo("\n  Next steps:")
    click.echo("    hat init <company>       create your first company")
    click.echo("    hat tools init           set up common tools")
    click.echo("    hat skills deploy        deploy Claude Code skills")


@main.command()
@click.argument("company", required=False, shell_complete=_complete_company)
def sync(company: str | None):
    """Morning sync — install tools, sync repos, scan secrets."""
    from hat.common import load_common_tools
    from hat.modules.tools import ToolsModule

    # Tools
    click.echo("Tools...")
    tools = load_common_tools()
    if tools:
        mod = ToolsModule()
        mod.activate(tools, secrets={})

    # Repos
    companies = [company] if company else list_companies()
    for name in companies:
        try:
            config = load_company_config(name)
            sources = config.get("git", {}).get("sources", [])
            if sources:
                click.echo(f"\nRepos ({name})...")
                from hat.repos import sync_repos
                from hat.secrets import SecretResolver
                resolver = SecretResolver()
                secrets = resolver.resolve_refs(config)
                identity = config.get("git", {}).get("identity")
                results = sync_repos(name, sources, secrets, identity)
                cloned = len([r for r in results["clone"] if r["status"] == "cloned"])
                pulled = len([r for r in results["pull"] if r["status"] == "updated"])
                click.echo(f"  {cloned} cloned, {pulled} pulled")
        except Exception as e:
            click.echo(f"  {name}: {e}")

    # Secrets
    click.echo("\nSecrets...")
    from hat.cli_secret import _collect_config_secrets
    from hat.secret_registry import register
    from hat.secrets import SecretResolver
    resolver = SecretResolver()
    for name in companies:
        try:
            config = load_company_config(name)
            for ref in _collect_config_secrets(config):
                try:
                    resolver._resolve_one(ref)
                    register(ref)
                except Exception:
                    pass
        except Exception:
            pass

    click.echo("\nSync complete.")


from hat.cli_repos import repos
from hat.cli_secret import secret_group
from hat.cli_config import config_group
from hat.cli_tools import tools_group, aliases, completions, skills
from hat.cli_net import net_group
from hat.cli_ssh import ssh_group
from hat.cli_vpn import vpn_group

main.add_command(repos)
main.add_command(secret_group)
main.add_command(config_group)
main.add_command(tools_group)
main.add_command(aliases)
main.add_command(completions)
main.add_command(skills)
main.add_command(net_group)
main.add_command(ssh_group)
main.add_command(vpn_group)
