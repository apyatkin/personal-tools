from __future__ import annotations

import tarfile
from datetime import datetime
from pathlib import Path

from hat.config import get_config_dir

EXCLUDE_PATTERNS = {"state.json", "state.env", "tools_state.json", "log.json", "tunnel_pids.json"}


def create_backup(output_dir: Path | None = None) -> Path:
    config_dir = get_config_dir()
    if not config_dir.exists():
        raise FileNotFoundError(f"Config dir not found: {config_dir}")

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest_dir = output_dir or Path.cwd()
    dest_dir.mkdir(parents=True, exist_ok=True)
    output = dest_dir / f"hat-backup-{timestamp}.tar.gz"

    def _filter(info: tarfile.TarInfo) -> tarfile.TarInfo | None:
        if info.name.split("/")[-1] in EXCLUDE_PATTERNS:
            return None
        return info

    with tarfile.open(output, "w:gz") as tar:
        tar.add(config_dir, arcname="hat", filter=_filter)

    return output


def restore_backup(archive: Path) -> list[str]:
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)

    with tarfile.open(archive, "r:gz") as tar:
        tar.extractall(config_dir.parent, filter="data")

    return [f"Restored to {config_dir}"]
