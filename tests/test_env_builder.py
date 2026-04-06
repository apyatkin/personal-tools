import textwrap
from hat.env_builder import build_company_env


def test_build_env_git_identity(tmp_path, monkeypatch):
    monkeypatch.setenv("HAT_CONFIG_DIR", str(tmp_path))
    company_dir = tmp_path / "companies" / "acme"
    company_dir.mkdir(parents=True)
    (company_dir / "config.yaml").write_text(
        textwrap.dedent("""\
        name: acme
        git:
          identity:
            name: Alex
            email: alex@acme.com
        env:
          FOO: bar
    """)
    )
    env = build_company_env("acme")
    assert env["GIT_AUTHOR_NAME"] == "Alex"
    assert env["GIT_AUTHOR_EMAIL"] == "alex@acme.com"
    assert env["FOO"] == "bar"


def test_build_env_cloud(tmp_path, monkeypatch):
    monkeypatch.setenv("HAT_CONFIG_DIR", str(tmp_path))
    company_dir = tmp_path / "companies" / "acme"
    company_dir.mkdir(parents=True)
    (company_dir / "config.yaml").write_text(
        textwrap.dedent("""\
        name: acme
        cloud:
          nomad:
            addr: https://nomad.acme.com
          vault:
            addr: https://vault.acme.com
    """)
    )
    env = build_company_env("acme")
    assert env["NOMAD_ADDR"] == "https://nomad.acme.com"
    assert env["VAULT_ADDR"] == "https://vault.acme.com"


def test_build_env_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("HAT_CONFIG_DIR", str(tmp_path))
    company_dir = tmp_path / "companies" / "acme"
    company_dir.mkdir(parents=True)
    (company_dir / "config.yaml").write_text("name: acme\n")
    env = build_company_env("acme")
    assert env == {}
