"""Interactive TUI for hat."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
from rich.panel import Panel

from hat.config import list_companies, load_company_config
from hat.state import StateManager


console = Console()


def run_tui():
    """Interactive menu."""
    while True:
        sm = StateManager()
        active = sm.active_company

        console.print(
            Panel.fit(
                f"[bold]hat[/bold] — Company Context Switcher\n"
                f"Active: [green]{active}[/green]"
                if active
                else "[bold]hat[/bold] — Company Context Switcher\nActive: [dim]none[/dim]",
                border_style="blue",
            )
        )

        companies = list_companies()
        if not companies:
            console.print(
                "[yellow]No companies configured. Run: hat init <name>[/yellow]"
            )
            return

        console.print("\n[bold]Companies:[/bold]")
        for i, name in enumerate(companies, 1):
            marker = " [green](active)[/green]" if name == active else ""
            console.print(f"  {i}. {name}{marker}")

        console.print("\n[bold]Actions:[/bold]")
        console.print(
            "  [cyan]1-{0}[/cyan] Switch company    [cyan]s[/cyan] Status    [cyan]d[/cyan] Doctor".format(
                len(companies)
            )
        )
        console.print(
            "  [cyan]v[/cyan]   VPN up/down        [cyan]h[/cyan] SSH hosts  [cyan]t[/cyan] Tools"
        )
        console.print("  [cyan]q[/cyan]   Quit")

        choice = Prompt.ask("\nChoice", default="q")

        if choice == "q":
            return
        elif choice == "s":
            _show_status(sm)
        elif choice == "d":
            _show_doctor()
        elif choice == "v":
            _vpn_toggle(sm)
        elif choice == "h":
            _show_ssh_hosts()
        elif choice == "t":
            _show_tools()
        elif choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(companies):
                _switch_company(companies[idx])

        console.print()


def _show_status(sm: StateManager):
    if not sm.active_company:
        console.print("[dim]No active context[/dim]")
        return
    table = Table(title=f"Active: {sm.active_company}")
    table.add_column("Module")
    table.add_column("Status")
    for mod in sm.activated_modules:
        table.add_row(mod, "[green]active[/green]")
    console.print(table)


def _show_doctor():
    from hat.doctor import run_checks

    results = run_checks()
    table = Table(title="Health Check")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Message")
    for r in results:
        color = {"ok": "green", "warn": "yellow", "error": "red"}[r.level]
        table.add_row(r.name, f"[{color}]{r.level}[/{color}]", r.message)
    console.print(table)


def _vpn_toggle(sm: StateManager):
    if not sm.active_company:
        console.print("[yellow]No active company[/yellow]")
        return
    config = load_company_config(sm.active_company)
    provider = config.get("vpn", {}).get("provider")
    if not provider:
        console.print("[yellow]No VPN configured[/yellow]")
        return
    action = Prompt.ask("VPN", choices=["up", "down", "status"], default="status")
    import subprocess

    subprocess.run(["hat", "vpn", action, sm.active_company])


def _show_ssh_hosts():
    import subprocess

    subprocess.run(["hat", "ssh", "list"])


def _show_tools():
    import subprocess

    subprocess.run(["hat", "tools", "list"])


def _switch_company(company: str):
    import subprocess

    subprocess.run(["hat", "on", company, "--no-vpn"])
