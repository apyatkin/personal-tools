"""Monitor domain expiry and SSL certificates."""

from __future__ import annotations

from dataclasses import dataclass
from hat.net import domain_info, cert_info


@dataclass
class MonitorAlert:
    company: str
    type: str  # "domain" or "cert"
    name: str
    days_left: int | None
    message: str


def check_all_domains(domains: dict[str, list[str]]) -> list[MonitorAlert]:
    """Check domain expiry. domains = {company: [domain1, domain2]}."""
    alerts = []
    for company, domain_list in domains.items():
        for domain in domain_list:
            try:
                info = domain_info(domain)
                expires = info.get("expires", "")
                if expires:
                    from datetime import datetime

                    try:
                        exp_date = datetime.strptime(expires[:10], "%Y-%m-%d")
                        days = (exp_date - datetime.now()).days
                        if days < 90:
                            alerts.append(
                                MonitorAlert(
                                    company=company,
                                    type="domain",
                                    name=domain,
                                    days_left=days,
                                    message=f"{domain} expires in {days} days ({expires[:10]})",
                                )
                            )
                    except ValueError:
                        pass
            except Exception:
                pass
    return alerts


def check_all_certs(hosts: dict[str, list[str]]) -> list[MonitorAlert]:
    """Check SSL cert expiry. hosts = {company: [host1, host2]}."""
    alerts = []
    for company, host_list in hosts.items():
        for host in host_list:
            try:
                info = cert_info(host)
                days = info.get("days_until_expiry")
                if days is not None and days < 90:
                    alerts.append(
                        MonitorAlert(
                            company=company,
                            type="cert",
                            name=host,
                            days_left=days,
                            message=f"{host} cert expires in {days} days",
                        )
                    )
                if info.get("self_signed"):
                    alerts.append(
                        MonitorAlert(
                            company=company,
                            type="cert",
                            name=host,
                            days_left=days,
                            message=f"{host} uses self-signed certificate",
                        )
                    )
            except Exception:
                pass
    return alerts
