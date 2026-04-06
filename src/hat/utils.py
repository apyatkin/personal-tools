"""Shared utilities for hat CLI."""

from __future__ import annotations

import os
import shutil


def find_binary(name: str) -> str:
    """Find full path of a binary. Sudo uses restricted PATH, so we need absolute paths."""
    path = shutil.which(name)
    if path:
        return path
    from hat.platform import find_binary_paths

    for prefix in find_binary_paths():
        candidate = f"{prefix}/{name}"
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return name


def sudo_env() -> dict[str, str]:
    """Build environment dict with extra binary paths in PATH for sudo commands."""
    from hat.platform import find_binary_paths

    extra = ":".join(find_binary_paths())
    return {**os.environ, "PATH": f"{extra}:{os.environ.get('PATH', '')}"}
