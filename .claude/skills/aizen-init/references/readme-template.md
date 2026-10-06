# README template (step 8)

Read at step 8. Fill every section with real values from the project; delete a section only if the plan has
nothing for it and say so in the step report.

```markdown
# <Project name>

<1–2 sentences: what the service does.>

## Tech stack
| Part | Choice | Version |

## Project structure
<tree, 2 levels, one comment per folder>

## Architecture
<layers, request flow: request-id → logging → auth → validation → handler; adapters behind interfaces>

## Resources / infrastructure
| Service | Image:tag | Port | Used for | Health check |

## Environment variables
| Variable | Required | Default / example | Description |
<every variable in .env.example>

## Configuration
<where the central config lives, how it validates, how to add a variable>

## Run locally
cp .env.example .env
docker compose up -d
curl http://localhost:<port>/health/ready

## API
| Method | Path | Auth | Description |   (at least /health, /health/ready, auth routes)

## Authentication & authorization
<token flow, roles, how to protect a route>

## Logging & request-id
<log format, X-Request-Id behavior>

## Testing
<command, what is covered>

## Git workflow
main / develop / feature/* / release/* / hotfix/*, Conventional Commits

## Troubleshooting
<app exits at startup = an infra connection failed: check `docker compose ps` and the log line>
```
