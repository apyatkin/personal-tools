---
name: kubernetes
description: Use when working with Kubernetes — pods, deployments, services, kubectl commands, cluster debugging, or any K8s-related task
---

# Kubernetes

## Company Context

To get company-specific Kubernetes settings:

1. Read `~/.config/ctx/state.json` to get `active_company`
2. Read `~/.config/ctx/companies/<active_company>/config.yaml`
3. Use `cloud.kubernetes` section — reads `kubeconfig`, `refresh.provider`, `refresh.cluster`

The `KUBECONFIG` env var should already be set by `ctx use`. If not, set it from the config.

## Commands

### Pods

```bash
kubectl get pods -n <ns>                              # list pods
kubectl get pods -n <ns> -o wide                      # with node info
kubectl describe pod <pod> -n <ns>                    # full details
kubectl logs -f <pod> -n <ns>                         # follow logs
kubectl logs -f <pod> -n <ns> -c <container>          # specific container
kubectl logs <pod> -n <ns> --previous                 # previous instance logs
kubectl logs -l app=<name> -n <ns> --prefix           # logs across pods by label
kubectl exec -it <pod> -n <ns> -- /bin/sh             # shell into pod
kubectl delete pod <pod> -n <ns>                      # delete pod (only when instructed)
```

### Deployments & Rollouts

```bash
kubectl get deployments -n <ns>
kubectl rollout status deployment/<name> -n <ns>      # watch rollout
kubectl rollout history deployment/<name> -n <ns>     # revision history
kubectl rollout undo deployment/<name> -n <ns>        # rollback (only when instructed)
kubectl scale deployment/<name> --replicas=<n> -n <ns>  # scale (only when instructed)
```

### Resources & Events

```bash
kubectl top pods -n <ns>                              # CPU/memory usage
kubectl top nodes                                     # node resource usage
kubectl get events -n <ns> --sort-by=.lastTimestamp   # recent events
kubectl get all -n <ns>                               # all resources
```

### Context

```bash
kubectl config get-contexts                           # list contexts
kubectl config current-context                        # current context
kubectl config use-context <name>                     # switch (only when instructed)
```

## Runbooks

### Debug CrashLoopBackOff

1. Describe the pod: `kubectl describe pod <pod> -n <ns>`
2. Check events at the bottom for error messages
3. Read previous instance logs: `kubectl logs <pod> -n <ns> --previous`
4. Check resource limits — OOM kills show as `OOMKilled` in `describe`
5. Check if readiness/liveness probes are misconfigured
6. If the container fails immediately, exec into a debug container or check the image

### Investigate OOM Kill

1. Confirm OOM: `kubectl describe pod <pod> -n <ns>` — look for `OOMKilled` in container status
2. Check current usage: `kubectl top pods -n <ns>`
3. Compare against limits in the deployment spec
4. If limits are too low: increase memory limits in the deployment
5. If there's a memory leak: check application logs, heap dumps

### Drain Node Safely

1. Cordon the node: `kubectl cordon <node>` (only when instructed)
2. Drain: `kubectl drain <node> --ignore-daemonsets --delete-emptydir-data` (only when instructed)
3. Verify pods rescheduled: `kubectl get pods -o wide -A | grep <node>`
4. When maintenance is done: `kubectl uncordon <node>` (only when instructed)

### View Logs Across Pods

1. Find pods by label: `kubectl get pods -l app=<name> -n <ns>`
2. Stream all at once: `kubectl logs -l app=<name> -n <ns> --prefix -f`
3. For older logs or many pods, use `--since=1h` to limit scope
