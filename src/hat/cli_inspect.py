"""Remote host inspection commands — CPU, memory, disk, network, logs."""

from __future__ import annotations

import json as _json
import shlex
import subprocess
import sys
from dataclasses import dataclass
from typing import Any

import click

from hat.config import load_company_config


# ─── SSH target resolution ─────────────────────────────────────────────────


@dataclass
class SSHTarget:
    host: str
    user: str | None = None
    port: int | None = None
    key: str | None = None
    jump: str | None = None

    def ssh_cmd(self) -> list[str]:
        cmd = [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=accept-new",
            "-o",
            "ConnectTimeout=10",
        ]
        if self.jump:
            cmd.extend(["-J", self.jump])
        if self.key:
            cmd.extend(["-i", self.key, "-o", "IdentitiesOnly=yes"])
        if self.port:
            cmd.extend(["-p", str(self.port)])
        target = f"{self.user}@{self.host}" if self.user else self.host
        cmd.append(target)
        return cmd


def _resolve_target(
    remote: str,
    user_override: str | None,
    port_override: int | None,
    key_override: str | None,
) -> SSHTarget:
    """Resolve a remote spec.

    `remote` can be:
      - a raw IP/hostname (uses defaults)
      - a host alias from any company's ssh.hosts
      - 'company:host' for explicit lookup
    """
    from hat.config import list_companies

    # Explicit company:host form
    company = None
    host_name = remote
    if ":" in remote and "/" not in remote:
        company, host_name = remote.split(":", 1)

    candidates = [company] if company else list_companies()

    target: SSHTarget | None = None
    for cname in candidates:
        try:
            cfg = load_company_config(cname)
        except Exception:
            continue
        ssh_cfg = cfg.get("ssh", {}) or {}
        hosts = ssh_cfg.get("hosts", {}) or {}
        if host_name not in hosts:
            continue
        entry = hosts[host_name]
        target = SSHTarget(
            host=entry["address"],
            user=entry.get("user") or ssh_cfg.get("default_user"),
            port=entry.get("port"),
        )
        # Resolve key from keychain ref if any
        key_ref = entry.get("key_ref") or ssh_cfg.get("default_key_ref")
        if key_ref:
            target.key = _materialize_key(key_ref)
        # Jump host
        if ssh_cfg.get("jump_host"):
            jh = ssh_cfg["jump_host"]
            ju = ssh_cfg.get("jump_user")
            target.jump = f"{ju}@{jh}" if ju else jh
        break

    if target is None:
        # Treat as raw IP/hostname
        target = SSHTarget(host=remote)

    # Apply overrides
    if user_override:
        target.user = user_override
    if port_override:
        target.port = port_override
    if key_override:
        # User-supplied path takes precedence; no temp file
        target.key = key_override

    return target


_KEY_TEMP_PATHS: list[str] = []


def _materialize_key(key_ref: str) -> str | None:
    """Resolve a hat secret ref (e.g. 'keychain:foo') to a temp file path."""
    import os
    import tempfile
    import atexit

    from hat.secrets import SecretResolver

    try:
        data = SecretResolver()._resolve_one(key_ref)
    except Exception:
        return None

    fd, path = tempfile.mkstemp(prefix="hat-inspect-", suffix=".key")
    payload = data if data.endswith("\n") else data + "\n"
    os.write(fd, payload.encode())
    os.close(fd)
    os.chmod(path, 0o600)
    _KEY_TEMP_PATHS.append(path)
    if len(_KEY_TEMP_PATHS) == 1:
        atexit.register(_cleanup_keys)
    return path


def _cleanup_keys():
    import os

    for p in _KEY_TEMP_PATHS:
        try:
            os.unlink(p)
        except OSError:
            pass


# ─── Remote command execution ──────────────────────────────────────────────


def _run_remote(target: SSHTarget, remote_cmd: str) -> str:
    """Run a shell command on the remote host, return stdout."""
    cmd = target.ssh_cmd() + [remote_cmd]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30, check=False
        )
    except subprocess.TimeoutExpired:
        click.echo(f"Error: SSH timeout connecting to {target.host}", err=True)
        sys.exit(1)
    except FileNotFoundError:
        click.echo("Error: ssh binary not found", err=True)
        sys.exit(1)

    if result.returncode != 0:
        click.echo(f"Error: remote command failed (exit {result.returncode})", err=True)
        if result.stderr:
            click.echo(result.stderr.strip(), err=True)
        sys.exit(result.returncode)
    return result.stdout


# ─── Output rendering ──────────────────────────────────────────────────────


def _render_table(
    title: str,
    columns: list[str],
    rows: list[list[Any]],
    json_mode: bool = False,
):
    if json_mode:
        out = {
            "title": title,
            "columns": columns,
            "rows": [{col: row[i] for i, col in enumerate(columns)} for row in rows],
        }
        click.echo(_json.dumps(out, indent=2, default=str))
        return

    from rich.console import Console
    from rich.table import Table

    table = Table(title=title, header_style="bold cyan", title_style="bold")
    for col in columns:
        table.add_column(col, overflow="fold")
    for row in rows:
        table.add_row(*[str(c) for c in row])
    Console().print(table)


def _render_kv(title: str, pairs: list[tuple[str, Any]], json_mode: bool = False):
    if json_mode:
        click.echo(
            _json.dumps({"title": title, "data": dict(pairs)}, indent=2, default=str)
        )
        return

    from rich.console import Console
    from rich.table import Table

    table = Table(title=title, header_style="bold cyan", title_style="bold")
    table.add_column("Metric", style="dim")
    table.add_column("Value")
    for k, v in pairs:
        table.add_row(str(k), str(v))
    Console().print(table)


# ─── Common option set ─────────────────────────────────────────────────────


def _remote_options(f):
    f = click.option(
        "-r",
        "--remote",
        required=True,
        help="Remote host (IP, hostname, or alias from any company's ssh.hosts; use 'company:host' for explicit lookup)",
    )(f)
    f = click.option("-u", "--user", default=None, help="SSH user override")(f)
    f = click.option("-p", "--port", type=int, default=None, help="SSH port override")(
        f
    )
    f = click.option(
        "-i",
        "--private-key",
        "private_key",
        type=click.Path(exists=True, dir_okay=False),
        default=None,
        help="Path to SSH private key",
    )(f)
    f = click.option("--json", "json_out", is_flag=True, help="Output as JSON")(f)
    return f


# ─── Inspect group ─────────────────────────────────────────────────────────


@click.group("inspect")
def inspect_group():
    """Remote host performance inspection — cpu, mem, disk, net, logs.

    \b
    Examples:
      hat inspect cpu -r bastion
      hat inspect mem -r 10.0.1.5 -i ~/.ssh/id_ed25519
      hat inspect sys -r 3205:web1
      hat inspect logs -r bastion -n 50
    """


# ─── cpu ───────────────────────────────────────────────────────────────────


@inspect_group.command("cpu")
@_remote_options
def cpu_cmd(remote, user, port, private_key, json_out):
    """Top 10 processes by CPU usage."""
    target = _resolve_target(remote, user, port, private_key)
    cmd = (
        "ps -eo pid,user,pcpu,pmem,rss,comm --sort=-pcpu --no-headers 2>/dev/null "
        "| head -10"
    )
    out = _run_remote(target, cmd)
    rows = []
    for line in out.strip().splitlines():
        parts = line.split(None, 5)
        if len(parts) < 6:
            continue
        pid, user_, pcpu, pmem, rss, comm = parts
        rows.append([pid, user_, f"{pcpu}%", f"{pmem}%", _human_kib(rss), comm])
    _render_table(
        f"Top 10 processes by CPU on {target.host}",
        ["PID", "USER", "CPU", "MEM", "RSS", "COMMAND"],
        rows,
        json_out,
    )


# ─── mem ───────────────────────────────────────────────────────────────────


@inspect_group.command("mem")
@_remote_options
def mem_cmd(remote, user, port, private_key, json_out):
    """Top 10 processes by memory + memory totals."""
    target = _resolve_target(remote, user, port, private_key)

    # Top 10 processes by RSS
    proc_out = _run_remote(
        target,
        "ps -eo pid,user,pcpu,pmem,rss,comm --sort=-rss --no-headers 2>/dev/null | head -10",
    )
    rows = []
    for line in proc_out.strip().splitlines():
        parts = line.split(None, 5)
        if len(parts) < 6:
            continue
        pid, user_, pcpu, pmem, rss, comm = parts
        rows.append([pid, user_, f"{pcpu}%", f"{pmem}%", _human_kib(rss), comm])

    # Memory totals
    mem_info = _parse_meminfo(_run_remote(target, "cat /proc/meminfo 2>/dev/null"))

    if json_out:
        click.echo(
            _json.dumps(
                {
                    "host": target.host,
                    "memory": mem_info,
                    "top_processes": [
                        dict(zip(["PID", "USER", "CPU", "MEM", "RSS", "COMMAND"], r))
                        for r in rows
                    ],
                },
                indent=2,
            )
        )
        return

    _render_kv(
        f"Memory on {target.host}",
        [
            ("Total", mem_info.get("MemTotal", "?")),
            ("Used", mem_info.get("MemUsed", "?")),
            ("Free", mem_info.get("MemFree", "?")),
            ("Available", mem_info.get("MemAvailable", "?")),
            ("Buffers", mem_info.get("Buffers", "?")),
            ("Cached", mem_info.get("Cached", "?")),
            ("Swap Total", mem_info.get("SwapTotal", "?")),
            ("Swap Used", mem_info.get("SwapUsed", "?")),
        ],
    )
    _render_table(
        "Top 10 processes by memory",
        ["PID", "USER", "CPU", "MEM", "RSS", "COMMAND"],
        rows,
    )


# ─── disk ──────────────────────────────────────────────────────────────────


@inspect_group.command("disk")
@_remote_options
def disk_cmd(remote, user, port, private_key, json_out):
    """Disk usage per filesystem."""
    target = _resolve_target(remote, user, port, private_key)
    out = _run_remote(
        target,
        "df -PT -x tmpfs -x devtmpfs -x squashfs -x overlay 2>/dev/null | tail -n +2",
    )
    rows = []
    for line in out.strip().splitlines():
        parts = line.split()
        if len(parts) < 7:
            continue
        fs, fstype, size, used, avail, pct, mount = parts[:7]
        rows.append(
            [
                fs,
                fstype,
                _human_kib(size),
                _human_kib(used),
                _human_kib(avail),
                pct,
                mount,
            ]
        )
    _render_table(
        f"Disk usage on {target.host}",
        ["Filesystem", "Type", "Size", "Used", "Avail", "Use%", "Mount"],
        rows,
        json_out,
    )


# ─── io ────────────────────────────────────────────────────────────────────


@inspect_group.command("io")
@_remote_options
def io_cmd(remote, user, port, private_key, json_out):
    """Disk I/O activity (1-second sample of /proc/diskstats)."""
    target = _resolve_target(remote, user, port, private_key)
    # Two snapshots joined with a literal '|' so we can split reliably
    cmd = (
        "awk '{print}' /proc/diskstats; echo '---SPLIT---'; "
        "sleep 1; awk '{print}' /proc/diskstats"
    )
    out = _run_remote(target, cmd)
    if "---SPLIT---" not in out:
        click.echo("Error: could not collect diskstats", err=True)
        sys.exit(1)
    snap1, snap2 = out.split("---SPLIT---", 1)

    def parse(text: str) -> dict[str, tuple[int, int]]:
        result: dict[str, tuple[int, int]] = {}
        for line in text.strip().splitlines():
            cols = line.split()
            if len(cols) < 14:
                continue
            dev = cols[2]
            try:
                # Field offsets per Documentation/admin-guide/iostats.rst:
                #   cols[3..]  → reads_completed, reads_merged, sectors_read, ...
                #   cols[5]   = sectors read; cols[9] = sectors written
                sectors_read = int(cols[5])
                sectors_written = int(cols[9])
            except (ValueError, IndexError):
                continue
            result[dev] = (sectors_read, sectors_written)
        return result

    s1 = parse(snap1)
    s2 = parse(snap2)
    rows = []
    for dev in sorted(s2.keys()):
        if dev.startswith(("loop", "ram", "dm-")):
            continue
        if dev not in s1:
            continue
        # 512-byte sectors → KB/s
        rkb = (s2[dev][0] - s1[dev][0]) // 2
        wkb = (s2[dev][1] - s1[dev][1]) // 2
        if rkb == 0 and wkb == 0:
            continue
        rows.append([dev, f"{rkb} KB/s", f"{wkb} KB/s"])

    if not rows:
        rows = [["(idle)", "0 KB/s", "0 KB/s"]]
    _render_table(
        f"Disk I/O on {target.host} (1s sample)",
        ["Device", "Read", "Write"],
        rows,
        json_out,
    )


# ─── net ───────────────────────────────────────────────────────────────────


@inspect_group.command("net")
@_remote_options
def net_cmd(remote, user, port, private_key, json_out):
    """Network interfaces, connections, throughput (1s sample)."""
    target = _resolve_target(remote, user, port, private_key)

    # Interface throughput from /proc/net/dev
    cmd = "cat /proc/net/dev; echo '---SPLIT---'; sleep 1; cat /proc/net/dev"
    out = _run_remote(target, cmd)
    if "---SPLIT---" not in out:
        click.echo("Error: could not collect /proc/net/dev", err=True)
        sys.exit(1)
    snap1, snap2 = out.split("---SPLIT---", 1)

    def parse_netdev(text: str) -> dict[str, tuple[int, int]]:
        result: dict[str, tuple[int, int]] = {}
        for line in text.strip().splitlines():
            if ":" not in line:
                continue
            iface, _, stats = line.partition(":")
            iface = iface.strip()
            cols = stats.split()
            if len(cols) < 16:
                continue
            try:
                rx_bytes = int(cols[0])
                tx_bytes = int(cols[8])
            except ValueError:
                continue
            result[iface] = (rx_bytes, tx_bytes)
        return result

    s1 = parse_netdev(snap1)
    s2 = parse_netdev(snap2)
    rows = []
    for iface in sorted(s2.keys()):
        if iface == "lo":
            continue
        if iface not in s1:
            continue
        rx_diff = s2[iface][0] - s1[iface][0]
        tx_diff = s2[iface][1] - s1[iface][1]
        if rx_diff == 0 and tx_diff == 0:
            continue
        rows.append([iface, _human_bytes(rx_diff), _human_bytes(tx_diff)])

    # Established connection count
    conn_out = _run_remote(
        target, "ss -tan 2>/dev/null | awk 'NR>1 {print $1}' | sort | uniq -c"
    )
    conn_pairs = []
    for line in conn_out.strip().splitlines():
        parts = line.split()
        if len(parts) == 2:
            conn_pairs.append((parts[1], int(parts[0])))

    if json_out:
        click.echo(
            _json.dumps(
                {
                    "host": target.host,
                    "interfaces": [
                        {"iface": r[0], "rx_per_sec": r[1], "tx_per_sec": r[2]}
                        for r in rows
                    ],
                    "connections": dict(conn_pairs),
                },
                indent=2,
            )
        )
        return

    _render_table(
        f"Network throughput on {target.host} (1s sample)",
        ["Interface", "RX/s", "TX/s"],
        rows or [["(none)", "-", "-"]],
    )
    if conn_pairs:
        _render_table(
            "TCP connections by state",
            ["State", "Count"],
            [[s, c] for s, c in conn_pairs],
        )


# ─── load ──────────────────────────────────────────────────────────────────


@inspect_group.command("load")
@_remote_options
def load_cmd(remote, user, port, private_key, json_out):
    """Load average, uptime, CPU count."""
    target = _resolve_target(remote, user, port, private_key)
    out = _run_remote(
        target,
        "uptime; nproc 2>/dev/null; cat /proc/loadavg 2>/dev/null",
    )
    lines = out.strip().splitlines()
    pairs = []
    if lines:
        pairs.append(("uptime", lines[0].strip()))
    if len(lines) >= 2:
        pairs.append(("CPU cores", lines[1].strip()))
    if len(lines) >= 3:
        la = lines[2].split()
        if len(la) >= 5:
            pairs.append(("load 1m", la[0]))
            pairs.append(("load 5m", la[1]))
            pairs.append(("load 15m", la[2]))
            pairs.append(("running/total tasks", la[3]))
            pairs.append(("last PID", la[4]))
    _render_kv(f"Load on {target.host}", pairs, json_out)


# ─── sys ───────────────────────────────────────────────────────────────────


@inspect_group.command("sys")
@_remote_options
def sys_cmd(remote, user, port, private_key, json_out):
    """Full system overview — load, mem, disk, network, top processes."""
    target = _resolve_target(remote, user, port, private_key)

    # Single round-trip for everything
    script = """
echo '===HOSTNAME==='; hostname
echo '===UPTIME==='; uptime
echo '===KERNEL==='; uname -sr
echo '===OS==='; (cat /etc/os-release 2>/dev/null | grep PRETTY_NAME | cut -d= -f2 | tr -d '"') || echo unknown
echo '===CPU==='; nproc 2>/dev/null
echo '===LOADAVG==='; cat /proc/loadavg 2>/dev/null
echo '===MEMINFO==='; cat /proc/meminfo 2>/dev/null
echo '===DISK==='; df -PT -x tmpfs -x devtmpfs -x squashfs -x overlay 2>/dev/null | tail -n +2
echo '===TOPCPU==='; ps -eo pid,user,pcpu,pmem,comm --sort=-pcpu --no-headers 2>/dev/null | head -5
echo '===TOPMEM==='; ps -eo pid,user,pcpu,pmem,rss,comm --sort=-rss --no-headers 2>/dev/null | head -5
"""
    out = _run_remote(target, script)
    sections = _parse_sections(out)

    mem_info = _parse_meminfo(sections.get("MEMINFO", ""))

    if json_out:
        click.echo(
            _json.dumps(
                {
                    "host": target.host,
                    "hostname": sections.get("HOSTNAME", "").strip(),
                    "os": sections.get("OS", "").strip(),
                    "kernel": sections.get("KERNEL", "").strip(),
                    "uptime": sections.get("UPTIME", "").strip(),
                    "cpu_cores": sections.get("CPU", "").strip(),
                    "loadavg": sections.get("LOADAVG", "").strip(),
                    "memory": mem_info,
                    "disk": sections.get("DISK", "").strip(),
                    "top_cpu": sections.get("TOPCPU", "").strip(),
                    "top_mem": sections.get("TOPMEM", "").strip(),
                },
                indent=2,
            )
        )
        return

    _render_kv(
        f"System overview — {target.host}",
        [
            ("hostname", sections.get("HOSTNAME", "?").strip()),
            ("OS", sections.get("OS", "?").strip()),
            ("kernel", sections.get("KERNEL", "?").strip()),
            ("uptime", sections.get("UPTIME", "?").strip()),
            ("CPU cores", sections.get("CPU", "?").strip()),
            ("load avg", sections.get("LOADAVG", "?").strip()),
            ("memory total", mem_info.get("MemTotal", "?")),
            ("memory used", mem_info.get("MemUsed", "?")),
            ("memory available", mem_info.get("MemAvailable", "?")),
        ],
    )

    # Disk
    disk_rows = []
    for line in sections.get("DISK", "").strip().splitlines():
        parts = line.split()
        if len(parts) >= 7:
            fs, fstype, size, used, avail, pct, mount = parts[:7]
            disk_rows.append(
                [fs, fstype, _human_kib(size), _human_kib(used), pct, mount]
            )
    if disk_rows:
        _render_table(
            "Disk usage",
            ["Filesystem", "Type", "Size", "Used", "Use%", "Mount"],
            disk_rows,
        )

    # Top CPU
    top_cpu_rows = []
    for line in sections.get("TOPCPU", "").strip().splitlines():
        parts = line.split(None, 4)
        if len(parts) == 5:
            top_cpu_rows.append(
                [parts[0], parts[1], f"{parts[2]}%", f"{parts[3]}%", parts[4]]
            )
    if top_cpu_rows:
        _render_table(
            "Top 5 by CPU",
            ["PID", "USER", "CPU", "MEM", "COMMAND"],
            top_cpu_rows,
        )

    # Top mem
    top_mem_rows = []
    for line in sections.get("TOPMEM", "").strip().splitlines():
        parts = line.split(None, 5)
        if len(parts) == 6:
            top_mem_rows.append(
                [
                    parts[0],
                    parts[1],
                    f"{parts[2]}%",
                    f"{parts[3]}%",
                    _human_kib(parts[4]),
                    parts[5],
                ]
            )
    if top_mem_rows:
        _render_table(
            "Top 5 by memory",
            ["PID", "USER", "CPU", "MEM", "RSS", "COMMAND"],
            top_mem_rows,
        )


# ─── logs ──────────────────────────────────────────────────────────────────


@inspect_group.command("logs")
@_remote_options
@click.option("-n", "--lines", default=50, help="Number of log lines (default: 50)")
@click.option(
    "-s",
    "--service",
    default=None,
    help="Filter by systemd unit (e.g. 'sshd', 'nginx')",
)
@click.option(
    "--since", default=None, help="systemd time spec, e.g. '1 hour ago', 'today'"
)
@click.option(
    "-l",
    "--level",
    type=click.Choice(["emerg", "alert", "crit", "err", "warning", "notice", "info"]),
    default=None,
    help="Min priority",
)
def logs_cmd(remote, user, port, private_key, json_out, lines, service, since, level):
    """Recent system logs (journalctl, fallback to /var/log/syslog)."""
    target = _resolve_target(remote, user, port, private_key)

    parts = ["journalctl", "--no-pager", "-o", "short-iso", "-n", str(lines)]
    if service:
        parts.extend(["-u", shlex.quote(service)])
    if since:
        parts.extend(["--since", shlex.quote(since)])
    if level:
        parts.extend(["-p", level])
    journal_cmd = " ".join(parts)
    fallback = f"tail -n {lines} /var/log/syslog 2>/dev/null || tail -n {lines} /var/log/messages 2>/dev/null"
    cmd = f"{journal_cmd} 2>/dev/null || {fallback}"

    out = _run_remote(target, cmd)
    log_lines = out.strip().splitlines()

    rows = []
    for line in log_lines:
        # journalctl short-iso format: "2026-04-09T10:30:45+0000 host unit: msg"
        parts = line.split(None, 3)
        if len(parts) == 4 and "T" in parts[0]:
            rows.append([parts[0], parts[1], parts[2].rstrip(":"), parts[3]])
        else:
            rows.append(["", "", "", line])

    title = f"Logs on {target.host}"
    if service:
        title += f" — unit: {service}"
    if level:
        title += f" — level: {level}"
    _render_table(title, ["Timestamp", "Host", "Unit", "Message"], rows, json_out)


# ─── helpers ───────────────────────────────────────────────────────────────


def _parse_sections(text: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current = None
    buf: list[str] = []
    for line in text.splitlines():
        if line.startswith("===") and line.endswith("==="):
            if current is not None:
                sections[current] = "\n".join(buf)
            current = line.strip("=")
            buf = []
        else:
            buf.append(line)
    if current is not None:
        sections[current] = "\n".join(buf)
    return sections


def _parse_meminfo(text: str) -> dict[str, str]:
    """Parse /proc/meminfo, return human-readable values."""
    raw: dict[str, int] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        v = v.strip().split()
        if v and v[0].isdigit():
            raw[k.strip()] = int(v[0])  # in kB

    out = {k: _human_kib(str(v)) for k, v in raw.items()}
    if "MemTotal" in raw and "MemAvailable" in raw:
        out["MemUsed"] = _human_kib(str(raw["MemTotal"] - raw["MemAvailable"]))
    if "SwapTotal" in raw and "SwapFree" in raw:
        out["SwapUsed"] = _human_kib(str(raw["SwapTotal"] - raw["SwapFree"]))
    return out


def _human_kib(value: str) -> str:
    """Convert a string of KiB to a human-readable size."""
    try:
        kb = float(value)
    except (ValueError, TypeError):
        return value
    return _human_bytes(kb * 1024)


def _human_bytes(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if abs(n) < 1024.0:
            return f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} EB"
