# DevSecOps Handover Documentation Templates

When completing Stage 4.5, generate the following 3 markdown documents inside the target project repository under `docs/`:

---

## 1. docs/INFRA_DOCS.md (Infrastructure Topology)

```markdown
# Infrastructure Documentation

## Overview
- Project: <project-name>
- Primary Environment: Production / Staging
- Target Platform: Linux VPS (Ubuntu 22.04 LTS) / Kubernetes
- Public URL: https://app.example.com
- Ingress/DNS: Cloudflare Tunnel / Cloudflare DNS Proxy

## Architecture & Topology
- Host: <IP or Domain>
- Container Engine: Docker Engine <version> / Docker Compose v2
- Ingress Router: Cloudflare Tunnel (`cloudflared`) / Nginx Reverse Proxy
- Application Port: 3000 (Internal Docker Network)

## Runner Configuration
- Type: GitHub-hosted (ubuntu-latest) / Self-hosted
- Build Pipeline: `.github/workflows/devsecops.yml`
- Container Registry: Docker Hub (`<username>/<repository>`)
```

---

## 2. docs/ENV_VARS.md (Environment Variables & Secrets)

```markdown
# Environment Variables & Secrets Reference

## CI/CD Secrets (Configured in Repository Settings)

| Secret Name | Description | Required | Scope |
| :--- | :--- | :--- | :--- |
| `DOCKERHUB_USERNAME` | Docker Hub account handle | Yes | CI Build & Push |
| `DOCKERHUB_TOKEN` | Docker Hub Personal Access Token (PAT) | Yes | CI Build & Push |
| `SSH_HOST` | Target deployment server IP | Yes | CD Deploy |
| `SSH_USER` | Deployment user with docker group | Yes | CD Deploy |
| `SSH_PRIVATE_KEY` | Ed25519 deploy key | Yes | CD Deploy |

## Application Runtime Variables (`.env`)

| Variable | Description | Default | Example |
| :--- | :--- | :--- | :--- |
| `NODE_ENV` | Application environment mode | `production` | `production` |
| `PORT` | Container listening port | `3000` | `3000` |
| `DATABASE_URL` | Primary database connection string | None | `postgresql://...` |

## Secret Rotation Policy
- Rotate Docker Hub PAT every 90 days.
- Rotate SSH deploy keys every 180 days.
```

---

## 3. docs/PROCEDURES.md (Operational Runbook)

```markdown
# Operational Runbook & Standard Procedures

## 1. Routine Deployment Workflow
1. Develop feature on `feature/<name>` branch.
2. Open Pull Request to `main`.
   - Pipeline runs Secret Scan (Gitleaks) + SAST (Semgrep) + Build & Container Scan (Trivy).
3. Review and merge to `main`.
   - Pipeline pushes tagged image to Docker Hub and executes automatic CD deployment.

## 2. Viewing Live Logs
```bash
# On the target server:
docker compose logs -f --tail=100 app
```

## 3. Immediate Rollback Procedure
If a regression or critical bug occurs after deployment:
1. Locate the previous stable image tag (e.g. `IMAGE_TAG=a1b2c3d`).
2. Run on the server:
   ```bash
   IMAGE_TAG=a1b2c3d docker compose up -d
   ```
3. Revert the commit in Git and push to trigger automated pipeline sync.

## 4. Emergency Stop
```bash
docker compose stop app
```
```
