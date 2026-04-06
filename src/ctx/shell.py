from __future__ import annotations


def generate_shell_init(shell: str) -> str:
    if shell != "zsh":
        raise ValueError(f"Unsupported shell: {shell}")

    return """\
# ctx shell integration
_ctx_precmd() {
  local env_file="${CTX_CONFIG_DIR:-$HOME/.config/ctx}/state.env"
  if [[ -f "$env_file" ]]; then
    source "$env_file"
  fi
  # Read active company for prompt
  local state_file="${CTX_CONFIG_DIR:-$HOME/.config/ctx}/state.json"
  if [[ -f "$state_file" ]]; then
    export CTX_ACTIVE=$(python3 -c "import json,sys;d=json.load(open('$state_file'));print(d.get('active_company',''))" 2>/dev/null)
  else
    unset CTX_ACTIVE
  fi
}
autoload -Uz add-zsh-hook
add-zsh-hook precmd _ctx_precmd

# Prompt indicator
if [[ -n "$CTX_ACTIVE" ]]; then
  RPROMPT="[${CTX_ACTIVE}] ${RPROMPT}"
fi
"""
