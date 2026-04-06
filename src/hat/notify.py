from __future__ import annotations

import subprocess

import yaml

from hat.config import get_config_dir


def is_enabled() -> bool:
    config_file = get_config_dir() / "config.yaml"
    if not config_file.exists():
        return False
    config = yaml.safe_load(config_file.read_text()) or {}
    return config.get("notifications", False)


def send_notification(title: str, message: str):
    if not is_enabled():
        return
    subprocess.Popen([
        "osascript", "-e",
        f'display notification "{message}" with title "{title}"',
    ])
