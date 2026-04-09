from __future__ import annotations

import click
from pathlib import Path

from hat.config import load_company_config, save_company_config, set_nested


@click.group("config")
def config_group():
    """Modify company configs without editing YAML."""


@config_group.command("set")
@click.argument("company")
@click.argument("path")
@click.argument("value")
def config_set(company: str, path: str, value: str):
    """Set a config value. Use dotted paths (e.g. cloud.nomad.addr).

    \b
    The value is parsed as YAML, so lists, booleans, and numbers work:
      hat config set acme venv.packages '[ansible, ansible-lint]'
      hat config set acme venv.enabled true
      hat config set acme some.port 8080
      hat config set acme some.name "plain string"
    """
    import yaml

    config = load_company_config(company)
    try:
        parsed = yaml.safe_load(value)
    except yaml.YAMLError:
        parsed = value
    set_nested(config, path, parsed)
    save_company_config(company, config)
    click.echo(f"{company}: {path} = {parsed!r}")


@config_group.command("add-ssh")
@click.argument("company")
@click.argument("keychain_name")
@click.option(
    "--file", "-f", "file_path", type=click.Path(exists=True), help="Read key from file"
)
@click.option(
    "--existing", is_flag=True, help="Key already in Keychain, just add ref to config"
)
def config_add_ssh(
    company: str, keychain_name: str, file_path: str | None, existing: bool
):
    """Store SSH key in Keychain and add ref to company config.

    \b
    Three modes:
      hat config add-ssh acme key -f ~/.ssh/key    store from file
      hat config add-ssh acme key                  paste key, Ctrl-D
      hat config add-ssh acme key --existing       key already in Keychain

    \b
    Examples:
      hat config add-ssh 3205 3205-sshkey --existing
      hat config add-ssh acme acme-sshkey -f ~/.ssh/acme_ed25519
    """
    if not existing:
        import base64

        if file_path:
            value = Path(file_path).read_text()
        else:
            click.echo("Paste SSH private key (Ctrl-D when done):")
            import sys

            value = sys.stdin.read()

        encoded = base64.b64encode(value.encode()).decode()
        from hat.platform import store_secret

        if store_secret(keychain_name, encoded):
            click.echo(f"Stored: {keychain_name}")
        else:
            click.echo(f"Failed to store: {keychain_name}")

    from hat.secret_registry import register

    register(f"keychain:{keychain_name}")

    config = load_company_config(company)
    set_nested(config, "ssh.keys[+]", f"keychain:{keychain_name}")
    save_company_config(company, config)
    click.echo(f"{company}: added keychain:{keychain_name} to ssh.keys")


@config_group.command("add-secret")
@click.argument("company")
@click.argument("config_path")
@click.argument("keychain_name")
@click.option(
    "--file",
    "-f",
    "file_path",
    type=click.Path(exists=True),
    help="Read value from file",
)
def config_add_secret(
    company: str, config_path: str, keychain_name: str, file_path: str | None
):
    """Store secret in keychain and add ref to company config.

    Examples:

      hat config add-secret acme cloud.nomad.token_ref acme-nomad-token

      hat config add-secret acme git.identity.ssh_key acme-sshkey -f ~/.ssh/key
    """
    import base64

    if file_path:
        value = Path(file_path).read_text()
    else:
        click.echo("Enter secret value (paste multiline, then Ctrl-D when done):")
        import sys

        value = sys.stdin.read()

    encoded = base64.b64encode(value.encode()).decode()
    from hat.platform import store_secret

    store_secret(keychain_name, encoded)

    from hat.secret_registry import register

    register(f"keychain:{keychain_name}")

    config = load_company_config(company)
    set_nested(config, config_path, f"keychain:{keychain_name}")
    save_company_config(company, config)
    click.echo(f"Stored in keychain: {keychain_name}")
    click.echo(f"{company}: {config_path} = keychain:{keychain_name}")


@config_group.command("add-git-source")
@click.argument("company")
@click.argument("provider", type=click.Choice(["gitlab", "github"]))
@click.argument("host_or_org")
@click.option("--group", default=None, help="GitLab group (defaults to host_or_org)")
@click.option("--token", "token_name", default=None, help="Keychain name for token")
def config_add_git_source(
    company: str,
    provider: str,
    host_or_org: str,
    group: str | None,
    token_name: str | None,
):
    """Add a git source (GitLab or GitHub) to company config.

    \b
    Examples:
      hat config add-git-source 3205 gitlab gitlab.3205.team --group infra --token 3205-gitlab-token
      hat config add-git-source acme github acme-org --token acme-github-pat
    """
    config = load_company_config(company)
    if "git" not in config:
        config["git"] = {}
    if "sources" not in config["git"]:
        config["git"]["sources"] = []

    source: dict = {"provider": provider}
    if provider == "gitlab":
        source["host"] = host_or_org
        source["group"] = group or host_or_org
    elif provider == "github":
        source["org"] = host_or_org

    if token_name:
        source["token_ref"] = f"keychain:{token_name}"

    config["git"]["sources"].append(source)
    save_company_config(company, config)
    click.echo(f"{company}: added {provider} source ({host_or_org})")


@config_group.command("validate")
@click.argument("company")
def config_validate(company: str):
    """Validate a company config."""
    from hat.validate import validate_config

    config = load_company_config(company)
    errors = validate_config(config)
    if not errors:
        click.echo("Config is valid.")
        return
    for e in errors:
        icon = (
            click.style("ERR", fg="red")
            if e.level == "error"
            else click.style("WARN", fg="yellow")
        )
        click.echo(f"  [{icon}] {e.path}: {e.message}")
