from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from hat.config import get_config_dir

MAX_ENTRIES = 100


def log_event(action: str, company: str, modules: list[str] | None = None):
    log_file = get_config_dir() / "log.json"
    entries = _read_log(log_file)
    entries.append(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "company": company,
            "modules": modules or [],
        }
    )
    entries = entries[-MAX_ENTRIES:]
    log_file.parent.mkdir(parents=True, exist_ok=True)
    log_file.write_text(json.dumps(entries, indent=2) + "\n")


def read_log(company: str | None = None, limit: int = 20) -> list[dict]:
    log_file = get_config_dir() / "log.json"
    entries = _read_log(log_file)
    if company:
        entries = [e for e in entries if e.get("company") == company]
    return entries[-limit:]


def _read_log(log_file: Path) -> list[dict]:
    if not log_file.exists():
        return []
    return json.loads(log_file.read_text())
