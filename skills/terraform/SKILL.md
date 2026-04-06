---
name: terraform
description: Use when working with Terraform or OpenTofu — plan, apply, state, modules, terragrunt, or any IaC-related task
---

# Terraform / OpenTofu

## Company Context

To get company-specific Terraform settings:

1. Read `~/Library/hat/state.json` to get `active_company`
2. Read `~/Library/hat/companies/<active_company>/config.yaml`
3. Use `cloud.terraform` section — reads `vars` for `TF_VAR_*` env vars

`TF_VAR_*` env vars should already be set by `hat on`.

## Commands

### Core Workflow

```bash
tofu init -backend=false                              # safe local init (no remote state)
tofu init                                             # full init with backend
tofu fmt                                              # format (required before commit)
tofu validate                                         # validate config
tflint                                                # lint
tofu plan -out=/tmp/plan.tfplan                       # plan to file
tofu apply /tmp/plan.tfplan                           # apply (only when instructed)
```

### State

```bash
tofu state list                                       # list resources
tofu state show <resource>                            # inspect resource
tofu state mv <old> <new>                             # rename (only when instructed)
tofu state rm <resource>                              # remove (only when instructed)
tofu import <resource> <id>                           # import (only when instructed)
```

### Terragrunt

```bash
terragrunt init
terragrunt plan
terragrunt apply                                      # only when instructed
terragrunt run-all plan                               # plan all modules
terragrunt run-all apply                              # only when instructed
terragrunt output
terragrunt state list
```

### Inspection

```bash
tofu output                                           # show outputs
tofu providers                                        # list providers
tofu graph | dot -Tpng > graph.png                    # dependency graph
```

## Runbooks

### Plan Safely

1. Format: `tofu fmt`
2. Validate: `tofu validate`
3. Lint: `tflint`
4. Plan to file: `tofu plan -out=/tmp/plan.tfplan`
5. Review the plan output carefully
6. Only apply when explicitly instructed

### Import Existing Resource

1. Add the resource block to your `.tf` files
2. Import (only when instructed): `tofu import <resource> <cloud-id>`
3. Plan: `tofu plan` — should show no changes if import matches config
4. If there are diffs, adjust the config to match reality

### Fix State Drift

1. Plan: `tofu plan` to see what drifted
2. Decide: update config to match reality, or apply to make reality match config
3. If updating config: edit `.tf` files, plan again to verify no changes
4. If applying (only when instructed): `tofu apply /tmp/plan.tfplan`

### Move State (Refactoring)

1. Plan the moves: identify old and new resource addresses
2. Move (only when instructed): `tofu state mv <old> <new>`
3. Plan: verify no create/destroy, only in-place changes if any

**Safety:** Never run `tofu apply`, `tofu destroy`, `tofu state rm`, or `tofu import` without explicit user instruction.
