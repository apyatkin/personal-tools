from __future__ import annotations

import click


@click.group("tools")
def tools_group():
    """Manage tools — list, add, remove, install.

    \b
    Tools are installed via three package managers:
      brew     Homebrew (native CLI tools)
      pipx     uv tool (Python tools in isolated venvs)
      npm      npm (Node.js tools)

    \b
    Tool list stored in ~/projects/common/tools.yaml
    """


@tools_group.command("list")
def tools_list():
    """List all configured tools and their install status."""
    import shutil
    from hat.common import load_common_tools

    tools = load_common_tools()
    if not tools:
        click.echo("No tools configured. Run 'hat tools init' first.")
        return

    for method in ["brew", "pipx", "npm"]:
        items = tools.get(method, [])
        if not items:
            continue
        click.echo(f"\n  {method}:")
        for tool in sorted(items):
            from hat.modules.tools import _npm_bin_name, _brew_bin_name, _pipx_bin_name

            if method == "npm":
                bin_name = _npm_bin_name(tool)
            elif method == "brew":
                bin_name = _brew_bin_name(tool)
            elif method == "pipx":
                bin_name = _pipx_bin_name(tool)
            else:
                bin_name = tool
            installed = shutil.which(bin_name) is not None
            status = (
                click.style("installed", fg="green")
                if installed
                else click.style("missing", fg="red")
            )
            click.echo(f"    {tool:30s} [{status}]")


@tools_group.command("add")
@click.argument("method", type=click.Choice(["brew", "pipx", "npm"]))
@click.argument("package")
def tools_add(method: str, package: str):
    """Add a tool to the list.

    \b
    Examples:
      hat tools add brew wireguard-tools
      hat tools add brew k9s
      hat tools add pipx black
      hat tools add npm @bitwarden/cli
    """
    from hat.common import load_common_tools, COMMON_DIR
    import yaml

    tools = load_common_tools()
    if not tools:
        tools = {"brew": [], "pipx": [], "npm": []}

    if method not in tools:
        tools[method] = []

    if package in tools[method]:
        click.echo(f"{package} already in {method} list.")
        return

    tools[method].append(package)
    tools_file = COMMON_DIR / "tools.yaml"
    tools_file.write_text(yaml.dump(tools, default_flow_style=False, sort_keys=False))
    click.echo(f"Added {package} to {method}.")
    click.echo("Run 'hat tools install' to install it.")


@tools_group.command("remove")
@click.argument("method", type=click.Choice(["brew", "pipx", "npm"]))
@click.argument("package")
def tools_remove(method: str, package: str):
    """Remove a tool from the list (does not uninstall).

    \b
    Examples:
      hat tools remove brew k9s
      hat tools remove pipx black
    """
    from hat.common import load_common_tools, COMMON_DIR
    import yaml

    tools = load_common_tools()
    if not tools or method not in tools or package not in tools.get(method, []):
        click.echo(f"{package} not found in {method} list.")
        return

    tools[method].remove(package)
    tools_file = COMMON_DIR / "tools.yaml"
    tools_file.write_text(yaml.dump(tools, default_flow_style=False, sort_keys=False))
    click.echo(f"Removed {package} from {method} list.")


@tools_group.command("install")
def tools_install():
    """Install/update all tools from ~/projects/common/tools.yaml."""
    from hat.common import load_common_tools

    tools_config = load_common_tools()
    if not tools_config:
        click.echo("No tools configured. Run 'hat tools init' first.")
        return
    from hat.modules.tools import ToolsModule

    mod = ToolsModule()
    mod.activate(tools_config, secrets={})


@tools_group.command("check")
def tools_check():
    """Check which tools are installed vs missing."""
    import shutil
    from hat.common import load_common_tools

    tools = load_common_tools()
    if not tools:
        click.echo("No tools configured. Run 'hat tools init' first.")
        return

    installed = 0
    missing = 0
    for method in ["brew", "pipx", "npm"]:
        for tool in tools.get(method, []):
            from hat.modules.tools import _npm_bin_name

            bin_name = _npm_bin_name(tool) if method == "npm" else tool
            if shutil.which(bin_name):
                installed += 1
            else:
                missing += 1
                click.echo(f"  missing: {tool} ({method})")

    click.echo(f"\n  {installed} installed, {missing} missing")
    if missing:
        click.echo("  Run 'hat tools install' to install missing tools.")


@tools_group.command("init")
def tools_init():
    """Generate ~/projects/common/tools.yaml with default tools."""
    from hat.common import generate_tools_config

    path = generate_tools_config()
    click.echo(f"Generated {path}")
    click.echo("View with: hat tools list")


@click.group()
def aliases():
    """Manage shell aliases."""


@aliases.command("generate")
def aliases_generate():
    """Generate ~/projects/common/aliases.sh."""
    from hat.common import generate_aliases

    path = generate_aliases()
    click.echo(f"Generated {path}")


@click.group()
def completions():
    """Manage shell completions — generate, output."""


@completions.command("generate")
def completions_generate():
    """Generate ~/projects/common/completions.sh."""
    from hat.common import generate_completions

    path = generate_completions()
    click.echo(f"Generated {path}")


@completions.command("output")
@click.argument("shell", default="zsh", type=click.Choice(["zsh", "bash"]))
def completions_output(shell: str):
    """Output the eval-able completion snippet for the given shell.

    \b
    Example:
      eval "$(hat completions output zsh)"
    """
    if shell == "zsh":
        click.echo('eval "$(_HAT_COMPLETE=zsh_source hat)"')
    else:
        click.echo('eval "$(_HAT_COMPLETE=bash_source hat)"')


@click.group()
def skills():
    """Manage Claude Code skills."""


@skills.command("deploy")
def skills_deploy():
    """Deploy skills to ~/projects/.claude/skills/ as symlinks."""
    from hat.skills import get_skills_source, deploy_skills

    source = get_skills_source()
    if not source.exists():
        click.echo(f"Skills source not found: {source}")
        return
    deployed = deploy_skills(source)
    if deployed:
        click.echo(f"Deployed {len(deployed)} skills: {', '.join(deployed)}")
    else:
        click.echo("All skills already deployed.")
