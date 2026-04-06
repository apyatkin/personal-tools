from __future__ import annotations

from pathlib import Path

PROJECTS_DIR = Path.home() / "projects"
COMMON_DIR = PROJECTS_DIR / "common"

ALIASES = '''\
# Kubernetes
alias k="kubectl"
alias kgp="kubectl get pods"
alias kgn="kubectl get nodes"
alias kgs="kubectl get svc"
alias kgd="kubectl get deployments"
alias kgi="kubectl get ingress"
alias kga="kubectl get all"
alias kd="kubectl describe"
alias kdp="kubectl describe pod"
alias kl="kubectl logs -f"
alias klp="kubectl logs -f --previous"
alias ke="kubectl exec -it"
alias kaf="kubectl apply -f"
alias kdel="kubectl delete"
alias kns="kubectl config set-context --current --namespace"
alias kctx="kubectl config use-context"
alias ktop="kubectl top pods"
alias kev="kubectl get events --sort-by=.lastTimestamp"

# Helm
alias h="helm"
alias hl="helm list"
alias hs="helm status"
alias hh="helm history"
alias hd="helm diff upgrade"
alias ht="helm template"

# Terraform / OpenTofu
alias tf="tofu"
alias tfi="tofu init"
alias tfp="tofu plan"
alias tfv="tofu validate"
alias tff="tofu fmt"
alias tfs="tofu state list"
alias tg="terragrunt"
alias tgp="terragrunt plan"
alias tga="terragrunt apply"

# Ansible
alias ap="ansible-playbook"
alias al="ansible-lint --profile min"
alias av="ansible-vault"

# Nomad
alias ns="nomad status"
alias nj="nomad job plan"
alias na="nomad alloc status"
alias nal="nomad alloc logs"

# Vault
alias vs="vault status"
alias vkl="vault kv list"
alias vkg="vault kv get"
alias vtl="vault token lookup"

# Consul
alias cm="consul members"
alias cs="consul catalog services"
alias ckv="consul kv get"

# Docker
alias d="docker"
alias dc="docker compose"
alias dcu="docker compose up -d"
alias dcd="docker compose down"
alias dcl="docker compose logs -f"
alias dps="docker ps"
alias dex="docker exec -it"

# Git
alias g="git"
alias gs="git status"
alias gd="git diff"
alias gl="git log --oneline -20"
alias gp="git pull --ff-only"
'''

COMPLETIONS = '''\
# Native completions
source <(kubectl completion zsh 2>/dev/null)
source <(helm completion zsh 2>/dev/null)
source <(gh completion -s zsh 2>/dev/null)
source <(glab completion -s zsh 2>/dev/null)
source <(docker completion zsh 2>/dev/null)

# Alias completions
compdef k=kubectl
compdef h=helm
compdef tf=tofu
compdef tg=terragrunt
compdef ap=ansible-playbook
compdef ns=nomad
compdef nj=nomad
compdef vs=vault
compdef cm=consul
compdef d=docker
compdef g=git
'''


def generate_aliases(target_dir: Path | None = None) -> Path:
    target = (target_dir or COMMON_DIR)
    target.mkdir(parents=True, exist_ok=True)
    path = target / "aliases.sh"
    path.write_text(ALIASES)
    return path


def generate_completions(target_dir: Path | None = None) -> Path:
    target = (target_dir or COMMON_DIR)
    target.mkdir(parents=True, exist_ok=True)
    path = target / "completions.sh"
    path.write_text(COMPLETIONS)
    return path
