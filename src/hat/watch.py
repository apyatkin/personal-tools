"""Real-time status dashboard."""

from __future__ import annotations

import time
import subprocess

from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel

from hat.config import list_companies, load_company_config
from hat.state import StateManager
from hat.utils import find_binary


console = Console()


def run_watch():
    """Live dashboard that auto-refreshes."""
    try:
        with Live(console=console, refresh_per_second=1) as live:
            while True:
                live.update(_build_dashboard())
                time.sleep(5)
    except KeyboardInterrupt:
        pass


def _build_dashboard() -> Table:
    sm = StateManager()

    grid = Table.grid(padding=1)
    grid.add_column()

    # Status
    active = sm.active_company or "none"
    color = "green" if sm.active_company else "dim"
    grid.add_row(
        Panel(
            f"[bold]Active:[/bold] [{color}]{active}[/{color}]\n"
            f"[bold]Modules:[/bold] {', '.join(sm.activated_modules) or 'none'}\n"
            f"[bold]Since:[/bold] {(sm.activated_at or 'n/a')[:19]}",
            title="[bold blue]hat status[/bold blue]",
            border_style="blue",
        )
    )

    # VPN status
    vpn_status = _check_vpn()
    vpn_color = "green" if vpn_status else "red"
    grid.add_row(
        Panel(
            f"VPN: [{vpn_color}]{'connected' if vpn_status else 'disconnected'}[/{vpn_color}]",
            title="[bold blue]VPN[/bold blue]",
            border_style="blue",
        )
    )

    # Companies table
    companies = list_companies()
    if companies:
        table = Table(title="Companies")
        table.add_column("Name")
        table.add_column("SSH Hosts")
        table.add_column("VPN")
        for name in companies:
            try:
                config = load_company_config(name)
                hosts = len(config.get("ssh", {}).get("hosts", {}))
                vpn = config.get("vpn", {}).get("provider", "-")
                marker = " *" if name == sm.active_company else ""
                table.add_row(f"{name}{marker}", str(hosts), vpn)
            except Exception:
                table.add_row(name, "?", "?")
        grid.add_row(table)

    grid.add_row("[dim]Refreshing every 5s. Ctrl-C to exit.[/dim]")
    return grid


def _check_vpn() -> bool:
    result = subprocess.run(
        ["sudo", find_binary("wg"), "show"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and bool(result.stdout.strip())
