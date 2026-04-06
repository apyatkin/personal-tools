from hat.validate import validate_config


def test_valid_config():
    config = {"name": "acme", "env": {"FOO": "bar"}}
    errors = validate_config(config)
    assert len(errors) == 0


def test_missing_name():
    errors = validate_config({"env": {}})
    assert any(e.path == "name" and e.level == "error" for e in errors)


def test_unknown_key():
    errors = validate_config({"name": "acme", "bogus": True})
    assert any(e.path == "bogus" and e.level == "warn" for e in errors)


def test_invalid_ref():
    config = {"name": "acme", "cloud": {"nomad": {"token_ref": "plaintext"}}}
    errors = validate_config(config)
    assert any("Invalid ref" in e.message for e in errors)


def test_valid_ref():
    config = {"name": "acme", "cloud": {"nomad": {"token_ref": "keychain:token"}}}
    errors = validate_config(config)
    assert len(errors) == 0
