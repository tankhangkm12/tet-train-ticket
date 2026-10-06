#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Gate for aizen-init: may step N start?

Checks that every earlier step left its report in .aizen/runs/init/reports/step-<k>.md with `Status: done` (or
`Status: skipped` + `Skip-approved-by: user`), that checkpoint steps (1, 5, 9, 10) carry `Approved: yes`, and
that the files each earlier step must produce exist. `gate.py 11` = everything is ready for handover.
Exit code: 0 may start, 1 blocked (prints why), 2 usage error. Standard library only.
"""
import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

CHECKPOINTS = {1, 5, 9, 10}
LAST = 10


def _any(p: Path, *names: str) -> bool:
    return any((p / n).exists() for n in names)


def _ignored(p: Path, entry: str) -> bool:
    gi = p / ".gitignore"
    return gi.exists() and entry in gi.read_text(encoding="utf-8").splitlines()


def _branch(p: Path, name: str) -> bool:
    r = subprocess.run(["git", "-C", str(p), "rev-parse", "--verify", "--quiet", name], capture_output=True)
    return r.returncode == 0


# files step k must leave behind: (description, check)
ARTIFACTS = {
    0: [(".git/ exists", lambda p: (p / ".git").is_dir()),
        ("branch develop exists", lambda p: _branch(p, "develop"))],
    1: [(".aizen/runs/init/plans/plan.md", lambda p: (p / ".aizen/runs/init/plans/plan.md").is_file())],
    3: [("Dockerfile", lambda p: _any(p, "Dockerfile")),
        ("docker-compose.yml / compose.yaml", lambda p: _any(p, "docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"))],
    4: [(".env.example", lambda p: (p / ".env.example").is_file()),
        (".env", lambda p: (p / ".env").is_file()),
        (".env in .gitignore", lambda p: _ignored(p, ".env"))],
    8: [("README.md", lambda p: (p / "README.md").is_file())],
    9: [(".aizen/runs/init/graphify/ not empty", lambda p: any((p / ".aizen/runs/init/graphify").glob("*")))],
}


def field(text: str, name: str) -> str:
    m = re.search(rf"^{name}:\s*(.+)$", text, re.M | re.I)
    return m.group(1).strip().lower() if m else ""


def blockers(project: Path, step: int) -> list[str]:
    out = []
    if not (project / ".aizen/runs/init/inputs.md").is_file():
        out.append("inputs not checked: run check_inputs.py first")
    if not _ignored(project, ".aizen/"):
        out.append(".aizen/ not in .gitignore")
    for k in range(step):
        rep = project / ".aizen/runs/init/reports" / f"step-{k}.md"
        if not rep.is_file():
            out.append(f"step {k}: report {rep.relative_to(project).as_posix()} missing")
            continue
        text = rep.read_text(encoding="utf-8")
        status = field(text, "Status")
        if status.startswith("skipped"):
            if not field(text, "Skip-approved-by").startswith("user"):
                out.append(f"step {k}: skipped without `Skip-approved-by: user — <quote>`")
            continue
        if not status.startswith("done"):
            out.append(f"step {k}: Status is '{status or 'none'}', need done")
            continue
        if k in CHECKPOINTS and not field(text, "Approved").startswith("yes"):
            out.append(f"step {k}: checkpoint not approved by the user (Approved: yes)")
        for desc, ok in ARTIFACTS.get(k, []):
            if not ok(project):
                out.append(f"step {k}: missing {desc}")
    return out


def selfcheck() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp)
        (p / ".aizen/runs/init/reports").mkdir(parents=True)
        (p / ".aizen/runs/init/plans").mkdir()
        (p / ".aizen/runs/init/graphify").mkdir()
        assert len(blockers(p, 0)) == 2  # no inputs, no .gitignore
        (p / ".aizen/runs/init/inputs.md").write_text("x")
        (p / ".gitignore").write_text(".aizen/\n.env\n")
        assert blockers(p, 0) == []
        assert blockers(p, 1) == ["step 0: report .aizen/runs/init/reports/step-0.md missing"]
        subprocess.run(["git", "init", "-q", "-b", "develop", str(p)], check=True)
        subprocess.run(["git", "-C", str(p), "-c", "user.email=a@b", "-c", "user.name=a",
                        "commit", "-q", "--allow-empty", "-m", "init"], check=True)
        rep = lambda k, body: (p / f".aizen/runs/init/reports/step-{k}.md").write_text(body)
        rep(0, "Status: done\n")
        assert blockers(p, 1) == []
        rep(1, "Status: done\nApproved: no\n")
        assert any("not approved" in b for b in blockers(p, 2))
        (p / ".aizen/runs/init/plans/plan.md").write_text("x")
        rep(1, "Status: done\nApproved: yes\n")
        assert blockers(p, 2) == []
        rep(2, "Status: skipped\n")
        assert any("Skip-approved-by" in b for b in blockers(p, 3))
        rep(2, "Status: skipped\nSkip-approved-by: user — 'bỏ qua bước 2'\n")
        rep(3, "Status: done\n")
        assert blockers(p, 4) == ["step 3: missing Dockerfile", "step 3: missing docker-compose.yml / compose.yaml"]
        (p / "Dockerfile").write_text("x")
        (p / "compose.yaml").write_text("x")
        for k in range(4, 11):
            rep(k, "Status: done\nApproved: yes\n")
        for f in (".env.example", ".env", "README.md", ".aizen/runs/init/graphify/GRAPH_REPORT.md"):
            (p / f).write_text("x")
        assert blockers(p, 11) == [], blockers(p, 11)
    print("gate selfcheck ok")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", nargs="?", type=int, help=f"step about to start (0-{LAST}), or {LAST + 1} for handover")
    ap.add_argument("--project", default=".", help="project root, default: current dir")
    ap.add_argument("--selfcheck", action="store_true", help="run internal asserts and exit")
    a = ap.parse_args()
    if a.selfcheck:
        selfcheck()
        return 0
    if a.step is None or not 0 <= a.step <= LAST + 1:
        ap.error(f"step must be 0-{LAST + 1}")
    project = Path(a.project).resolve()
    if not project.is_dir():
        print(f"project folder not found: {project}", file=sys.stderr)
        return 2
    errs = blockers(project, a.step)
    label = "handover" if a.step > LAST else f"step {a.step}"
    if errs:
        print(f"BLOCKED — {label} cannot start:\n" + "\n".join(f"  - {e}" for e in errs), file=sys.stderr)
        return 1
    print(f"ok — {label} may start")
    return 0


if __name__ == "__main__":
    sys.exit(main())
