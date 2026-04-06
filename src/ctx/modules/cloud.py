from __future__ import annotations

import subprocess
from pathlib import Path

from ctx.modules import Module, ModuleStatus
from ctx.state import StateManager


class CloudModule(Module):
    name = "cloud"
    order = 7

    def __init__(self):
        self._active_providers: list[str] = []
        self._env_vars: dict[str, str] = {}

    def activate(self, config: dict, secrets: dict) -> None:
        if not config:
            return

        env_vars: dict[str, str] = {}

        if "aws" in config:
            aws = config["aws"]
            env_vars["AWS_PROFILE"] = aws["profile"]
            if aws.get("sso"):
                subprocess.run(
                    ["aws", "sso", "login", "--profile", aws["profile"]],
                    capture_output=True, text=True,
                )
            self._active_providers.append("aws")

        if "kubernetes" in config:
            k8s = config["kubernetes"]
            kubeconfig = k8s.get("kubeconfig", "")
            env_vars["KUBECONFIG"] = str(Path(kubeconfig).expanduser())
            refresh = k8s.get("refresh")
            if refresh:
                self._refresh_kubeconfig(refresh)
            self._active_providers.append("kubernetes")

        if "nomad" in config:
            nomad = config["nomad"]
            env_vars["NOMAD_ADDR"] = nomad["addr"]
            token_ref = nomad.get("token_ref")
            if token_ref and token_ref in secrets:
                env_vars["NOMAD_TOKEN"] = secrets[token_ref]
            cacert = nomad.get("cacert")
            if cacert:
                env_vars["NOMAD_CACERT"] = str(Path(cacert).expanduser())
            self._active_providers.append("nomad")

        if "vault" in config:
            vault = config["vault"]
            env_vars["VAULT_ADDR"] = vault["addr"]
            token_ref = vault.get("token_ref")
            if token_ref and token_ref in secrets:
                env_vars["VAULT_TOKEN"] = secrets[token_ref]
            self._active_providers.append("vault")

        if "consul" in config:
            consul = config["consul"]
            env_vars["CONSUL_HTTP_ADDR"] = consul["addr"]
            token_ref = consul.get("token_ref")
            if token_ref and token_ref in secrets:
                env_vars["CONSUL_HTTP_TOKEN"] = secrets[token_ref]
            self._active_providers.append("consul")

        if "yandex" in config:
            yc = config["yandex"]
            subprocess.run(
                ["yc", "config", "profile", "activate", yc["profile"]],
                capture_output=True, text=True,
            )
            self._active_providers.append("yandex")

        if "digitalocean" in config:
            do = config["digitalocean"]
            subprocess.run(
                ["doctl", "auth", "switch", "--context", do["context"]],
                capture_output=True, text=True,
            )
            self._active_providers.append("digitalocean")

        if "hetzner" in config:
            hz = config["hetzner"]
            token_ref = hz.get("token_ref")
            if token_ref and token_ref in secrets:
                env_vars["HCLOUD_TOKEN"] = secrets[token_ref]
            self._active_providers.append("hetzner")

        if "terraform" in config:
            tf = config["terraform"]
            for var_name, var_value in tf.get("vars", {}).items():
                env_vars[f"TF_VAR_{var_name}"] = var_value
            self._active_providers.append("terraform")

        self._env_vars = env_vars
        if env_vars:
            sm = StateManager()
            existing = {}
            if sm._env_file.exists():
                for line in sm._env_file.read_text().splitlines():
                    if line.startswith("export "):
                        key, _, val = line[7:].partition("=")
                        existing[key] = val.strip('"')
            existing.update(env_vars)
            sm.write_env(existing)

    def _refresh_kubeconfig(self, refresh: dict) -> None:
        provider = refresh.get("provider")
        cluster = refresh.get("cluster", "")
        if provider == "yandex":
            subprocess.run(
                ["yc", "managed-kubernetes", "cluster", "get-credentials",
                 cluster, "--external", "--force"],
                capture_output=True, text=True,
            )
        elif provider == "aws":
            subprocess.run(
                ["aws", "eks", "update-kubeconfig", "--name", cluster],
                capture_output=True, text=True,
            )
        elif provider == "digitalocean":
            subprocess.run(
                ["doctl", "kubernetes", "cluster", "kubeconfig", "save", cluster],
                capture_output=True, text=True,
            )

    def deactivate(self) -> None:
        self._active_providers = []
        self._env_vars = {}

    def status(self) -> ModuleStatus:
        if not self._active_providers:
            return ModuleStatus(active=False)
        return ModuleStatus(
            active=True,
            details=", ".join(self._active_providers),
        )
