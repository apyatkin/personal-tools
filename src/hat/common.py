from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECTS_DIR = Path.home() / "projects"
COMMON_DIR = PROJECTS_DIR / "common"

DEFAULT_TOOLS = {
    "brew": [
        "awscli",
        "bash",
        "kubectl",
        "helm",
        "terraform",
        "nomad",
        "consul",
        "vault",
        "yc",
        "doctl",
        "hcloud",
        "gh",
        "glab",
        "jq",
        "wireguard-tools",
        "docker",
    ],
    "pipx": [
        "ansible",
        "ansible-lint",
        "yamllint",
        "ruff",
    ],
    "npm": [
        "@bitwarden/cli",
    ],
}


def load_common_tools(common_dir: Path | None = None) -> dict[str, Any]:
    tools_file = (common_dir or COMMON_DIR) / "tools.yaml"
    if not tools_file.exists():
        return {}
    with open(tools_file) as f:
        return yaml.safe_load(f) or {}


def generate_tools_config(target_dir: Path | None = None) -> Path:
    target = target_dir or COMMON_DIR
    target.mkdir(parents=True, exist_ok=True)
    path = target / "tools.yaml"
    path.write_text(yaml.dump(DEFAULT_TOOLS, default_flow_style=False, sort_keys=False))
    return path


ALIASES = """\
# Kubernetes
alias k="kubectl"
alias kgp="kubectl get pods"
alias kgpa="kubectl get pods -A"
alias kgpw="kubectl get pods -o wide"
alias kgn="kubectl get nodes"
alias kgs="kubectl get svc"
alias kgd="kubectl get deployments"
alias kgi="kubectl get ingress"
alias kga="kubectl get all"
alias kgns="kubectl get namespaces"
alias kgcm="kubectl get configmaps"
alias kgsec="kubectl get secrets"
alias kgpv="kubectl get pv"
alias kgpvc="kubectl get pvc"
alias kd="kubectl describe"
alias kdp="kubectl describe pod"
alias kdn="kubectl describe node"
alias kds="kubectl describe svc"
alias kl="kubectl logs -f"
alias klp="kubectl logs -f --previous"
alias ke="kubectl exec -it"
alias kaf="kubectl apply -f"
alias kdf="kubectl delete -f"
alias kdel="kubectl delete"
alias kns="kubectl config set-context --current --namespace"
alias kctx="kubectl config use-context"
alias ktop="kubectl top pods"
alias ktopn="kubectl top nodes"
alias kev="kubectl get events --sort-by=.lastTimestamp"
alias kpf="kubectl port-forward"
alias kscale="kubectl scale"
alias kroll="kubectl rollout"
alias krr="kubectl rollout restart"
alias krs="kubectl rollout status"

# Helm
alias h="helm"
alias hl="helm list"
alias hla="helm list -A"
alias hs="helm status"
alias hh="helm history"
alias hd="helm diff upgrade"
alias ht="helm template"
alias hu="helm upgrade --install"
alias hr="helm rollback"
alias hrep="helm repo update"

# Terraform / OpenTofu
alias tf="tofu"
alias tfi="tofu init"
alias tfp="tofu plan"
alias tfa="tofu apply"
alias tfv="tofu validate"
alias tff="tofu fmt"
alias tfs="tofu state list"
alias tfss="tofu state show"
alias tfo="tofu output"
alias tg="terragrunt"
alias tgp="terragrunt plan"
alias tga="terragrunt apply"
alias tgra="terragrunt run-all plan"

# Ansible
alias ap="ansible-playbook"
alias apc="ansible-playbook --check --diff"
alias al="ansible-lint --profile min"
alias av="ansible-vault"
alias ave="ansible-vault encrypt"
alias avd="ansible-vault decrypt"
alias avv="ansible-vault view"

# Nomad
alias ns="nomad status"
alias nj="nomad job plan"
alias njr="nomad job run"
alias na="nomad alloc status"
alias nal="nomad alloc logs"
alias nale="nomad alloc logs -stderr"
alias nalf="nomad alloc logs -f -stderr"
alias nae="nomad alloc exec"
alias nns="nomad node status"

# Vault
alias vs="vault status"
alias vkl="vault kv list"
alias vkg="vault kv get"
alias vkgj="vault kv get -format=json"
alias vtl="vault token lookup"
alias vsl="vault secrets list"
alias vpl="vault policy list"

# Consul
alias cm="consul members"
alias cs="consul catalog services"
alias cn="consul catalog nodes"
alias ckv="consul kv get"
alias ckvr="consul kv get -recurse"

# Docker
alias d="docker"
alias dc="docker compose"
alias dcu="docker compose up -d"
alias dcub="docker compose up --build"
alias dcd="docker compose down"
alias dcl="docker compose logs -f"
alias dcp="docker compose ps"
alias dce="docker compose exec"
alias dps="docker ps"
alias dpsa="docker ps -a"
alias dex="docker exec -it"
alias dl="docker logs -f"
alias dimg="docker images"
alias drmi="docker rmi"
alias dprune="docker system prune"
alias dstats="docker stats"

# Git
alias g="git"
alias gs="git status"
alias gd="git diff"
alias gds="git diff --staged"
alias gl="git log --oneline -20"
alias glg="git log --graph --oneline -20"
alias gp="git pull --ff-only"
alias gps="git push"
alias ga="git add"
alias gc="git commit"
alias gcm="git commit -m"
alias gco="git checkout"
alias gb="git branch"
alias gba="git branch -a"
alias gst="git stash"
alias gstp="git stash pop"
alias gf="git fetch --all"
alias grb="git rebase"
alias gm="git merge"

# System / Files
alias ll="ls -la"
alias la="ls -A"
alias lt="ls -lt"
alias ..="cd .."
alias ...="cd ../.."
alias md="mkdir -p"
alias cpv="rsync -ah --progress"
alias duh="du -h --max-depth=1 | sort -rh"
alias duf="df -h"
alias psg="ps aux | grep -i"
alias topcpu="ps aux --sort=-%cpu | head -20"
alias topmem="ps aux --sort=-%mem | head -20"
alias myip="curl -s ifconfig.me"
alias ports="lsof -i -P -n | grep LISTEN"
alias flushdns="sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder"
alias watch="watch "
"""

COMPLETIONS = """\
# Native completions
source <(kubectl completion zsh 2>/dev/null)
source <(helm completion zsh 2>/dev/null)
source <(gh completion -s zsh 2>/dev/null)
source <(glab completion -s zsh 2>/dev/null)
source <(docker completion zsh 2>/dev/null)
source <(tofu -install-autocomplete 2>/dev/null || true)
source <(nomad -autocomplete-install 2>/dev/null || true)

# Alias completions
compdef k=kubectl
compdef h=helm
compdef tf=tofu
compdef tg=terragrunt
compdef ap=ansible-playbook
compdef ns=nomad
compdef nj=nomad
compdef na=nomad
compdef vs=vault
compdef cm=consul
compdef d=docker
compdef dc="docker compose"
compdef g=git
"""


def generate_aliases(target_dir: Path | None = None) -> Path:
    target = target_dir or COMMON_DIR
    target.mkdir(parents=True, exist_ok=True)
    path = target / "aliases.sh"
    path.write_text(ALIASES)
    return path


def generate_completions(target_dir: Path | None = None) -> Path:
    target = target_dir or COMMON_DIR
    target.mkdir(parents=True, exist_ok=True)
    path = target / "completions.sh"
    path.write_text(COMPLETIONS)
    return path
