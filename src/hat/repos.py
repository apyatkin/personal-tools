from __future__ import annotations

import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import httpx


def get_repos_dir(company: str) -> Path:
    return Path.home() / "projects" / company / "repos"


def list_remote_repos(source: dict, secrets: dict) -> list[dict]:
    provider = source["provider"]
    if provider == "gitlab":
        return _list_gitlab(source, secrets)
    elif provider == "github":
        return _list_github(source, secrets)
    else:
        raise ValueError(f"Unknown git provider: {provider}")


def _list_gitlab(source: dict, secrets: dict) -> list[dict]:
    host = source["host"]
    group = source["group"]
    token = secrets.get(source.get("token_ref", ""), "")
    base_url = f"https://{host}/api/v4"

    repos = []
    page = 1
    with httpx.Client() as client:
        while True:
            resp = client.get(
                f"{base_url}/groups/{group}/projects",
                params={"include_subgroups": "true", "per_page": 100, "page": page},
                headers={"PRIVATE-TOKEN": token},
            )
            resp.raise_for_status()
            projects = resp.json()
            if not projects:
                break

            for proj in projects:
                full_path = proj["path_with_namespace"]
                # Strip the group prefix to get relative path
                prefix = group + "/"
                if full_path.startswith(prefix):
                    relative = full_path[len(prefix) :]
                else:
                    relative = full_path.rsplit("/", 1)[-1]

                repos.append(
                    {
                        "relative_path": relative,
                        "clone_url": proj["ssh_url_to_repo"],
                    }
                )

            next_page = resp.headers.get("x-next-page", "")
            if not next_page:
                break
            page = int(next_page)

    return repos


def _list_github(source: dict, secrets: dict) -> list[dict]:
    org = source["org"]
    token = secrets.get(source.get("token_ref", ""), "")

    per_page = 100
    repos = []
    page = 1
    with httpx.Client() as client:
        while True:
            resp = client.get(
                f"https://api.github.com/orgs/{org}/repos",
                params={"per_page": per_page, "page": page},
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            items = resp.json()
            if not items:
                break

            for repo in items:
                repos.append(
                    {
                        "relative_path": repo["name"],
                        "clone_url": repo["ssh_url"],
                    }
                )

            if len(items) < per_page:
                break

            page += 1

    return repos


def clone_repos(
    company: str,
    sources: list[dict],
    secrets: dict,
    git_identity: dict | None = None,
    concurrency: int = 4,
) -> list[dict]:
    repos_dir = get_repos_dir(company)
    repos_dir.mkdir(parents=True, exist_ok=True)

    all_repos = []
    for source in sources:
        remote_repos = list_remote_repos(source, secrets)
        all_repos.extend(remote_repos)

    results = []

    def _clone_one(repo: dict) -> dict:
        target = repos_dir / repo["relative_path"]
        if target.exists():
            return {"path": str(target), "status": "exists"}
        target.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            ["git", "clone", repo["clone_url"], str(target)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return {
                "path": str(target),
                "status": "failed",
                "reason": result.stderr.strip(),
            }

        if git_identity:
            subprocess.run(
                ["git", "config", "user.name", git_identity["name"]],
                cwd=str(target),
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", git_identity["email"]],
                cwd=str(target),
                capture_output=True,
            )

        return {"path": str(target), "status": "cloned"}

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = {pool.submit(_clone_one, r): r for r in all_repos}
        for future in as_completed(futures):
            results.append(future.result())

    return results


def sync_repos(
    company: str,
    sources: list[dict],
    secrets: dict,
    git_identity: dict | None = None,
    concurrency: int = 4,
) -> dict[str, list[dict]]:
    clone_results = clone_repos(company, sources, secrets, git_identity, concurrency)
    repos_dir = get_repos_dir(company)
    pull_results = pull_repos(repos_dir, concurrency)
    return {"clone": clone_results, "pull": pull_results}


def pull_repos(repos_dir: Path, concurrency: int = 4) -> list[dict]:
    if not repos_dir.exists():
        return []

    git_dirs = [p.parent for p in repos_dir.rglob(".git") if p.is_dir()]

    results = []

    def _pull_one(repo_path: Path) -> dict:
        # Check for uncommitted changes
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(repo_path),
            capture_output=True,
            text=True,
        )
        if status_result.stdout.strip():
            return {
                "path": str(repo_path),
                "status": "skipped",
                "reason": "uncommitted changes",
            }

        pull_result = subprocess.run(
            ["git", "pull", "--ff-only"],
            cwd=str(repo_path),
            capture_output=True,
            text=True,
        )
        if pull_result.returncode != 0:
            return {
                "path": str(repo_path),
                "status": "failed",
                "reason": pull_result.stderr.strip(),
            }
        return {"path": str(repo_path), "status": "updated"}

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = {pool.submit(_pull_one, d): d for d in git_dirs}
        for future in as_completed(futures):
            results.append(future.result())

    return results
