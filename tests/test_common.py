from ctx.common import generate_aliases, generate_completions


def test_generate_aliases(tmp_path):
    path = generate_aliases(tmp_path)
    assert path.exists()
    content = path.read_text()
    assert 'alias k="kubectl"' in content
    assert 'alias tf="tofu"' in content
    assert 'alias ap="ansible-playbook"' in content
    assert 'alias dc="docker compose"' in content
    assert 'alias g="git"' in content


def test_generate_completions(tmp_path):
    path = generate_completions(tmp_path)
    assert path.exists()
    content = path.read_text()
    assert "kubectl completion zsh" in content
    assert "compdef k=kubectl" in content
    assert "compdef tf=tofu" in content


def test_generate_aliases_idempotent(tmp_path):
    generate_aliases(tmp_path)
    generate_aliases(tmp_path)
    assert (tmp_path / "aliases.sh").exists()


def test_generate_completions_idempotent(tmp_path):
    generate_completions(tmp_path)
    generate_completions(tmp_path)
    assert (tmp_path / "completions.sh").exists()
