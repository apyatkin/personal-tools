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
@click.option("--company", default=None, help="Filter by company")
@click.option("--check", is_flag=True, help="Verify each secret is accessible")
def secret_list(company: str | None, check: bool):
    """List secrets referenced in company configs.

    Shows every *_ref field found in company configs, grouped by company.
    Use --check to verify each secret is actually accessible in Keychain/Bitwarden.

    \b
    Examples:
      hat secret list                  all companies
      hat secret list --company acme   just acme
      hat secret list --check          verify accessibility
    """
    from hat.config import list_companies, load_company_config
    from hat.secrets import SecretResolver

    companies = [company] if company else list_companies()
    resolver = SecretResolver()
    found = False

    for name in companies:
        try:
            config = load_company_config(name)
        except Exception:
            continue
        refs = resolver._find_refs(config)
        if refs:
            found = True
            click.echo(f"\n  {name}:")
            for ref in sorted(set(refs)):
                if check:
                    try:
                        resolver._resolve_one(ref)
                        status = click.style("OK", fg="green")
                    except Exception:
                        status = click.style("MISSING", fg="red")
                    click.echo(f"    {ref}  [{status}]")
                else:
                    click.echo(f"    {ref}")

    if not found:
        if company:
            click.echo(f"No secrets referenced in {company} config.")
        else:
            click.echo("No secrets referenced in any company config.")
            click.echo("Add secrets with: hat config add-secret <company> <path> <name>")
