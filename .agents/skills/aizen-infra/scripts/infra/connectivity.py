#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Validate connectivity to target DevSecOps infrastructure.

Checks:
- VPS: TCP socket ping on SSH port, optional SSH exec of 'docker info'.
- Kubernetes: Checks kubeconfig validity via 'kubectl cluster-info'.
- Cloudflare: Verifies API token validity via Cloudflare v4 REST API.
"""
import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import urllib.request


def check_tcp_port(host: str, port: int, timeout: float = 5.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def check_vps(host: str, port: int, user: str = None, key: str = None) -> dict:
    report = {
        "target": "vps",
        "host": host,
        "port": port,
        "tcp_reachable": check_tcp_port(host, port),
        "docker_available": False,
        "details": ""
    }

    if not report["tcp_reachable"]:
        report["details"] = f"Port {port} on {host} is unreachable. Check firewall or security group."
        return report

    report["details"] = f"Port {port} is open and accepting TCP connections."

    # If SSH client is available and user is provided, probe docker
    if user and shutil.which("ssh"):
        cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", "-p", str(port)]
        if key:
            cmd.extend(["-i", key])
        cmd.extend([f"{user}@{host}", "docker --version"])

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if res.returncode == 0:
                report["docker_available"] = True
                report["details"] += f" SSH OK. Remote Docker: {res.stdout.strip()}."
            else:
                report["details"] += f" SSH reached but Docker check failed: {res.stderr.strip()}."
        except Exception as e:
            report["details"] += f" SSH probe skipped or failed: {e}."

    return report


def check_k8s(kubeconfig: str = None) -> dict:
    report = {
        "target": "kubernetes",
        "kubectl_installed": bool(shutil.which("kubectl")),
        "cluster_reachable": False,
        "details": ""
    }

    if not report["kubectl_installed"]:
        report["details"] = "'kubectl' command not found in PATH."
        return report

    cmd = ["kubectl", "cluster-info", "--request-timeout=5s"]
    if kubeconfig:
        cmd.extend(["--kubeconfig", kubeconfig])

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if res.returncode == 0:
            report["cluster_reachable"] = True
            report["details"] = "Kubernetes control plane is reachable: " + res.stdout.splitlines()[0]
        else:
            report["details"] = f"Cluster unreachable: {res.stderr.strip()}"
    except Exception as e:
        report["details"] = f"kubectl execution error: {e}"

    return report


def check_cloudflare(token: str = None) -> dict:
    cf_token = token or os.environ.get("CLOUDFLARE_API_TOKEN")
    report = {
        "target": "cloudflare",
        "token_provided": bool(cf_token),
        "valid": False,
        "details": ""
    }

    if not cf_token:
        report["details"] = "No CLOUDFLARE_API_TOKEN in the environment (the owner exports it; never pass it as an argument)."
        return report

    req = urllib.request.Request(
        "https://api.cloudflare.com/client/v4/user/tokens/verify",
        headers={
            "Authorization": f"Bearer {cf_token}",
            "Content-Type": "application/json"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("success"):
                report["valid"] = True
                status_msg = data.get("messages", [{}])[0].get("message", "Token is active")
                report["details"] = f"Cloudflare API Token verified: {status_msg}."
            else:
                report["details"] = f"Cloudflare API Token invalid: {data.get('errors')}"
    except Exception as e:
        report["details"] = f"Cloudflare API verification request failed: {e}"

    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--type", choices=["vps", "k8s", "cloudflare", "all"], required=True,
                        help="Infrastructure type to check")
    parser.add_argument("--host", help="VPS hostname or IP address")
    parser.add_argument("--port", type=int, default=22, help="SSH port (default: 22)")
    parser.add_argument("--user", help="SSH username")
    parser.add_argument("--key", help="Path to SSH private key")
    parser.add_argument("--kubeconfig", help="Path to kubeconfig file")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    args = parser.parse_args()
    results = []

    if args.type in ("vps", "all"):
        if not args.host and args.type == "vps":
            parser.error("--host is required for VPS check")
        if args.host:
            results.append(check_vps(args.host, args.port, args.user, args.key))

    if args.type in ("k8s", "all"):
        results.append(check_k8s(args.kubeconfig))

    if args.type in ("cloudflare", "all"):
        results.append(check_cloudflare())  # token from CLOUDFLARE_API_TOKEN only, never argv

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for r in results:
            ok = r.get("tcp_reachable") or r.get("cluster_reachable") or r.get("valid")
            status = "PASS" if ok else "WARN/FAIL"
            print(f"[{status}] {r['target'].upper()}: {r['details']}")

    sys.exit(0)


if __name__ == "__main__":
    main()
