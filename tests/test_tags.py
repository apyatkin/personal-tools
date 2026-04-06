import yaml
from hat.config import list_companies


def test_list_companies_with_tag(tmp_path, monkeypatch):
    monkeypatch.setenv("HAT_CONFIG_DIR", str(tmp_path))
    for name, tags in [("acme", ["infra"]), ("globex", ["infra", "prod"]), ("initech", [])]:
        d = tmp_path / "companies" / name
        d.mkdir(parents=True)
        (d / "config.yaml").write_text(yaml.dump({"name": name, "tags": tags}))

    assert set(list_companies()) == {"acme", "globex", "initech"}
    assert set(list_companies(tag="infra")) == {"acme", "globex"}
    assert list_companies(tag="prod") == ["globex"]
    assert list_companies(tag="nonexistent") == []
