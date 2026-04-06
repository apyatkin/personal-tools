from hat.common import (
    generate_aliases,
    generate_completions,
    generate_tools_config,
    load_common_tools,
)


def test_generate_aliases(tmp_path):
    path = generate_aliases(tmp_path)
    assert path.exists()
    content = path.read_text()
    assert 'alias k="kubectl"' in content
    assert 'alias tf="tofu"' in content
    assert 'alias ap="ansible-playbook"' in content
    assert 'alias dc="docker compose"' in content
    assert 'alias g="git"' in content
    assert 'alias kgpa="kubectl get pods -A"' in content
    assert 'alias ll="ls -la"' in content
    assert 'alias gcm="git commit -m"' in content
    assert "alias topcpu=" in content


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


def test_generate_tools_config(tmp_path):
    path = generate_tools_config(tmp_path)
    assert path.exists()
    content = path.read_text()
    assert "kubectl" in content
    assert "ansible" in content


def test_load_common_tools(tmp_path):
    generate_tools_config(tmp_path)
    tools = load_common_tools(tmp_path)
    assert "brew" in tools
    assert "kubectl" in tools["brew"]
    assert "pipx" in tools
    assert "ansible" in tools["pipx"]


def test_load_common_tools_missing(tmp_path):
    tools = load_common_tools(tmp_path)
    assert tools == {}
