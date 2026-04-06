from __future__ import annotations

import click

from hat.config import load_company_config, save_company_config


def _complete_company(ctx, param, incomplete):
    from hat.config import list_companies
    return [c for c in list_companies() if c.startswith(incomplete)]


def _complete_host(ctx, param, incomplete):
    company = ctx.params.get("company")
    if not company:
        return []
    try:
        config = load_company_config(company)
        hosts = config.get("ssh", {}).get("hosts", {})
        return [h for h in hosts if h.startswith(incomplete)]
    except Exception:
        return []


@click.group("ssh")
def ssh_group():
    """SSH management — connect, configure, manage hosts."""


@ssh_group.command("connect")
@click.argument("company", shell_complete=_complete_company)
@click.argument("host", shell_complete=_complete_host)
@click.option("-u", "--user", default=None, help="Override SSH user")
@click.option("-p", "--port", default=None, type=int, help="Override SSH port")
@click.option("-k", "--key", "key_override", default=None, help="Override key (keychain name)")
def ssh_connect(company: str, host: str, user: str | None, port: int | None, key_override: str | None):
    """SSH into a host.

    \b
    HOST can be a named host from config or a raw IP/hostname.
    Uses company defaults for user, key, and jump host.
    Use flags to override any setting.

    \b
    Examples:
      hat ssh connect 3205 bastion
      hat ssh connect 3205 webserver -u root
      hat ssh connect 3205 10.0.1.50 -u admin -p 2222
    """
    import os
    import tempfile
    from hat.secrets import SecretResolver

    config = load_company_config(company)
    ssh_config = config.get("ssh", {})

    # Resolve host
    hosts = ssh_config.get("hosts", {})
    host_entry = hosts.get(host)
    if host_entry:
        target = host_entry["address"]
        if not user:
            user = host_entry.get("user")
        if not port:
            port = host_entry.get("port")
        host_key_ref = host_entry.get("key_ref")
    else:
        target = host
        host_key_ref = None

    # Apply defaults
    if not user:
        user = ssh_config.get("default_user")
    if not port:
        port = None  # use SSH default 22

    # Determine key: override > host-specific > default
    if key_override:
        key_ref = f"keychain:{key_override}"
    elif host_key_ref:
        key_ref = host_key_ref
    else:
        key_ref = ssh_config.get("default_key_ref")

    cmd = ["ssh"]

    # Jump host
    jump_host = ssh_config.get("jump_host")
    if jump_host:
        jump_user = ssh_config.get("jump_user")
        jump = f"{jump_user}@{jump_host}" if jump_user else jump_host
        cmd.extend(["-J", jump])

    # Key
    if key_ref:
        resolver = SecretResolver()
        try:
            key_data = resolver._resolve_one(key_ref)
            fd, key_path = tempfile.mkstemp(prefix="hat-ssh-", suffix=".key")
            os.write(fd, key_data.encode())
            os.close(fd)
            os.chmod(key_path, 0o600)
            cmd.extend(["-i", key_path])
        except Exception as e:
            click.echo(f"Warning: could not load key {key_ref}: {e}")

    if port:
        cmd.extend(["-p", str(port)])
    if user:
        cmd.extend(["-l", user])
    cmd.append(target)

    from hat.activity_log import log_event
    log_event("ssh", company, [host])
    os.execvp("ssh", cmd)


def _show_hosts_for_company(company: str) -> bool:
    """Show SSH hosts for a company. Returns True if any hosts found."""
    from hat.output import header, item
    config = load_company_config(company)
    ssh_config = config.get("ssh", {})

    defaults = []
    if ssh_config.get("default_user"):
        defaults.append(f"user: {ssh_config['default_user']}")
    if ssh_config.get("default_key_ref"):
        defaults.append(f"key: {ssh_config['default_key_ref']}")
    if ssh_config.get("jump_host"):
        jump = ssh_config["jump_host"]
        if ssh_config.get("jump_user"):
            jump = f"{ssh_config['jump_user']}@{jump}"
        defaults.append(f"jump: {jump}")

    hosts = ssh_config.get("hosts", {})
    if not hosts:
        return False

    header(company)
    if defaults:
        item("defaults", ", ".join(defaults))
    for name, entry in sorted(hosts.items()):
        addr = entry.get("address", "?")
        parts = [addr]
        if entry.get("user"):
            parts.append(f"user={entry['user']}")
        if entry.get("port"):
            parts.append(f"port={entry['port']}")
        if entry.get("key_ref"):
            parts.append(f"key={entry['key_ref']}")
        item(name, " ".join(parts))
    return True


@ssh_group.command("list")
@click.argument("company", required=False, shell_complete=_complete_company)
def ssh_list(company: str | None):
    """List SSH hosts.

    \b
    Without company, lists hosts for all companies.
    With company, lists hosts for that company only.

    \b
    Examples:
      hat ssh list
      hat ssh list 3205

    \b
    To connect:
      hat ssh connect <company> <host>
    """
    from hat.config import list_companies

    companies = [company] if company else list_companies()
    found = False

    for name in companies:
        try:
            if _show_hosts_for_company(name):
                found = True
        except Exception:
            continue

    if not found:
        click.echo("No SSH hosts configured.")
        click.echo("Add one: hat ssh add <company> <name> <address>")
        return

    click.echo(f"\n  Connect: hat ssh connect <company> <host>")


@ssh_group.command("add")
@click.argument("company", shell_complete=_complete_company)
@click.argument("name")
@click.argument("address")
@click.option("-u", "--user", default=None, help="SSH user (overrides company default)")
@click.option("-p", "--port", default=None, type=int, help="SSH port (default: 22)")
@click.option("-k", "--key", "key_ref", default=None, help="Keychain name for SSH key")
def ssh_add(company: str, name: str, address: str, user: str | None, port: int | None, key_ref: str | None):
    """Add an SSH host.

    \b
    Examples:
      hat ssh add 3205 bastion 10.0.1.1
      hat ssh add 3205 db db.internal -u postgres -p 5432
      hat ssh add 3205 web 10.0.1.10 -u root -k 3205-web-key
    """
    config = load_company_config(company)
    if "ssh" not in config:
        config["ssh"] = {}
    if "hosts" not in config["ssh"]:
        config["ssh"]["hosts"] = {}

    entry = {"address": address}
    if user:
        entry["user"] = user
    if port:
        entry["port"] = port
    if key_ref:
        entry["key_ref"] = f"keychain:{key_ref}"

    config["ssh"]["hosts"][name] = entry
    save_company_config(company, config)
    click.echo(f"{company}: added host '{name}' ({address})")


@ssh_group.command("remove")
@click.argument("company", shell_complete=_complete_company)
@click.argument("name", shell_complete=_complete_host)
def ssh_remove(company: str, name: str):
    """Remove an SSH host.

    \b
    Example:
      hat ssh remove 3205 old-server
    """
    config = load_company_config(company)
    hosts = config.get("ssh", {}).get("hosts", {})
    if name not in hosts:
        click.echo(f"Host '{name}' not found in {company}.")
        return
    del hosts[name]
    save_company_config(company, config)
    click.echo(f"{company}: removed host '{name}'")


@ssh_group.command("generate-config")
@click.argument("company", required=False, shell_complete=_complete_company)
def ssh_generate_config(company: str | None):
    """Generate ~/.ssh/config entries for company hosts.

    \b
    Examples:
      hat ssh generate-config acme
      hat ssh generate-config          # all companies
    """
    from hat.config import list_companies as _list

    companies = [company] if company else _list()
    lines = ["# Generated by hat - do not edit manually", ""]

    for name in companies:
        try:
            config = load_company_config(name)
        except Exception:
            continue
        ssh = config.get("ssh", {})
        hosts = ssh.get("hosts", {})
        if not hosts:
            continue

        lines.append(f"# --- {name} ---")
        jump = ssh.get("jump_host")
        jump_user = ssh.get("jump_user")
        default_user = ssh.get("default_user")

        for host_name, entry in sorted(hosts.items()):
            alias = f"{name}-{host_name}"
            lines.append(f"Host {alias}")
            lines.append(f"    HostName {entry['address']}")
            user = entry.get("user") or default_user
            if user:
                lines.append(f"    User {user}")
            port = entry.get("port")
            if port:
                lines.append(f"    Port {port}")
            if jump:
                proxy = f"{jump_user}@{jump}" if jump_user else jump
                lines.append(f"    ProxyJump {proxy}")
            lines.append("")

    output = "\n".join(lines)
    click.echo(output)
    click.echo("# Append to ~/.ssh/config:")
    click.echo("# hat ssh generate-config >> ~/.ssh/config")


@ssh_group.command("config")
@click.argument("company", shell_complete=_complete_company)
@click.option("--default-user", default=None, help="Set default SSH user")
@click.option("--default-key", default=None, help="Set default SSH key (keychain name)")
@click.option("--jump", default=None, help="Set jump host (address or user@address)")
@click.option("--jump-key", default=None, help="Set jump host key (keychain name)")
def ssh_config_cmd(company: str, default_user: str | None, default_key: str | None, jump: str | None, jump_key: str | None):
    """Show or set SSH defaults for a company.

    \b
    Without options, shows current config.
    With options, sets the values.

    \b
    Examples:
      hat ssh config 3205
      hat ssh config 3205 --default-user deploy
      hat ssh config 3205 --default-key 3205-sshkey
      hat ssh config 3205 --jump deploy@bastion.3205.com
      hat ssh config 3205 --jump bastion.3205.com --jump-key 3205-bastion
    """
    config = load_company_config(company)
    if "ssh" not in config:
        config["ssh"] = {}
    ssh = config["ssh"]
    changed = False

    if default_user:
        ssh["default_user"] = default_user
        changed = True
    if default_key:
        ssh["default_key_ref"] = f"keychain:{default_key}"
        changed = True
    if jump:
        if "@" in jump:
            user, host = jump.split("@", 1)
            ssh["jump_user"] = user
            ssh["jump_host"] = host
        else:
            ssh["jump_host"] = jump
        changed = True
    if jump_key:
        ssh["jump_key_ref"] = f"keychain:{jump_key}"
        changed = True

    if changed:
        save_company_config(company, config)
        click.echo(f"{company}: SSH config updated.")

    # Always show current config
    click.echo(f"\n  SSH config for {company}:")
    click.echo(f"    default_user:    {ssh.get('default_user', '(not set)')}")
    click.echo(f"    default_key_ref: {ssh.get('default_key_ref', '(not set)')}")
    click.echo(f"    jump_host:       {ssh.get('jump_host', '(not set)')}")
    click.echo(f"    jump_user:       {ssh.get('jump_user', '(not set)')}")
    click.echo(f"    jump_key_ref:    {ssh.get('jump_key_ref', '(not set)')}")
    click.echo(f"    keys:            {len(ssh.get('keys', []))} loaded")
    click.echo(f"    hosts:           {len(ssh.get('hosts', {}))} configured")
