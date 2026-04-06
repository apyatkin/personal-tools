---
name: consul
description: Use when working with Consul — services, KV store, health checks, service mesh, or any Consul-related task
---

# Consul

## Company Context

Read `state.json` for `active_company`, then load `config.yaml` for that company. Consul configuration lives under `cloud.consul` and provides:

| Field       | Purpose                                                       |
|-------------|---------------------------------------------------------------|
| `addr`      | Consul API address (e.g. `https://consul.example.com:8500`)  |
| `token_ref` | Reference to the ACL token in the secrets store              |

`CONSUL_HTTP_ADDR` and `CONSUL_HTTP_TOKEN` are set automatically when you run `hat on <company>`. You do not need to set these manually.

## Commands

### Cluster

```bash
# List all cluster members (servers and clients)
consul members

# Show detailed member info including roles
consul members -detailed

# Check Raft cluster health and leader status
consul operator raft list-peers

# Stream live agent logs (useful for debugging)
consul monitor

# Stream live logs at a specific level
consul monitor -log-level=debug

# Check agent health and configuration
consul info
```

### Services

```bash
# List all registered services
consul catalog services

# List all registered nodes
consul catalog nodes

# List nodes providing a specific service
consul catalog nodes -service=<service-name>

# Check health status of all services
consul health checks --service <service-name>

# List passing/warning/critical health checks
consul health checks --state passing
consul health checks --state warning
consul health checks --state critical

# List service mesh intentions
consul intention list

# Read a specific intention
consul intention check <source> <destination>
```

### KV Store

```bash
# Read a single key from the KV store
consul kv get <key>

# Read a key and show metadata (flags, modify index)
consul kv get -detailed <key>

# List all keys under a prefix (recursive)
consul kv get -recurse <prefix>/

# Write a key (ONLY when explicitly instructed)
consul kv put <key> <value>

# Write a key from a file (ONLY when explicitly instructed)
consul kv put <key> @<file>

# Delete a single key (ONLY when explicitly instructed)
consul kv delete <key>

# Delete all keys under a prefix (ONLY when explicitly instructed)
consul kv delete -recurse <prefix>/
```

### DNS

Consul exposes a DNS interface on port 8600 (by default on localhost) for service discovery queries.

```bash
# Resolve a service address via Consul DNS
dig @127.0.0.1 -p 8600 <service-name>.service.consul

# Resolve with SRV records (includes port information)
dig @127.0.0.1 -p 8600 <service-name>.service.consul SRV

# Resolve a service in a specific datacenter
dig @127.0.0.1 -p 8600 <service-name>.service.<datacenter>.consul

# Resolve a node address
dig @127.0.0.1 -p 8600 <node-name>.node.consul

# Resolve a tagged service variant
dig @127.0.0.1 -p 8600 <tag>.<service-name>.service.consul

# Check if the Consul DNS port is reachable
dig @127.0.0.1 -p 8600 consul.service.consul
```

## Runbooks

### List Services and Health

When you need to understand what services are registered and their health status:

1. List all registered services:
   ```bash
   consul catalog services
   ```

2. For each service of interest, list nodes providing it:
   ```bash
   consul catalog nodes -service=<service-name>
   ```

3. Check health checks for the service:
   ```bash
   consul health checks --service <service-name>
   ```

4. Look for checks in `critical` state and note the `Output` field for error details.

5. Verify the service is resolvable via DNS:
   ```bash
   dig @127.0.0.1 -p 8600 <service-name>.service.consul
   ```

### Read KV Tree

When you need to inspect configuration stored in Consul's KV store:

1. List all keys under a known prefix:
   ```bash
   consul kv get -recurse <prefix>/
   ```

2. Read a specific key with full metadata:
   ```bash
   consul kv get -detailed <key>
   ```

3. The `ModifyIndex` in the metadata helps you determine when the key was last changed.

4. For multi-line or binary values, pipe through `base64 -D` or inspect carefully.

### Check Cluster Health

When investigating cluster issues or before maintenance:

1. Check all cluster members and their status:
   ```bash
   consul members
   ```
   Look for members in `failed` or `left` state.

2. Verify Raft leader election and peer count:
   ```bash
   consul operator raft list-peers
   ```
   Confirm there is exactly one `Leader` and all expected servers are listed.

3. Check agent-level metrics and configuration:
   ```bash
   consul info
   ```

4. If issues are found, tail live agent logs to see what is happening:
   ```bash
   consul monitor -log-level=info
   ```

### Debug Service DNS

When a service cannot be resolved via DNS:

1. Confirm the service is registered:
   ```bash
   consul catalog services
   ```

2. Check the health of the service:
   ```bash
   consul health checks --service <service-name>
   ```
   Only passing instances are returned in DNS queries by default.

3. Attempt a DNS resolution:
   ```bash
   dig @127.0.0.1 -p 8600 <service-name>.service.consul
   ```

4. If no answer is returned, check if all instances are unhealthy (critical checks exclude them from DNS).

5. Try resolving with all health states (using the `any` tag):
   ```bash
   dig @127.0.0.1 -p 8600 <service-name>.service.consul
   ```
   If the service exists but all checks are critical, this confirms the health issue.

6. Review health check output for details:
   ```bash
   consul health checks --service <service-name> --state critical
   ```

## Safety

**Never** run the following without an explicit instruction from the user:

- `consul kv put` — writes or overwrites a KV entry
- `consul kv delete` — deletes a KV key or tree
- `consul leave` — gracefully removes the agent from the cluster
- `consul force-leave` — forcibly removes a node from the cluster

Read-only commands (`consul members`, `consul catalog services`, `consul catalog nodes`, `consul health checks`, `consul kv get`, `consul kv get -recurse`, `consul intention list`, `consul operator raft list-peers`, `consul monitor`, `consul info`) are always safe to run.
