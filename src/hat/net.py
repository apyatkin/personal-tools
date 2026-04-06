from __future__ import annotations

import socket
import ssl
import subprocess
from datetime import datetime


def domain_info(domain: str) -> dict:
    """Get WHOIS + RDAP info for a domain."""
    info = {"domain": domain}

    # WHOIS
    result = subprocess.run(["whois", domain], capture_output=True, text=True)
    info["whois_raw"] = result.stdout

    for line in result.stdout.splitlines():
        line = line.strip()
        lower = line.lower()
        if "registrar:" in lower:
            info["registrar"] = line.split(":", 1)[1].strip()
        elif "creation date:" in lower or "created:" in lower:
            info.setdefault("created", line.split(":", 1)[1].strip())
        elif "expir" in lower and "date" in lower:
            info.setdefault("expires", line.split(":", 1)[1].strip())
        elif "name server:" in lower or "nserver:" in lower:
            info.setdefault("nameservers", []).append(line.split(":", 1)[1].strip())

    # RDAP fallback for missing fields
    try:
        import httpx

        resp = httpx.get(
            f"https://rdap.org/domain/{domain}", timeout=10, follow_redirects=True
        )
        if resp.status_code == 200:
            rdap = resp.json()
            for event in rdap.get("events", []):
                action = event.get("eventAction", "")
                date = event.get("eventDate", "")
                if action == "expiration" and "expires" not in info:
                    info["expires"] = date[:10]
                elif action == "registration" and "created" not in info:
                    info["created"] = date[:10]
                elif action == "last changed":
                    info["updated"] = date[:10]
            # Registrar from RDAP
            if "registrar" not in info:
                for entity in rdap.get("entities", []):
                    if "registrar" in entity.get("roles", []):
                        vcard = entity.get("vcardArray", [None, []])[1]
                        for field in vcard:
                            if field[0] == "fn":
                                info["registrar"] = field[3]
    except Exception:
        pass

    return info


def cert_info(host: str, port: int = 443) -> dict:
    """Get SSL certificate info."""
    chain_error = None

    ctx = ssl.create_default_context()
    try:
        with ctx.wrap_socket(socket.socket(), server_hostname=host) as s:
            s.settimeout(10)
            s.connect((host, port))
            cert = s.getpeercert()
            der = s.getpeercert(binary_form=True)
    except ssl.SSLCertVerificationError as e:
        chain_error = str(e)
        # Retry without verification — getpeercert() returns {} with CERT_NONE
        # so use openssl to parse the cert instead
        ctx2 = ssl.create_default_context()
        ctx2.check_hostname = False
        ctx2.verify_mode = ssl.CERT_NONE
        with ctx2.wrap_socket(socket.socket(), server_hostname=host) as s:
            s.settimeout(10)
            s.connect((host, port))
            der = s.getpeercert(binary_form=True)
        # Parse DER cert via openssl
        if der:
            return _parse_der_cert(der, chain_error)
        return {"chain_error": chain_error}
    except Exception as e:
        return {"error": str(e)}

    return _parse_cert(cert, der)


def _parse_der_cert(der: bytes, chain_error: str | None = None) -> dict:
    """Parse a DER certificate using openssl (for when getpeercert() returns {})."""
    pem = ssl.DER_cert_to_PEM_cert(der)
    result = subprocess.run(
        ["openssl", "x509", "-text", "-noout"],
        input=pem,
        capture_output=True,
        text=True,
    )
    info = {}
    if chain_error:
        info["chain_error"] = chain_error

    for line in result.stdout.splitlines():
        line = line.strip()
        if line.startswith("Subject:"):
            info["subject"] = (
                line.split("CN=")[-1].split(",")[0].strip()
                if "CN=" in line
                else line.split(":", 1)[1].strip()
            )
        elif line.startswith("Issuer:"):
            info["issuer"] = (
                line.split("CN=")[-1].split(",")[0].strip()
                if "CN=" in line
                else line.split(":", 1)[1].strip()
            )
            if "O=" in line:
                info["issuer_org"] = line.split("O=")[-1].split(",")[0].strip()
        elif line.startswith("Not Before:"):
            info["not_before"] = line.split(":", 1)[1].strip()
        elif line.startswith("Not After :"):
            not_after = line.split(":", 1)[1].strip()
            info["not_after"] = not_after
            try:
                expiry = datetime.strptime(not_after.strip(), "%b %d %H:%M:%S %Y %Z")
                info["days_until_expiry"] = (expiry - datetime.now()).days
                info["expired"] = info["days_until_expiry"] < 0
            except ValueError:
                pass

    info["self_signed"] = info.get("subject", "") == info.get("issuer", "")
    return info


def _parse_cert(cert: dict, der: bytes, chain_error: str | None = None) -> dict:
    info = {}
    if cert:
        # Subject
        subject = dict(x[0] for x in cert.get("subject", ()))
        info["subject"] = subject.get("commonName", "")
        info["organization"] = subject.get("organizationName", "")

        # Issuer
        issuer = dict(x[0] for x in cert.get("issuer", ()))
        info["issuer"] = issuer.get("commonName", "")
        info["issuer_org"] = issuer.get("organizationName", "")

        # Self-signed check
        info["self_signed"] = info["subject"] == info["issuer"]

        # Dates
        not_before = cert.get("notBefore", "")
        not_after = cert.get("notAfter", "")
        info["not_before"] = not_before
        info["not_after"] = not_after

        # Check expiry
        if not_after:
            try:
                expiry = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
                info["days_until_expiry"] = (expiry - datetime.now()).days
                info["expired"] = info["days_until_expiry"] < 0
            except ValueError:
                pass

        # SANs
        sans = cert.get("subjectAltName", ())
        info["san"] = [v for _, v in sans]

    if chain_error:
        info["chain_error"] = chain_error

    return info


def ip_info(address: str) -> dict:
    """Get IP address info using ipinfo.io."""
    import httpx

    try:
        resp = httpx.get(f"https://ipinfo.io/{address}/json", timeout=10)
        data = resp.json()
        return {
            "ip": data.get("ip", address),
            "country": data.get("country", ""),
            "region": data.get("region", ""),
            "city": data.get("city", ""),
            "isp": data.get("org", ""),
            "org": data.get("org", ""),
            "as": data.get("org", ""),
            "lookup_url": f"https://ipinfo.io/{address}",
        }
    except Exception as e:
        return {"ip": address, "error": str(e)}


def dns_lookup(domain: str) -> dict:
    """Simplified DNS lookup — A, AAAA, MX, NS, CNAME, TXT."""
    results = {"domain": domain}
    for rtype in ["A", "AAAA", "MX", "NS", "CNAME", "TXT"]:
        result = subprocess.run(
            ["dig", "+short", domain, rtype],
            capture_output=True,
            text=True,
        )
        records = [
            line.strip() for line in result.stdout.strip().splitlines() if line.strip()
        ]
        if records:
            results[rtype] = records
    return results


def net_check(host: str, ports: list[int] | None = None) -> dict:
    """Combined ping + traceroute + port check."""
    results = {"host": host}

    # Ping
    ping_result = subprocess.run(
        ["ping", "-c", "3", "-W", "2", host],
        capture_output=True,
        text=True,
    )
    results["ping"] = {
        "success": ping_result.returncode == 0,
        "output": ping_result.stdout.strip().splitlines()[-2:]
        if ping_result.stdout
        else [],
    }

    # Traceroute (quick, max 15 hops)
    trace_result = subprocess.run(
        ["traceroute", "-m", "15", "-w", "2", host],
        capture_output=True,
        text=True,
        timeout=30,
    )
    results["traceroute"] = trace_result.stdout.strip().splitlines()[:15]

    # Port check
    if ports:
        port_results = {}
        for port in ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)
                result = sock.connect_ex((host, port))
                port_results[port] = "open" if result == 0 else "closed"
                sock.close()
            except Exception:
                port_results[port] = "error"
        results["ports"] = port_results

    return results
