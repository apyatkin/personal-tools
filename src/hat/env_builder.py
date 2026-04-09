from __future__ import annotations

from pathlib import Path

from hat.config import load_company_config
from hat.secrets import SecretResolver


def build_company_env(company: str) -> dict[str, str]:
    """Build env vars for a company without activating modules or modifying state."""
    config = load_company_config(company)
    resolver = SecretResolver()
    secrets = resolver.resolve_refs(config)

    env_vars: dict[str, str] = {}

    # Git identity
    git = config.get("git", {})
    identity = git.get("identity", {})
    if identity.get("name"):
        env_vars["GIT_AUTHOR_NAME"] = identity["name"]
        env_vars["GIT_COMMITTER_NAME"] = identity["name"]
    if identity.get("email"):
        env_vars["GIT_AUTHOR_EMAIL"] = identity["email"]
        env_vars["GIT_COMMITTER_EMAIL"] = identity["email"]

    # Git sources — export URLs and tokens
    for source in git.get("sources", []):
        provider = source.get("provider", "")
        if provider == "gitlab":
            host = source.get("host", "")
            if host:
                env_vars["GITLAB_URL"] = f"https://{host}"
                env_vars["GITLAB_HOST"] = host
            token_ref = source.get("token_ref")
            if token_ref and token_ref in secrets:
                env_vars["GITLAB_TOKEN"] = secrets[token_ref]
        elif provider == "github":
            org = source.get("org", "")
            if org:
                env_vars["GITHUB_ORG"] = org
            token_ref = source.get("token_ref")
            if token_ref and token_ref in secrets:
                env_vars["GITHUB_TOKEN"] = secrets[token_ref]

    # Cloud providers
    cloud = config.get("cloud", {})
    if "aws" in cloud:
        aws = cloud["aws"]
        if aws.get("region"):
            env_vars["AWS_DEFAULT_REGION"] = aws["region"]
        access_key_ref = aws.get("access_key_ref")
        secret_key_ref = aws.get("secret_key_ref")
        has_keys = (
            access_key_ref
            and access_key_ref in secrets
            and secret_key_ref
            and secret_key_ref in secrets
        )
        if has_keys:
            env_vars["AWS_ACCESS_KEY_ID"] = secrets[access_key_ref]
            env_vars["AWS_SECRET_ACCESS_KEY"] = secrets[secret_key_ref]
        elif aws.get("profile"):
            env_vars["AWS_PROFILE"] = aws["profile"]
    if "kubernetes" in cloud:
        kubeconfig = cloud["kubernetes"].get("kubeconfig", "")
        if kubeconfig:
            env_vars["KUBECONFIG"] = str(Path(kubeconfig).expanduser())
    if "nomad" in cloud:
        env_vars["NOMAD_ADDR"] = cloud["nomad"]["addr"]
        token_ref = cloud["nomad"].get("token_ref")
        if token_ref and token_ref in secrets:
            env_vars["NOMAD_TOKEN"] = secrets[token_ref]
        cacert = cloud["nomad"].get("cacert")
        if cacert:
            env_vars["NOMAD_CACERT"] = str(Path(cacert).expanduser())
    if "vault" in cloud:
        env_vars["VAULT_ADDR"] = cloud["vault"]["addr"]
        token_ref = cloud["vault"].get("token_ref")
        if token_ref and token_ref in secrets:
            env_vars["VAULT_TOKEN"] = secrets[token_ref]
    if "consul" in cloud:
        env_vars["CONSUL_HTTP_ADDR"] = cloud["consul"]["addr"]
        token_ref = cloud["consul"].get("token_ref")
        if token_ref and token_ref in secrets:
            env_vars["CONSUL_HTTP_TOKEN"] = secrets[token_ref]
    if "hetzner" in cloud:
        token_ref = cloud["hetzner"].get("token_ref")
        if token_ref and token_ref in secrets:
            env_vars["HCLOUD_TOKEN"] = secrets[token_ref]
    if "terraform" in cloud:
        for k, v in cloud["terraform"].get("vars", {}).items():
            env_vars[f"TF_VAR_{k}"] = v

    # Custom env vars
    env_vars.update(config.get("env", {}))

    # Venv — only export VIRTUAL_ENV if the venv actually exists.
    # build_company_env is a pure/no-side-effect helper so we don't
    # create the venv here; that happens during `hat on <company>`.
    venv_cfg = config.get("venv") or {}
    if venv_cfg and venv_cfg.get("enabled", True) is not False:
        venv_path = venv_cfg.get("path") or (
            Path.home() / "projects" / config.get("name", company) / "venv"
        )
        venv_path = Path(str(venv_path)).expanduser()
        if (venv_path / "bin" / "python").exists():
            env_vars["VIRTUAL_ENV"] = str(venv_path)

    # Proxy
    proxy = config.get("proxy", {})
    if "http" in proxy:
        env_vars["HTTP_PROXY"] = proxy["http"]
        env_vars["http_proxy"] = proxy["http"]
    if "https" in proxy:
        env_vars["HTTPS_PROXY"] = proxy["https"]
        env_vars["https_proxy"] = proxy["https"]
    if "no_proxy" in proxy:
        env_vars["NO_PROXY"] = proxy["no_proxy"]
        env_vars["no_proxy"] = proxy["no_proxy"]

    return env_vars
