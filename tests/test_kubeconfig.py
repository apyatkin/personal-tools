import yaml
from hat.kubeconfig import merge_kubeconfigs


def test_merge_kubeconfigs(tmp_path, monkeypatch):
    monkeypatch.setenv("HAT_CONFIG_DIR", str(tmp_path))

    # Create company with kubeconfig
    acme_dir = tmp_path / "companies" / "acme"
    acme_dir.mkdir(parents=True)
    kc_file = tmp_path / "acme-kubeconfig"
    kc_file.write_text(
        yaml.dump(
            {
                "apiVersion": "v1",
                "kind": "Config",
                "clusters": [
                    {"name": "prod", "cluster": {"server": "https://k8s.acme.com"}}
                ],
                "contexts": [
                    {"name": "prod", "context": {"cluster": "prod", "user": "admin"}}
                ],
                "users": [{"name": "admin", "user": {"token": "abc"}}],
            }
        )
    )
    (acme_dir / "config.yaml").write_text(
        yaml.dump(
            {
                "name": "acme",
                "cloud": {"kubernetes": {"kubeconfig": str(kc_file)}},
            }
        )
    )

    path = merge_kubeconfigs(["acme"])
    merged = yaml.safe_load(path.read_text())
    assert len(merged["clusters"]) == 1
    assert merged["clusters"][0]["name"] == "acme-prod"
    assert merged["contexts"][0]["name"] == "acme-prod"
    assert merged["users"][0]["name"] == "acme-admin"


def test_merge_no_kubeconfigs(tmp_path, monkeypatch):
    monkeypatch.setenv("HAT_CONFIG_DIR", str(tmp_path))
    acme_dir = tmp_path / "companies" / "acme"
    acme_dir.mkdir(parents=True)
    (acme_dir / "config.yaml").write_text("name: acme\n")

    path = merge_kubeconfigs(["acme"])
    merged = yaml.safe_load(path.read_text())
    assert merged["clusters"] == []
