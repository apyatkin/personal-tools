from pathlib import Path
from unittest.mock import patch, MagicMock

from hat.repos import (
    list_remote_repos,
    pull_repos,
    get_repos_dir,
)


def test_get_repos_dir():
    path = get_repos_dir("acme")
    assert path == Path.home() / "projects" / "acme" / "repos"


def test_list_remote_gitlab():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {
            "path_with_namespace": "infrastructure/deploy/charts",
            "ssh_url_to_repo": "git@gitlab.acme.com:infrastructure/deploy/charts.git",
        },
        {
            "path_with_namespace": "infrastructure/terraform-modules",
            "ssh_url_to_repo": "git@gitlab.acme.com:infrastructure/terraform-modules.git",
        },
    ]
    mock_response.headers = {}

    source = {
        "provider": "gitlab",
        "host": "gitlab.acme.com",
        "group": "infrastructure",
        "token_ref": "keychain:token",
    }
    secrets = {"keychain:token": "glpat-123"}

    with patch("hat.repos.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value = mock_client
        repos = list_remote_repos(source, secrets)

    assert len(repos) == 2
    assert repos[0]["relative_path"] == "deploy/charts"
    assert repos[1]["relative_path"] == "terraform-modules"


def test_list_remote_github():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"name": "api-server", "ssh_url": "git@github.com:acme-oss/api-server.git"},
        {"name": "docs", "ssh_url": "git@github.com:acme-oss/docs.git"},
    ]
    mock_response.headers = {}

    source = {
        "provider": "github",
        "org": "acme-oss",
        "token_ref": "keychain:gh-token",
    }
    secrets = {"keychain:gh-token": "ghp_123"}

    with patch("hat.repos.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value = mock_client
        repos = list_remote_repos(source, secrets)

    assert len(repos) == 2
    assert repos[0]["relative_path"] == "api-server"


def test_pull_repos_skips_dirty(tmp_path):
    # Create a fake repo with uncommitted changes
    repo_dir = tmp_path / "acme" / "repos" / "dirty-repo"
    repo_dir.mkdir(parents=True)
    (repo_dir / ".git").mkdir()

    with patch("hat.repos.subprocess.run") as mock_run:
        # git status --porcelain returns non-empty = dirty
        mock_run.return_value = MagicMock(returncode=0, stdout="M file.txt\n")
        results = pull_repos(tmp_path / "acme" / "repos")

    assert results[0]["status"] == "skipped"
    assert "uncommitted" in results[0]["reason"]
