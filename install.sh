#!/usr/bin/env bash
# hat — installation script
#
# Interactive (next-next-finish):
#   curl -fsSL https://raw.githubusercontent.com/apyatkin/hatctl/main/install.sh | bash
#
# Silent (no prompts, defaults to first company "default"):
#   curl -fsSL https://raw.githubusercontent.com/apyatkin/hatctl/main/install.sh | bash -s -- --silent
#
# Silent with custom company name:
#   curl -fsSL .../install.sh | bash -s -- --silent --company myco
#
# Skip first-company creation:
#   curl -fsSL .../install.sh | bash -s -- --silent --no-init
#
# Install from GitHub instead of PyPI:
#   curl -fsSL .../install.sh | bash -s -- --from-github

set -euo pipefail

SILENT=0
COMPANY=""
NO_INIT=0
SOURCE="pypi"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --silent|-s)    SILENT=1; shift ;;
        --company)      COMPANY="$2"; shift 2 ;;
        --no-init)      NO_INIT=1; shift ;;
        --from-github)  SOURCE="github"; shift ;;
        --help|-h)
            sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
    esac
done

# Colors (only when stdout is a TTY)
if [[ -t 1 ]]; then
    BOLD=$(tput bold) DIM=$(tput dim) RED=$(tput setaf 1) GREEN=$(tput setaf 2) YELLOW=$(tput setaf 3) BLUE=$(tput setaf 4) RESET=$(tput sgr0)
else
    BOLD="" DIM="" RED="" GREEN="" YELLOW="" BLUE="" RESET=""
fi

step()  { echo "${BLUE}==>${RESET} ${BOLD}$*${RESET}"; }
ok()    { echo "  ${GREEN}✓${RESET} $*"; }
warn()  { echo "  ${YELLOW}!${RESET} $*"; }
err()   { echo "  ${RED}✗${RESET} $*" >&2; }
ask()   {
    # ask <prompt> <default-yes|no>
    if [[ $SILENT -eq 1 ]]; then
        [[ "$2" == "yes" ]]
        return $?
    fi
    local default_yn="$2"
    local prompt
    if [[ "$default_yn" == "yes" ]]; then
        prompt="$1 [Y/n] "
    else
        prompt="$1 [y/N] "
    fi
    read -r -p "$prompt" reply </dev/tty || reply=""
    reply="${reply:-$default_yn}"
    [[ "$reply" =~ ^[YyJj]([Ee][Ss])?$ ]] || [[ "$reply" == "yes" ]]
}
prompt_value() {
    # prompt_value <question> <default>
    if [[ $SILENT -eq 1 ]]; then
        echo "$2"
        return
    fi
    local reply
    read -r -p "$1 [$2]: " reply </dev/tty || reply=""
    echo "${reply:-$2}"
}

cat <<EOF
${BOLD}hat installer${RESET}
${DIM}Switch between company environments — VPN, SSH, cloud, env vars, git identity.${RESET}

EOF

# ─── 1. Check Python ────────────────────────────────────────────────────────
step "Checking Python 3.11+"
if command -v python3 >/dev/null 2>&1; then
    PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    PY_MAJOR=${PY_VERSION%.*}
    PY_MINOR=${PY_VERSION#*.}
    if [[ "$PY_MAJOR" -ge 3 && "$PY_MINOR" -ge 11 ]]; then
        ok "python3 $PY_VERSION"
    else
        err "python3 $PY_VERSION found — need 3.11+"
        exit 1
    fi
else
    err "python3 not found. Install Python 3.11+ first."
    exit 1
fi

# ─── 2. Check / install uv ──────────────────────────────────────────────────
step "Checking uv (Python tool installer)"
if command -v uv >/dev/null 2>&1; then
    ok "uv already installed: $(uv --version)"
else
    warn "uv not found"
    if ask "  Install uv now?" "yes"; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
        # uv installer puts binary in ~/.local/bin or ~/.cargo/bin
        export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
        if command -v uv >/dev/null 2>&1; then
            ok "uv installed: $(uv --version)"
        else
            err "uv install failed — please install manually: https://docs.astral.sh/uv/"
            exit 1
        fi
    else
        err "Cannot continue without uv"
        exit 1
    fi
fi

# ─── 3. Install hatctl ──────────────────────────────────────────────────────
step "Installing hatctl"
if [[ "$SOURCE" == "github" ]]; then
    PACKAGE="git+https://github.com/apyatkin/hatctl.git"
else
    PACKAGE="hatctl"
fi

if command -v hat >/dev/null 2>&1 && hat --version >/dev/null 2>&1; then
    CURRENT=$(hat --version 2>&1 | awk '{print $NF}')
    ok "hat already installed (v$CURRENT) — upgrading"
    uv tool install --force "$PACKAGE" >/dev/null 2>&1 || uv tool install --force "$PACKAGE"
else
    uv tool install "$PACKAGE" >/dev/null 2>&1 || uv tool install "$PACKAGE"
fi

# Make sure ~/.local/bin is in PATH for the rest of this script
export PATH="$HOME/.local/bin:$PATH"

if ! command -v hat >/dev/null 2>&1; then
    err "hat command not found in PATH after install"
    err "Add this to your shell rc: export PATH=\"\$HOME/.local/bin:\$PATH\""
    exit 1
fi
ok "hat installed: $(hat --version)"

# ─── 4. Run hat setup ───────────────────────────────────────────────────────
step "Running first-time setup"
if [[ $SILENT -eq 1 ]]; then
    # Pipe "no" to skip Touch ID prompt in silent mode
    yes n 2>/dev/null | hat setup || true
else
    hat setup || true
fi

# ─── 5. Shell integration ───────────────────────────────────────────────────
step "Configuring shell integration"
SHELL_RC=""
case "${SHELL:-/bin/zsh}" in
    */zsh)  SHELL_RC="$HOME/.zshrc";  SHELL_NAME="zsh"  ;;
    */bash) SHELL_RC="$HOME/.bashrc"; SHELL_NAME="bash" ;;
    *)      SHELL_RC=""; SHELL_NAME="" ;;
esac

if [[ -n "$SHELL_RC" ]]; then
    HAT_INIT_LINE='eval "$(hat shell-init '"$SHELL_NAME"')"'
    HAT_COMP_LINE='eval "$(_HAT_COMPLETE='"$SHELL_NAME"'_source hat)"'

    if [[ -f "$SHELL_RC" ]] && grep -q 'hat shell-init' "$SHELL_RC"; then
        ok "shell integration already in $SHELL_RC"
    elif ask "  Add hat shell integration to $SHELL_RC?" "yes"; then
        {
            echo ""
            echo "# hat — company context switcher"
            echo "$HAT_INIT_LINE"
            echo "$HAT_COMP_LINE"
        } >> "$SHELL_RC"
        ok "added to $SHELL_RC"
        warn "restart your shell or: source $SHELL_RC"
    else
        warn "skipped — add manually:"
        echo "    $HAT_INIT_LINE"
        echo "    $HAT_COMP_LINE"
    fi
else
    warn "unknown shell ${SHELL:-?} — add hat shell-init manually"
fi

# ─── 6. Create first company ────────────────────────────────────────────────
if [[ $NO_INIT -eq 1 ]]; then
    step "Skipping first-company creation (--no-init)"
else
    step "Creating your first company"
    if [[ $SILENT -eq 1 ]]; then
        FIRST_COMPANY="${COMPANY:-default}"
    else
        if ask "  Create a company config now?" "yes"; then
            FIRST_COMPANY=$(prompt_value "  Company name" "${COMPANY:-mycompany}")
        else
            FIRST_COMPANY=""
        fi
    fi

    if [[ -n "$FIRST_COMPANY" ]]; then
        # Validate name
        if [[ ! "$FIRST_COMPANY" =~ ^[a-zA-Z0-9_-]+$ ]]; then
            err "invalid company name '$FIRST_COMPANY' — use letters, numbers, _, -"
        else
            if hat list 2>/dev/null | grep -qE "^[ ]*$FIRST_COMPANY( |$)"; then
                ok "company '$FIRST_COMPANY' already exists"
            else
                hat init "$FIRST_COMPANY" || warn "could not create '$FIRST_COMPANY'"
            fi
        fi
    fi
fi

# ─── Done ───────────────────────────────────────────────────────────────────
echo
echo "${GREEN}${BOLD}✓ Installation complete${RESET}"
echo
echo "${BOLD}Next steps:${RESET}"
echo "  1. ${DIM}Restart your shell${RESET} (or: source $SHELL_RC)"
if [[ -n "${FIRST_COMPANY:-}" ]]; then
    echo "  2. ${DIM}Configure your company:${RESET}  hat config set $FIRST_COMPANY git.identity.name 'Your Name'"
    echo "  3. ${DIM}Activate it:${RESET}             hat on $FIRST_COMPANY"
else
    echo "  2. ${DIM}Create a company:${RESET}        hat init <name>"
fi
echo
echo "${DIM}Docs:        https://github.com/apyatkin/hatctl${RESET}"
echo "${DIM}Telemetry:   anonymous crash reports are enabled — disable with 'hat telemetry off'${RESET}"
