# Delivery path — steps (v24)

Used by `devops`. Build the path from commit to running service, prove it works, hand the owner the trigger.
CI/CD, manifests and IaC are risk modules by default (`references/plan/planning-method.md`).

## Rules

1. **Never handle a secret value** (`secrets.md`) — the path a secret travels, by name; the owner types the value.
2. **Know the real state before proposing a change** — `plan` / `helm diff` / `kubectl diff` as an A3 read; put
   the real diff in the approval quote. Unexpected destroys or replacements stop the work.
3. **One quote per action** (`authority.md`): command, context, change, blast radius, rollback (verified to
   exist), recovery check, cost.
4. **Not done until the rollback was rehearsed** in non-production (`deploy-and-rollback.md` §4).
5. **The repo chooses the stack** — detect and follow; never introduce a tool because it is good.
6. **Unknown environment is production** until the owner classifies it.
7. **Build once, promote the same artifact** — pin the digest.
8. **Size and cost are computed** with `scripts/core/capacity.py`, low/expected/high, dated prices.
9. Production writes, IAM, secret values, DNS, certificates, billing, branch protection, releases/tags,
   `--force`/`--auto-approve`/`--no-verify`: A4. Even in an incident you prepare the rollback; the owner runs it.

## Path ownership

| devops | dev |
|---|---|
| `.github/workflows/`, `.gitlab-ci.yml`, `Jenkinsfile`, `ci/` | application source |
| `Dockerfile*`, `.dockerignore`, `docker-compose*.yml` | health/readiness handlers, config module |
| `deploy/`, `k8s/`, `charts/`, `helm/`, Kustomize | migration scripts (devops prepares how they run) |
| `infra/`, `*.tf`, `*.tfvars`, Pulumi/CDK | dependency manifests |
| `.env.example` keys, secret wiring, alerts/dashboards as code | code reading those variables, log statements |

## Steps

- **Y0 Locate** plan, infra docs, stack from repo files, reachable CLIs/MCP (`mcp-and-tools.md` §1) and which
  credentials this session has — a production-write credential is reported immediately.
- **Y1 Read and check** — drift between repo and reality (A3 reads only); open questions (limits, replicas,
  retention, timeouts, alert thresholds, who is paged).
- **Y2 Infra brief** — files, what is applied where, blast radius, rollback, recovery check, cost delta, secret names.
- **Y3 Build** the files; commit each step.
- **Y4 Static gate** — pipeline lint, Dockerfile lint, `helm lint`+`template`, `terraform fmt -check`+`validate`,
  secret scan. Missing tool → `[unverified]`.
- **Y5 Non-prod apply** — A3 per action: quote → yes → run → record; prove a real request works, the rollback
  worked, logs and metrics arrive.
- **Y6 Hand off** — infra doc from `assets/infra/infrastructure.md`; PR text from `assets/infra/release-pr-template.md`;
  every push/apply as a command with verification and rollback. Production release: `assets/infra/release-packet.md`.

## Guides (in `references/infra/`)

| Task | Read |
|---|---|
| CI, pipeline stages, slow pipeline | `pipeline-design.md`, `platforms/github-actions.md` / `platforms/gitlab-ci.md` |
| security gates (secrets, SAST, SCA, image CVEs) and their thresholds | `security-gates.md`; scaffold with `scripts/infra/pipeline_scaffold.py` (never overwrites without `--force`) |
| containerize, image, compose | `platforms/docker.md` (+ Docker's vendored guides) · rootless: `platforms/podman.md` |
| registry, image tags, pushing | `platforms/docker-hub.md` |
| deploy, environments, staging | `deploy-and-rollback.md`, `environments.md` |
| reachability of a VPS, cluster or Cloudflare before a deploy | `scripts/infra/connectivity.py` (A3 read) |
| public exposure without open ports | `platforms/cloudflare.md` |
| Kubernetes / Helm / Kustomize | `platforms/kubernetes-helm.md` (+ KubeShark failure modes) |
| Terraform | `platforms/terraform.md` |
| monitoring, alerts, logs, health | `observability.md` |
| secret wiring, which secret names a pipeline needs | `secrets.md` first, then `scripts/infra/secrets_checklist.py` |
| production incident, postmortem | `incidents.md` (replaces Y1–Y5) |
| hand-over docs for an infra change (topology, env vars, runbook) | `assets/infra/handover-docs.md` |
| platform not covered yet | `platforms/_new-platform.md` |
| red pipeline | Y0 → diagnose (`mcp-and-tools.md` §4) → Y3–Y6 |
