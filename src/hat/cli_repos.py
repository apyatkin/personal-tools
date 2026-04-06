from __future__ import annotations

import click

from hat.config import load_company_config, list_companies
from hat.secrets import SecretResolver
from hat.repos import (
    clone_repos,
    pull_repos,
    sync_repos,
    get_repos_dir,
    list_remote_repos,
)


@click.group()
def repos():
    """Manage company git repositories."""


@repos.command("clone")
@click.argument("company")
@click.option("--concurrency", "-j", default=4, help="Parallel clone workers")
def repos_clone(company: str, concurrency: int):
    """Clone all repos from configured git sources."""
    config = load_company_config(company)
    sources = config.get("git", {}).get("sources", [])
    if not sources:
        click.echo("No git sources configured.")
        return

    resolver = SecretResolver()
    secrets = resolver.resolve_refs(config)
    identity = config.get("git", {}).get("identity")

    click.echo(f"Cloning repos for {company}...")
    results = clone_repos(company, sources, secrets, identity, concurrency)

    cloned = [r for r in results if r["status"] == "cloned"]
    exists = [r for r in results if r["status"] == "exists"]
    failed = [r for r in results if r["status"] == "failed"]

    click.echo(
        f"Done: {len(cloned)} cloned, {len(exists)} already existed, {len(failed)} failed"
    )
    for f in failed:
        click.echo(f"  FAIL: {f['path']} — {f['reason']}")


@repos.command("pull")
@click.argument("company", required=False)
@click.option("--all", "pull_all", is_flag=True, help="Pull all companies")
@click.option("--tag", default=None, help="Pull companies with this tag")
def repos_pull(company: str | None, pull_all: bool, tag: str | None):
    """Pull updates for company repos."""
    if pull_all:
        companies = list_companies()
    elif tag:
        companies = list_companies(tag=tag)
    elif company:
        companies = [company]
    else:
        click.echo("Specify a company or --all")
        return

    for name in companies:
        repos_dir = get_repos_dir(name)
        if not repos_dir.exists():
            click.echo(f"{name}: no repos directory")
            continue
        click.echo(f"Pulling {name}...")
        results = pull_repos(repos_dir)
        updated = [r for r in results if r["status"] == "updated"]
        skipped = [r for r in results if r["status"] == "skipped"]
        failed = [r for r in results if r["status"] == "failed"]
        click.echo(
            f"  {len(updated)} updated, {len(skipped)} skipped, {len(failed)} failed"
        )
        for s in skipped:
            click.echo(f"  SKIP: {s['path']} — {s['reason']}")
        for f in failed:
            click.echo(f"  FAIL: {f['path']} — {f['reason']}")


@repos.command("sync")
@click.argument("company")
@click.option("--concurrency", "-j", default=4, help="Parallel workers")
def repos_sync(company: str, concurrency: int):
    """Clone new repos and pull updates for existing ones."""
    config = load_company_config(company)
    sources = config.get("git", {}).get("sources", [])
    if not sources:
        click.echo("No git sources configured.")
        return

    resolver = SecretResolver()
    secrets = resolver.resolve_refs(config)
    identity = config.get("git", {}).get("identity")

    click.echo(f"Syncing repos for {company}...")
    results = sync_repos(company, sources, secrets, identity, concurrency)

    cloned = [r for r in results["clone"] if r["status"] == "cloned"]
    pulled = [r for r in results["pull"] if r["status"] == "updated"]
    failed = [r for r in results["clone"] + results["pull"] if r["status"] == "failed"]

    click.echo(
        f"Done: {len(cloned)} cloned, {len(pulled)} pulled, {len(failed)} failed"
    )
    for f in failed:
        click.echo(f"  FAIL: {f['path']} — {f.get('reason', 'unknown')}")


@repos.command("list")
@click.argument("company")
def repos_list(company: str):
    """List local vs remote repos."""
    config = load_company_config(company)
    sources = config.get("git", {}).get("sources", [])
    if not sources:
        click.echo("No git sources configured.")
        return

    resolver = SecretResolver()
    secrets = resolver.resolve_refs(config)
    repos_dir = get_repos_dir(company)

    for source in sources:
        remote_repos = list_remote_repos(source, secrets)
        provider = source.get("provider")
        group = source.get("group") or source.get("org")
        click.echo(f"\n{provider}: {group}")
        for repo in remote_repos:
            local_path = repos_dir / repo["relative_path"]
            marker = "  [cloned]" if local_path.exists() else "  [missing]"
            click.echo(f"  {repo['relative_path']}{marker}")
