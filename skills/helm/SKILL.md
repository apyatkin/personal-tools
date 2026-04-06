---
name: helm
description: Use when working with Helm — charts, releases, values files, helm diff, or any Helm-related task
---

# Helm

## Company Context

To get company-specific Helm settings:

1. Read `~/.config/ctx/state.json` to get `active_company`
2. Read `~/.config/ctx/companies/<active_company>/config.yaml`
3. Use `cloud.kubernetes` section — Helm uses the same cluster context as kubectl

The `KUBECONFIG` env var should already be set by `ctx use`.

## Commands

### Releases

```bash
helm list -n <ns>                                     # list releases
helm status <release> -n <ns>                         # release status
helm history <release> -n <ns>                        # revision history
helm get values <release> -n <ns>                     # current values
helm get manifest <release> -n <ns>                   # rendered manifests
```

### Install & Upgrade

```bash
helm template <chart> . -f values.yaml               # render locally (safe)
helm diff upgrade <release> . -f values.yaml -n <ns>  # diff before apply (safe)
helm upgrade --install <release> . -f values.yaml -n <ns>  # apply (only when instructed)
helm upgrade --install <release> . -f values.yaml -n <ns> --dry-run  # dry run
```

### Rollback

```bash
helm rollback <release> <revision> -n <ns>            # rollback (only when instructed)
```

### Repos

```bash
helm repo list                                        # list repos
helm repo update                                      # update repo index
helm search repo <keyword>                            # search charts
```

## Runbooks

### Diff Before Upgrade

1. Always render locally first: `helm template <chart> . -f values.yaml`
2. Check the diff: `helm diff upgrade <release> . -f values.yaml -n <ns>`
3. Review every change carefully
4. Only apply when explicitly instructed: `helm upgrade --install <release> . -f values.yaml -n <ns>`

### Rollback Release

1. Check history: `helm history <release> -n <ns>`
2. Identify the last good revision number
3. Rollback (only when instructed): `helm rollback <release> <revision> -n <ns>`
4. Verify pods are healthy: `kubectl get pods -n <ns>`

### Template Locally

1. Render: `helm template <chart> . -f values.yaml`
2. Inspect the output for correctness
3. Check for common issues: missing values, wrong image tags, resource limits
