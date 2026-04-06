from __future__ import annotations

import os
import signal
import subprocess

from hat.config import load_company_config


def start_tunnels(company: str) -> list[dict]:
    config = load_company_config(company)
    ssh_config = config.get("ssh", {})
    jump_host = ssh_config.get("jump_host")
    if not jump_host:
        return []

    jump_user = ssh_config.get("jump_user")
    jump = f"{jump_user}@{jump_host}" if jump_user else jump_host

    results = []

    for tunnel in ssh_config.get("tunnels", []):
        local = tunnel["local_port"]
        remote_host = tunnel["remote_host"]
        remote_port = tunnel["remote_port"]
        proc = subprocess.Popen(
            ["ssh", "-f", "-N", "-L", f"{local}:{remote_host}:{remote_port}", jump],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        results.append({"type": "forward", "local_port": local, "pid": proc.pid})

    socks = ssh_config.get("socks_proxy", {})
    if socks.get("port"):
        proc = subprocess.Popen(
            ["ssh", "-f", "-N", "-D", str(socks["port"]), jump],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        results.append({"type": "socks", "local_port": socks["port"], "pid": proc.pid})

    return results


def stop_tunnels(pids: list[int]) -> list[dict]:
    results = []
    for pid in pids:
        try:
            # Verify it's actually an SSH process before killing
            check = subprocess.run(
                ["ps", "-p", str(pid), "-o", "comm="],
                capture_output=True,
                text=True,
            )
            if "ssh" not in check.stdout.lower():
                results.append(
                    {"pid": pid, "status": "skipped", "reason": "not an SSH process"}
                )
                continue
            os.kill(pid, signal.SIGTERM)
            results.append({"pid": pid, "status": "stopped"})
        except ProcessLookupError:
            results.append({"pid": pid, "status": "already_dead"})
    return results
