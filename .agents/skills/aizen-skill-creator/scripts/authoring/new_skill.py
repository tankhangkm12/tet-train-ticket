#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""new_skill.py — scaffold a new Aizen entry skill (docs/aizen-skill-standard.md, v3).

    uv run <SKILL_DIR>/scripts/authoring/new_skill.py <name> --description "<what. Use when … Not for …>" [--title "..."]
    uv run <SKILL_DIR>/scripts/authoring/new_skill.py --selfcheck

Creates <repo>/skills/<name>/ with SKILL.md (from assets/authoring/) and manifest.json only — add rules/,
agents/, references/, scripts/, assets/ when the skill has something to put there (no empty folders)
and prints the README/docs rows to add. Never overwrites an existing skill.
Repo = --repo, else the Aizen-Skills checkout this skill is linked from.
Exit code: 0 created, 1 refused (exists / repo not found), 2 usage error. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[2]  # <skill>/scripts/authoring/new_skill.py
NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def find_repo(given: str | None) -> Path | None:
    for cand in ([Path(given)] if given else [SKILL_DIR.parent.parent, Path.cwd(), *Path.cwd().parents]):
        if (cand / "bin" / "cli.js").is_file() and (cand / "skills").is_dir():
            return cand.resolve()
    return None


def create(repo: Path, name: str, description: str, title: str) -> Path:
    dest = repo / "skills" / name
    if dest.exists():
        raise FileExistsError(f"{dest} already exists — pick another name or edit that skill")
    dest.mkdir(parents=True)
    tmpl = (SKILL_DIR / "assets" / "authoring" / "skill-template.md").read_text(encoding="utf-8")
    (dest / "SKILL.md").write_text(tmpl.replace("{{NAME}}", name).replace("{{DESCRIPTION}}", description)
                                   .replace("{{TITLE}}", title), encoding="utf-8")
    manifest = {"name": name, "version": "1.0.0", "description": title, "framework": "Aizen", "kind": "entry",
                "requires": ["aizen-core"]}
    (dest / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return dest


def next_steps(name: str, title: str) -> str:
    return f"""next — fill SKILL.md, then register the skill (npm test checks these):
  README.md, table "Danh sách skill":
    | [`{name}`](skills/{name}) | {title} |
  docs/huong-dan-su-dung.md §2:  | {title} | `{name}` | "<từ khoá>" |
  docs/huong-dan-su-dung.md §4:  | `{name}` | <luôn kèm gì> |
  docs/prompt-mau.md:            a ```text block starting with /{name}
then: npm test && node bin/cli.js sync"""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Scaffold a new Aizen skill.")
    ap.add_argument("name", nargs="?")
    ap.add_argument("--description", help="frontmatter description: what · Use when … · Not for … (≤ 1024 chars)")
    ap.add_argument("--title", help="one-line purpose for manifest/README (default: first sentence of description)")
    ap.add_argument("--repo", help="Aizen-Skills checkout (default: auto-detect)")
    ap.add_argument("--selfcheck", action="store_true")
    a = ap.parse_args(argv)
    if a.selfcheck:
        return _selfcheck()
    if not a.name or not a.description:
        ap.error("name and --description are required")
    if not NAME.match(a.name):
        ap.error("name: lowercase letters, digits and single hyphens, e.g. pdf-reader")
    if len(a.description) > 1024 or "\n" in a.description:
        ap.error("description must be one line of at most 1024 characters")
    repo = find_repo(a.repo)
    if not repo:
        print("Aizen-Skills repo not found — pass --repo <path to the checkout with bin/cli.js>", file=sys.stderr)
        return 1
    title = a.title or a.description.split(". ")[0].rstrip(".")
    try:
        dest = create(repo, a.name, a.description, title)
    except FileExistsError as e:
        print(e, file=sys.stderr)
        return 1
    print(f"created {dest}")
    print(next_steps(a.name, title))
    return 0


def _selfcheck() -> int:
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        (repo / "bin").mkdir()
        (repo / "bin" / "cli.js").touch()
        (repo / "skills").mkdir()
        dest = create(repo, "demo-skill", "Does X. Use when Y. Not for: Z.", "Does X")
        skill = (dest / "SKILL.md").read_text(encoding="utf-8")
        assert "name: demo-skill" in skill and "{{" not in skill, skill
        assert json.loads((dest / "manifest.json").read_text(encoding="utf-8"))["name"] == "demo-skill"
        man = json.loads((dest / "manifest.json").read_text(encoding="utf-8"))
        assert man["kind"] == "entry" and man["requires"] == ["aizen-core"], man
        assert sorted(x.name for x in dest.iterdir()) == ["SKILL.md", "manifest.json"], "no empty parts"
        try:
            create(repo, "demo-skill", "d", "t")
            raise AssertionError("must refuse an existing skill")
        except FileExistsError:
            pass
        assert find_repo(tmp) == repo.resolve()
    print("new_skill.py self-check OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
