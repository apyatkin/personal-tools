# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

`hat` is a Python CLI tool for switching between multiple company environments. "Put on your company hat" — manages VPN, SSH keys, cloud credentials, env vars, DNS, git identity, docker registries, browser profiles, and tool installation.

## Development

```bash
uv venv && uv pip install -e .     # install in dev mode
uv run hat --version               # verify CLI works (should show 1.0.0)
uv run pytest tests/ -v            # run all tests
uv run pytest tests/test_foo.py -v # run single test file
```

## Architecture

- `src/hat/cli.py` — Click command definitions, wires everything together
- `src/hat/config.py` — YAML config loading from `~/Library/hat/companies/<name>/config.yaml`
- `src/hat/state.py` — State management (`state.json` + `state.env`)
- `src/hat/secrets.py` — Secret resolution from macOS Keychain and Bitwarden (base64-encoded in Keychain)
- `src/hat/shell.py` — Shell integration code generation for zsh (sources aliases + completions)
- `src/hat/common.py` — Global shared config: aliases, completions, tools (`~/projects/common/`)
- `src/hat/skills.py` — Claude Code skill deployment (`~/projects/.claude/skills/`)
- `src/hat/repos.py` — Git repo cloning/pulling via GitLab/GitHub APIs
- `src/hat/modules/` — Each module has `activate()`, `deactivate()`, `status()` methods:
  - Activation order: tools(0) → vpn(2) → dns(3) → hosts(4) → ssh(5) → git(6) → cloud(7) → env(8) → docker(9) → proxy(10) → browser(11) → apps(12)
  - Deactivation runs in reverse order

## Key Design Decisions

- Config at `~/Library/hat/` (macOS standard), override with `HAT_CONFIG_DIR`
- Hard switch only — one active company at a time (`hat on` / `hat off`)
- All company config sections are optional
- Tools defined globally in `~/projects/common/tools.yaml` (not per-company)
- Secrets referenced via `*_ref` fields using `keychain:<name>` or `bitwarden:<path>` syntax
- Keychain secrets are base64-encoded to support multiline values (SSH keys, certs)
- Privileged operations (vpn, dns, hosts) prompt before running `sudo`
- Tool update checks throttled to once per 24 hours
- GitLab repos preserve nested subgroup structure
- Shell aliases and completions in `~/projects/common/`, sourced by shell hook
