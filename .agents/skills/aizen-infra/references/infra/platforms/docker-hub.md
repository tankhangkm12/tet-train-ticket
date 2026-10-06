# Docker Hub Containerization & Security Guidelines

> Aizen: pushing an image is a write to a shared system — A3 in non-production pipelines, A4 for release tags. The token is a Personal Access Token typed by the owner into the CI secret store, never into chat or argv.

Best practices for container building, secure tagging, and Docker Hub credentials management.

---

## 1. Multi-Stage Dockerfile Standards

Always use multi-stage builds to minimize attack surface and image size:

1. **Builder Stage**: Installs SDKs, dev dependencies, compilers, and runs tests/builds.
2. **Runner Stage**: Uses a minimal runtime base (e.g. `alpine` or `gcr.io/distroless`), copies only built binaries/dist folders, and strips build tools.
3. **Non-Root User**: Never run containerized applications as `root`. Always create and switch to a dedicated unprivileged user:
   ```dockerfile
   RUN addgroup -g 1001 -S appgroup && adduser -S appuser -u 1001 -G appgroup
   USER appuser
   ```

---

## 2. Immutable Image Tagging Strategy

Deploying with mutable tags like `:latest` creates non-reproducible environments, complicates rollbacks, and breaks caching integrity.

### Recommended Tagging Scheme:
- **Primary Tag (Immutable)**: `${DOCKERHUB_REPO}:${GITHUB_SHA:0:7}` (e.g. `myuser/myapp:a1b2c3d`).
  * Used in all deployment commands (`docker compose`, `k8s deployment.yaml`).
- **Release Tag (Semantic)**: `${DOCKERHUB_REPO}:v1.2.3` (applied when Git tags are pushed).
- **Secondary Tag (Convenience)**: `${DOCKERHUB_REPO}:latest` (updated on main branch builds only).

---

## 3. Docker Hub Personal Access Token (PAT) Management

### Why PATs are Required:
- Account passwords grant full admin access, cannot be scoped, and expose 2FA-protected accounts.
- PATs can be scoped strictly to **Read & Write** or **Read-only**, and revoked instantly without changing your main password.

### Generation Steps:
1. Log in to [Docker Hub](https://hub.docker.com).
2. Go to **Account Settings** -> **Security** -> **New Access Token**.
3. Description: `ci-cd-pipeline-<project-name>`.
4. Permissions: **Read & Write**.
5. Save the generated `dckr_pat_...` string into CI/CD secrets:
   - Secret Name: `DOCKERHUB_TOKEN`
   - Secret Value: `dckr_pat_xxxxxxxxxxxxxxxxxxxx`
   - Never share, commit, or print this value.
