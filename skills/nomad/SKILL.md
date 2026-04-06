---
name: nomad
description: Use when working with Nomad — jobs, allocations, deployments, nomad CLI, or any Nomad-related task
---

# Nomad

## Company Context

Read `state.json` for `active_company`, then load `config.yaml` for that company. Nomad configuration lives under `cloud.nomad` and provides:

| Field       | Purpose                                      |
|-------------|----------------------------------------------|
| `addr`      | Nomad API address (e.g. `https://nomad:4646`) |
| `token_ref` | Reference to the ACL token in secrets store  |
| `cacert`    | Path to CA certificate for TLS verification  |

`NOMAD_ADDR` and `NOMAD_TOKEN` are set automatically when you run `ctx use <company>`. If TLS is required, `NOMAD_CACERT` is also exported. You do not need to set these manually.

## Commands

### Jobs

```bash
# List all jobs
nomad status

# Inspect a specific job
nomad status <job>

# Show job version history
nomad job history <job>

# Dry-run: plan a job file to see the diff (safe — makes no changes)
nomad job plan <job.nomad.hcl>

# Run a job (ONLY when explicitly instructed)
nomad job run <job.nomad.hcl>

# Stop a job (ONLY when explicitly instructed)
nomad job stop <job>

# Force a new deployment (periodic job)
nomad job periodic force <job>
```

### Allocations

```bash
# List all allocations for a job
nomad job allocs <job>

# Inspect a specific allocation
nomad alloc status <alloc-id>

# Stream stdout logs for an allocation
nomad alloc logs <alloc-id>

# Stream stderr logs for an allocation
nomad alloc logs -stderr <alloc-id>

# Follow (tail) stdout logs
nomad alloc logs -f <alloc-id>

# Follow stderr
nomad alloc logs -f -stderr <alloc-id>

# Follow logs for a specific task within an allocation
nomad alloc logs -f <alloc-id> <task-name>

# Execute a command inside a running allocation
nomad alloc exec -task <task-name> <alloc-id> /bin/sh

# Execute a one-off command
nomad alloc exec -task <task-name> <alloc-id> env
```

### Nodes & Cluster

```bash
# List all client nodes
nomad node status

# Inspect a specific node
nomad node status <node-id>

# Check cluster health (Raft peers)
nomad operator raft list-peers

# Drain a node before maintenance (ONLY when explicitly instructed)
nomad node drain -enable -deadline 10m <node-id>

# Disable drain after maintenance (ONLY when explicitly instructed)
nomad node drain -disable <node-id>

# Check ACL token (verify auth is working)
nomad acl token self
```

## Runbooks

### Debug Failed Allocation

When a job allocation is in `failed` or `lost` state:

1. List jobs to find the affected job:
   ```bash
   nomad status
   ```

2. Get job detail and look for failed allocations:
   ```bash
   nomad status <job>
   ```

3. Inspect the failing allocation (note the alloc ID from step 2):
   ```bash
   nomad alloc status <alloc-id>
   ```

4. Check the `Recent Events` section in alloc status output for error messages (OOM kill, port conflict, image pull failure, etc.).

5. Read stderr logs for the task:
   ```bash
   nomad alloc logs -stderr <alloc-id>
   ```

6. If the container exited immediately, also read stdout:
   ```bash
   nomad alloc logs <alloc-id>
   ```

7. Cross-reference with the node the alloc ran on:
   ```bash
   nomad node status <node-id>
   ```

### Rolling Deploy

When deploying a new version of a job:

1. Edit the job spec with the new version or image tag.

2. Plan the job to see what will change (this is always safe):
   ```bash
   nomad job plan <job.nomad.hcl>
   ```

3. Review the diff output — confirm the only changes are the expected ones.

4. When explicitly instructed to apply, run the job:
   ```bash
   nomad job run <job.nomad.hcl>
   ```

5. Watch the deployment status:
   ```bash
   nomad status <job>
   ```

6. Follow logs during rollout:
   ```bash
   nomad alloc logs -f <new-alloc-id>
   ```

7. If a deployment gets stuck, check the deployment detail:
   ```bash
   nomad job deployments <job>
   ```

### Drain Node

Before taking a node offline for maintenance (only when explicitly instructed):

1. Identify the node ID:
   ```bash
   nomad node status
   ```

2. Inspect the node to see currently running allocations:
   ```bash
   nomad node status <node-id>
   ```

3. Enable drain with a deadline (allocations migrate to other nodes):
   ```bash
   nomad node drain -enable -deadline 10m <node-id>
   ```

4. Monitor until the node shows `ineligible` and all allocs have migrated:
   ```bash
   nomad node status <node-id>
   ```

5. Perform maintenance on the node.

6. Re-enable the node after maintenance:
   ```bash
   nomad node drain -disable <node-id>
   ```

### Read Allocation Logs

When a developer asks for logs from a running or recently-stopped service:

1. Find the job:
   ```bash
   nomad status <job>
   ```

2. List allocations and find the relevant one (most recent, `running` status):
   ```bash
   nomad job allocs <job>
   ```

3. For real-time log tailing:
   ```bash
   nomad alloc logs -f <alloc-id>
   ```

4. For stderr (crash logs, panic output):
   ```bash
   nomad alloc logs -f -stderr <alloc-id>
   ```

5. If the job has multiple tasks (e.g. sidecar), specify the task:
   ```bash
   nomad alloc logs -f <alloc-id> <task-name>
   ```

## Safety

**Never** run the following without an explicit instruction from the user:

- `nomad job run` — deploys or updates a running job
- `nomad job stop` — stops and removes a job
- `nomad system gc` — forces garbage collection of stopped allocations and jobs
- `nomad node drain -enable` — drains a client node

Read-only commands (`nomad status`, `nomad alloc status`, `nomad alloc logs`, `nomad job plan`, `nomad operator raft list-peers`) are always safe to run.
