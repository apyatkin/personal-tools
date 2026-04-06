# ctx — Company Context Switcher

## Overview

A Python CLI tool that manages switching between multiple company environments. Each company has a declarative YAML config describing its environment (VPN, SSH keys, cloud credentials, env vars, DNS, etc.). The tool activates/deactivates these resources in a defined order, ensuring clean transitions between companies.

## CLI Interface

```
ctx use <company>          # switch full context (hard switch — deactivates previous first)
ctx off                    # deactivate current context
ctx status                 # show active company + module states
ctx list                   # list configured companies
ctx init <company>         # scaffold a new company config

ctx repos clone <company>  # clone all repos from configured git group(s)
ctx repos pull <company>   # git pull all repos for a company
ctx repos pull --all       # git pull all repos for all companies
ctx repos list <company>   # list local vs remote repos

ctx secret set <ref>       # store a secret (e.g. keychain:acme-token)

ctx shell-init zsh         # output shell hook code for ~/.zshrc
```

### Switching behavior

Hard switch only — one active company at a time. `ctx use <new>` always runs full deactivation of the current context before activating the new one.

## Configuration

### Location

```
~/.config/ctx/
  companies/
    <name>/
      config.yaml
      kubeconfig          # optional, referenced from config
      ssh_config          # optional
      wg0.conf            # optional
      nomad-ca.pem        # optional
  state.json              # active context + module states
  state.env               # exported env vars for shell integration
```

### Company config schema

`~/.config/ctx/companies/<name>/config.yaml` — all sections are optional:

```yaml
name: acme
description: "Acme Corp production infrastructure"

git:
  identity:
    name: "Alexander Pyatkin"
    email: "alex@acme.com"
  sources:
    - provider: gitlab
      host: gitlab.acme.com
      group: infrastructure
      token_ref: keychain:acme-gitlab-token
    - provider: github
      org: acme-oss
      token_ref: bitwarden:acme-github-pat

env:
  AWS_PROFILE: acme-prod
  VAULT_ADDR: https://vault.acme.com:8200
  CONSUL_HTTP_ADDR: https://consul.acme.com:8500

ssh:
  keys:
    - ~/.ssh/acme_ed25519
    - ~/.ssh/acme_bastion
  config: ~/.config/ctx/companies/acme/ssh_config

vpn:
  provider: wireguard       # wireguard | amnezia | tailscale
  config: ~/.config/ctx/companies/acme/wg0.conf
  interface: wg-acme

dns:
  resolvers:
    - 10.0.0.53
    - 10.0.0.54
  search_domains:
    - acme.internal

hosts:
  entries:
    - "10.0.1.10 grafana.acme.internal"
    - "10.0.1.11 vault.acme.internal"

proxy:
  http: http://proxy.acme.com:3128
  https: http://proxy.acme.com:3128
  no_proxy: "*.acme.internal,10.0.0.0/8"

cloud:
  aws:
    profile: acme-prod
    sso: true
  kubernetes:
    kubeconfig: ~/.config/ctx/companies/acme/kubeconfig
    refresh:
      provider: yandex       # yandex | aws | digitalocean
      cluster: acme-k8s-prod
  nomad:
    addr: https://nomad.acme.internal:4646
    token_ref: keychain:acme-nomad-token
    cacert: ~/.config/ctx/companies/acme/nomad-ca.pem
  vault:
    addr: https://vault.acme.com:8200
    auth_method: token       # token | ldap | oidc
    token_ref: bitwarden:acme-vault-token
  consul:
    addr: https://consul.acme.com:8500
    token_ref: keychain:acme-consul-token
  yandex:
    profile: acme
  digitalocean:
    context: acme
  hetzner:
    token_ref: keychain:acme-hcloud-token
    context: acme
  terraform:
    vars:
      backend_bucket: acme-tf-state
      region: eu-central-1

docker:
  registries:
    - host: registry.acme.com
      username_ref: keychain:acme-registry-user
      password_ref: keychain:acme-registry-pass

browser:
  profile: "Acme"
  app: google-chrome         # google-chrome | firefox | arc

apps:
  slack:
    workspace: acme-corp

tools:
  brew:
    - kubectl
    - helm
    - terraform
    - nomad
    - consul
    - vault
    - yc
    - doctl
    - hcloud
    - gh
    - glab
    - jq
    - wireguard-tools
    - docker
  pipx:                        # installed into isolated venvs via uv tool / pipx
    - ansible
    - ansible-lint
    - yamllint
    - ruff
```

## Module Architecture

Each module implements a standard interface:

```python
class Module:
    name: str
    def activate(self, config: dict, secrets: dict) -> None: ...
    def deactivate(self) -> None: ...
    def status(self) -> ModuleStatus: ...  # active/inactive + details
```

### Activation order (deactivation is reverse)

| Order | Module    | Activate                                                                 | Deactivate                          |
|-------|-----------|--------------------------------------------------------------------------|-------------------------------------|
| 0     | tools     | Check/install/update required tools via brew and uv tool                | No-op                               |
| 1     | secrets   | Connect to Keychain/Bitwarden, resolve all `*_ref` values               | Clear cached secrets from memory    |
| 2     | vpn       | `wg-quick up`, `amnezia-cli connect`, or `tailscale up`                 | Disconnect                          |
| 3     | dns       | Write `/etc/resolver/<domain>` files (macOS)                            | Remove resolver files               |
| 4     | hosts     | Append entries to `/etc/hosts` with marker comments                     | Remove marked entries               |
| 5     | ssh       | `ssh-add` keys, merge ssh_config snippet                                | `ssh-add -d` keys, remove snippet   |
| 6     | git       | Set identity via `GIT_AUTHOR_NAME`, `GIT_AUTHOR_EMAIL`, etc.            | Unset                               |
| 7     | cloud     | Set cloud env vars, run login/refresh commands per provider              | Unset vars                          |
| 8     | env       | Export arbitrary env vars, write to state.env                           | Unset, clear state.env              |
| 9     | docker    | `docker login` for each registry                                        | `docker logout` for each registry   |
| 10    | proxy     | Set `HTTP_PROXY`, `HTTPS_PROXY`, `NO_PROXY`                            | Unset                               |
| 11    | browser   | `open -a <app> --args --profile-directory=<profile>`                    | No-op                               |
| 12    | apps      | Open Slack workspace URL, etc.                                          | No-op                               |

### Privileged operations

Modules that need `sudo` (vpn, dns, hosts) display the exact commands they will run and prompt the user for confirmation before elevating.

### State tracking

`~/.config/ctx/state.json` tracks the active company and which modules were successfully activated. This allows `ctx off` and `ctx status` to work correctly even after a shell restart or partial activation failure.

```json
{
  "active_company": "acme",
  "activated_modules": ["secrets", "vpn", "dns", "hosts", "ssh", "git", "cloud", "env", "docker"],
  "activated_at": "2026-04-06T14:30:00Z"
}
```

## Tool Management

The `tools` module runs first on every `ctx use` and ensures all required CLI tools are installed and up to date.

### Two install methods

| Method | For | How |
|--------|-----|-----|
| `brew` | Native CLI tools (kubectl, helm, terraform, nomad, vault, etc.) | `brew install <pkg>` / `brew upgrade <pkg>` |
| `pipx` | Python tools (ansible, ansible-lint, yamllint, ruff, etc.) | `uv tool install <pkg>` / `uv tool upgrade <pkg>` |

`pipx` entries use `uv tool` under the hood — each tool gets its own isolated venv, so there are no dependency conflicts between tools or with the system Python.

### Behavior on `ctx use`

1. Collect all tools from the company's `tools.brew` and `tools.pipx` lists
2. For each tool, check if it's installed (`which <binary>`)
3. **Missing tools:** install them (`brew install` or `uv tool install`)
4. **Installed tools:** check for updates (`brew outdated`, `uv tool upgrade --dry-run`) and upgrade if available
5. Report summary: installed N, updated N, already up to date N

### Update frequency

To avoid slowing down every switch, update checks are throttled — at most once per 24 hours per tool. Last-checked timestamps are stored in `~/.config/ctx/tools_state.json`. Force a full check with `ctx use <company> --check-tools`.

### Standalone command

```
ctx tools check <company>   # check + install/update without full context switch
```

## Secret Resolution

Two backends, mixable per company:

### macOS Keychain

```
keychain:<service-name>
```

- Read: `security find-generic-password -s <service-name> -w`
- Write: `ctx secret set keychain:<service-name>` prompts interactively, calls `security add-generic-password`

### Bitwarden

```
bitwarden:<item-name>
bitwarden:<item-name>/password
bitwarden:<item-name>/field/<field-name>
bitwarden:<item-name>/notes
```

- Uses `bw` CLI. Session unlocked once at activation start, locked at deactivation.
- Reuses existing unlocked session if available.

## Repo Management

### Directory structure

```
~/projects/
  <company>/
    repos/
      <nested-gitlab-path>/     # preserves GitLab subgroup structure
        repo-a/
        repo-b/
      <github-repo>/
```

GitLab repos preserve the path relative to the configured group. For example, if `group: infrastructure` and that group contains subgroup `deploy` with project `charts`, the path is:
`~/projects/acme/repos/deploy/charts/`

A top-level project `terraform-modules` in the same group becomes:
`~/projects/acme/repos/terraform-modules/`

### Clone flow (`ctx repos clone <company>`)

1. Read `git.sources` from company config
2. For each source:
   - **GitLab:** `GET /api/v4/groups/<group>/projects?include_subgroups=true` (paginated)
   - **GitHub:** `GET /orgs/<org>/repos` (paginated)
3. Clone into `~/projects/<company>/repos/` preserving nested structure for GitLab
4. Skip repos that already exist locally
5. Run clones in parallel (default concurrency: 4)
6. Set git identity per-repo from `git.identity` in company config

### Pull flow (`ctx repos pull <company>`)

1. Find all git repos under `~/projects/<company>/repos/`
2. For each repo:
   - Skip if uncommitted changes (warn user)
   - `git pull --ff-only` on current branch
3. Run in parallel
4. Report summary: updated / skipped / failed

### List flow (`ctx repos list <company>`)

Fetch remote repos and compare against local. Show which are cloned and which are missing.

## Shell Integration

### Setup (one-time)

Add to `~/.zshrc`:

```bash
eval "$(ctx shell-init zsh)"
```

### What `ctx shell-init zsh` outputs

- A `precmd` hook that sources `~/.config/ctx/state.env` if it exists
- A prompt indicator showing the active company (e.g. `[acme]`)

### How it works

`ctx use <company>` runs as a normal process (connects VPN, modifies /etc/hosts, etc.) and writes env vars to `~/.config/ctx/state.env`. The shell hook picks up these env vars automatically. `ctx off` clears the state file.

## Package & Dependencies

Installable via `uv tool install` from this repo. Python package using `pyproject.toml`.

### Dependencies

- `click` — CLI framework
- `pyyaml` — config parsing
- `keyring` — macOS Keychain access
- `httpx` — GitLab/GitHub API calls

### Project structure

```
personal-tools/
  pyproject.toml
  src/
    ctx/
      __init__.py
      cli.py              # click command definitions
      config.py           # config loading and validation
      state.py            # state.json / state.env management
      secrets.py          # keychain + bitwarden resolution
      shell.py            # shell-init output
      repos.py            # clone/pull/list logic
      modules/
        __init__.py       # Module base class, registry, ordering
        tools.py
        vpn.py
        dns.py
        hosts.py
        ssh.py
        git.py
        cloud.py
        env.py
        docker.py
        proxy.py
        browser.py
        apps.py
```
