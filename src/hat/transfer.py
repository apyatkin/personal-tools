"""Export/import company configs as encrypted archives."""

from __future__ import annotations

import tarfile
from pathlib import Path

from hat.config import get_config_dir


def export_company(company: str, output_dir: Path | None = None) -> Path:
    """Export a company config as a tar.gz (without secret values)."""
    config_dir = get_config_dir() / "companies" / company
    if not config_dir.exists():
        raise FileNotFoundError(f"Company '{company}' not found")

    output = (output_dir or Path.cwd()) / f"hat-{company}-export.tar.gz"
    with tarfile.open(output, "w:gz") as tar:
        tar.add(config_dir, arcname=company)

    return output


def import_company(archive: Path, name: str | None = None) -> str:
    """Import a company config from a tar.gz archive."""
    with tarfile.open(archive, "r:gz") as tar:
        members = tar.getnames()
        # Detect company name from archive
        company = members[0].split("/")[0] if members else "imported"
        if name:
            company = name

        target = get_config_dir() / "companies" / company
        target.mkdir(parents=True, exist_ok=True)

        for member in tar.getmembers():
            # Rewrite paths to target company name
            member.name = member.name.replace(members[0].split("/")[0], company, 1)
            tar.extract(member, get_config_dir() / "companies")

    return company
