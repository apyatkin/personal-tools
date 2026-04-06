from __future__ import annotations

from pathlib import Path

import yaml

from hat.config import get_config_dir, load_company_config, list_companies


def merge_kubeconfigs(companies: list[str] | None = None) -> Path:
    if companies is None:
        companies = list_companies()

    merged = {
        "apiVersion": "v1",
        "kind": "Config",
        "clusters": [],
        "contexts": [],
        "users": [],
        "current-context": "",
    }

    for company in companies:
        config = load_company_config(company)
        kubeconfig_path = (
            config.get("cloud", {}).get("kubernetes", {}).get("kubeconfig")
        )
        if not kubeconfig_path:
            continue

        kc_file = Path(kubeconfig_path).expanduser()
        if not kc_file.exists():
            continue

        kc = yaml.safe_load(kc_file.read_text())
        if not kc:
            continue

        for cluster in kc.get("clusters", []):
            cluster["name"] = f"{company}-{cluster['name']}"
            merged["clusters"].append(cluster)

        for user in kc.get("users", []):
            user["name"] = f"{company}-{user['name']}"
            merged["users"].append(user)

        for ctx in kc.get("contexts", []):
            original_name = ctx["name"]
            ctx["name"] = f"{company}-{original_name}"
            ctx["context"]["cluster"] = f"{company}-{ctx['context']['cluster']}"
            ctx["context"]["user"] = f"{company}-{ctx['context']['user']}"
            merged["contexts"].append(ctx)

    output = get_config_dir() / "merged-kubeconfig"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(yaml.dump(merged, default_flow_style=False))
    return output
