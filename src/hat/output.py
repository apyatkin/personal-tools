"""Consistent colored output helpers."""

from __future__ import annotations

import click


def header(text: str):
    click.echo(click.style(f"\n  {text}", bold=True))


def item(name: str, value: str, width: int = 20):
    click.echo(f"    {name:<{width}} {value}")


def ok(text: str):
    click.echo(f"    {click.style('OK', fg='green')}  {text}")


def warn(text: str):
    click.echo(f"    {click.style('WARN', fg='yellow')}  {text}")


def fail(text: str):
    click.echo(f"    {click.style('FAIL', fg='red')}  {text}")


def status_badge(label: str, active: bool) -> str:
    color = "green" if active else "red"
    state = "active" if active else "inactive"
    return f"{label} [{click.style(state, fg=color)}]"
