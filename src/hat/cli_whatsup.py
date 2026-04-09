"""Cluster state overview commands — `hat whatsup k8s` / `hat whatsup nomad`.

These commands run locally against an already-configured cluster (kubectl
kubeconfig + context, or NOMAD_ADDR + NOMAD_TOKEN). They print a summary
of the cluster's current state with three verbosity levels:

  --overview (default) — one-screen summary
  --errors             — only problems
  --deep               — everything the overview has plus expanded details
"""

from __future__ import annotations

import json as _json
import os
import shlex
import subprocess
import sys
from typing import Any

import click


# ─── Common helpers ────────────────────────────────────────────────────────


def _load_active_company_env(*keys: str) -> dict[str, str]:
    """Return selected env vars from the currently-active hat company.

    Returns an empty dict if no company is active or the lookup fails.
    Used as a fallback so cluster commands work without a prior
    `hat on <company>` in the same shell.
    """
    try:
        from hat.state import StateManager
        from hat.env_builder import build_company_env
    except Exception:
        return {}
    try:
        sm = StateManager()
        if not sm.active_company:
            return {}
        full = build_company_env(sm.active_company)
    except Exception:
        return {}
    return {k: full[k] for k in keys if k in full}


def _run_local(
    cmd: list[str], env: dict | None = None, timeout: int = 120
) -> tuple[int, str, str]:
    """Run a local command. Returns (returncode, stdout, stderr)."""
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, env=env, check=False
        )
        return r.returncode, r.stdout, r.stderr
    except FileNotFoundError:
        return 127, "", f"{cmd[0]}: not found"
    except subprocess.TimeoutExpired:
        return 124, "", f"{cmd[0]}: timeout"


def _render_table(
    title: str, columns: list[str], rows: list[list[Any]], json_mode: bool = False
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


def _humanize_k8s_memory(value: str) -> str:
    """Convert a Kubernetes resource quantity like '131548412Ki' to '125.5 GB'."""
    if not value or value == "?":
        return value
    v = value.strip()
    # Binary suffixes (base 1024)
    binary = {"Ki": 1024, "Mi": 1024**2, "Gi": 1024**3, "Ti": 1024**4, "Pi": 1024**5}
    # Decimal suffixes (base 1000)
    decimal = {"K": 1000, "M": 1000**2, "G": 1000**3, "T": 1000**4, "P": 1000**5}

    try:
        for suffix, mult in binary.items():
            if v.endswith(suffix):
                n = float(v[: -len(suffix)]) * mult
                return _format_bytes(n)
        for suffix, mult in decimal.items():
            if v.endswith(suffix):
                n = float(v[: -len(suffix)]) * mult
                return _format_bytes(n)
        n = float(v)
        return _format_bytes(n)
    except ValueError:
        return value


def _format_bytes(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if abs(n) < 1024.0:
            return f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} EB"


def _status_style(status: str) -> str:
    s = status.lower()
    if s in ("running", "active", "ready", "ok", "healthy", "completed"):
        return "green"
    if s in (
        "pending",
        "creating",
        "containercreating",
        "init",
        "terminating",
        "draining",
    ):
        return "yellow"
    return "red"


def _colorize(value: str) -> str:
    return f"[{_status_style(value)}]{value}[/{_status_style(value)}]"


# ─── whatsup group ─────────────────────────────────────────────────────────


@click.group("whatsup")
def whatsup_group():
    """Cluster state overviews — k8s, nomad.

    \b
    Examples:
      hat whatsup k8s
      hat whatsup k8s --kubeconfig /path/to/cluster.yaml
      hat whatsup k8s --errors
      hat whatsup k8s --deep
      hat whatsup nomad
      hat whatsup nomad --errors
    """


# ─── output-level option set ───────────────────────────────────────────────


def _level_options(f):
    f = click.option(
        "--overview",
        "level",
        flag_value="overview",
        default=True,
        help="One-screen summary (default)",
    )(f)
    f = click.option(
        "--errors",
        "level",
        flag_value="errors",
        help="Only problems (failing pods, unhealthy nodes, warning events)",
    )(f)
    f = click.option(
        "--deep",
        "level",
        flag_value="deep",
        help="Expanded detail — top, events, deployments, all the things",
    )(f)
    f = click.option("--json", "json_out", is_flag=True, help="Output as JSON")(f)
    return f


# ═══════════════════════════════════════════════════════════════════════════
# K8S
# ═══════════════════════════════════════════════════════════════════════════


@whatsup_group.command("k8s")
@click.option(
    "--kubeconfig",
    default=None,
    help="Path to kubeconfig file. Default: $KUBECONFIG env var or ~/.kube/config.",
)
@click.option(
    "--context",
    "k8s_context",
    default=None,
    help="Kubeconfig context name OR path to a kubeconfig file (auto-detected).",
)
@click.option(
    "-n",
    "--namespace",
    default=None,
    help="Limit to a namespace (default: all namespaces)",
)
@_level_options
def k8s_cmd(kubeconfig, k8s_context, namespace, level, json_out):
    """Kubernetes cluster overview.

    \b
    Examples:
      hat whatsup k8s                                     # uses $KUBECONFIG or ~/.kube/config
      hat whatsup k8s --kubeconfig /path/to/cluster.yaml
      hat whatsup k8s --context prod                      # context name inside kubeconfig
      hat whatsup k8s --context /path/to/cluster.yaml     # or a file path — auto-detected
      hat whatsup k8s --errors                            # only problems
      hat whatsup k8s --deep -n kube-system
    """
    # If --context is actually a file path, treat it as --kubeconfig
    if k8s_context and os.path.isfile(k8s_context):
        if kubeconfig and kubeconfig != k8s_context:
            click.echo(
                "Error: --kubeconfig and --context both given as file paths",
                err=True,
            )
            sys.exit(2)
        kubeconfig = k8s_context
        k8s_context = None

    base = ["kubectl"]
    if kubeconfig:
        base.extend(["--kubeconfig", kubeconfig])
    if k8s_context:
        base.extend(["--context", k8s_context])

    ns_args = ["-n", namespace] if namespace else ["--all-namespaces"]

    def kc(args: list[str], accept_fail: bool = False) -> str:
        rc, out, err = _run_local(base + args)
        if rc != 0 and not accept_fail:
            click.echo(
                f"Error: kubectl {' '.join(args)} failed: {err.strip() or 'exit ' + str(rc)}",
                err=True,
            )
            if rc == 127:
                sys.exit(1)
        return out

    # Current context + server info
    ctx_out = kc(["config", "current-context"], accept_fail=True).strip()
    ver_out = kc(["version", "-o", "json"], accept_fail=True)
    server_version = ""
    try:
        ver = _json.loads(ver_out) if ver_out else {}
        server_version = ver.get("serverVersion", {}).get("gitVersion", "") or ver.get(
            "serverVersion", {}
        ).get("major", "") + "." + ver.get("serverVersion", {}).get("minor", "")
    except (ValueError, KeyError):
        server_version = "?"

    # Nodes
    nodes_json = kc(["get", "nodes", "-o", "json"], accept_fail=True)
    node_rows = []
    ready_count = 0
    total_nodes = 0
    try:
        nodes = _json.loads(nodes_json).get("items", []) if nodes_json else []
        total_nodes = len(nodes)
        for n in nodes:
            name = n["metadata"]["name"]
            conditions = {
                c["type"]: c["status"] for c in n["status"].get("conditions", [])
            }
            ready = "Ready" if conditions.get("Ready") == "True" else "NotReady"
            if ready == "Ready":
                ready_count += 1
            roles = [
                k.split("/", 1)[1]
                for k in n["metadata"].get("labels", {})
                if k.startswith("node-role.kubernetes.io/")
            ]
            role = ",".join(roles) or "worker"
            version = n["status"]["nodeInfo"]["kubeletVersion"]
            taints = len(n["spec"].get("taints", []) or [])
            # Allocatable
            alloc = n["status"].get("allocatable", {})
            cpu = alloc.get("cpu", "?")
            mem = _humanize_k8s_memory(alloc.get("memory", "?"))
            node_rows.append([name, ready, role, version, cpu, mem, str(taints)])
    except (ValueError, KeyError):
        pass

    # All pods (for problem + counts)
    pods_json = kc(["get", "pods", *ns_args, "-o", "json"], accept_fail=True)
    pods = []
    try:
        pods = _json.loads(pods_json).get("items", []) if pods_json else []
    except ValueError:
        pods = []

    status_counts: dict[str, int] = {}
    problem_rows = []
    for p in pods:
        phase = p["status"].get("phase", "Unknown")
        status_counts[phase] = status_counts.get(phase, 0) + 1

        name = p["metadata"]["name"]
        ns = p["metadata"]["namespace"]
        node = p["spec"].get("nodeName", "?")

        container_statuses = p["status"].get("containerStatuses", []) or []
        restarts = sum(c.get("restartCount", 0) for c in container_statuses)
        ready_containers = sum(1 for c in container_statuses if c.get("ready"))
        total_containers = len(container_statuses)

        # Detect problems
        is_problem = False
        problem_reason = ""
        if phase not in ("Running", "Succeeded"):
            is_problem = True
            problem_reason = phase
        for c in container_statuses:
            waiting = c.get("state", {}).get("waiting") or {}
            if waiting:
                reason = waiting.get("reason", "")
                if reason in (
                    "CrashLoopBackOff",
                    "ImagePullBackOff",
                    "ErrImagePull",
                    "CreateContainerError",
                    "RunContainerError",
                ):
                    is_problem = True
                    problem_reason = reason
            if c.get("restartCount", 0) >= 5:
                is_problem = True
                problem_reason = problem_reason or f"{c['restartCount']} restarts"

        if is_problem:
            ready_str = f"{ready_containers}/{total_containers}"
            problem_rows.append(
                [ns, name, ready_str, problem_reason, str(restarts), node]
            )

    # Events (warnings)
    events_out = kc(
        [
            "get",
            "events",
            *ns_args,
            "--sort-by=.lastTimestamp",
            "--field-selector=type=Warning",
            "-o",
            "json",
        ],
        accept_fail=True,
    )
    event_rows = []
    try:
        events = _json.loads(events_out).get("items", []) if events_out else []
        # Latest 20 warnings
        for ev in list(reversed(events))[:20]:
            ns = ev["metadata"].get("namespace", "")
            last = ev.get("lastTimestamp", ev.get("eventTime", ""))
            reason = ev.get("reason", "")
            obj = f"{ev.get('involvedObject', {}).get('kind', '')}/{ev.get('involvedObject', {}).get('name', '')}"
            msg = ev.get("message", "").replace("\n", " ")
            if len(msg) > 80:
                msg = msg[:77] + "..."
            event_rows.append([last, ns, reason, obj, msg])
    except ValueError:
        pass

    # Namespaces count
    ns_json = kc(["get", "namespaces", "-o", "json"], accept_fail=True)
    ns_count = 0
    try:
        ns_count = len(_json.loads(ns_json).get("items", [])) if ns_json else 0
    except ValueError:
        pass

    # Deployments not fully available
    dep_rows = []
    if level in ("overview", "deep", "errors"):
        dep_json = kc(["get", "deployments", *ns_args, "-o", "json"], accept_fail=True)
        try:
            deps = _json.loads(dep_json).get("items", []) if dep_json else []
            for d in deps:
                spec_replicas = d["spec"].get("replicas", 0) or 0
                status = d["status"]
                available = status.get("availableReplicas", 0) or 0
                ready = status.get("readyReplicas", 0) or 0
                if available < spec_replicas or ready < spec_replicas:
                    dep_rows.append(
                        [
                            d["metadata"]["namespace"],
                            d["metadata"]["name"],
                            f"{ready}/{spec_replicas}",
                            f"{available}",
                        ]
                    )
        except ValueError:
            pass

    # Optional: kubectl top nodes / pods (deep mode)
    top_node_rows = []
    top_pod_rows = []
    if level == "deep":
        rc, out, _ = _run_local(base + ["top", "nodes", "--no-headers"])
        if rc == 0:
            for line in out.strip().splitlines():
                parts = line.split()
                if len(parts) >= 5:
                    top_node_rows.append(parts[:5])
        rc, out, _ = _run_local(
            base + ["top", "pods", *ns_args, "--no-headers", "--sort-by=cpu"]
        )
        if rc == 0:
            for line in out.strip().splitlines()[:15]:
                parts = line.split()
                if len(parts) >= 4:
                    top_pod_rows.append(parts[: 4 if namespace else 5])

    # PVC state (overview/deep)
    pvc_rows = []
    if level in ("overview", "deep", "errors"):
        pvc_json = kc(["get", "pvc", *ns_args, "-o", "json"], accept_fail=True)
        try:
            pvcs = _json.loads(pvc_json).get("items", []) if pvc_json else []
            for pvc in pvcs:
                phase = pvc["status"].get("phase", "?")
                if phase != "Bound" or level == "deep":
                    pvc_rows.append(
                        [
                            pvc["metadata"]["namespace"],
                            pvc["metadata"]["name"],
                            phase,
                            pvc["spec"]
                            .get("resources", {})
                            .get("requests", {})
                            .get("storage", "?"),
                        ]
                    )
        except ValueError:
            pass

    # ─── Render ────────────────────────────────────────────────────────────

    if json_out:
        click.echo(
            _json.dumps(
                {
                    "context": ctx_out,
                    "server_version": server_version,
                    "nodes_total": total_nodes,
                    "nodes_ready": ready_count,
                    "nodes": [
                        dict(
                            zip(
                                [
                                    "name",
                                    "ready",
                                    "role",
                                    "version",
                                    "cpu",
                                    "mem",
                                    "taints",
                                ],
                                r,
                            )
                        )
                        for r in node_rows
                    ],
                    "namespaces": ns_count,
                    "pods_by_phase": status_counts,
                    "problem_pods": [
                        dict(
                            zip(
                                [
                                    "namespace",
                                    "name",
                                    "ready",
                                    "reason",
                                    "restarts",
                                    "node",
                                ],
                                r,
                            )
                        )
                        for r in problem_rows
                    ],
                    "warning_events": [
                        dict(
                            zip(["time", "namespace", "reason", "object", "message"], r)
                        )
                        for r in event_rows
                    ],
                    "degraded_deployments": [
                        dict(zip(["namespace", "name", "ready", "available"], r))
                        for r in dep_rows
                    ],
                    "unbound_pvcs": [
                        dict(zip(["namespace", "name", "phase", "size"], r))
                        for r in pvc_rows
                    ],
                },
                indent=2,
            )
        )
        return

    # ── errors mode: just the problems ──
    if level == "errors":
        any_problems = False
        if [n for n in node_rows if n[1] != "Ready"]:
            any_problems = True
            _render_table(
                "Non-Ready nodes",
                ["Name", "Status", "Role", "Version", "CPU", "Memory", "Taints"],
                [n for n in node_rows if n[1] != "Ready"],
            )
        if problem_rows:
            any_problems = True
            _render_table(
                f"Problem pods ({len(problem_rows)})",
                ["NS", "Name", "Ready", "Reason", "Restarts", "Node"],
                problem_rows,
            )
        if dep_rows:
            any_problems = True
            _render_table(
                f"Degraded deployments ({len(dep_rows)})",
                ["NS", "Name", "Ready", "Available"],
                dep_rows,
            )
        if pvc_rows:
            any_problems = True
            _render_table(
                f"Unbound PVCs ({len(pvc_rows)})",
                ["NS", "Name", "Phase", "Size"],
                pvc_rows,
            )
        if event_rows:
            any_problems = True
            _render_table(
                f"Recent warning events (last {len(event_rows)})",
                ["Time", "NS", "Reason", "Object", "Message"],
                event_rows,
            )
        if not any_problems:
            from rich.console import Console

            Console().print("[green bold]✓ No problems found[/green bold]")
        return

    # ── overview / deep ──
    _render_kv(
        f"Kubernetes — {ctx_out or '(no context)'}",
        [
            ("Context", ctx_out or "?"),
            ("Server version", server_version or "?"),
            ("Nodes", f"{ready_count}/{total_nodes} ready"),
            ("Namespaces", str(ns_count)),
            ("Pods running", str(status_counts.get("Running", 0))),
            ("Pods pending", str(status_counts.get("Pending", 0))),
            ("Pods failed", str(status_counts.get("Failed", 0))),
            ("Pods succeeded", str(status_counts.get("Succeeded", 0))),
        ],
    )

    if node_rows:
        _render_table(
            "Nodes",
            ["Name", "Status", "Role", "Version", "CPU", "Memory", "Taints"],
            node_rows,
        )

    if problem_rows:
        _render_table(
            f"Problem pods ({len(problem_rows)})",
            ["NS", "Name", "Ready", "Reason", "Restarts", "Node"],
            problem_rows,
        )
    else:
        from rich.console import Console

        Console().print("  [green]No problem pods[/green]")

    if dep_rows:
        _render_table(
            f"Degraded deployments ({len(dep_rows)})",
            ["NS", "Name", "Ready", "Available"],
            dep_rows,
        )

    if pvc_rows and level == "deep":
        _render_table(
            f"PVCs ({len(pvc_rows)})",
            ["NS", "Name", "Phase", "Size"],
            pvc_rows,
        )
    elif [p for p in pvc_rows if p[2] != "Bound"]:
        unbound = [p for p in pvc_rows if p[2] != "Bound"]
        _render_table(
            f"Unbound PVCs ({len(unbound)})",
            ["NS", "Name", "Phase", "Size"],
            unbound,
        )

    if level == "deep":
        if top_node_rows:
            _render_table(
                "Node resource usage (kubectl top)",
                ["Name", "CPU", "CPU%", "Memory", "Mem%"],
                top_node_rows,
            )
        if top_pod_rows:
            cols = (
                ["Name", "CPU", "Memory"]
                if namespace
                else ["NS", "Name", "CPU", "Memory"]
            )
            _render_table(
                "Top 15 pods by CPU", cols[: len(top_pod_rows[0])], top_pod_rows
            )

    if event_rows:
        # Limit events shown in overview to 5, deep to 20
        limit = 20 if level == "deep" else 5
        _render_table(
            f"Recent warning events (last {min(limit, len(event_rows))})",
            ["Time", "NS", "Reason", "Object", "Message"],
            event_rows[:limit],
        )


# ═══════════════════════════════════════════════════════════════════════════
# NOMAD
# ═══════════════════════════════════════════════════════════════════════════


@whatsup_group.command("nomad")
@click.option(
    "--address",
    default=None,
    help="Nomad HTTP address (defaults to $NOMAD_ADDR, or active company config)",
)
@click.option(
    "--token",
    default=None,
    help="ACL token (defaults to $NOMAD_TOKEN, or active company keychain secret)",
)
@click.option(
    "--region",
    default=None,
    help="Nomad region (defaults to cluster default)",
)
@_level_options
def nomad_cmd(address, token, region, level, json_out):
    """Nomad cluster overview.

    \b
    Examples:
      hat whatsup nomad                        # uses active company's NOMAD_ADDR/TOKEN
      hat whatsup nomad --address http://deploy.nomad-sf.sf-serv.ac:4646
      hat whatsup nomad --errors
      hat whatsup nomad --deep
    """
    env = os.environ.copy()

    # If neither cli flags nor env vars are set, try loading from the
    # currently-active hat company so `hat whatsup nomad` works even
    # when the user hasn't run `hat on <company>` in the current shell.
    if not address and not env.get("NOMAD_ADDR"):
        loaded = _load_active_company_env("NOMAD_ADDR", "NOMAD_TOKEN")
        if loaded.get("NOMAD_ADDR"):
            env["NOMAD_ADDR"] = loaded["NOMAD_ADDR"]
        if loaded.get("NOMAD_TOKEN") and not token and not env.get("NOMAD_TOKEN"):
            env["NOMAD_TOKEN"] = loaded["NOMAD_TOKEN"]

    if address:
        env["NOMAD_ADDR"] = address
    if token:
        env["NOMAD_TOKEN"] = token
    if region:
        env["NOMAD_REGION"] = region

    fetch_errors: list[str] = []

    def nomad(args: list[str], accept_fail: bool = False) -> tuple[int, str]:
        rc, out, err = _run_local(["nomad"] + args, env=env)
        if rc != 0:
            msg = err.strip() or f"exit {rc}"
            if accept_fail:
                fetch_errors.append(f"nomad {' '.join(args)}: {msg}")
            else:
                click.echo(f"Error: nomad {' '.join(args)} failed: {msg}", err=True)
                if rc == 127:
                    sys.exit(1)
        return rc, out

    nomad_addr = env.get("NOMAD_ADDR", "(not set)")

    # Server health — raft peers (text output only; requires management token)
    rc, raft = nomad(["operator", "raft", "list-peers"], accept_fail=True)
    raft_rows = []
    if rc == 0 and raft:
        for line in raft.strip().splitlines():
            if not line.strip() or line.startswith("Node"):
                continue
            cols = line.split()
            # Format: Node ID Address State Voter RaftProtocol
            if len(cols) >= 6:
                raft_rows.append(
                    [
                        cols[0],
                        cols[1][:16],
                        cols[2],
                        cols[3],
                        cols[4],
                        cols[5],
                    ]
                )

    # Nodes (clients)
    rc, nodes_raw = nomad(["node", "status", "-json"], accept_fail=True)
    node_rows = []
    node_counts = {"ready": 0, "down": 0, "draining": 0, "ineligible": 0}
    try:
        nodes = _json.loads(nodes_raw) if nodes_raw else []
        for n in nodes:
            name = n.get("Name", "?")
            status = n.get("Status", "?")
            dc = n.get("Datacenter", "?")
            eligibility = n.get("SchedulingEligibility", "?")
            drain = n.get("Drain", False)
            version = n.get("Version", "?")
            node_rows.append(
                [
                    name,
                    status,
                    dc,
                    version,
                    eligibility,
                    "yes" if drain else "no",
                ]
            )
            if status == "ready" and eligibility == "eligible" and not drain:
                node_counts["ready"] += 1
            elif drain:
                node_counts["draining"] += 1
            elif eligibility != "eligible":
                node_counts["ineligible"] += 1
            else:
                node_counts["down"] += 1
    except ValueError:
        pass

    # Jobs — use HTTP API directly (faster than `nomad job status -json`
    # which fetches full job detail for every job).
    rc, jobs_raw = nomad(["operator", "api", "/v1/jobs"], accept_fail=True)
    jobs = []
    try:
        jobs = _json.loads(jobs_raw) if jobs_raw else []
    except ValueError:
        jobs = []

    job_counts = {
        "running": 0,
        "pending": 0,
        "dead": 0,
        "other": 0,
    }
    problem_jobs = []
    historically_noisy = []  # jobs running now but with many past failures
    job_rows = []
    for j in jobs:
        name = j.get("Name") or j.get("ID", "?")
        status = j.get("Status", "?")
        jtype = j.get("Type", "?")
        summary = j.get("JobSummary", {}).get("Summary", {}) or {}
        running = sum(g.get("Running", 0) for g in summary.values())
        failed = sum(g.get("Failed", 0) for g in summary.values())
        queued = sum(g.get("Queued", 0) for g in summary.values())
        lost = sum(g.get("Lost", 0) for g in summary.values())

        job_rows.append(
            [name, jtype, status, str(running), str(queued), str(failed), str(lost)]
        )
        job_counts[status if status in ("running", "pending", "dead") else "other"] += 1

        # Problem criteria (current state, not cumulative counters):
        #   - service/system job not running when it should be
        #   - anything with queued tasks (can't be placed)
        #   - job explicitly dead (batch ignored — dead is normal for finished batch)
        is_problem = False
        if jtype in ("service", "system") and status != "running":
            is_problem = True
        elif status == "pending" and queued > 0:
            is_problem = True
        elif jtype in ("service", "system") and running == 0 and queued == 0:
            # Expected to be running but nothing is
            is_problem = True

        if is_problem:
            problem_jobs.append(
                [name, jtype, status, str(running), str(queued), str(failed), str(lost)]
            )
        elif failed >= 100 or lost >= 100:
            # For --deep: jobs with high historical failure/lost counters
            historically_noisy.append(
                [name, jtype, status, str(running), str(queued), str(failed), str(lost)]
            )

    # Failed/lost allocations across all jobs via HTTP API
    alloc_rows = []
    rc, bulk_allocs = nomad(["operator", "api", "/v1/allocations"], accept_fail=True)
    try:
        allocs = _json.loads(bulk_allocs) if bulk_allocs else []
        for a in allocs:
            status = a.get("ClientStatus", "?")
            desired = a.get("DesiredStatus", "?")
            if status in ("failed", "lost") or (
                desired == "run" and status not in ("running", "pending")
            ):
                alloc_rows.append(
                    [
                        (a.get("ID") or "")[:8],
                        a.get("JobID", "?"),
                        a.get("TaskGroup", "?"),
                        status,
                        desired,
                        a.get("NodeName", "?"),
                    ]
                )
    except ValueError:
        pass
    # Limit for display
    alloc_rows = alloc_rows[:30]

    # Deep: recent deployments
    deploy_rows = []
    if level == "deep":
        rc, dep_raw = nomad(["deployment", "list", "-json"], accept_fail=True)
        try:
            deps = _json.loads(dep_raw) if dep_raw else []
            for d in list(deps)[:15]:
                deploy_rows.append(
                    [
                        (d.get("ID") or "")[:8],
                        d.get("JobID", "?"),
                        d.get("Status", "?"),
                        d.get("StatusDescription", ""),
                    ]
                )
        except ValueError:
            pass

    # ─── Render ────────────────────────────────────────────────────────────

    if json_out:
        click.echo(
            _json.dumps(
                {
                    "address": nomad_addr,
                    "raft_peers": [
                        dict(
                            zip(
                                ["node", "id", "address", "role", "voter", "protocol"],
                                r,
                            )
                        )
                        for r in raft_rows
                    ],
                    "nodes_summary": node_counts,
                    "nodes": [
                        dict(
                            zip(
                                [
                                    "name",
                                    "status",
                                    "dc",
                                    "version",
                                    "eligibility",
                                    "drain",
                                ],
                                r,
                            )
                        )
                        for r in node_rows
                    ],
                    "jobs_summary": job_counts,
                    "jobs": [
                        dict(
                            zip(
                                [
                                    "name",
                                    "type",
                                    "status",
                                    "running",
                                    "queued",
                                    "failed",
                                    "lost",
                                ],
                                r,
                            )
                        )
                        for r in job_rows
                    ],
                    "problem_jobs": [
                        dict(
                            zip(
                                [
                                    "name",
                                    "type",
                                    "status",
                                    "running",
                                    "queued",
                                    "failed",
                                    "lost",
                                ],
                                r,
                            )
                        )
                        for r in problem_jobs
                    ],
                    "failed_allocs": [
                        dict(
                            zip(["id", "job", "group", "status", "desired", "node"], r)
                        )
                        for r in alloc_rows
                    ],
                    "deployments": [
                        dict(zip(["id", "job", "status", "description"], r))
                        for r in deploy_rows
                    ],
                },
                indent=2,
            )
        )
        return

    # ── errors mode ──
    if level == "errors":
        any_problems = False
        not_ready_nodes = [n for n in node_rows if n[1] != "ready" or n[5] == "yes"]
        if not_ready_nodes:
            any_problems = True
            _render_table(
                f"Unhealthy/draining nodes ({len(not_ready_nodes)})",
                ["Name", "Status", "DC", "Version", "Eligibility", "Drain"],
                not_ready_nodes,
            )
        if problem_jobs:
            any_problems = True
            _render_table(
                f"Problem jobs ({len(problem_jobs)})",
                ["Name", "Type", "Status", "Run", "Queue", "Fail", "Lost"],
                problem_jobs,
            )
        if alloc_rows:
            any_problems = True
            _render_table(
                f"Failed/lost allocations ({len(alloc_rows)})",
                ["ID", "Job", "Group", "Status", "Desired", "Node"],
                alloc_rows,
            )
        if not any_problems:
            from rich.console import Console

            Console().print("[green bold]✓ No problems found[/green bold]")
        return

    # ── overview / deep ──
    _render_kv(
        f"Nomad — {nomad_addr}",
        [
            ("Address", nomad_addr),
            (
                "Servers (raft)",
                f"{len(raft_rows)} ({sum(1 for r in raft_rows if r[3] == 'leader')} leader)",
            ),
            ("Clients ready", str(node_counts["ready"])),
            ("Clients draining", str(node_counts["draining"])),
            (
                "Clients down/ineligible",
                str(node_counts["down"] + node_counts["ineligible"]),
            ),
            ("Jobs running", str(job_counts["running"])),
            ("Jobs pending", str(job_counts["pending"])),
            ("Jobs dead", str(job_counts["dead"])),
        ],
    )

    if fetch_errors:
        from rich.console import Console

        Console().print("  [yellow]Warnings:[/yellow]")
        for e in fetch_errors:
            Console().print(f"    [yellow]![/yellow] {e}")

    if raft_rows:
        _render_table(
            "Raft servers",
            ["Node", "ID", "Address", "Role", "Voter", "Protocol"],
            raft_rows,
        )

    if node_rows:
        # In overview, only show non-ready or all if <=10
        display_nodes = (
            node_rows
            if level == "deep" or len(node_rows) <= 10
            else [n for n in node_rows if n[1] != "ready" or n[5] == "yes"]
        )
        if display_nodes:
            _render_table(
                f"Clients ({len(display_nodes)}/{len(node_rows)} shown)",
                ["Name", "Status", "DC", "Version", "Eligibility", "Drain"],
                display_nodes,
            )

    if problem_jobs:
        _render_table(
            f"Problem jobs ({len(problem_jobs)})",
            ["Name", "Type", "Status", "Run", "Queue", "Fail", "Lost"],
            problem_jobs,
        )
    else:
        from rich.console import Console

        Console().print("  [green]No problem jobs[/green]")

    if alloc_rows:
        _render_table(
            f"Failed/lost allocations ({len(alloc_rows)})",
            ["ID", "Job", "Group", "Status", "Desired", "Node"],
            alloc_rows,
        )

    if historically_noisy and level != "errors":
        # Show top 20 noisiest (by total Failed + Lost)
        top_noisy = sorted(
            historically_noisy,
            key=lambda r: int(r[5]) + int(r[6]),
            reverse=True,
        )[:20]
        _render_table(
            f"Noisy jobs — running but with ≥100 historical failures/lost "
            f"({len(historically_noisy)} total, top 20)",
            ["Name", "Type", "Status", "Run", "Queue", "Fail", "Lost"],
            top_noisy,
        )

    if level == "deep":
        if job_rows:
            _render_table(
                f"All jobs ({len(job_rows)})",
                ["Name", "Type", "Status", "Run", "Queue", "Fail", "Lost"],
                job_rows,
            )
        if deploy_rows:
            _render_table(
                f"Recent deployments ({len(deploy_rows)})",
                ["ID", "Job", "Status", "Description"],
                deploy_rows,
            )


# Silence unused-import warnings from the helper shims above
_ = (_colorize, _status_style, shlex)
