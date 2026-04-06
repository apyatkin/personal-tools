---
name: github
description: Use when working with GitHub — PRs, Actions, gh CLI, GitHub API, or any GitHub-related task
---

# GitHub

## Company Context

To get company-specific GitHub settings:

1. Read `~/Library/hat/state.json` to get `active_company`
2. Read `~/Library/hat/companies/<active_company>/config.yaml`
3. Find entries in `git.sources` where `provider: github` — use `org`, `token_ref`

If no company is active, ask the user which company context to use.

## Commands

### Pull Requests

```bash
gh pr list                                # list open PRs
gh pr create --title "title" --body "desc"  # create PR
gh pr view <number>                       # view PR details
gh pr diff <number>                       # view diff
gh pr checks <number>                     # CI status
gh pr merge <number> --squash             # merge with squash
gh pr review <number> --approve           # approve PR
```

### Actions / Workflows

```bash
gh run list                               # list workflow runs
gh run view <run-id>                      # run summary
gh run view <run-id> --log                # full logs
gh run rerun <run-id>                     # rerun failed
gh run watch <run-id>                     # live status
```

### Issues & Releases

```bash
gh issue list -l "bug"                    # list by label
gh issue create --title "title" --body "desc"
gh release list                           # list releases
gh release create <tag> --title "title" --notes "notes"
```

### API

```bash
gh api repos/<owner>/<repo>/pulls/<n>/comments   # PR comments
gh api repos/<owner>/<repo>/actions/runs          # workflow runs
```

## Runbooks

### Debug Failing Workflow

1. List recent runs: `gh run list`
2. View the failed run: `gh run view <run-id>`
3. Read full logs: `gh run view <run-id> --log`
4. Find the failed step and error message
5. If transient: `gh run rerun <run-id>`
6. If real failure: fix locally, push, monitor with `gh run watch`

### Review a Pull Request

1. View the PR: `gh pr view <number>`
2. Check CI: `gh pr checks <number>`
3. Review diff: `gh pr diff <number>`
4. Read comments: `gh api repos/<owner>/<repo>/pulls/<number>/comments`
5. Approve: `gh pr review <number> --approve`
6. Merge: `gh pr merge <number> --squash`

### Create a Release

1. Ensure all changes are merged to main
2. Tag: `git tag v<version>`
3. Push tag: `git push origin v<version>`
4. Create release: `gh release create v<version> --title "v<version>" --generate-notes`
