from __future__ import annotations


def generate_shell_init(shell: str) -> str:
    if shell == "zsh":
        return _zsh_init()
    elif shell == "bash":
        return _bash_init()
    else:
        raise ValueError(f"Unsupported shell: {shell}")


def _zsh_init() -> str:
    return """\
# hat shell integration

# Common aliases and completions
[[ -f ~/projects/common/aliases.sh ]] && source ~/projects/common/aliases.sh
[[ -f ~/projects/common/completions.sh ]] && source ~/projects/common/completions.sh

# hat env and prompt
_hat_precmd() {
  local env_file="${HAT_CONFIG_DIR:-$HOME/Library/hat}/state.env"
  if [[ -f "$env_file" ]]; then
    source "$env_file"
  fi
  local active_file="${HAT_CONFIG_DIR:-$HOME/Library/hat}/active"
  if [[ -f "$active_file" ]]; then
    export HAT_ACTIVE=$(cat "$active_file")
  else
    unset HAT_ACTIVE
  fi
  _hat_manage_venv
}

# Activate / deactivate the company venv based on VIRTUAL_ENV and HAT_ACTIVE.
# Saves the original PATH on first activation and restores it on deactivation,
# so sourcing state.env repeatedly is idempotent.
_hat_manage_venv() {
  if [[ -n "$HAT_ACTIVE" && -n "$VIRTUAL_ENV" && -x "$VIRTUAL_ENV/bin/python" ]]; then
    if [[ -z "$_HAT_ORIG_PATH" ]]; then
      export _HAT_ORIG_PATH="$PATH"
    fi
    case ":$PATH:" in
      *":$VIRTUAL_ENV/bin:"*) ;;
      *) export PATH="$VIRTUAL_ENV/bin:$PATH" ;;
    esac
  elif [[ -z "$HAT_ACTIVE" && -n "$_HAT_ORIG_PATH" ]]; then
    export PATH="$_HAT_ORIG_PATH"
    unset _HAT_ORIG_PATH VIRTUAL_ENV
  fi
}
autoload -Uz add-zsh-hook
add-zsh-hook precmd _hat_precmd

# Prompt indicator with VPN status
_hat_prompt_info() {
  local info=""
  if [[ -n "$HAT_ACTIVE" ]]; then
    info="$HAT_ACTIVE"
    # Check VPN (fast, no sudo)
    if ls /var/run/wireguard/ &>/dev/null 2>&1; then
      info="$info|vpn"
    fi
    echo "[$info]"
  fi
}
RPROMPT='$(_hat_prompt_info) '${RPROMPT}
"""


def _bash_init() -> str:
    from hat.platform import get_default_config_dir

    config_dir = get_default_config_dir()
    return f"""\
# hat shell integration (bash)

[[ -f ~/projects/common/aliases.sh ]] && source ~/projects/common/aliases.sh
[[ -f ~/projects/common/completions.sh ]] && source ~/projects/common/completions.sh

_hat_manage_venv() {{
  if [[ -n "$HAT_ACTIVE" && -n "$VIRTUAL_ENV" && -x "$VIRTUAL_ENV/bin/python" ]]; then
    if [[ -z "$_HAT_ORIG_PATH" ]]; then
      export _HAT_ORIG_PATH="$PATH"
    fi
    case ":$PATH:" in
      *":$VIRTUAL_ENV/bin:"*) ;;
      *) export PATH="$VIRTUAL_ENV/bin:$PATH" ;;
    esac
  elif [[ -z "$HAT_ACTIVE" && -n "$_HAT_ORIG_PATH" ]]; then
    export PATH="$_HAT_ORIG_PATH"
    unset _HAT_ORIG_PATH VIRTUAL_ENV
  fi
}}

_hat_prompt() {{
  local env_file="{config_dir}/state.env"
  if [[ -f "$env_file" ]]; then
    source "$env_file"
  fi
  local active_file="{config_dir}/active"
  if [[ -f "$active_file" ]]; then
    export HAT_ACTIVE=$(cat "$active_file")
  else
    unset HAT_ACTIVE
  fi
  _hat_manage_venv
}}
PROMPT_COMMAND="_hat_prompt;$PROMPT_COMMAND"

if [[ -n "$HAT_ACTIVE" ]]; then
  PS1="[$HAT_ACTIVE] $PS1"
fi
"""
