---
name: vault
description: Use when working with HashiCorp Vault — secrets, auth, policies, vault CLI, or any Vault-related task
---

# HashiCorp Vault

## Company Context

Read `state.json` for `active_company`, then load `config.yaml` for that company. Vault configuration lives under `cloud.vault` and provides:

| Field         | Purpose                                                    |
|---------------|------------------------------------------------------------|
| `addr`        | Vault API address (e.g. `https://vault.example.com:8200`) |
| `auth_method` | Authentication method: `token`, `ldap`, or `oidc`         |
| `token_ref`   | Reference to the Vault token in the secrets store          |

`VAULT_ADDR` and `VAULT_TOKEN` are set automatically when you run `hat on <company>`. You do not need to set these manually.

## Commands

### Status & Auth

```bash
# Check seal status, HA mode, and storage backend
vault status

# Inspect the current token (TTL, policies, capabilities)
vault token lookup

# Renew the current token
vault token renew

# Authenticate with a token (interactive prompt)
vault login -method=token

# Authenticate with LDAP
vault login -method=ldap username=<your-username>

# Authenticate with OIDC (opens browser)
vault login -method=oidc

# Check what capabilities your token has on a specific path
vault token capabilities secret/data/<path>
```

### Secrets (KV v2)

```bash
# List all mounted secret engines
vault secrets list

# List keys at a path (KV v2)
vault kv list secret/<path>

# Read a secret
vault kv get secret/<path>/<key>

# Read a secret and output as JSON (useful for scripting)
vault kv get -format=json secret/<path>/<key>

# Read a specific version of a secret
vault kv get -version=<n> secret/<path>/<key>

# View version history and metadata for a secret
vault kv metadata get secret/<path>/<key>

# Write a secret (ONLY when explicitly instructed)
vault kv put secret/<path>/<key> field1=value1 field2=value2

# Patch (update specific fields only, ONLY when explicitly instructed)
vault kv patch secret/<path>/<key> field1=new-value

# Roll back a secret to a previous version (ONLY when explicitly instructed)
vault kv rollback -version=<n> secret/<path>/<key>

# Delete the latest version of a secret (ONLY when explicitly instructed)
vault kv delete secret/<path>/<key>

# Permanently destroy a specific version (ONLY when explicitly instructed)
vault kv destroy -versions=<n> secret/<path>/<key>
```

### Policies

```bash
# List all policies
vault policy list

# Read a specific policy
vault policy read <policy-name>

# Write (create or update) a policy (ONLY when explicitly instructed)
vault policy write <policy-name> <policy-file.hcl>

# Delete a policy (ONLY when explicitly instructed)
vault policy delete <policy-name>
```

### Audit

```bash
# List configured audit devices
vault audit list

# Enable a file audit device (ONLY when explicitly instructed)
vault audit enable file file_path=/var/log/vault-audit.log

# Disable an audit device (ONLY when explicitly instructed)
vault audit disable <mount-path>
```

## Runbooks

### Read Secrets Safely

When reading a secret for inspection or passing to another tool:

1. Confirm the path is known:
   ```bash
   vault kv list secret/<path>
   ```

2. Read the secret and confirm field names:
   ```bash
   vault kv get secret/<path>/<key>
   ```

3. For scripting, extract a specific field from JSON output:
   ```bash
   vault kv get -format=json secret/<path>/<key> | jq -r '.data.data.<field>'
   ```

4. Check the version metadata before trusting the value:
   ```bash
   vault kv metadata get secret/<path>/<key>
   ```

### Rotate Token

When a token is expiring or has been compromised:

1. Check the current token's remaining TTL:
   ```bash
   vault token lookup
   ```

2. If the token is still valid, renew it:
   ```bash
   vault token renew
   ```

3. If the token has expired, re-authenticate using the configured method:
   ```bash
   # Token method
   vault login -method=token

   # LDAP method
   vault login -method=ldap username=<your-username>

   # OIDC method (opens browser)
   vault login -method=oidc
   ```

4. After login, verify the new token:
   ```bash
   vault token lookup
   ```

5. Update `hat` or any credential store with the new token if required.

### Check Seal Status

When Vault may be sealed or unreachable:

1. Check current seal status:
   ```bash
   vault status
   ```

2. Look for `Sealed: true` in the output. If sealed, unseal operations are required (coordinate with the Vault admin).

3. If `Sealed: false`, check HA status — confirm the active node and standby nodes:
   ```bash
   vault status
   ```
   The `HA Mode` and `Active Node Address` fields indicate which node is serving traffic.

4. Confirm connectivity by looking up the current token:
   ```bash
   vault token lookup
   ```

### Verify Audit Logging

When confirming that audit logging is active before performing sensitive operations:

1. List all audit devices:
   ```bash
   vault audit list
   ```

2. Verify at least one audit device is listed and enabled.

3. If no audit device is configured, notify the team before proceeding. Do not enable audit devices without explicit instruction.

4. After performing sensitive operations, confirm log entries are being written to the audit device path.

## Safety

**Never** perform the following without an explicit instruction from the user:

- `vault kv put` / `vault kv patch` — writes or modifies secret values
- `vault kv delete` / `vault kv destroy` — deletes secret versions
- `vault kv rollback` — rolls back a secret to a previous version
- `vault policy write` / `vault policy delete` — modifies access policies
- `vault audit enable` / `vault audit disable` — changes audit configuration

Read-only commands (`vault status`, `vault token lookup`, `vault kv get`, `vault kv list`, `vault kv metadata get`, `vault policy read`, `vault audit list`) are always safe to run.
