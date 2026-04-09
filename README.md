# hat — Put On Your Company Hat

> Version 2.1.0 | [PyPI](https://pypi.org/project/hatctl/) | [GitHub](https://github.com/apyatkin/personal-tools)

A CLI tool for switching between multiple company environments. Manages VPN, SSH keys, cloud credentials, env vars, DNS, git identity, docker registries, browser profiles, tool installation, and git repo cloning.

## Install

### One-liner (recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/apyatkin/hatctl/main/install.sh | bash
```

For unattended/CI use, add `-s -- --silent`.

### Homebrew

```bash
brew install apyatkin/tap/hatctl
```

### uv (PyPI)

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/getting-started/installation/).

```bash
uv tool install hatctl
```

This installs `hat` to `~/.local/bin/`. Make sure it's in your PATH:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

## Setup

Run once after installing:

```bash
hat setup
```

This will:
1. Create `~/projects/` directory structure
2. Enable **Touch ID for sudo** (optional — fingerprint instead of password for VPN, DNS, etc.)
3. Generate shell aliases (130+) and completions
4. Show next steps

Then add to `~/.zshrc`:

```bash
eval "$(hat shell-init zsh)"
eval "$(_HAT_COMPLETE=zsh_source hat)"
```

## Update

```bash
uv tool install hatctl --upgrade
```

## Uninstall

```bash
uv tool uninstall hatctl
```

## Quick Start

```bash
# Create a company
hat init acme

# Configure SSH
hat ssh config acme --default-user deploy --default-key acme-sshkey
hat ssh add acme bastion 10.0.1.1
hat ssh add acme web 10.0.1.10 -u root -p 2222

# Configure VPN
hat vpn config acme --provider wireguard

# Store secrets
hat secret set keychain:acme-gitlab-token
hat config add-ssh acme acme-sshkey -f ~/.ssh/acme_ed25519
hat config add-secret acme cloud.nomad.token_ref acme-nomad-token

# Put on your hat
hat on acme

# What hat am I wearing?
hat status

# Switch companies (takes off previous hat first)
hat on globex

# Take off your hat (disconnects VPN too)
hat off
```

## Company Config

Each company lives in `~/Library/hat/companies/<name>/config.yaml`. All sections are optional:

```yaml
name: acme
description: "Acme Corp"
tags: [infra, production]

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
  default_user: deploy
  default_key_ref: keychain:acme-sshkey
  jump_host: bastion.acme.com
  jump_user: deploy
  keys:
    - keychain:acme-sshkey
  hosts:
    bastion:
      address: 10.0.1.1
    web:
      address: 10.0.1.10
      user: root
      port: 2222
      key_ref: keychain:acme-web-key

vpn:
  provider: wireguard   # wireguard | amnezia | tailscale
  config: ~/projects/acme/wg0.conf

dns:
  resolvers: [10.0.0.53]
  search_domains: [acme.internal]

hosts:
  entries:
    - "10.0.1.10 grafana.acme.internal"

cloud:
  aws:
    profile: acme-prod
    sso: true
  kubernetes:
    kubeconfig: ~/projects/acme/kubeconfig
    refresh:
      provider: yandex
      cluster: acme-k8s
  nomad:
    addr: https://nomad.acme.com:4646
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
  profile: "Profile 1"
  app: google-chrome

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

## SSH Management

```bash
hat ssh config acme                           # show SSH config
hat ssh config acme --default-user deploy     # set default user
hat ssh config acme --default-key acme-sshkey # set default key
hat ssh config acme --jump deploy@bastion.com # set jump host

hat ssh add acme bastion 10.0.1.1             # add host
hat ssh add acme db db.internal -u postgres -p 5432 -k acme-db-key
hat ssh list                                  # all hosts, all companies
hat ssh list acme                             # hosts for one company
hat ssh connect acme bastion                  # connect (uses defaults)
hat ssh connect acme web -u root              # override user
hat ssh remove acme old-server                # remove host
```

SSH keys stored in Keychain are extracted to a temp file (0600) during `hat on`, loaded via `ssh-add`, deleted on `hat off`.

## VPN Management

```bash
hat vpn config acme --provider wireguard      # set provider
hat vpn config acme                           # show config
hat vpn up acme                               # connect (prompts)
hat vpn up acme -y                            # connect (no prompt, Touch ID)
hat vpn down acme                             # disconnect
hat vpn down acme -y                          # disconnect (no prompt)
hat vpn status                                # all companies
hat vpn status acme                           # one company
```

VPN config file defaults to `~/projects/<company>/wg0.conf`. Supports WireGuard, AmneziaVPN, Tailscale.

`hat on` connects VPN automatically. `hat off` disconnects it. Use `hat on --no-vpn` to skip.

## Secrets

Stored in macOS Keychain or Bitwarden. Referenced in config via `*_ref` fields.

```bash
hat secret set keychain:acme-token            # paste value, Ctrl-D
hat secret set keychain:acme-key -f key.pem   # from file
hat secret get keychain:acme-token            # display value
hat secret list                               # all secrets
hat secret list --company acme                # one company
hat secret list --check                       # verify accessibility
hat secret scan                               # find + register existing secrets
hat secret delete keychain:old-token          # remove
```

## Repo Management

```bash
hat repos clone acme                          # clone all (GitLab subgroups preserved)
hat repos pull acme                           # pull updates
hat repos pull --all                          # all companies
hat repos pull --tag infra                    # companies with tag
hat repos sync acme                           # clone new + pull existing
hat repos list acme                           # local vs remote
```

Repos cloned to `~/projects/<company>/repos/`.

## Tool Management

Tools defined globally in `~/projects/common/tools.yaml`. Three package managers: brew, pipx (uv tool), npm.

```bash
hat tools init                                # generate default tools.yaml
hat tools list                                # show all with install status
hat tools add brew k9s                        # add a tool
hat tools add npm @bitwarden/cli              # add npm package
hat tools remove brew k9s                     # remove from list
hat tools install                             # install/update all
hat tools check                               # show what's missing
```

## Shell Aliases & Completions

130+ aliases for kubectl, helm, terraform, ansible, nomad, vault, consul, docker, git, and system tools.

```bash
hat aliases generate                          # ~/projects/common/aliases.sh
hat completions generate                      # ~/projects/common/completions.sh
```

Sourced automatically by `hat shell-init zsh`.

## Network Tools

```bash
hat net domain example.com                    # WHOIS + RDAP (expiry, registrar)
hat net cert example.com                      # SSL cert (self-signed, chain, expiry)
hat net ip 8.8.8.8                            # geolocation, ISP, hosting
hat net dns example.com                       # A, AAAA, MX, NS, CNAME, TXT
hat net check host.com                        # ping + traceroute + ports
hat net check host.com -p 8080 -p 443        # specific ports
```

## Claude Code Skills

13 skills for Claude Code: GitLab, GitHub, Favro, Jira, Kubernetes, Helm, Terraform, Ansible, Nomad, Vault, Consul, Docker, Code Review.

```bash
hat skills deploy
```

## What Happens on `hat on`

Modules activate in order (deactivate in reverse):

1. **tools** — install/update CLI tools
2. **vpn** — connect VPN (skips if already connected)
3. **dns** — configure resolvers
4. **hosts** — add `/etc/hosts` entries
5. **ssh** — load SSH keys (from Keychain → temp file → ssh-add)
6. **git** — set git identity
7. **cloud** — set cloud credentials (AWS, K8s, Nomad, Vault, etc.)
8. **env** — export custom env vars
9. **docker** — registry login
10. **proxy** — set proxy env vars
11. **browser** — open with company profile
12. **apps** — open Slack, etc.

If a module fails, already-activated modules are rolled back. State tracked in `~/Library/hat/` with atomic writes.

## All Commands

```
hat setup                                     first-time setup
hat on <company> [--no-vpn]                   put on a company hat
hat off [company]                             take off (disconnects VPN)
hat status                                    what hat am I wearing?
hat list [--tag TAG]                          list all hats
hat init <company>                            scaffold new company

hat ssh config <company> [options]            show/set SSH defaults
hat ssh add <company> <name> <addr> [opts]    add SSH host
hat ssh list [company]                        list SSH hosts
hat ssh connect <company> <host> [opts]       connect via SSH
hat ssh remove <company> <name>               remove SSH host

hat vpn config <company> [options]            show/set VPN config
hat vpn up <company> [-y]                     connect VPN
hat vpn down <company> [-y]                   disconnect VPN
hat vpn status [company]                      check VPN status

hat config set <company> <path> <value>       set config value
hat config add-ssh <company> <name> [-f]      store SSH key
hat config add-secret <company> <path> <name> store secret + ref
hat config validate <company>                 validate config
hat template <company> --from <other>         clone config

hat secret set <ref> [-f FILE]                store secret
hat secret get <ref>                          display secret
hat secret list [--company] [--check]         list secrets
hat secret scan                               find existing secrets
hat secret delete <ref>                       remove secret

hat repos clone <company>                     clone all repos
hat repos pull <company> [--all] [--tag]      pull updates
hat repos sync <company>                      clone + pull
hat repos list <company>                      local vs remote

hat tools init                                generate tools.yaml
hat tools list                                show install status
hat tools add <method> <package>              add tool
hat tools remove <method> <package>           remove tool
hat tools install                             install/update all
hat tools check                               show missing

hat tunnel start <company>                    start SSH tunnels
hat tunnel stop                               stop tunnels

hat run <company> -- <command>                run in company env
hat env <company> [--export]                  show env vars
hat shell <company>                           spawn company shell
hat diff <company1> <company2>                compare configs

hat net domain <domain>                       WHOIS + RDAP
hat net cert <host>                           SSL certificate
hat net ip <address>                          IP geolocation
hat net dns <domain>                          DNS records
hat net check <host> [-p PORT]                ping + trace + ports

hat doctor [company]                          health check
hat log [--company] [-n LIMIT]                activity log
hat migrate                                   migrate from old path
hat backup [-o DIR]                           backup configs
hat restore <archive>                         restore backup
hat kubeconfig merge                          merge kubeconfigs
hat aliases generate                          generate aliases
hat completions generate                      generate completions
hat skills deploy                             deploy Claude skills
```
