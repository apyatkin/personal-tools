import pytest

from ctx.secrets import SecretResolver, parse_secret_ref


def test_parse_keychain_ref():
    backend, path = parse_secret_ref("keychain:acme-gitlab-token")
    assert backend == "keychain"
    assert path == "acme-gitlab-token"


def test_parse_bitwarden_ref():
    backend, path = parse_secret_ref("bitwarden:acme-vault/password")
    assert backend == "bitwarden"
    assert path == "acme-vault/password"


def test_parse_invalid_ref():
    with pytest.raises(ValueError, match="Invalid secret ref"):
        parse_secret_ref("plaintext-value")


def test_resolve_refs_in_config():
    resolver = SecretResolver()
    resolver._cache = {
        "keychain:acme-token": "secret123",
        "bitwarden:acme-vault/password": "vaultpass",
    }
    config = {
        "cloud": {
            "nomad": {
                "addr": "https://nomad.acme.com",
                "token_ref": "keychain:acme-token",
            },
            "vault": {
                "token_ref": "bitwarden:acme-vault/password",
            },
        },
        "env": {"FOO": "bar"},
    }
    secrets = resolver.resolve_refs(config)
    assert secrets["keychain:acme-token"] == "secret123"
    assert secrets["bitwarden:acme-vault/password"] == "vaultpass"


def test_find_all_refs():
    config = {
        "docker": {
            "registries": [
                {
                    "host": "reg.acme.com",
                    "username_ref": "keychain:reg-user",
                    "password_ref": "keychain:reg-pass",
                }
            ]
        },
        "cloud": {"hetzner": {"token_ref": "bitwarden:hcloud"}},
    }
    resolver = SecretResolver()
    refs = resolver._find_refs(config)
    assert set(refs) == {"keychain:reg-user", "keychain:reg-pass", "bitwarden:hcloud"}
