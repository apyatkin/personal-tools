from __future__ import annotations

import click

from hat.config import load_company_config, save_company_config, set_nested


@click.group("config")
def config_group():
    """Modify company configs without editing YAML."""


@config_group.command("set")
@click.argument("company")
@click.argument("path")
@click.argument("value")
def config_set(company: str, path: str, value: str):
    """Set a config value. Use dotted paths (e.g. cloud.nomad.addr)."""
    config = load_company_config(company)
    set_nested(config, path, value)
    save_company_config(company, config)
    click.echo(f"{company}: {path} = {value}")


@config_group.command("add-ssh")
@click.argument("company")
@click.argument("keychain_name")
@click.option("--file", "-f", "file_path", type=click.Path(exists=True), help="Read key from file")
@click.option("--existing", is_flag=True, help="Key already in Keychain, just add ref to config")
def config_add_ssh(company: str, keychain_name: str, file_path: str | None, existing: bool):
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
        import subprocess

        if file_path:
            value = open(file_path).read()
        else:
            click.echo("Paste SSH private key (Ctrl-D when done):")
            import sys
            value = sys.stdin.read()

        encoded = base64.b64encode(value.encode()).decode()
        subprocess.run(
            ["security", "add-generic-password", "-s", keychain_name, "-a", keychain_name,
             "-w", encoded, "-U"],
            check=True,
        )
        click.echo(f"Stored in keychain: {keychain_name}")

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
@click.option("--file", "-f", "file_path", type=click.Path(exists=True), help="Read value from file")
def config_add_secret(company: str, config_path: str, keychain_name: str, file_path: str | None):
    """Store secret in keychain and add ref to company config.

    Examples:

      hat config add-secret acme cloud.nomad.token_ref acme-nomad-token

      hat config add-secret acme git.identity.ssh_key acme-sshkey -f ~/.ssh/key
    """
    import base64
    import subprocess

    if file_path:
        value = open(file_path).read()
    else:
        click.echo("Enter secret value (paste multiline, then Ctrl-D when done):")
        import sys
        value = sys.stdin.read()

    encoded = base64.b64encode(value.encode()).decode()
    subprocess.run(
        ["security", "add-generic-password", "-s", keychain_name, "-a", keychain_name,
         "-w", encoded, "-U"],
        check=True,
    )

    from hat.secret_registry import register
    register(f"keychain:{keychain_name}")

    config = load_company_config(company)
    set_nested(config, config_path, f"keychain:{keychain_name}")
    save_company_config(company, config)
    click.echo(f"Stored in keychain: {keychain_name}")
    click.echo(f"{company}: {config_path} = keychain:{keychain_name}")


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
        icon = click.style("ERR", fg="red") if e.level == "error" else click.style("WARN", fg="yellow")
        click.echo(f"  [{icon}] {e.path}: {e.message}")


@config_group.command("add-host")
@click.argument("company")
@click.argument("name")
@click.argument("address")
@click.option("-u", "--user", default=None, help="SSH user")
@click.option("-k", "--key", "key_ref", default=None, help="Keychain ref for SSH key (e.g. acme-db-key)")
def config_add_host(company: str, name: str, address: str, user: str | None, key_ref: str | None):
    """Add an SSH host to company config.

    Examples:

      hat config add-host acme bastion 10.0.1.1 -u deploy
      hat config add-host acme db db.internal -u postgres -k acme-db-key
    """
    from hat.config import load_company_config, save_company_config
    config = load_company_config(company)
    if "ssh" not in config:
        config["ssh"] = {}
    if "hosts" not in config["ssh"]:
        config["ssh"]["hosts"] = {}

    host_entry = {"address": address}
    if user:
        host_entry["user"] = user
    if key_ref:
        host_entry["key_ref"] = f"keychain:{key_ref}"

    config["ssh"]["hosts"][name] = host_entry
    save_company_config(company, config)
    click.echo(f"{company}: added host '{name}' ({address})")
