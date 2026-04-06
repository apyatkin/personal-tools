from ctx.shell import generate_shell_init


def test_generate_zsh_init():
    output = generate_shell_init("zsh")
    assert "precmd" in output
    assert "state.env" in output
    assert "CTX_ACTIVE" in output


def test_generate_unknown_shell():
    import pytest
    with pytest.raises(ValueError, match="Unsupported shell"):
        generate_shell_init("fish")
