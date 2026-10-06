# Podman — rootless containers, the same images

Podman runs OCI images without a daemon and, by default, without root. Images built with Docker run unchanged;
what differs is the runtime around them. Version first: `podman --version` (4.x and 5.x differ in networking
and Quadlet support) — cite docs.podman.io for that version.

## 1. Detect and decide

| Signature in the repo or host | Means |
|---|---|
| `Containerfile`, `podman-compose.yml`, `*.container` / `*.pod` Quadlet units under `~/.config/containers/systemd/` | the team runs Podman |
| only `Dockerfile` + `compose.yaml` | Docker; Podman is an option, not a default — offer it as a decision (`references/core/decisions.md`) |

Rootless is the reason to pick Podman (no root daemon to compromise). Choosing it changes ports, volumes and
service management, so it is a plan decision, never a silent swap.

## 2. Differences that break things

- **Ports below 1024** are not bindable rootless (`net.ipv4.ip_unprivileged_port_start`, a host setting = A3).
  Publish on 8080/8443 and put the proxy in front.
- **Volume ownership**: rootless containers map UIDs through `/etc/subuid`. Use `:Z`/`:z` on SELinux hosts and
  `--userns=keep-id` when the container must write files owned by the host user.
- **Compose**: `podman compose` delegates to a compose provider (`docker-compose` or `podman-compose`); healthcheck
  and `depends_on: condition` support varies by provider and version — verify before relying on it.
- **Services**: run long-lived containers as systemd units through **Quadlet** (`.container` files), not
  `podman generate systemd` (deprecated) and not `--restart=always` alone (no daemon restarts them after reboot).
- **Pods**: a Podman pod shares one network namespace like a Kubernetes pod; `podman kube play` runs a subset of
  Kubernetes YAML locally — useful for parity, not a substitute for testing on the real cluster.
- **Registry auth** lives in `${XDG_RUNTIME_DIR}/containers/auth.json`; the owner logs in, never the agent.

## 3. Same rules as Docker

Image rules, pinning by digest, build once and promote, and the destructive-command tiers are those of
`docker.md` and its vendored guides — `podman` accepts the same build and run flags for everything in them.
