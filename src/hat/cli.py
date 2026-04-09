from __future__ import annotations

import os

import click
import yaml

from hat.config import (
    get_config_dir,
    load_company_config,
    list_companies,
    validate_company_name,
)
from hat.modules import Orchestrator
from hat.modules.tools import ToolsModule
from hat.modules.venv import VenvModule
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
    builtin = [
        ToolsModule(),
        VenvModule(),
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
    ]

    try:
        from hat.plugins import load_plugins

        plugins = load_plugins()
    except Exception:
        plugins = []

    return Orchestrator(builtin + plugins)


MODULE_NAMES = frozenset(
    {
        "tools",
        "venv",
        "vpn",
        "dns",
        "hosts",
        "ssh",
        "git",
        "cloud",
        "env",
        "docker",
        "proxy",
        "browser",
        "apps",
    }
)


def _complete_company(ctx, param, incomplete):
    return [c for c in list_companies() if c.startswith(incomplete)]


class _AliasedGroup(click.Group):
    """Click group that supports hidden command aliases."""

    _aliases: dict[str, str] = {
        "tools": "package",  # backward-compat: `hat tools ...` -> `hat package ...`
    }

    def get_command(self, ctx, cmd_name):
        rv = super().get_command(ctx, cmd_name)
        if rv is not None:
            return rv
        target = self._aliases.get(cmd_name)
        if target:
            return super().get_command(ctx, target)
        return None


@click.group(cls=_AliasedGroup, invoke_without_command=True)
@click.version_option(package_name="hatctl")
@click.pass_context
def main(ctx):
    """Company context switcher."""
    if ctx.invoked_subcommand is None:
        from hat.tui import run_tui

        run_tui()


@main.command("tui")
def tui_cmd():
    """Interactive menu."""
    from hat.tui import run_tui

    run_tui()


@main.command()
def watch():
    """Live dashboard — auto-refreshing status."""
    from hat.watch import run_watch

    run_watch()


@main.command("plugins")
def plugins_cmd():
    """List loaded plugins."""
    from hat.plugins import load_plugins, PLUGINS_DIR

    click.echo(f"Plugin directory: {PLUGINS_DIR}")
    plugins = load_plugins()
    if not plugins:
        click.echo("No plugins loaded.")
        click.echo(f"Add .py files to {PLUGINS_DIR}/")
        return
    for p in plugins:
        click.echo(f"  {p.name} (order={p.order})")


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
    # VenvModule needs to know the company name to default its path.
    os.environ["HAT_ACTIVATING_COMPANY"] = company
    try:
        orch = _build_orchestrator()
        activated = orch.activate(
            config=module_config,
            secrets=secrets,
            only_configured=True,
            on_activate=lambda name: click.echo(f"  {name}..."),
        )
    except RuntimeError as e:
        click.echo(click.style(f"Activation failed: {e}", fg="red"))
        return
    finally:
        os.environ.pop("HAT_ACTIVATING_COMPANY", None)

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
@click.option(
    "--from",
    "from_company",
    default=None,
    shell_complete=_complete_company,
    help="Clone config from an existing company instead of scaffolding from scratch",
)
def init(company: str, from_company: str | None):
    """Scaffold a new company config.

    \b
    Two modes:
      hat init acme                 # scaffold from blank template
      hat init acme --from foo      # clone existing 'foo' config, clear secrets
    """
    validate_company_name(company)

    # Clone mode: delegate to config.clone_company_config (also used by the
    # deprecated `hat template` command).
    if from_company:
        from hat.config import clone_company_config

        path = clone_company_config(from_company, company)
        click.echo(f"Created {path} (based on {from_company})")
        click.echo("Secrets have been cleared — add them with 'hat config add-secret'.")
        return

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

    scaffold = {
        "name": company,
        "description": "",
        "git": {
            "identity": {"name": "", "email": ""},
            "sources": [],
        },
        "env": {},
        "venv": {
            "enabled": True,
            "packages": ["ansible"],
        },
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
    config_file.write_text(
        yaml.dump(scaffold, default_flow_style=False, sort_keys=False)
    )
    click.echo(f"Created {config_file}")
    click.echo(f"Created {projects_dir}/")
    click.echo("Next steps:")
    click.echo(f"  hat ssh config {company} --default-user <user>")
    click.echo(
        f"  hat vpn config {company} --provider wireguard --config-file {projects_dir}/wg0.conf"
    )
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
@click.option("--fix", is_flag=True, help="Auto-fix common issues")
def doctor(company: str | None, fix: bool):
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

    if fix:
        from hat.doctor import fix_issues

        fixes = fix_issues()
        if fixes:
            click.echo("\nFixes applied:")
            for f in fixes:
                click.echo(f"  {f}")
        else:
            click.echo("\nNothing to fix.")


@main.command()
def migrate():
    """Migrate config from ~/.config/ctx/ to ~/Library/hat/."""
    from hat.migrate import migrate_from_ctx

    actions = migrate_from_ctx()
    for action in actions:
        click.echo(action)


@main.command()
@click.option(
    "-o",
    "--output",
    "output_dir",
    type=click.Path(),
    default=None,
    help="Output directory",
)
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


@main.command("export")
@click.argument("company", shell_complete=_complete_company)
@click.option("-o", "--output", "output_dir", type=click.Path(), default=None)
def export_cmd(company: str, output_dir: str | None):
    """Export a company config for sharing."""
    from hat.transfer import export_company
    from pathlib import Path

    path = export_company(company, Path(output_dir) if output_dir else None)
    click.echo(f"Exported to: {path}")
    click.echo("Share this file — secrets are referenced, not included.")


@main.command("import")
@click.argument("archive", type=click.Path(exists=True))
@click.option("--name", default=None, help="Override company name")
def import_cmd(archive: str, name: str | None):
    """Import a company config from an export."""
    from hat.transfer import import_company
    from pathlib import Path

    company = import_company(Path(archive), name)
    click.echo(f"Imported: {company}")
    click.echo(f"Add secrets: hat secret list --company {company}")


@main.command(hidden=True)
@click.argument("company", shell_complete=_complete_company)
@click.option(
    "--from", "from_company", required=True, help="Source company to copy from"
)
@click.pass_context
def template(ctx, company: str, from_company: str):
    """DEPRECATED — use `hat init <name> --from <existing>` instead."""
    click.echo(
        "Note: 'hat template' is deprecated; use 'hat init <name> --from <existing>' instead.",
        err=True,
    )
    ctx.invoke(init, company=company, from_company=from_company)


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
    yaml1 = yaml.dump(config1, default_flow_style=False, sort_keys=True).splitlines(
        keepends=True
    )
    yaml2 = yaml.dump(config2, default_flow_style=False, sort_keys=True).splitlines(
        keepends=True
    )
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


@main.command("completion", hidden=True)
@click.argument("shell", default="zsh")
def completion_cmd(shell: str):
    """DEPRECATED — use `hat completions output <shell>` instead."""
    if shell == "zsh":
        click.echo('eval "$(_HAT_COMPLETE=zsh_source hat)"')
    elif shell == "bash":
        click.echo('eval "$(_HAT_COMPLETE=bash_source hat)"')
    else:
        click.echo(f"Unsupported shell: {shell}", err=True)


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

    # 2. Touch ID for sudo (macOS only)
    from hat.platform import SYSTEM

    if SYSTEM == "Darwin":
        pam_file = Path("/etc/pam.d/sudo_local")
        if pam_file.exists() and "pam_tid.so" in pam_file.read_text():
            click.echo("  [OK] Touch ID for sudo (already enabled)")
        else:
            if click.confirm(
                "\n  Enable Touch ID for sudo? (uses fingerprint instead of password)",
                default=True,
            ):
                result = subprocess.run(
                    [
                        "sudo",
                        "sh",
                        "-c",
                        'echo "auth       sufficient     pam_tid.so" > /etc/pam.d/sudo_local',
                    ],
                    capture_output=False,
                )
                if result.returncode == 0:
                    click.echo("  [OK] Touch ID for sudo enabled")
                else:
                    click.echo("  [SKIP] Could not enable Touch ID")
            else:
                click.echo("  [SKIP] Touch ID for sudo")
    else:
        click.echo("  [SKIP] Touch ID (macOS only)")

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


HELP_TOPICS = {
    "ssh": """SSH Management

  Configure:
    hat ssh config <company> --default-user deploy --default-key my-key
    hat ssh config <company> --jump deploy@bastion.acme.com

  Add hosts:
    hat ssh add <company> <name> <address> [-u USER] [-p PORT] [-k KEY]

  Connect:
    hat ssh connect <company> <host>

  List & manage:
    hat ssh list [company]
    hat ssh remove <company> <host>
    hat ssh generate-config [company]  # for ~/.ssh/config""",
    "vpn": """VPN Management

  Configure:
    hat vpn config <company> --provider wireguard
    hat vpn config <company> --provider tailscale

  Connect/disconnect:
    hat vpn up <company> [-y]
    hat vpn down <company> [-y]

  Status:
    hat vpn status [company]

  Supported: wireguard, amnezia, tailscale""",
    "secrets": """Secret Management

  Store:
    hat secret set keychain:<name>              paste, Ctrl-D
    hat secret set keychain:<name> -f file.pem  from file
    hat config add-secret <company> <path> <name>

  Retrieve:
    hat secret get keychain:<name>

  List & scan:
    hat secret list [--company NAME] [--check]
    hat secret scan

  Backends: keychain:<name>, bitwarden:<item>[/password|/notes|/field/<name>]""",
    "package": """Package Management

  Setup:
    hat package init             generate ~/projects/common/tools.yaml
    hat package list             show all with install status
    hat package install          install/update everything

  Manage:
    hat package add brew kubectl
    hat package add pipx ansible
    hat package add npm @bitwarden/cli
    hat package remove brew k9s

  Package managers: brew, pipx (uv tool), npm

  Note: `hat tools …` still works as a hidden alias for backward compat.""",
    "net": """Network Tools

    hat net domain example.com     WHOIS + RDAP (expiry, registrar)
    hat net cert example.com       SSL certificate (chain, self-signed, expiry)
    hat net ip 8.8.8.8             IP geolocation, ISP
    hat net dns example.com        A, AAAA, MX, NS, CNAME, TXT records
    hat net check host.com         ping + traceroute + port check
    hat net check host -p 8080     specific ports""",
    "config": """Configuration

  Company config: ~/Library/hat/companies/<name>/config.yaml
  Common tools:   ~/projects/common/tools.yaml
  Global config:  ~/Library/hat/config.yaml

  Commands:
    hat init <company>                     create company
    hat config set <company> <path> <val>  set any field
    hat config add-ssh <company> <name>    add SSH key
    hat config add-secret <company> ...    add secret ref
    hat config validate <company>          check config
    hat template <company> --from <other>  clone config""",
}


@main.command("help")
@click.argument("topic", required=False)
def help_cmd(topic: str | None):
    """Show help for a topic.

    \b
    Topics: ssh, vpn, secrets, tools, net, config
    """
    if not topic:
        click.echo("Available topics:")
        for t in sorted(HELP_TOPICS):
            click.echo(f"  hat help {t}")
        return
    text = HELP_TOPICS.get(topic)
    if not text:
        click.echo(f"Unknown topic: {topic}")
        click.echo(f"Available: {', '.join(sorted(HELP_TOPICS))}")
        return
    click.echo(text)


@main.command("telemetry")
@click.argument("action", type=click.Choice(["on", "off", "status"]), default="status")
def telemetry_cmd(action: str):
    """Manage anonymous crash reporting (on/off/status)."""
    from hat.telemetry import is_enabled, set_enabled

    if action == "on":
        set_enabled(True)
        click.echo("Telemetry enabled.")
    elif action == "off":
        set_enabled(False)
        click.echo("Telemetry disabled.")
    else:
        click.echo(f"Telemetry: {'enabled' if is_enabled() else 'disabled'}")
        click.echo("Override with HAT_TELEMETRY=0 or `hat telemetry off`")


from hat.cli_repos import repos
from hat.cli_secret import secret_group
from hat.cli_config import config_group
from hat.cli_tools import package_group, aliases, completions, skills
from hat.cli_net import net_group
from hat.cli_ssh import ssh_group
from hat.cli_vpn import vpn_group
from hat.cli_inspect import inspect_group
from hat.cli_whatsup import whatsup_group

main.add_command(repos)
main.add_command(secret_group)
main.add_command(config_group)
main.add_command(package_group)
main.add_command(aliases)
main.add_command(completions)
main.add_command(skills)
main.add_command(net_group)
main.add_command(ssh_group)
main.add_command(vpn_group)
main.add_command(inspect_group)
main.add_command(whatsup_group)


def entrypoint():
    """Console script entrypoint — wraps main() to capture exceptions to Sentry."""
    from hat.telemetry import (
        init as _telemetry_init,
        capture_exception,
        is_first_run,
        set_enabled,
    )

    if is_first_run():
        click.echo(
            "Notice: hat sends anonymous crash reports to help fix bugs. "
            "Run `hat telemetry off` to disable.",
            err=True,
        )
        set_enabled(True)

    _telemetry_init()

    try:
        main(standalone_mode=False)
    except click.exceptions.Abort:
        raise SystemExit(1)
    except click.exceptions.ClickException as e:
        e.show()
        raise SystemExit(e.exit_code)
    except SystemExit:
        raise
    except BaseException as e:
        capture_exception(e)
        raise
