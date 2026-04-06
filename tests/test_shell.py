from hat.shell import generate_shell_init


def test_generate_zsh_init():
    output = generate_shell_init("zsh")
    assert "precmd" in output
    assert "state.env" in output
    assert "HAT_ACTIVE" in output
    assert "active_file" in output


def test_generate_unknown_shell():
    import pytest

    with pytest.raises(ValueError, match="Unsupported shell"):
        generate_shell_init("fish")


def test_shell_init_sources_aliases():
    from hat.shell import generate_shell_init

    output = generate_shell_init("zsh")
    assert "aliases.sh" in output
    assert "completions.sh" in output
