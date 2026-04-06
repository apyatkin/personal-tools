# hat — Put On Your Company Hat

> Version 2.0.0

A CLI tool for switching between multiple company environments. Manages VPN, SSH keys, cloud credentials, env vars, DNS, git identity, docker registries, browser profiles, tool installation, and git repo cloning.

## Install

```bash
# From PyPI
uv tool install hatctl

# Or from GitHub
uv tool install git+https://github.com/apyatkin/personal-tools.git
```

## Update

```bash
uv tool install hatctl --upgrade

# Or from GitHub
uv tool install git+https://github.com/apyatkin/personal-tools.git --force
```

## Uninstall

```bash
uv tool uninstall hatctl
```

## Shell Integration

Add to `~/.zshrc`:

```bash
eval "$(hat shell-init zsh)"
```

This sources env vars, aliases, and completions on every prompt and adds a `[company]` indicator.

## Quick Start

```bash
# Create a company config
hat init acme

# Or configure without editing YAML
hat config set acme git.identity.name "Your Name"
hat config set acme git.identity.email "you@acme.com"
hat config set acme cloud.nomad.addr "https://nomad.acme.com:4646"
hat config add-ssh acme ~/.ssh/acme_ed25519
hat config add-secret acme cloud.nomad.token_ref acme-nomad-token

# Put on your Acme hat
hat on acme

# What hat am I wearing?
hat status

# Switch to another company (takes off previous hat first)
hat on globex

# Take off your hat
hat off
```

## Company Config

Each company lives in `~/Library/hat/companies/<name>/config.yaml`. All sections are optional — only configure what you need:

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
  config: ~/Library/hat/companies/acme/ssh_config

vpn:
  provider: wireguard   # wireguard | amnezia | tailscale
  config: ~/Library/hat/companies/acme/wg0.conf
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
    kubeconfig: ~/Library/hat/companies/acme/kubeconfig
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

## Config Without Editing YAML

```bash
# Set any config value
hat config set <company> <path> <value>

# Add SSH key (stored in Keychain, never on disk)
hat config add-ssh <company> <keychain-name> -f ~/.ssh/key
hat config add-ssh <company> <keychain-name>   # paste key, Ctrl-D

# Store secret in Keychain + add ref to config
hat config add-secret <company> <config-path> <keychain-name>
hat config add-secret <company> <config-path> <keychain-name> -f <file>
```

SSH keys stored in Keychain are extracted to a temporary file (0600 permissions) during `hat on`, loaded via `ssh-add`, and deleted on `hat off`. Keys never persist on disk.

## Secrets

Secrets are referenced in config via `*_ref` fields and resolved at activation time from:

- **macOS Keychain:** `keychain:<service-name>`
- **Bitwarden:** `bitwarden:<item>`, `bitwarden:<item>/password`, `bitwarden:<item>/field/<name>`

Values are base64-encoded in Keychain to support multiline secrets (SSH keys, certs).

```bash
# Store a secret (paste multiline, Ctrl-D to finish)
hat secret set keychain:acme-gitlab-token

# Store from file (SSH keys, certs)
hat secret set keychain:acme-sshkey -f ~/.ssh/acme_ed25519

# Display a secret
hat secret get keychain:acme-gitlab-token
```

## Repo Management

Clone all repos from a company's GitLab groups and GitHub orgs:

```bash
# Clone all repos (preserves GitLab subgroup structure)
hat repos clone acme

# Pull updates for all repos
hat repos pull acme

# Pull all companies
hat repos pull --all

# Show what's cloned vs missing
hat repos list acme
```

Repos are cloned to `~/projects/<company>/repos/`.

## Tool Management

Tools are defined globally in `~/projects/common/tools.yaml` (not per-company). They're automatically checked on each `hat on`. Missing tools are installed, outdated tools are upgraded. Update checks are throttled to once per 24 hours.

```bash
# Generate default tools.yaml
hat tools init

# Edit to customize
$EDITOR ~/projects/common/tools.yaml

# Check tools without switching context
hat tools check
```

- `brew` tools: installed via Homebrew
- `pipx` tools: installed via `uv tool` (isolated Python venvs)

## Shell Aliases & Completions

Generate global aliases and completions for all DevOps tools:

```bash
hat aliases generate       # ~/projects/common/aliases.sh
hat completions generate   # ~/projects/common/completions.sh
```

These are sourced automatically by `hat shell-init zsh`. Includes aliases like `k` for kubectl, `tf` for tofu, `dc` for docker compose, and completions for all tools.

## Claude Code Skills

12 DevOps skills for Claude Code are included in `skills/`. Deploy them to make them available across all company repos:

```bash
# Set skills source in global config
mkdir -p ~/Library/hat
echo "skills_source: /path/to/personal-tools/skills" > ~/Library/hat/config.yaml

# Deploy skills as symlinks
hat skills deploy
```

Skills cover: GitLab, GitHub, Favro, Jira, Kubernetes, Helm, Terraform, Ansible, Nomad, Vault, Consul, Docker.

## What Happens on `hat on`

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

State is tracked in `~/Library/hat/state.json` so `hat off` and `hat status` work across shell restarts.

## Network Tools

```bash
hat net domain example.com       # WHOIS/RDAP lookup
hat net cert example.com         # SSL certificate info
hat net ip 1.2.3.4               # IP geolocation + ISP
hat net dns example.com          # A, AAAA, MX, NS, CNAME, TXT records
hat net check host.com           # ping + traceroute + port check
hat net check host.com -p 8080   # check specific ports
```

## All Commands

```
hat on <company>                          put on a company hat
hat off                                   take off your hat
hat status                                what hat am I wearing?
hat list [--tag TAG]                      list all hats
hat init <company>                        scaffold new company config

hat config set <company> <path> <value>   set a config value
hat config add-ssh <company> <name> [-f]  store SSH key + add to config
hat config add-secret <company> <path> <name>  store secret + add ref
hat config add-host <company> <name> <addr> [-u USER] [-k KEY]
hat config validate <company>             validate config
hat template <company> --from <other>     clone company config

hat ssh <company> <host> [-u USER]        SSH via jump host (named or raw)
hat tunnel start <company>                start SSH tunnels
hat tunnel stop                           stop tunnels

hat repos clone <company>                 clone all repos
hat repos pull <company> [--tag TAG]      pull updates
hat repos pull --all                      pull all companies
hat repos sync <company>                  clone + pull in one
hat repos list <company>                  list local vs remote

hat run <company> -- <command>            run command in company env
hat env <company> [--export]              show env vars (dry run)
hat shell <company>                       spawn shell with company env
hat diff <company1> <company2>            compare configs

hat secret set <ref> [-f FILE]            store a secret
hat secret get <ref>                      display a secret

hat doctor [<company>]                    health check
hat log [--company NAME] [-n LIMIT]       activity log
hat migrate                               migrate from ~/.config/ctx/
hat backup [-o DIR]                       backup configs
hat restore <archive>                     restore from backup

hat tools init                            generate tools.yaml
hat tools check                           check/install tools

hat net domain <domain>                   WHOIS info
hat net cert <host>                       SSL certificate info
hat net ip <address>                      IP geolocation
hat net dns <domain>                      DNS records
hat net check <host> [-p PORT]            ping + traceroute + ports

hat kubeconfig merge                      merge all kubeconfigs
hat aliases generate                      generate aliases.sh
hat completions generate                  generate completions.sh
hat completion zsh                        shell completion code
hat skills deploy                         deploy Claude Code skills
hat shell-init zsh                        output shell integration
```
