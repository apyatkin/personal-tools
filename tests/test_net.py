from unittest.mock import patch, MagicMock
from hat.net import domain_info, dns_lookup, ip_info


def test_domain_info():
    whois_output = """\
Domain Name: EXAMPLE.COM
Registrar: Example Registrar
Creation Date: 2020-01-01
Expiry Date: 2025-01-01
Name Server: ns1.example.com
Name Server: ns2.example.com
"""
    with patch("hat.net.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=whois_output, returncode=0)
        info = domain_info("example.com")
    assert info["domain"] == "example.com"
    assert info["registrar"] == "Example Registrar"
    assert len(info.get("nameservers", [])) == 2


def test_dns_lookup():
    with patch("hat.net.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="93.184.216.34\n", returncode=0)
        info = dns_lookup("example.com")
    assert "A" in info or len(info) >= 1


def test_ip_info():
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "ip": "1.2.3.4",
        "country": "US",
        "region": "California",
        "city": "LA",
        "org": "AS14061 DigitalOcean",
    }
    with patch("httpx.get", return_value=mock_response):
        info = ip_info("1.2.3.4")
    assert info["country"] == "US"
    assert "ipinfo.io" in info["lookup_url"]
