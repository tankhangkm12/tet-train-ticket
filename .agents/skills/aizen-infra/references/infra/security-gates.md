# DevSecOps Security Gates & Thresholds

> Aizen: these thresholds are the defaults to offer; the owner decides what blocks a merge (`pipeline-design.md` §2). Rewriting published history or rotating a secret is the owner's action (A4) — the agent prepares the exact commands.

This document defines the automated quality gates, exit codes, and severity thresholds enforced across the CI/CD pipeline.

---

## 1. Secret Scanning Gate (Gitleaks)

- **Purpose**: Prevent credentials, tokens, private keys, and connection strings from entering git history.
- **Enforcement**: Runs as Stage 1 before any build or artifact compilation.
- **Exit Code**: `exit-code: 1` on any detected secret (blocks the entire pipeline immediately).
- **Configuration** (`.gitleaks.toml`):
  ```toml
  [extend]
  useDefault = true

  [allowlist]
  description = "Whitelisted mock fixtures in unit tests"
  paths = [
    '''tests/fixtures/.*''',
    '''test-data/.*'''
  ]
  ```
- **Remediation**:
  1. Revoke the exposed secret immediately (assume compromised).
  2. Rewrite commit history using `git filter-repo` or BFG if committed upstream.
  3. Rotate token and migrate the new value to the CI/CD Secret Store.

---

## 2. Static Application Security Testing (SAST - Semgrep / SonarQube)

- **Purpose**: Detect security flaws, SQL injection, XSS, insecure deserialization, and misconfigurations in source code.
- **Engine Rules**:
  - `p/security-audit`
  - `p/owasp-top-ten`
  - `p/cwe-top-25`
- **Severity Threshold**:
  - `ERROR`: Blocks the build immediately.
  - `WARNING`: Triggers pipeline warning / PR comment, requires engineer review.
  - `INFO`: Logged in artifacts for audit trail.

---

## 3. Container & CVE Vulnerability Scanning (Trivy)

- **Purpose**: Scan OS packages and application dependencies in the built Docker image before pushing to Docker Hub.
- **Scanning Configuration**:
  ```yaml
  vuln-type: 'os,library'
  severity: 'CRITICAL,HIGH'
  ignore-unfixed: true
  exit-code: 1
  ```
- **Threshold Rules**:
  - `CRITICAL`: 0 allowed. If an unpatched critical CVE is detected in a base image, downgrade/upgrade the base image (e.g. from `node:18` to `node:20-alpine3.20`).
  - `HIGH`: 0 allowed for packages with available fixes.
  - `MEDIUM` / `LOW`: Reported in artifacts, does not block build.

---

## 4. DAST / Post-Deployment Health Check (OWASP ZAP / Curl)

- **Sanity Smoke Test**:
  - Verify HTTP 200/301 response from the public Cloudflare URL.
  - Verify TLS certificate validity and HTTPS redirect.
  - Verify Security Headers:
    * `X-Frame-Options: DENY` or `SAMEORIGIN`
    * `X-Content-Type-Options: nosniff`
    * `Strict-Transport-Security: max-age=31536000; includeSubDomains`
