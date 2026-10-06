#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""graph.py — keep a graphify code map of the project for every Aizen role (v25).

    uv run <CORE_DIR>/scripts/core/graph.py --project .            # build or refresh (code only, no LLM, no network)
    uv run <CORE_DIR>/scripts/core/graph.py --project . --check    # status only
    uv run <CORE_DIR>/scripts/core/graph.py --project . --install  # install graphify first (A3: The owner approved it)

The map lives in <main checkout>/graphify-out/ (also when run from a worktree) and is kept out of git through
.git/info/exclude, so no tracked file changes. Roles then ask it instead of grepping blind:
graphify query "<question>" / affected "<symbol>" / path "A" "B" / explain "X" --graph <main>/graphify-out/graph.json
(references/core/code-map.md).

Exit code: 0 map ready, 1 build failed, 2 usage error, 3 graphify not installed (prints the install command).
Python >= 3.9, standard library only.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

PACKAGE = "graphifyy"  # PyPI name; the CLI is `graphify`


def git(cwd: Path, *args: str) -> str:
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def find_cli() -> str | None:
    found = shutil.which("graphify")
    if found:
        return found
    for d in (Path.home() / ".local" / "bin",):  # uv/pipx shim dir, often not yet on PATH after an install
        for name in ("graphify.exe", "graphify"):
            if (d / name).is_file():
                return str(d / name)
    return None


def install_cmd() -> list[str]:
    if shutil.which("uv"):
        return ["uv", "tool", "install", "--upgrade", PACKAGE]
    if shutil.which("pipx"):
        return ["pipx", "install", PACKAGE]
    return [sys.executable, "-m", "pip", "install", "--user", "--upgrade", PACKAGE]


def exclude(main: Path) -> None:
    """Keep graphify-out/ out of git without touching a tracked file."""
    if subprocess.run(["git", "check-ignore", "-q", "graphify-out/"], cwd=main).returncode == 0:
        return
    info = Path(git(main, "rev-parse", "--path-format=absolute", "--git-common-dir")) / "info" / "exclude"
    info.parent.mkdir(parents=True, exist_ok=True)
    old = info.read_text(encoding="utf-8") if info.exists() else ""
    info.write_text(old + ("" if old.endswith("\n") or not old else "\n") + "graphify-out/\n", encoding="utf-8")


def summary(graph: Path) -> str:
    try:
        g = json.loads(graph.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return f"map: missing ({graph.as_posix()})"
    return f"map: {graph.as_posix()} · {len(g.get('nodes', []))} nodes · {len(g.get('links', []))} edges"


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description="Build/refresh the graphify code map of a project.")
    ap.add_argument("--project", default=".", help="project dir or one of its worktrees (default: .)")
    ap.add_argument("--check", action="store_true", help="report status only, build nothing")
    ap.add_argument("--install", action="store_true", help="install graphify if missing (A3 — needs approval)")
    a = ap.parse_args(argv)

    project = Path(a.project).resolve()
    common = git(project, "rev-parse", "--path-format=absolute", "--git-common-dir") if project.is_dir() else ""
    if not common:
        print(f"usage: {project} is not inside a git repository", file=sys.stderr)
        return 2
    main_dir = Path(common).parent
    graph = main_dir / "graphify-out" / "graph.json"

    cli = find_cli()
    if not cli and a.install and not a.check:
        cmd = install_cmd()
        print("installing: " + " ".join(cmd))
        if subprocess.run(cmd).returncode != 0:
            print("install failed — see the output above", file=sys.stderr)
            return 1
        cli = find_cli()
    if not cli:
        print("graphify: not installed — A3, ask the owner, then: " + " ".join(install_cmd())
              + "  (or rerun with --install)")
        print(summary(graph) if graph.exists() else "map: none — search with grep/glob meanwhile")
        return 3
    if a.check:
        print(f"graphify: {cli}")
        print(summary(graph))
        return 0 if graph.exists() else 3

    exclude(main_dir)
    # ponytail: code-only AST rebuild (cheap, offline); docs need the /graphify skill and an LLM — not done here.
    r = subprocess.run([cli, "update", "."], cwd=main_dir, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=1800)
    if r.returncode != 0 or not graph.exists():
        print("\n".join(((r.stdout or "") + (r.stderr or "")).strip().splitlines()[-20:]), file=sys.stderr)
        print("map: build failed — search with grep/glob instead", file=sys.stderr)
        return 1
    print(summary(graph))
    print(f'ask: graphify query "<question>" --graph "{graph.as_posix()}"  (also: affected, path, explain)')
    return 0


if __name__ == "__main__":
    sys.exit(main())
