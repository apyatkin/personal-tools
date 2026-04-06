import os
import textwrap

import pytest

from ctx.config import load_company_config, list_companies, get_config_dir


def test_get_config_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("CTX_CONFIG_DIR", str(tmp_path))
    assert get_config_dir() == tmp_path


def test_get_config_dir_default(monkeypatch):
    monkeypatch.delenv("CTX_CONFIG_DIR", raising=False)
    result = get_config_dir()
    assert str(result).endswith(".config/ctx")


def test_load_company_config(tmp_path, monkeypatch):
    monkeypatch.setenv("CTX_CONFIG_DIR", str(tmp_path))
    company_dir = tmp_path / "companies" / "acme"
    company_dir.mkdir(parents=True)
    config_file = company_dir / "config.yaml"
    config_file.write_text(textwrap.dedent("""\
        name: acme
        description: "Acme Corp"
        env:
          FOO: bar
    """))
    config = load_company_config("acme")
    assert config["name"] == "acme"
    assert config["env"]["FOO"] == "bar"


def test_load_company_config_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("CTX_CONFIG_DIR", str(tmp_path))
    with pytest.raises(FileNotFoundError):
        load_company_config("nonexistent")


def test_list_companies(tmp_path, monkeypatch):
    monkeypatch.setenv("CTX_CONFIG_DIR", str(tmp_path))
    companies_dir = tmp_path / "companies"
    companies_dir.mkdir()
    (companies_dir / "acme").mkdir()
    (companies_dir / "acme" / "config.yaml").write_text("name: acme\n")
    (companies_dir / "globex").mkdir()
    (companies_dir / "globex" / "config.yaml").write_text("name: globex\n")
    result = list_companies()
    assert set(result) == {"acme", "globex"}


def test_list_companies_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("CTX_CONFIG_DIR", str(tmp_path))
    result = list_companies()
    assert result == []
