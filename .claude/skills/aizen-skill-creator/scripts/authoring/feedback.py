#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""feedback.py — the skill feedback log behind rules/continuous-improvement.md.

    uv run <SKILL_DIR>/scripts/authoring/feedback.py log --skill <id> --kind bug|gap|friction|wrong-doc --text "…"
                                               [--evidence "…"] [--prompt "<prompt that showed it>"]
    uv run <SKILL_DIR>/scripts/authoring/feedback.py list [--skill <id>] [--open]
    uv run <SKILL_DIR>/scripts/authoring/feedback.py resolve --skill <id> --id <n> --commit <sha>
    uv run <SKILL_DIR>/scripts/authoring/feedback.py --selfcheck

Entries are JSONL in <repo>/.aizen/knowledge/feedback/<skill>.jsonl (local, git-ignored). `list` groups similar open
entries so a problem seen twice is visible as `x2`. Repo = --repo, else found like new_skill.py.
Exit code: 0 ok, 1 repo/entry not found, 2 usage error. Standard library only.
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from new_skill import NAME, find_repo

KINDS = ("bug", "gap", "friction", "wrong-doc")


def log_dir(repo: Path) -> Path:
    return repo / ".aizen" / "knowledge" / "feedback"


def read(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def log(repo: Path, skill: str, kind: str, text: str, evidence: str = "", prompt: str = "") -> dict:
    path = log_dir(repo) / f"{skill}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = read(path)
    row = {"id": max((r["id"] for r in rows), default=0) + 1, "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "kind": kind, "text": text, "evidence": evidence, "prompt": prompt, "resolved": None}
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def _norm(s: str) -> str:
    return " ".join(re.findall(r"\w+", s.lower()))


def groups(rows: list[dict]) -> list[list[dict]]:
    # ponytail: pairwise difflib on the first entry of each group, O(n·groups); fine for hundreds of entries.
    out: list[list[dict]] = []
    for r in rows:
        for g in out:
            if g[0]["kind"] == r["kind"] and difflib.SequenceMatcher(None, _norm(g[0]["text"]), _norm(r["text"])).ratio() >= 0.6:
                g.append(r)
                break
        else:
            out.append([r])
    return sorted(out, key=len, reverse=True)


def listing(repo: Path, skill: str | None, open_only: bool) -> str:
    files = [log_dir(repo) / f"{skill}.jsonl"] if skill else sorted(log_dir(repo).glob("*.jsonl"))
    lines = []
    for f in files:
        rows = [r for r in read(f) if not (open_only and r["resolved"])]
        for g in groups(rows):
            r = g[0]
            state = f"fixed {r['resolved']}" if r["resolved"] else "open"
            ids = ",".join(str(x["id"]) for x in g)
            lines.append(f"{f.stem:<28} x{len(g):<3} {r['kind']:<9} {state:<14} #{ids:<8} {r['text']}")
    return "\n".join(lines) or "no feedback"


def resolve(repo: Path, skill: str, entry: int, commit: str) -> bool:
    path = log_dir(repo) / f"{skill}.jsonl"
    rows = read(path)
    hit = [r for r in rows if r["id"] == entry]
    for r in hit:
        r["resolved"] = commit
    write(path, rows)
    return bool(hit)


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv == ["--selfcheck"]:
        return _selfcheck()
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--repo")
    sub = p.add_subparsers(dest="cmd", required=True)
    lg = sub.add_parser("log")
    lg.add_argument("--skill", required=True)
    lg.add_argument("--kind", required=True, choices=KINDS)
    lg.add_argument("--text", required=True)
    lg.add_argument("--evidence", default="")
    lg.add_argument("--prompt", default="")
    ls = sub.add_parser("list")
    ls.add_argument("--skill")
    ls.add_argument("--open", action="store_true")
    rs = sub.add_parser("resolve")
    rs.add_argument("--skill", required=True)
    rs.add_argument("--id", type=int, required=True)
    rs.add_argument("--commit", required=True)
    a = p.parse_args(argv)
    if getattr(a, "skill", None) and not NAME.match(a.skill):
        print(f"bad skill id: {a.skill}", file=sys.stderr)
        return 2
    repo = find_repo(a.repo)
    if not repo:
        print("Aizen-Skills repo not found; pass --repo <path>", file=sys.stderr)
        return 1
    if a.cmd == "log":
        r = log(repo, a.skill, a.kind, a.text, a.evidence, a.prompt)
        print(f"logged {a.skill} #{r['id']} ({a.kind})")
    elif a.cmd == "list":
        print(listing(repo, a.skill, a.open))
    elif not resolve(repo, a.skill, a.id, a.commit):
        print(f"{a.skill} #{a.id} not found", file=sys.stderr)
        return 1
    return 0


def _selfcheck() -> int:
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        log(repo, "demo", "bug", "step 3 script crashes on Windows paths")
        log(repo, "demo", "bug", "Step 3 script crashes on windows paths!", prompt="run demo on C:\\x")
        log(repo, "demo", "gap", "no support for monorepos")
        g = groups(read(log_dir(repo) / "demo.jsonl"))
        assert [len(x) for x in g] == [2, 1], g
        assert "x2" in listing(repo, "demo", True)
        assert resolve(repo, "demo", 1, "abc123") and not resolve(repo, "demo", 9, "x")
        out = listing(repo, None, True)
        assert "#2" in out and "#1," not in out and "fixed" not in out, out
        assert main(["--repo", tmp, "log", "--skill", "Bad Id", "--kind", "bug", "--text", "x"]) == 2
    print("feedback.py self-check OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
