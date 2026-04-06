from __future__ import annotations

import click


def _all_known_refs() -> list[str]:
    """All known secret refs — from registry + company configs."""
    from hat.secret_registry import load as load_registry
    from hat.config import list_companies, load_company_config
    from hat.secrets import SecretResolver
    refs = set(load_registry())
    resolver = SecretResolver()
    for company in list_companies():
        try:
            config = load_company_config(company)
            refs.update(resolver._find_refs(config))
        except Exception:
            continue
    return sorted(refs)


def _complete_ref(ctx, param, incomplete):
    return [r for r in _all_known_refs() if r.startswith(incomplete)]


@click.group("secret")
def secret_group():
    """Manage secrets stored in macOS Keychain or Bitwarden.

    Secrets are referenced in company configs via *_ref fields
    (e.g. token_ref: keychain:acme-token). This command manages
    those secrets.

    \b
    Backends:
      keychain:<name>                  macOS Keychain
      bitwarden:<item>                 Bitwarden (password field)
      bitwarden:<item>/password        Bitwarden password
      bitwarden:<item>/notes           Bitwarden notes
      bitwarden:<item>/field/<name>    Bitwarden custom field
    """


@secret_group.command("set")
@click.argument("ref", shell_complete=_complete_ref)
@click.option("--file", "-f", "file_path", type=click.Path(exists=True), help="Read value from file")
def secret_set(ref: str, file_path: str | None):
    """Store a secret in macOS Keychain.

    \b
    REF format: keychain:<name>

    \b
    Three ways to provide the value:
      hat secret set keychain:token              paste value, then Ctrl-D
      hat secret set keychain:sshkey -f key.pem  read from file
      echo "val" | hat secret set keychain:tok   pipe from stdin

    \b
    Examples:
      hat secret set keychain:acme-gitlab-token
      hat secret set keychain:acme-sshkey -f ~/.ssh/acme_ed25519
      hat secret set keychain:acme-vault-token

    Bitwarden secrets must be stored via the bw CLI or web vault.
    """
    from hat.secrets import parse_secret_ref
    from hat.secret_registry import register
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
        register(ref)
        click.echo(f"Stored in keychain: {path}")
    elif backend == "bitwarden":
        click.echo("Bitwarden secrets must be stored via the bw CLI or web vault.")


@secret_group.command("get")
@click.argument("ref", shell_complete=_complete_ref)
def secret_get(ref: str):
    """Display a secret value.

    \b
    Examples:
      hat secret get keychain:acme-gitlab-token
      hat secret get bitwarden:acme-vault/password
    """
    from hat.secrets import SecretResolver
    from hat.activity_log import log_event
    resolver = SecretResolver()
    value = resolver._resolve_one(ref)
    log_event("secret-get", "keychain" if ref.startswith("keychain:") else "bitwarden", [ref])
    click.echo(value)


@secret_group.command("list")
@click.option("--company", default=None, help="Show only refs used by this company")
@click.option("--check", is_flag=True, help="Verify each secret is accessible")
def secret_list(company: str | None, check: bool):
    """List all hat-managed secrets.

    Shows all secrets hat knows about — both from the secret registry
    (everything stored via hat secret set) and from company configs.
    Use --company to filter to refs used by a specific company.
    Use --check to verify each secret is actually accessible.

    \b
    Examples:
      hat secret list                  all hat secrets
      hat secret list --company acme   secrets used by acme
      hat secret list --check          verify accessibility
    """
    from hat.config import list_companies, load_company_config
    from hat.secrets import SecretResolver
    from hat.secret_registry import load as load_registry

    resolver = SecretResolver()

    if company:
        # Show refs for one company
        try:
            config = load_company_config(company)
        except Exception:
            click.echo(f"Company '{company}' not found.")
            return
        refs = sorted(set(resolver._find_refs(config)))
        if not refs:
            click.echo(f"No secrets referenced in {company} config.")
            return
        click.echo(f"\n  {company}:")
        for ref in refs:
            _print_ref(ref, check, resolver)
        return

    # Show all: registry + per-company
    registry = load_registry()
    all_refs = set(registry)

    # Collect per-company refs
    company_refs: dict[str, list[str]] = {}
    for name in list_companies():
        try:
            config = load_company_config(name)
        except Exception:
            continue
        refs = resolver._find_refs(config)
        if refs:
            company_refs[name] = sorted(set(refs))
            all_refs.update(refs)

    if not all_refs:
        click.echo("No secrets found.")
        click.echo("Store one with: hat secret set keychain:<name>")
        return

    # Show per-company
    for name, refs in sorted(company_refs.items()):
        click.echo(f"\n  {name}:")
        for ref in refs:
            _print_ref(ref, check, resolver)

    # Show registry-only secrets (not in any company config)
    config_refs = set()
    for refs in company_refs.values():
        config_refs.update(refs)
    orphans = sorted(set(registry) - config_refs)
    if orphans:
        click.echo(f"\n  (not assigned to a company):")
        for ref in orphans:
            _print_ref(ref, check, resolver)


@secret_group.command("delete")
@click.argument("ref", shell_complete=_complete_ref)
def secret_delete(ref: str):
    """Remove a secret from Keychain and the registry.

    \b
    Examples:
      hat secret delete keychain:old-token
    """
    from hat.secrets import parse_secret_ref
    from hat.secret_registry import unregister
    import subprocess
    backend, path = parse_secret_ref(ref)

    if backend == "keychain":
        result = subprocess.run(
            ["security", "delete-generic-password", "-s", path],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            click.echo(f"Deleted from keychain: {path}")
        else:
            click.echo(f"Not found in keychain: {path}")
    elif backend == "bitwarden":
        click.echo("Delete Bitwarden secrets via the bw CLI or web vault.")

    unregister(ref)
    click.echo(f"Removed from registry: {ref}")


def _print_ref(ref: str, check: bool, resolver) -> None:
    if check:
        try:
            resolver._resolve_one(ref)
            status = click.style("OK", fg="green")
        except Exception:
            status = click.style("MISSING", fg="red")
        click.echo(f"    {ref}  [{status}]")
    else:
        click.echo(f"    {ref}")
