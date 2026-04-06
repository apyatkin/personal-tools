# ctx — Company Context Switcher

A CLI tool for switching between multiple company environments. Manages VPN, SSH keys, cloud credentials, env vars, DNS, git identity, docker registries, browser profiles, tool installation, and git repo cloning.

## Install

```bash
# Requires Python 3.11+ and uv

# From GitHub
uv tool install git+https://github.com/apyatkin/personal-tools.git

# Or from local clone (editable — code changes take effect immediately)
git clone https://github.com/apyatkin/personal-tools.git
cd personal-tools
uv tool install -e .
```

## Update

```bash
# After pulling new changes or editing code locally
uv tool install -e /path/to/personal-tools --force

# Or from GitHub (latest)
uv tool install git+https://github.com/apyatkin/personal-tools.git --force
```

With editable install (`-e`), most code changes work immediately. Use `--force` after changing `pyproject.toml` or dependencies.

## Uninstall

```bash
uv tool uninstall ctx-switch
```

## Shell Integration

Add to `~/.zshrc`:

```bash
eval "$(ctx shell-init zsh)"
```

This sources env vars on every prompt and adds a `[company]` indicator to your prompt.

## Quick Start

```bash
# Create a company config
ctx init acme

# Edit the config
$EDITOR ~/Library/ctx/companies/acme/config.yaml

# Switch to that company
ctx use acme

# Check what's active
ctx status

# Switch to another company (deactivates previous)
ctx use globex

# Deactivate everything
ctx off
```

## Company Config

Each company lives in `~/Library/ctx/companies/<name>/config.yaml`. All sections are optional — only configure what you need:

```yaml
name: acme
description: "Acme Corp"

git:
  identity:
    name: "Your Name"
    email: "you@acme.com"
  sources:
    - provider: gitlab
      host: gitlab.acme.com
      group: infrastructure
      token_ref: keychain:acme-gitlab-token
    - provider: github
      org: acme-oss
      token_ref: keychain:acme-github-pat

env:
  CUSTOM_VAR: value

ssh:
  keys:
    - ~/.ssh/acme_ed25519
  config: ~/Library/ctx/companies/acme/ssh_config

vpn:
  provider: wireguard   # wireguard | amnezia | tailscale
  config: ~/Library/ctx/companies/acme/wg0.conf
  interface: wg-acme

dns:
  resolvers:
    - 10.0.0.53
  search_domains:
    - acme.internal

hosts:
  entries:
    - "10.0.1.10 grafana.acme.internal"

cloud:
  aws:
    profile: acme-prod
    sso: true
  kubernetes:
    kubeconfig: ~/Library/ctx/companies/acme/kubeconfig
    refresh:
      provider: yandex   # yandex | aws | digitalocean
      cluster: acme-k8s
  nomad:
    addr: https://nomad.acme.internal:4646
    token_ref: keychain:acme-nomad-token
  vault:
    addr: https://vault.acme.com:8200
    token_ref: keychain:acme-vault-token
  consul:
    addr: https://consul.acme.com:8500
    token_ref: keychain:acme-consul-token
  yandex:
    profile: acme
  digitalocean:
    context: acme
  hetzner:
    token_ref: keychain:acme-hcloud-token
  terraform:
    vars:
      backend_bucket: acme-tf-state

docker:
  registries:
    - host: registry.acme.com
      username_ref: keychain:acme-reg-user
      password_ref: keychain:acme-reg-pass

proxy:
  http: http://proxy.acme.com:3128
  https: http://proxy.acme.com:3128
  no_proxy: "*.acme.internal,10.0.0.0/8"

browser:
  profile: "Acme"
  app: google-chrome     # google-chrome | firefox | arc

apps:
  slack:
    workspace: acme-corp
  jira:
    host: acme.atlassian.net
    project: INFRA
    token_ref: keychain:acme-jira-token
  favro:
    organization_id: "org-123"
    token_ref: keychain:acme-favro-token
```

## Secrets

Secrets are referenced in config via `*_ref` fields and resolved at activation time from:

- **macOS Keychain:** `keychain:<service-name>`
- **Bitwarden:** `bitwarden:<item>`, `bitwarden:<item>/password`, `bitwarden:<item>/field/<name>`

Values are base64-encoded in Keychain to support multiline secrets (SSH keys, certs).

```bash
# Store a secret (paste multiline, Ctrl-D to finish)
ctx secret set keychain:acme-gitlab-token

# Store from file (SSH keys, certs)
ctx secret set keychain:acme-sshkey -f ~/.ssh/acme_ed25519

# Display a secret
ctx secret get keychain:acme-gitlab-token
```

## Repo Management

Clone all repos from a company's GitLab groups and GitHub orgs:

```bash
# Clone all repos (preserves GitLab subgroup structure)
ctx repos clone acme

# Pull updates for all repos
ctx repos pull acme

# Pull all companies
ctx repos pull --all

# Show what's cloned vs missing
ctx repos list acme
```

Repos are cloned to `~/projects/<company>/repos/`.

## Tool Management

Tools are defined globally in `~/projects/common/tools.yaml` (not per-company). They're automatically checked on each `ctx use`. Missing tools are installed, outdated tools are upgraded. Update checks are throttled to once per 24 hours.

```bash
# Generate default tools.yaml
ctx tools init

# Edit to customize
$EDITOR ~/projects/common/tools.yaml

# Check tools without switching context
ctx tools check
```

`tools.yaml` format:
```yaml
brew:
  - kubectl
  - helm
  - terraform
  - nomad
  - vault
  - consul
  - yc
  - doctl
  - hcloud
  - gh
  - glab
  - jq
  - wireguard-tools
  - docker
pipx:
  - ansible
  - ansible-lint
  - yamllint
  - ruff
```

- `brew` tools: installed via Homebrew
- `pipx` tools: installed via `uv tool` (isolated Python venvs)

## Claude Code Skills

12 DevOps skills for Claude Code are included in `skills/`. Deploy them to make them available across all company repos:

```bash
# Set skills source in global config
echo "skills_source: $(pwd)/skills" > ~/Library/ctx/config.yaml

# Deploy skills as symlinks
ctx skills deploy
```

This creates `~/projects/.claude/skills/` with symlinks to each skill. Skills cover: GitLab, GitHub, Favro, Jira, Kubernetes, Helm, Terraform, Ansible, Nomad, Vault, Consul, Docker.

Each skill reads the active company's `ctx` config for connection details.

## What Happens on `ctx use`

Modules activate in this order (deactivate in reverse):

1. **tools** — install/update required CLI tools
2. **vpn** — connect VPN (prompts before `sudo`)
3. **dns** — configure resolvers (prompts before `sudo`)
4. **hosts** — add `/etc/hosts` entries (prompts before `sudo`)
5. **ssh** — load SSH keys into agent
6. **git** — set git identity via env vars
7. **cloud** — set cloud credentials, run login commands
8. **env** — export custom env vars
9. **docker** — log into registries
10. **proxy** — set proxy env vars
11. **browser** — open browser with company profile
12. **apps** — open Slack, etc.

State is tracked in `~/Library/ctx/state.json` so `ctx off` and `ctx status` work across shell restarts.

## Shell Aliases & Completions

Generate global aliases and completions for all DevOps tools:

```bash
ctx aliases generate       # ~/projects/common/aliases.sh
ctx completions generate   # ~/projects/common/completions.sh
```

These are sourced automatically by `ctx shell-init zsh`. Includes aliases like `k` for kubectl, `tf` for tofu, `dc` for docker compose, and completions for all tools.

## All Commands

```
ctx use <company>              switch context (hard switch)
ctx off                        deactivate current context
ctx status                     show active company and modules
ctx list                       list configured companies
ctx init <company>             scaffold new company config

ctx repos clone <company>      clone all repos from git sources
ctx repos pull <company>       pull updates for company repos
ctx repos pull --all           pull all companies
ctx repos list <company>       list local vs remote repos

ctx secret set <ref>           store a secret (multiline paste, Ctrl-D)
ctx secret set <ref> -f <file>  store from file
ctx secret get <ref>           display a secret

ctx tools init                 generate ~/projects/common/tools.yaml
ctx tools check                check/install tools

ctx aliases generate           generate ~/projects/common/aliases.sh
ctx completions generate       generate ~/projects/common/completions.sh

ctx skills deploy              deploy Claude Code skills

ctx shell-init zsh             output shell integration code
```
