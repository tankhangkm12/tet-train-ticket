#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Check the required inputs and prepare the agent workspace for aizen-init.

Needs a GitHub/GitLab repo URL and at least one project document (file, folder or http(s) link).
On success: creates the project folder if absent, <project>/.aizen/runs/init/{plans,reports,graphify}, writes .aizen/runs/init/inputs.md and appends the
missing lines of assets/gitignore-agent.txt to <project>/.gitignore (never removes anything).
Exit code: 0 ok, 1 inputs missing/invalid (ask the user), 2 usage error. Standard library only.
"""
import argparse
import re
import sys
import tempfile
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
GITIGNORE = SKILL_DIR / "assets" / "gitignore-agent.txt"
REPO_RE = re.compile(r"^(https://|ssh://git@|git@)(github\.com|gitlab\.[\w.-]+|[\w.-]*gitlab[\w.-]*)[:/][\w./-]+?(\.git)?/?$")


def problems(repo: str | None, docs: list[str]) -> list[str]:
    out = []
    if not repo:
        out.append("missing --repo: ask the user for the GitHub/GitLab repository URL")
    elif not REPO_RE.match(repo):
        out.append(f"--repo is not a GitHub/GitLab URL: {repo}")
    if not docs:
        out.append("missing --docs: ask the user for the detailed project documents")
    for d in docs:
        if not d.startswith(("http://", "https://")) and not Path(d).exists():
            out.append(f"document not found: {d}")
    return out


def prepare(project: Path, repo: str, docs: list[str]) -> list[str]:
    ws = project / ".aizen/runs/init"
    for sub in ("plans", "reports", "graphify"):
        (ws / sub).mkdir(parents=True, exist_ok=True)
    (ws / "inputs.md").write_text(
        "# Inputs\n\nRepo: " + repo + "\n\nDocs:\n" + "".join(f"- {d}\n" for d in docs), encoding="utf-8")
    gi = project / ".gitignore"
    have = set(gi.read_text(encoding="utf-8").splitlines()) if gi.exists() else set()
    add = [l for l in GITIGNORE.read_text(encoding="utf-8").splitlines() if l.strip() and l not in have]
    if add:
        text = gi.read_text(encoding="utf-8") if gi.exists() else ""
        gi.write_text(text + ("\n" if text and not text.endswith("\n") else "") + "\n".join(add) + "\n", encoding="utf-8")
    return add


def selfcheck() -> None:
    assert REPO_RE.match("https://github.com/acme/api.git")
    assert REPO_RE.match("git@gitlab.com:team/sub/api.git")
    assert REPO_RE.match("https://gitlab.company.vn/team/api")
    assert not REPO_RE.match("https://bitbucket.org/acme/api")
    assert problems(None, []) and len(problems(None, [])) == 2
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp)
        doc = p / "srs.md"
        doc.write_text("x")
        assert problems("https://github.com/a/b", [str(doc), "https://notion.so/x"]) == []
        assert problems("https://github.com/a/b", [str(p / "nope.md")])
        (p / ".gitignore").write_text("node_modules/")
        added = prepare(p, "https://github.com/a/b", [str(doc)])
        assert ".aizen/" in added and (p / ".aizen/runs/init" / "reports").is_dir()
        assert prepare(p, "https://github.com/a/b", [str(doc)]) == []  # idempotent
        assert (p / ".gitignore").read_text().startswith("node_modules/\n")
    print("check_inputs selfcheck ok")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", default=".", help="project root (local clone), default: current dir")
    ap.add_argument("--repo", help="GitHub/GitLab repository URL")
    ap.add_argument("--docs", nargs="*", default=[], help="project documents: files, folders or http(s) links")
    ap.add_argument("--selfcheck", action="store_true", help="run internal asserts and exit")
    a = ap.parse_args()
    if a.selfcheck:
        selfcheck()
        return 0
    errs = problems(a.repo, a.docs)
    if errs:
        print("STOP — inputs missing, ask the user:\n" + "\n".join(f"  - {e}" for e in errs), file=sys.stderr)
        return 1
    project = Path(a.project).resolve()
    if project.exists() and not project.is_dir():
        print(f"project path is a file: {project}", file=sys.stderr)
        return 2
    project.mkdir(parents=True, exist_ok=True)
    added = prepare(project, a.repo, a.docs)
    print(f"ok — workspace {project / '.aizen/runs/init'} ready; .gitignore +{len(added)} lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
