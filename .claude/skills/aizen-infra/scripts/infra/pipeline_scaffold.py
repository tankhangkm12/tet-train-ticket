#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Scaffold production-grade DevSecOps CI/CD pipelines and multi-stage Dockerfiles.

Supported Engines:
- github-actions: .github/workflows/devsecops.yml
- gitlab-ci: .gitlab-ci.yml
- jenkins: Jenkinsfile
- argocd: k8s/argocd-application.yaml & k8s/deployment.yaml

Supported Stacks:
- nodejs: Node.js 20 multi-stage with devDependencies pruning & non-root user
- python: Python 3.11-slim multi-stage with wheel/user deps & non-root appuser
- golang: Go 1.22-alpine static build with scratch/alpine runner
"""
import argparse
import os
import sys

GITHUB_ACTIONS_TEMPLATE = """name: DevSecOps Production Pipeline

on:
  push:
    branches: [ main, master, develop ]
  pull_request:
    branches: [ main, master ]

env:
  IMAGE_NAME: {dockerhub_repo}

jobs:
  # -----------------------------------------------------------
  # STAGE 1: Secret Scanning
  # -----------------------------------------------------------
  secret-scan:
    name: 🛡️ Secret Scan (Gitleaks)
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Run Gitleaks
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{{{ secrets.GITHUB_TOKEN }}}}

  # -----------------------------------------------------------
  # STAGE 2: Static Application Security Testing (SAST)
  # -----------------------------------------------------------
  sast:
    name: 🔍 SAST Code Analysis (Semgrep)
    runs-on: ubuntu-latest
    needs: secret-scan
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4
      - name: Run Semgrep OSS
        run: |
          docker run --rm -v "${{{{ github.workspace }}}}:/src" returntocorp/semgrep semgrep \\
            --config=auto --error --severity=ERROR

  # -----------------------------------------------------------
  # STAGE 3: Build & Container Vulnerability Scan (Trivy)
  # -----------------------------------------------------------
  build-and-scan:
    name: 🐳 Build & Scan Container
    runs-on: ubuntu-latest
    needs: sast
    outputs:
      image_tag: ${{{{ steps.meta.outputs.tag }}}}
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Set Image Tag
        id: meta
        run: |
          TAG=$(echo "${{{{ github.sha }}}}" | cut -c1-7)
          echo "tag=${{TAG}}" >> $GITHUB_OUTPUT

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build Local Image for Scanning
        uses: docker/build-push-action@v5
        with:
          context: .
          load: true
          tags: ${{{{ env.IMAGE_NAME }}}}:${{{{ steps.meta.outputs.tag }}}}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Run Trivy Vulnerability Scanner
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{{{ env.IMAGE_NAME }}}}:${{{{ steps.meta.outputs.tag }}}}
          format: 'table'
          exit-code: '1'
          ignore-unfixed: true
          vuln-type: 'os,library'
          severity: 'CRITICAL,HIGH'

      - name: Login to Docker Hub
        if: github.event_name == 'push'
        uses: docker/login-action@v3
        with:
          username: ${{{{ secrets.DOCKERHUB_USERNAME }}}}
          password: ${{{{ secrets.DOCKERHUB_TOKEN }}}}

      - name: Push Container to Docker Hub
        if: github.event_name == 'push'
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: |
            ${{{{ env.IMAGE_NAME }}}}:${{{{ steps.meta.outputs.tag }}}}
            ${{{{ env.IMAGE_NAME }}}}:latest

  # -----------------------------------------------------------
  # STAGE 4: Continuous Deployment (CD)
  # -----------------------------------------------------------
  deploy:
    name: 🚀 Deploy to Target Infrastructure
    runs-on: ubuntu-latest
    needs: build-and-scan
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    steps:
      - name: Deploy to VPS over SSH
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{{{ secrets.SSH_HOST }}}}
          username: ${{{{ secrets.SSH_USER }}}}
          key: ${{{{ secrets.SSH_PRIVATE_KEY }}}}
          port: ${{{{ secrets.SSH_PORT || 22 }}}}
          script: |
            docker login -u "${{{{ secrets.DOCKERHUB_USERNAME }}}}" -p "${{{{ secrets.DOCKERHUB_TOKEN }}}}"
            docker pull ${{{{ env.IMAGE_NAME }}}}:${{{{ needs.build-and-scan.outputs.image_tag }}}}
            IMAGE_TAG=${{{{ needs.build-and-scan.outputs.image_tag }}}} docker compose up -d --pull always
            docker image prune -f
"""

GITLAB_CI_TEMPLATE = """# GitLab CI/CD DevSecOps Pipeline
stages:
  - secret-scan
  - sast
  - build-and-scan
  - deploy

variables:
  IMAGE_NAME: "{dockerhub_repo}"
  DOCKER_DRIVER: overlay2

secret-scan:
  stage: secret-scan
  image:
    name: zricethezav/gitleaks:latest
    entrypoint: [""]
  script:
    - gitleaks detect --verbose --redact

sast:
  stage: sast
  image: returntocorp/semgrep:latest
  script:
    - semgrep --config=auto --error --severity=ERROR

build-and-scan:
  stage: build-and-scan
  image: docker:24.0.5
  services:
    - docker:24.0.5-dind
  before_script:
    - echo "$DOCKERHUB_TOKEN" | docker login -u "$DOCKERHUB_USERNAME" --password-stdin
    - apk add --no-cache curl
    - curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin
  script:
    - export IMAGE_TAG=$(echo $CI_COMMIT_SHA | cut -c1-7)
    - docker build -t $IMAGE_NAME:$IMAGE_TAG .
    - trivy image --exit-code 1 --severity CRITICAL,HIGH --ignore-unfixed $IMAGE_NAME:$IMAGE_TAG
    - docker push $IMAGE_NAME:$IMAGE_TAG
    - docker tag $IMAGE_NAME:$IMAGE_TAG $IMAGE_NAME:latest
    - docker push $IMAGE_NAME:latest
  only:
    - main
    - master

deploy:
  stage: deploy
  image: alpine:latest
  before_script:
    - apk add --no-cache openssh-client
    - eval $(ssh-agent -s)
    - echo "$SSH_PRIVATE_KEY" | tr -d '\\r' | ssh-add -
    - mkdir -p ~/.ssh && chmod 700 ~/.ssh
    - ssh-keyscan -H -p ${{SSH_PORT:-22}} "$SSH_HOST" >> ~/.ssh/known_hosts
  script:
    - export IMAGE_TAG=$(echo $CI_COMMIT_SHA | cut -c1-7)
    - |
      ssh -p ${{SSH_PORT:-22}} $SSH_USER@$SSH_HOST "
        echo '$DOCKERHUB_TOKEN' | docker login -u '$DOCKERHUB_USERNAME' --password-stdin &&
        IMAGE_TAG=$IMAGE_TAG docker compose up -d --pull always &&
        docker image prune -f
      "
  only:
    - main
    - master
"""

JENKINS_TEMPLATE = """pipeline {{
    agent any

    environment {{
        IMAGE_NAME = '{dockerhub_repo}'
        DOCKERHUB_CREDS = credentials('dockerhub-credentials')
        SSH_CREDS = credentials('vps-ssh-key')
    }}

    stages {{
        stage('Secret Scan') {{
            steps {{
                sh 'docker run --rm -v $(pwd):/path zricethezav/gitleaks:latest detect --source="/path" --verbose --redact'
            }}
        }}

        stage('SAST Analysis') {{
            steps {{
                sh 'docker run --rm -v $(pwd):/src returntocorp/semgrep semgrep --config=auto --error --severity=ERROR'
            }}
        }}

        stage('Build & Vulnerability Scan') {{
            steps {{
                script {{
                    def gitCommit = sh(script: 'git rev-parse --short HEAD', returnStdout: true).trim()
                    env.IMAGE_TAG = gitCommit
                    sh "docker build -t ${{IMAGE_NAME}}:${{IMAGE_TAG}} ."
                    sh "docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:latest image --exit-code 1 --severity CRITICAL,HIGH --ignore-unfixed ${{IMAGE_NAME}}:${{IMAGE_TAG}}"
                }}
            }}
        }}

        stage('Push to Docker Hub') {{
            when {{
                branch 'main'
            }}
            steps {{
                sh 'echo "$DOCKERHUB_CREDS_PSW" | docker login -u "$DOCKERHUB_CREDS_USR" --password-stdin'
                sh "docker push ${{IMAGE_NAME}}:${{IMAGE_TAG}}"
                sh "docker tag ${{IMAGE_NAME}}:${{IMAGE_TAG}} ${{IMAGE_NAME}}:latest"
                sh "docker push ${{IMAGE_NAME}}:latest"
            }}
        }}

        stage('Deploy to Target Host') {{
            when {{
                branch 'main'
            }}
            steps {{
                sshagent(['vps-ssh-key']) {{
                    sh '''
                        ssh -o StrictHostKeyChecking=no $SSH_USER@$SSH_HOST "
                            echo '$DOCKERHUB_CREDS_PSW' | docker login -u '$DOCKERHUB_CREDS_USR' --password-stdin &&
                            IMAGE_TAG=${{IMAGE_TAG}} docker compose up -d --pull always &&
                            docker image prune -f
                        "
                    '''
                }}
            }}
        }}
    }}
}}
"""

ARGOCD_APP_TEMPLATE = """apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: devsecops-app
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: default
  source:
    repoURL: https://github.com/your-org/your-repo.git
    targetRevision: HEAD
    path: k8s
  destination:
    server: https://kubernetes.default.svc
    namespace: production
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
"""

ARGOCD_DEPLOYMENT_TEMPLATE = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
  namespace: production
  labels:
    app: devsecops-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: devsecops-app
  template:
    metadata:
      labels:
        app: devsecops-app
    spec:
      containers:
        - name: app
          image: {dockerhub_repo}:latest
          imagePullPolicy: Always
          ports:
            - containerPort: 3000
          resources:
            requests:
              memory: "128Mi"
              cpu: "100m"
            limits:
              memory: "512Mi"
              cpu: "500m"
          securityContext:
            runAsNonRoot: true
            runAsUser: 1001
            readOnlyRootFilesystem: false
            allowPrivilegeEscalation: false
"""

DOCKER_COMPOSE_TEMPLATE = """version: '3.8'

services:
  app:
    image: {dockerhub_repo}:${{IMAGE_TAG:-latest}}
    restart: unless-stopped
    expose:
      - "{port}"
    environment:
      - NODE_ENV=production
      - PORT={port}

  cloudflared:
    image: cloudflare/cloudflared:latest
    restart: unless-stopped
    command: tunnel run
    environment:
      - TUNNEL_TOKEN=${{CLOUDFLARE_TUNNEL_TOKEN}}
    depends_on:
      - app
"""

DOCKERFILE_NODE = """# -----------------------------------------------------------
# Multi-stage production Dockerfile for Node.js
# -----------------------------------------------------------
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
# Install all dependencies (including devDependencies required for compilation)
RUN npm ci
COPY . .
# Compile TypeScript / bundle code if build script exists
RUN npm run build --if-present
# Prune devDependencies to keep image lean
RUN npm prune --omit=dev

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
RUN addgroup -g 1001 -S nodejs && adduser -S nodejs -u 1001
COPY --from=builder /app/package*.json ./
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder --chown=nodejs:nodejs /app ./
USER nodejs
EXPOSE 3000
CMD ["npm", "start"]
"""

DOCKERFILE_PYTHON = """# -----------------------------------------------------------
# Multi-stage production Dockerfile for Python
# -----------------------------------------------------------
FROM python:3.11-slim AS builder
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends gcc build-essential && rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.11-slim AS runner
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1 \\
    PATH="/home/appuser/.local/bin:$PATH"
RUN addgroup --system --gid 1001 appuser && adduser --system --uid 1001 --gid 1001 appuser
COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local
COPY --chown=appuser:appuser . .
USER appuser
EXPOSE 8000
CMD ["python", "main.py"]
"""

DOCKERFILE_GOLANG = """# -----------------------------------------------------------
# Multi-stage production Dockerfile for Go
# -----------------------------------------------------------
FROM golang:1.22-alpine AS builder
WORKDIR /app
RUN apk add --no-cache git ca-certificates
COPY go.mod go.sum* ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-w -s" -o /app/server .

FROM alpine:3.19 AS runner
WORKDIR /app
RUN apk add --no-cache ca-certificates tzdata && \\
    addgroup -g 1001 -S appuser && adduser -S appuser -u 1001
COPY --from=builder --chown=appuser:appuser /app/server /app/server
USER appuser
EXPOSE 8080
CMD ["/app/server"]
"""


def write_new(path: str, content: str, force: bool) -> bool:
    """Write a scaffold file without ever replacing the owner's file unless --force."""
    if os.path.exists(path) and not force:
        print(f"! {path} exists; left intact (re-run with --force to replace it)")
        return False
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return True


def scaffold_pipeline(engine: str, dockerhub_repo: str, out_dir: str = ".", force: bool = False):
    if engine == "github-actions":
        wf_dir = os.path.join(out_dir, ".github", "workflows")
        os.makedirs(wf_dir, exist_ok=True)
        target_file = os.path.join(wf_dir, "devsecops.yml")
        content = GITHUB_ACTIONS_TEMPLATE.format(dockerhub_repo=dockerhub_repo)
        if write_new(target_file, content, force):
            print(f"✓ Created GitHub Actions DevSecOps workflow: {target_file}")
    elif engine == "gitlab-ci":
        target_file = os.path.join(out_dir, ".gitlab-ci.yml")
        content = GITLAB_CI_TEMPLATE.format(dockerhub_repo=dockerhub_repo)
        if write_new(target_file, content, force):
            print(f"✓ Created GitLab CI DevSecOps workflow: {target_file}")
    elif engine == "jenkins":
        target_file = os.path.join(out_dir, "Jenkinsfile")
        content = JENKINS_TEMPLATE.format(dockerhub_repo=dockerhub_repo)
        if write_new(target_file, content, force):
            print(f"✓ Created Jenkinsfile DevSecOps pipeline: {target_file}")
    elif engine == "argocd":
        k8s_dir = os.path.join(out_dir, "k8s")
        os.makedirs(k8s_dir, exist_ok=True)
        app_file = os.path.join(k8s_dir, "argocd-application.yaml")
        dep_file = os.path.join(k8s_dir, "deployment.yaml")
        if write_new(app_file, ARGOCD_APP_TEMPLATE, force):
            print(f"✓ Created ArgoCD application manifest: {app_file}")
        if write_new(dep_file, ARGOCD_DEPLOYMENT_TEMPLATE.format(dockerhub_repo=dockerhub_repo), force):
            print(f"✓ Created Kubernetes deployment manifest: {dep_file}")


def scaffold_dockerfile(stack: str, out_dir: str = "."):
    df_path = os.path.join(out_dir, "Dockerfile")
    if os.path.exists(df_path):
        print(f"! Dockerfile already exists at {df_path}; leaving intact.")
        return

    if stack == "python":
        content = DOCKERFILE_PYTHON
    elif stack == "golang":
        content = DOCKERFILE_GOLANG
    else:
        content = DOCKERFILE_NODE

    with open(df_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✓ Created multi-stage Dockerfile ({stack}): {df_path}")


def scaffold_compose(dockerhub_repo: str, stack: str, out_dir: str = "."):
    compose_path = os.path.join(out_dir, "docker-compose.yml")
    if os.path.exists(compose_path):
        print(f"! docker-compose.yml already exists at {compose_path}; leaving intact.")
        return

    port = "3000" if stack == "nodejs" else ("8000" if stack == "python" else "8080")
    content = DOCKER_COMPOSE_TEMPLATE.format(dockerhub_repo=dockerhub_repo, port=port)
    with open(compose_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✓ Created Docker Compose with Cloudflare Tunnel service: {compose_path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", choices=["github-actions", "gitlab-ci", "jenkins", "argocd"],
                        default="github-actions", help="CI/CD engine")
    parser.add_argument("--dockerhub", default="myuser/myapp", help="Docker Hub repository (username/image)")
    parser.add_argument("--stack", "--app", dest="stack", default="nodejs", choices=["nodejs", "python", "golang"],
                        help="App stack (aliases: --stack, --app)")
    parser.add_argument("--compose", action="store_true", help="Generate docker-compose.yml with Cloudflare Tunnel")
    parser.add_argument("--out", default=".", help="Output directory")
    parser.add_argument("--force", action="store_true", help="replace existing pipeline files")

    args = parser.parse_args()
    os.makedirs(args.out, exist_ok=True)
    scaffold_pipeline(args.engine, args.dockerhub, args.out, args.force)
    scaffold_dockerfile(args.stack, args.out)
    if args.compose:
        scaffold_compose(args.dockerhub, args.stack, args.out)


def _selfcheck() -> None:
    import contextlib
    import io
    import tempfile
    with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()):
        wf = os.path.join(d, ".github", "workflows", "devsecops.yml")
        scaffold_pipeline("github-actions", "me/app", d)
        assert os.path.isfile(wf)
        with open(wf, "w", encoding="utf-8") as f:
            f.write("mine")
        scaffold_pipeline("github-actions", "me/app", d)
        assert open(wf, encoding="utf-8").read() == "mine", "must not overwrite without --force"
        scaffold_pipeline("github-actions", "me/app", d, force=True)
        assert "trivy" in open(wf, encoding="utf-8").read().lower()
    print("pipeline_scaffold.py self-check OK")


if __name__ == "__main__":
    if sys.argv[1:] == ["--selfcheck"]:
        _selfcheck()
    else:
        main()
