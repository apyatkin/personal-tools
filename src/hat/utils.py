"""Shared utilities for hat CLI."""

from __future__ import annotations

import os
import shutil


def find_binary(name: str) -> str:
    """Find full path of a binary. Sudo uses restricted PATH, so we need absolute paths."""
    path = shutil.which(name)
    if path:
        return path
    for prefix in ["/opt/homebrew/bin", "/usr/local/bin"]:
        candidate = f"{prefix}/{name}"
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return name


def sudo_env() -> dict[str, str]:
    """Build environment dict with Homebrew in PATH for sudo commands."""
    return {
        **os.environ,
        "PATH": f"/opt/homebrew/bin:/usr/local/bin:{os.environ.get('PATH', '')}",
    }
