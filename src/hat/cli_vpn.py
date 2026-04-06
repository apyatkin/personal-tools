from __future__ import annotations

import click

import shutil

from hat.config import load_company_config, save_company_config


def _find_binary(name: str) -> str:
    """Find full path of a binary. sudo uses restricted PATH, so we need absolute paths."""
    path = shutil.which(name)
    if path:
        return path
    # Common Homebrew locations
    for prefix in ["/opt/homebrew/bin", "/usr/local/bin"]:
        candidate = f"{prefix}/{name}"
        import os
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return name  # fallback to bare name


def _complete_company(ctx, param, incomplete):
    from hat.config import list_companies
    return [c for c in list_companies() if c.startswith(incomplete)]


@click.group("vpn")
def vpn_group():
    """VPN management — configure and control VPN connections.

    \b
    Supported providers:
      wireguard    WireGuard via wg-quick
      amnezia      AmneziaVPN via amnezia-cli
      tailscale    Tailscale via tailscale CLI
    """


@vpn_group.command("config")
@click.argument("company", shell_complete=_complete_company)
@click.option("--provider", type=click.Choice(["wireguard", "amnezia", "tailscale"]), help="VPN provider")
@click.option("--config-file", "config_path", default=None, help="Path to VPN config file")
@click.option("--interface", default=None, help="WireGuard interface name")
def vpn_config(company: str, provider: str | None, config_path: str | None, interface: str | None):
    """Show or set VPN config for a company.

    \b
    Without options, shows current VPN config.
    With options, updates the config.

    \b
    Examples:
      hat vpn config 3205
      hat vpn config 3205 --provider wireguard --config-file ~/wg/3205.conf --interface wg-3205
      hat vpn config 3205 --provider amnezia --config-file ~/amnezia/3205.conf
      hat vpn config 3205 --provider tailscale
    """
    config = load_company_config(company)
    if "vpn" not in config:
        config["vpn"] = {}
    vpn = config["vpn"]
    changed = False

    if provider:
        vpn["provider"] = provider
        changed = True
        # Set default config path for wireguard/amnezia if not explicitly provided
        if provider in ("wireguard", "amnezia") and not config_path and not vpn.get("config"):
            from pathlib import Path
            default_path = str(Path.home() / "projects" / company / "wg0.conf")
            vpn["config"] = default_path
            click.echo(f"  Default config path: {default_path}")
    if config_path:
        vpn["config"] = config_path
        changed = True
    if interface:
        vpn["interface"] = interface
        changed = True

    if changed:
        save_company_config(company, config)
        # Secure VPN config file permissions
        conf_path = vpn.get("config")
        if conf_path:
            import os
            from pathlib import Path
            p = Path(conf_path).expanduser()
            if p.exists():
                os.chmod(p, 0o600)
        click.echo(f"{company}: VPN config updated.")

    click.echo(f"\n  VPN config for {company}:")
    click.echo(f"    provider:  {vpn.get('provider', '(not set)')}")
    click.echo(f"    config:    {vpn.get('config', '(not set)')}")
    click.echo(f"    interface: {vpn.get('interface', '(not set)')}")


@vpn_group.command("up")
@click.argument("company", shell_complete=_complete_company)
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation")
def vpn_up(company: str, yes: bool):
    """Connect VPN for a company.

    \b
    Examples:
      hat vpn up 3205
      hat vpn up 3205 -y     skip confirmation
    """
    import subprocess

    config = load_company_config(company)
    vpn = config.get("vpn", {})
    provider = vpn.get("provider")

    if not provider:
        click.echo(f"No VPN configured for {company}.")
        click.echo(f"Set one: hat vpn config {company} --provider wireguard --config-file /path/to/wg.conf")
        return

    config_path = vpn.get("config")

    if provider == "wireguard":
        if not config_path:
            click.echo("WireGuard requires --config-file. Set it: hat vpn config <company> --config-file /path")
            return
        cmd = ["sudo", _find_binary("wg-quick"), "up", config_path]
    elif provider == "amnezia":
        if not config_path:
            click.echo("Amnezia requires --config-file. Set it: hat vpn config <company> --config-file /path")
            return
        cmd = ["sudo", _find_binary("amnezia-cli"), "connect", config_path]
    elif provider == "tailscale":
        cmd = ["sudo", _find_binary("tailscale"), "up"]
    else:
        click.echo(f"Unknown provider: {provider}")
        return

    if not yes:
        click.confirm(f"Will run: {' '.join(cmd)}\nProceed?", default=True, abort=True)
    try:
        import os
        env = {**os.environ, "PATH": f"/opt/homebrew/bin:/usr/local/bin:{os.environ.get('PATH', '')}"}
        subprocess.run(cmd, check=True, env=env)
    except subprocess.CalledProcessError as e:
        click.echo(click.style(f"VPN connect failed (exit {e.returncode})", fg="red"))
        return
    click.echo(f"VPN connected ({provider}).")

    from hat.activity_log import log_event
    log_event("vpn-up", company, [provider])


@vpn_group.command("down")
@click.argument("company", shell_complete=_complete_company)
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation")
def vpn_down(company: str, yes: bool):
    """Disconnect VPN for a company.

    \b
    Examples:
      hat vpn down 3205
      hat vpn down 3205 -y
    """
    import subprocess

    config = load_company_config(company)
    vpn = config.get("vpn", {})
    provider = vpn.get("provider")

    if not provider:
        click.echo(f"No VPN configured for {company}.")
        return

    if provider == "wireguard":
        interface = vpn.get("interface") or vpn.get("config")
        cmd = ["sudo", _find_binary("wg-quick"), "down", interface]
    elif provider == "amnezia":
        cmd = ["sudo", _find_binary("amnezia-cli"), "disconnect"]
    elif provider == "tailscale":
        cmd = ["sudo", _find_binary("tailscale"), "down"]
    else:
        click.echo(f"Unknown provider: {provider}")
        return

    try:
        import os
        env = {**os.environ, "PATH": f"/opt/homebrew/bin:/usr/local/bin:{os.environ.get('PATH', '')}"}
        subprocess.run(cmd, check=True, env=env)
    except subprocess.CalledProcessError as e:
        click.echo(click.style(f"VPN disconnect failed (exit {e.returncode})", fg="red"))
        return
    click.echo(f"VPN disconnected ({provider}).")

    from hat.activity_log import log_event
    log_event("vpn-down", company, [provider])


@vpn_group.command("status")
@click.argument("company", required=False, shell_complete=_complete_company)
def vpn_status(company: str | None):
    """Check VPN connection status.

    \b
    Without company, shows status for all configured VPNs.
    With company, shows status for that company only.

    \b
    Examples:
      hat vpn status
      hat vpn status 3205
    """
    import subprocess
    from hat.config import list_companies

    companies = [company] if company else list_companies()

    for name in companies:
        try:
            config = load_company_config(name)
        except Exception:
            continue
        vpn = config.get("vpn", {})
        provider = vpn.get("provider")
        if not provider:
            continue

        connected = False
        if provider == "wireguard":
            interface = vpn.get("interface", "")
            result = subprocess.run(
                ["sudo", _find_binary("wg"), "show", interface],
                capture_output=True, text=True,
            )
            connected = result.returncode == 0
        elif provider == "tailscale":
            result = subprocess.run(
                [_find_binary("tailscale"), "status"],
                capture_output=True, text=True,
            )
            connected = result.returncode == 0 and "stopped" not in result.stdout.lower()
        elif provider == "amnezia":
            connected = False  # no easy status check

        status = click.style("connected", fg="green") if connected else click.style("disconnected", fg="red")
        click.echo(f"  {name}: {provider} [{status}]")
