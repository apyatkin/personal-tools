from __future__ import annotations

import click


def _collect_all_refs() -> list[str]:
    """Collect all secret refs from all company configs."""
    from hat.config import list_companies, load_company_config
    from hat.secrets import SecretResolver
    refs = []
    resolver = SecretResolver()
    for company in list_companies():
        try:
            config = load_company_config(company)
            refs.extend(resolver._find_refs(config))
        except Exception:
            continue
    return sorted(set(refs))


def _complete_ref(ctx, param, incomplete):
    return [r for r in _collect_all_refs() if r.startswith(incomplete)]


@click.group("secret")
def secret_group():
    """Manage secrets."""


@secret_group.command("set")
@click.argument("ref", shell_complete=_complete_ref)
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
@click.argument("ref", shell_complete=_complete_ref)
def secret_get(ref: str):
    """Display a secret value."""
    from hat.secrets import SecretResolver
    from hat.activity_log import log_event
    resolver = SecretResolver()
    value = resolver._resolve_one(ref)
    log_event("secret-get", "keychain" if ref.startswith("keychain:") else "bitwarden", [ref])
    click.echo(value)


@secret_group.command("list")
@click.option("--company", default=None, help="Filter by company")
def secret_list(company: str | None):
    """List all secret refs across company configs."""
    from hat.config import list_companies, load_company_config
    from hat.secrets import SecretResolver

    companies = [company] if company else list_companies()
    resolver = SecretResolver()

    for name in companies:
        try:
            config = load_company_config(name)
        except Exception:
            continue
        refs = resolver._find_refs(config)
        if refs:
            click.echo(f"\n  {name}:")
            for ref in sorted(refs):
                click.echo(f"    {ref}")

    if not companies:
        click.echo("No companies configured.")
