# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

`hat` (package: hatctl) is a Python CLI tool for switching between multiple company environments. "Put on your company hat" — manages VPN, SSH, cloud credentials, env vars, DNS, git identity, docker, browser profiles, tool installation, and repo management.

## Development

```bash
uv venv && uv pip install -e .      # install in dev mode
uv run hat --version                 # verify
uv run pytest tests/ -v              # all tests
uv run pytest tests/test_foo.py -v   # single file
uv run ruff check .                  # lint
uv run ruff format --check .         # format check
```

## Architecture

### Core
- `src/hat/cli.py` — Main Click group + core commands (on, off, status, list, init, setup, run, env, shell, diff, log, doctor, migrate, backup, restore, template, completion)
- `src/hat/config.py` — YAML config loading/saving, `validate_company_name()`, `set_nested()`, `list_companies(tag=)`
- `src/hat/state.py` — StateManager: `state.json`, `state.env`, `active` flat file. Atomic writes via temp+rename.
- `src/hat/secrets.py` — SecretResolver for macOS Keychain (base64) and Bitwarden
- `src/hat/secret_registry.py` — Tracks hat-managed secrets in `secrets.json`
- `src/hat/utils.py` — Shared `find_binary()` and `sudo_env()` for subprocess calls with Homebrew PATH
- `src/hat/env_builder.py` — `build_company_env()` without side effects (used by run, env, shell)

### CLI Subgroups (split from cli.py)
- `src/hat/cli_ssh.py` — `hat ssh` group: list, connect, add, remove, config
- `src/hat/cli_vpn.py` — `hat vpn` group: config, up, down, status
- `src/hat/cli_repos.py` — `hat repos` group: clone, pull, sync, list
- `src/hat/cli_secret.py` — `hat secret` group: set, get, list, scan, delete
- `src/hat/cli_config.py` — `hat config` group: set, add-ssh, add-secret, validate
- `src/hat/cli_tools.py` — `hat tools` group: init, list, add, remove, install, check + aliases, completions, skills
- `src/hat/cli_net.py` — `hat net` group: domain, cert, ip, dns, check

### Modules (activate/deactivate lifecycle)
- `src/hat/modules/__init__.py` — Module ABC, ModuleStatus, Orchestrator (with rollback on failure)
- Activation order: tools(0) → vpn(2) → dns(3) → hosts(4) → ssh(5) → git(6) → cloud(7) → env(8) → docker(9) → proxy(10) → browser(11) → apps(12)
- Deactivation runs in reverse, continues on per-module failure

### Support
- `src/hat/common.py` — Global tools.yaml, 130+ aliases, completions
- `src/hat/shell.py` — zsh shell integration (reads flat `active` file, not python3)
- `src/hat/repos.py` — GitLab/GitHub API clone/pull with ThreadPoolExecutor
- `src/hat/net.py` — Network tools: WHOIS+RDAP, SSL cert, IP geo, DNS, ping/trace/ports
- `src/hat/tunnel.py` — SSH tunnels + SOCKS proxy (PID tracking, SSH process verification)
- `src/hat/notify.py` — macOS notifications via osascript (opt-in)
- `src/hat/activity_log.py` — JSON activity log (last 100 entries)
- `src/hat/doctor.py` — Health checks
- `src/hat/validate.py` — Config schema validation
- `src/hat/backup.py`, `migrate.py`, `kubeconfig.py`, `skills.py`

## Key Design Decisions

- Config at `~/Library/hat/` (macOS), override with `HAT_CONFIG_DIR`
- Hard switch: one company at a time (`hat on` / `hat off`)
- `hat off` disconnects VPN; `hat on --no-vpn` skips VPN
- Secrets via `*_ref` fields: `keychain:<name>` or `bitwarden:<path>`
- Keychain secrets base64-encoded for multiline (SSH keys, certs)
- SSH keys extracted from Keychain → temp file (0600) → ssh-add → deleted on off
- VPN checks "already connected" before connecting
- Atomic state writes (write temp → chmod 0600 → os.replace)
- Shell hook reads flat `~/Library/hat/active` file (no python3 subprocess)
- Tools in `~/projects/common/tools.yaml` (brew, pipx, npm)
- Company names validated: `^[a-zA-Z0-9_-]+$`
- `find_binary()` + `sudo_env()` in utils.py for Homebrew PATH in sudo
- All sensitive files 0600 permissions
- Module rollback on activation failure; deactivation continues on per-module error

## CI

- `.github/workflows/test.yml` — runs on push to main + PRs: ruff check, ruff format, pytest
- `.github/workflows/publish.yml` — runs on `v*` tags: test → build → PyPI publish (OIDC trusted publisher)
