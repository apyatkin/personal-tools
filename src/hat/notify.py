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
    # Escape backslashes and quotes for AppleScript
    safe_title = title.replace("\\", "\\\\").replace('"', '\\"')
    safe_message = message.replace("\\", "\\\\").replace('"', '\\"')
    subprocess.Popen(
        [
            "osascript",
            "-e",
            f'display notification "{safe_message}" with title "{safe_title}"',
        ]
    )
