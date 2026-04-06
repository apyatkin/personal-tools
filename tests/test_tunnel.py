from unittest.mock import patch, MagicMock
from hat.tunnel import start_tunnels, stop_tunnels


def test_start_tunnels(tmp_path, monkeypatch):
    monkeypatch.setenv("HAT_CONFIG_DIR", str(tmp_path))
    company_dir = tmp_path / "companies" / "acme"
    company_dir.mkdir(parents=True)
    (company_dir / "config.yaml").write_text("""\
name: acme
ssh:
  jump_host: bastion.acme.com
  tunnels:
    - local_port: 8200
      remote_host: vault.internal
      remote_port: 8200
  socks_proxy:
    port: 1080
""")
    with patch("hat.tunnel.subprocess.Popen") as mock_popen:
        mock_popen.return_value = MagicMock(pid=12345)
        results = start_tunnels("acme")
    assert len(results) == 2
    assert results[0]["type"] == "forward"
    assert results[1]["type"] == "socks"


def test_stop_tunnels():
    mock_ps = MagicMock()
    mock_ps.stdout = "ssh\n"
    with (
        patch("hat.tunnel.os.kill"),
        patch("hat.tunnel.subprocess.run", return_value=mock_ps),
    ):
        results = stop_tunnels([123, 456])
    assert len(results) == 2
    assert all(r["status"] == "stopped" for r in results)


def test_start_no_jump_host(tmp_path, monkeypatch):
    monkeypatch.setenv("HAT_CONFIG_DIR", str(tmp_path))
    company_dir = tmp_path / "companies" / "acme"
    company_dir.mkdir(parents=True)
    (company_dir / "config.yaml").write_text("name: acme\n")
    results = start_tunnels("acme")
    assert results == []
