---
name: gitlab
description: Use when working with GitLab — MRs, CI pipelines, glab CLI, GitLab API, or any GitLab-related task
---

# GitLab

## Company Context

To get company-specific GitLab settings:

1. Read `~/Library/hat/state.json` to get `active_company`
2. Read `~/Library/hat/companies/<active_company>/config.yaml`
3. Find entries in `git.sources` where `provider: gitlab` — use `host`, `group`, `token_ref`

If no company is active, ask the user which company context to use.

## Commands

### Merge Requests

```bash
glab mr list                              # list open MRs
glab mr create --title "title" --description "desc"  # create MR
glab mr view <number>                     # view MR details
glab mr merge <number> --squash           # merge with squash
glab mr approve <number>                  # approve MR
glab mr diff <number>                     # view diff
```

### CI/CD

```bash
glab ci status                            # current pipeline status
glab ci view <pipeline-id>               # pipeline detail
glab ci trace <job-id>                    # stream job logs
glab ci retry <job-id>                    # retry failed job
```

### Issues

```bash
glab issue list                           # list issues
glab issue create --title "title"         # create issue
glab issue view <number>                  # view issue
```

### API (when glab doesn't cover it)

```bash
curl -H "PRIVATE-TOKEN: $TOKEN" "https://<host>/api/v4/groups/<group>/projects?include_subgroups=true"
curl -H "PRIVATE-TOKEN: $TOKEN" "https://<host>/api/v4/projects/<id>/pipelines"
curl -H "PRIVATE-TOKEN: $TOKEN" "https://<host>/api/v4/projects/<id>/merge_requests?state=opened"
```

## Runbooks

### Debug Failing CI Pipeline

1. Check pipeline status: `glab ci status`
2. Find the failed job: `glab ci view <pipeline-id>`
3. Read job logs: `glab ci trace <job-id>`
4. Look for the error message in the logs
5. If it's a flaky test or transient error: `glab ci retry <job-id>`
6. If it's a real failure: fix locally, push, verify new pipeline

### Review a Merge Request

1. View the MR: `glab mr view <number>`
2. Check CI status: `glab ci status`
3. Review the diff: `glab mr diff <number>`
4. If changes look good and CI passes: `glab mr approve <number>`
5. Merge when ready: `glab mr merge <number> --squash`

### Recover from Force-Push

1. Check reflog on the remote branch: `git reflog show origin/<branch>`
2. Find the commit before the force-push
3. Reset to that commit: `git reset --hard <sha>`
4. Force-push the recovery: `git push --force-with-lease origin <branch>`
