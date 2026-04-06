from __future__ import annotations

import click
from pathlib import Path


def _collect_config_secrets(config: dict) -> list[str]:
    """Collect all secret refs from a config — *_ref fields + keychain: entries in ssh.keys."""
    from hat.secrets import SecretResolver

    resolver = SecretResolver()
    refs = resolver._find_refs(config)
    for key in config.get("ssh", {}).get("keys", []):
        if isinstance(key, str) and (
            key.startswith("keychain:") or key.startswith("bitwarden:")
        ):
            refs.append(key)
    return refs


def _all_known_refs() -> list[str]:
    """All known secret refs — from registry + company configs."""
    from hat.secret_registry import load as load_registry
    from hat.config import list_companies, load_company_config

    refs = set(load_registry())
    for company in list_companies():
        try:
            config = load_company_config(company)
            refs.update(_collect_config_secrets(config))
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
@click.option(
    "--file",
    "-f",
    "file_path",
    type=click.Path(exists=True),
    help="Read value from file",
)
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

    backend, path = parse_secret_ref(ref)

    if file_path:
        value = Path(file_path).read_text()
    else:
        click.echo("Enter secret value (paste multiline, then Ctrl-D when done):")
        import sys

        value = sys.stdin.read()

    if backend == "keychain":
        encoded = base64.b64encode(value.encode()).decode()
        from hat.platform import store_secret

        if store_secret(path, encoded):
            register(ref)
            click.echo(f"Stored: {path}")
        else:
            click.echo(f"Failed to store: {path}")
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
    log_event(
        "secret-get", "keychain" if ref.startswith("keychain:") else "bitwarden", [ref]
    )
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
        refs = sorted(set(_collect_config_secrets(config)))
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
        refs = _collect_config_secrets(config)
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
        click.echo("\n  (not assigned to a company):")
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

    backend, path = parse_secret_ref(ref)

    if backend == "keychain":
        from hat.platform import delete_secret

        if delete_secret(path):
            click.echo(f"Deleted from credential store: {path}")
        else:
            click.echo(f"Not found in credential store: {path}")
    elif backend == "bitwarden":
        click.echo("Delete Bitwarden secrets via the bw CLI or web vault.")

    unregister(ref)
    click.echo(f"Removed from registry: {ref}")


@secret_group.command("scan")
def secret_scan():
    """Find hat secrets already in Keychain and register them.

    Scans company configs for *_ref fields and tries to resolve each one.
    Any that exist in Keychain are added to the registry.
    """
    from hat.config import list_companies, load_company_config
    from hat.secrets import SecretResolver
    from hat.secret_registry import register

    resolver = SecretResolver()
    found = []

    for name in list_companies():
        try:
            config = load_company_config(name)
        except Exception:
            continue
        refs = _collect_config_secrets(config)
        for ref in refs:
            try:
                resolver._resolve_one(ref)
                register(ref)
                if ref not in found:
                    found.append(ref)
            except Exception:
                pass

    if found:
        click.echo(f"Registered {len(found)} secret(s):")
        for ref in sorted(set(found)):
            click.echo(f"  {ref}")
    else:
        click.echo("No accessible secrets found in company configs.")


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
