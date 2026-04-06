from __future__ import annotations


def generate_shell_init(shell: str) -> str:
    if shell != "zsh":
        raise ValueError(f"Unsupported shell: {shell}")

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
