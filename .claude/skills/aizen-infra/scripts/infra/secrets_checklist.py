#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Secret names for a pipeline, and a scan for plaintext secrets in the workspace (aizen-infra, v24).

Never takes a secret value as an argument: values are typed by the owner into the CI secret store
(references/infra/secrets.md).

Features:
- Generates required secrets checklist for GitHub / GitLab / Jenkins.
- Scans current workspace for exposed plaintext secrets or uncommitted .env files.
"""
import argparse
import os
import re
import sys

SECRET_DEFINITIONS = {
    "common": [
        ("DOCKERHUB_USERNAME", "Docker Hub account username", True),
        ("DOCKERHUB_TOKEN", "Docker Hub Personal Access Token (PAT) with Read/Write permission", True),
    ],
    "vps": [
        ("SSH_HOST", "Target server IP address or hostname", True),
        ("SSH_USER", "Remote deployment user (e.g. deployer / ubuntu)", True),
        ("SSH_PRIVATE_KEY", "ED25519 or RSA private key for passwordless SSH login", True),
        ("SSH_PORT", "SSH port (default 22)", False),
    ],
    "k8s": [
        ("KUBECONFIG_DATA", "Base64-encoded Kubeconfig credentials for cluster authentication", True),
    ],
    "cloudflare": [
        ("CLOUDFLARE_API_TOKEN", "Cloudflare API Token with Zone:DNS or Tunnel:Edit permissions", True),
        ("CLOUDFLARE_ZONE_ID", "Target Cloudflare Zone ID", False),
    ]
}


def mask_secret(value: str) -> str:
    if not value or len(value) < 8:
        return "***"
    return value[:3] + "..." + value[-3:]



def scan_workspace_for_leaks(root_dir: str = ".") -> list[dict]:
    findings = []
    suspicious_patterns = [
        ("Private Key", re.compile(r"-----BEGIN (?:RSA|OPENSSH|EC|DSA) PRIVATE KEY-----")),
        ("Docker Hub Token", re.compile(r"dckr_pat_[A-Za-z0-9_-]{20,}")),
        ("Cloudflare Token", re.compile(r"(?:api_token|cloudflare_token)\s*=\s*['\"][A-Za-z0-9_-]{30,}['\"]", re.I)),
        ("Generic Secret Assign", re.compile(r"(?:PASSWORD|SECRET|API_KEY|TOKEN)\s*=\s*['\"][^\s'\"]{8,}['\"]", re.I))
    ]

    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Skip git and dependency folders
        dirnames[:] = [d for d in dirnames if d not in (".git", "node_modules", ".venv", "venv", "__pycache__")]
        for f in filenames:
            if f.endswith((".pyc", ".png", ".jpg", ".tar", ".gz", ".zip")):
                continue
            filepath = os.path.join(dirpath, f)
            if f in (".env", ".env.local", ".env.production"):
                findings.append({
                    "file": filepath,
                    "type": "Unencrypted Env File",
                    "detail": "Sensitive environment file should never be committed to git."
                })
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as fh:
                    for line_no, line in enumerate(fh, 1):
                        for label, regex in suspicious_patterns:
                            if regex.search(line):
                                findings.append({
                                    "file": filepath,
                                    "line": line_no,
                                    "type": label,
                                    "detail": f"Potential plaintext credential exposed on line {line_no}."
                                })
            except Exception:
                pass

    return findings


def print_secrets_template(target: str, platform: str = "github"):
    keys = list(SECRET_DEFINITIONS["common"])
    if target in ("vps", "all"):
        keys.extend(SECRET_DEFINITIONS["vps"])
    if target in ("k8s", "all"):
        keys.extend(SECRET_DEFINITIONS["k8s"])
    if target in ("cloudflare", "all"):
        keys.extend(SECRET_DEFINITIONS["cloudflare"])

    print(f"\n=======================================================")
    print(f"  🔐 REQUIRED SECRETS CHECKLIST ({platform.upper()} - {target.upper()})")
    print(f"=======================================================\n")
    print(f"Add the following key-value pairs into your {platform} Secret Store:\n")

    for key, desc, required in keys:
        req_str = "[REQUIRED]" if required else "[OPTIONAL]"
        print(f"  • {key.ljust(22)} {req_str} {desc}")

    print("\nSecurity Best Practices:")
    print("  1. Never paste raw secrets in chat or commit them into git.")
    print("  2. In Docker Hub, generate a dedicated Token at: https://hub.docker.com/settings/security")
    print("  3. For SSH, generate a dedicated deploy key: ssh-keygen -t ed25519 -C 'ci-deployer'\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checklist", action="store_true", help="Print secrets checklist")
    parser.add_argument("--target", choices=["vps", "k8s", "cloudflare", "all"], default="vps")
    parser.add_argument("--platform", choices=["github", "gitlab", "jenkins"], default="github")
    parser.add_argument("--scan-leaks", action="store_true", help="Scan local workspace for plaintext secrets")
    args = parser.parse_args()

    if args.scan_leaks:
        print("[Secret Scanner] Scanning repository for exposed credentials...")
        leaks = scan_workspace_for_leaks(".")
        if leaks:
            print(f"❌ FOUND {len(leaks)} POTENTIAL SECURITY LEAKS:")
            for l in leaks:
                line_info = f" (line {l['line']})" if "line" in l else ""
                print(f"  - [{l['type']}] {l['file']}{line_info}: {l['detail']}")
            sys.exit(1)
        else:
            print("✓ Clean! No exposed plaintext secrets detected.")
            sys.exit(0)

    # Default action
    print_secrets_template(args.target, args.platform)


if __name__ == "__main__":
    main()
