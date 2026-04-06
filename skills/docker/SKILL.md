---
name: docker
description: Use when working with Docker — containers, compose, building images, registries, or any Docker-related task
---

# Docker

## Company Context

Read `state.json` for `active_company`, then load `config.yaml` for that company. Docker registry configuration lives under `docker.registries` and provides a list of registry entries, each with:

| Field          | Purpose                                              |
|----------------|------------------------------------------------------|
| `host`         | Registry hostname (e.g. `registry.example.com`)     |
| `username_ref` | Reference to the registry username in secrets store  |
| `password_ref` | Reference to the registry password in secrets store  |

Registry authentication is configured automatically when you run `ctx use <company>` (credentials are resolved from the secrets store and `docker login` is invoked). You do not need to authenticate manually unless troubleshooting.

## Commands

### Containers

```bash
# List running containers
docker ps

# List all containers including stopped ones
docker ps -a

# Show recent logs for a container
docker logs <container-name-or-id>

# Follow (tail) logs for a container
docker logs -f <container-name-or-id>

# Show last 100 lines of logs
docker logs --tail 100 <container-name-or-id>

# Execute an interactive shell in a running container
docker exec -it <container-name-or-id> /bin/sh

# Execute a command in a running container
docker exec <container-name-or-id> env

# Inspect full container metadata (ports, mounts, env, networking)
docker inspect <container-name-or-id>

# Show real-time CPU, memory, and network stats for all containers
docker stats

# Show stats for a specific container (non-streaming)
docker stats --no-stream <container-name-or-id>
```

### Compose

```bash
# Build images and start all services in the foreground
docker compose up --build

# Start all services in the background (detached)
docker compose up -d

# Build images and start in background
docker compose up --build -d

# View logs for all services
docker compose logs

# Follow logs for all services
docker compose logs -f

# Follow logs for a specific service
docker compose logs -f <service-name>

# Show last 50 lines for a specific service
docker compose logs --tail 50 <service-name>

# Stop and remove containers, networks (keeps volumes)
docker compose down

# Stop and remove containers, networks, and volumes
docker compose down -v

# List containers managed by compose
docker compose ps

# Execute a command in a running compose service
docker compose exec <service-name> /bin/sh

# Run a one-off command in a new container (does not affect running services)
docker compose run --rm <service-name> <command>

# Rebuild a single service
docker compose up --build <service-name>

# Restart a specific service
docker compose restart <service-name>
```

### Build & Push

```bash
# Build an image with a tag
docker build -t <image>:<tag> .

# Build with a specific Dockerfile
docker build -f Dockerfile.prod -t <image>:<tag> .

# Build ignoring the layer cache (full rebuild)
docker build --no-cache -t <image>:<tag> .

# Build with build arguments
docker build --build-arg ENV=production -t <image>:<tag> .

# Tag an existing image with a new name
docker tag <source-image>:<tag> <registry-host>/<image>:<tag>

# Push an image to a registry (ONLY when explicitly instructed)
docker push <registry-host>/<image>:<tag>

# Push all tags for an image (ONLY when explicitly instructed)
docker push --all-tags <registry-host>/<image>
```

### Registry

```bash
# Authenticate to a container registry
docker login <registry-host>

# Authenticate non-interactively (e.g. in scripts)
echo "<password>" | docker login <registry-host> -u <username> --password-stdin

# Log out of a registry
docker logout <registry-host>

# Pull an image from a registry
docker pull <registry-host>/<image>:<tag>
```

### Cleanup

```bash
# Show disk usage by images, containers, volumes, and build cache
docker system df

# Show verbose disk usage breakdown
docker system df -v

# Remove all stopped containers, unused networks, dangling images, and build cache
# (ONLY when explicitly instructed)
docker system prune

# Include unused (not just dangling) images in the prune
# (ONLY when explicitly instructed)
docker system prune -a

# Remove unused volumes
# (ONLY when explicitly instructed)
docker volume prune

# Remove all unused images (dangling only)
docker image prune

# Remove a specific image
docker rmi <image>:<tag>
```

## Runbooks

### Debug Container

When a container is failing, restarting, or behaving unexpectedly:

1. Check if the container is running:
   ```bash
   docker ps -a
   ```
   Note the `STATUS` column — look for `Exited`, `Restarting`, or `Up (unhealthy)`.

2. Read recent logs:
   ```bash
   docker logs --tail 100 <container-name>
   ```

3. Follow logs in real time to catch new errors:
   ```bash
   docker logs -f <container-name>
   ```

4. If the container is running, exec into it for live inspection:
   ```bash
   docker exec -it <container-name> /bin/sh
   ```

5. Check environment variables and mounts:
   ```bash
   docker inspect <container-name>
   ```
   Look at the `Env`, `Mounts`, `NetworkSettings`, and `State` sections.

6. Check resource usage — high CPU or memory near limits can cause OOM kills:
   ```bash
   docker stats --no-stream <container-name>
   ```

7. If using Compose, check the Compose-level view:
   ```bash
   docker compose ps
   docker compose logs <service-name>
   ```

### Rebuild from Scratch

When a cached build is producing stale results or a full rebuild is required:

1. Stop and remove existing containers:
   ```bash
   docker compose down
   ```

2. Remove the built image to force a clean build:
   ```bash
   docker rmi <image>:<tag>
   ```

3. Build without cache:
   ```bash
   docker build --no-cache -t <image>:<tag> .
   ```

4. Or, using Compose:
   ```bash
   docker compose build --no-cache
   docker compose up -d
   ```

5. Verify the new containers are running:
   ```bash
   docker compose ps
   docker compose logs -f
   ```

### Clean Up Disk Space

When Docker is consuming too much disk space:

1. First, assess what is using space:
   ```bash
   docker system df -v
   ```
   Identify whether it is images, volumes, or build cache causing the bloat.

2. Remove stopped containers and dangling images (safe cleanup — only when explicitly instructed):
   ```bash
   docker system prune
   ```

3. If volumes are also consuming space (only when explicitly instructed):
   ```bash
   docker volume prune
   ```

4. For a more aggressive cleanup including unused images (only when explicitly instructed):
   ```bash
   docker system prune -a
   ```

5. After pruning, confirm disk usage has dropped:
   ```bash
   docker system df
   ```

### Registry Auth

When authenticating to a private registry or troubleshooting auth issues:

1. Resolve registry credentials from the secrets store (via `ctx use <company>` — this should already be done).

2. Log in to the registry:
   ```bash
   docker login <registry-host>
   ```

3. Verify login succeeded by pulling a known image:
   ```bash
   docker pull <registry-host>/<image>:<tag>
   ```

4. If login fails, check that the credentials in config.yaml (`username_ref`, `password_ref`) point to valid secrets and that they have not expired.

5. To log in non-interactively (e.g. in CI scripts):
   ```bash
   echo "$REGISTRY_PASSWORD" | docker login <registry-host> -u "$REGISTRY_USERNAME" --password-stdin
   ```

6. To log out when done:
   ```bash
   docker logout <registry-host>
   ```
