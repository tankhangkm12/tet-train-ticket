#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""fetch_skill.py — copy a skill into Aizen-Skills and bring it to the Aizen structure (docs/aizen-skill-standard.md).

    uv run <SKILL_DIR>/scripts/fetch_skill.py <source> <name> [--repo <Aizen-Skills checkout>]
    uv run <SKILL_DIR>/scripts/fetch_skill.py --selfcheck

<source> = a GitHub folder URL (https://github.com/<owner>/<repo>/tree/<ref>/<path>) or a local folder holding SKILL.md.
Result:
  <repo>/skills/<name>/                     the copy: frontmatter name = <name>, nested SKILL.md renamed to guide.md,
                                            manifest.json with "source" (url, ref, license)
  <repo>/.aizen/cache/import/<name>/baseline/       the untouched original, for the A/B test (git-ignored, not installed)
Never overwrites: an existing skills/<name> is refused. GITHUB_TOKEN (optional) raises the GitHub API rate limit.
Exit code: 0 done, 1 refused or fetch failed, 2 usage error. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
GITHUB = re.compile(r"^https://github\.com/([^/]+)/([^/]+)/tree/([^/]+)/(.+?)/?$")
JUNK = ("__pycache__", ".git", ".DS_Store", "node_modules")


def find_repo(given: str | None) -> Path | None:
    for cand in ([Path(given)] if given else [SKILL_DIR.parent.parent, Path.cwd(), *Path.cwd().parents]):
        if (cand / "bin" / "cli.js").is_file() and (cand / "skills").is_dir():
            return cand.resolve()
    return None


def get(url: str) -> bytes:
    headers = {"User-Agent": "aizen-aizen-skill-importer", "Accept": "application/vnd.github+json"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as r:
        return r.read()


def fetch_github(api_url: str, dest: Path) -> None:
    for item in json.loads(get(api_url)):
        name = item["name"]
        if name in JUNK or "/" in name or "\\" in name or name in (".", ".."):
            continue
        if item["type"] == "file":
            (dest / name).write_bytes(get(item["download_url"]))
        elif item["type"] == "dir":
            (dest / name).mkdir()
            fetch_github(item["url"], dest / name)


def aizenize(dest: Path, name: str, source: str, ref: str) -> list[str]:
    """Frontmatter name, no nested SKILL.md, manifest with source. Returns what was added/changed."""
    notes = []
    skill_md = dest / "SKILL.md"
    text = skill_md.read_text(encoding="utf-8")
    m = re.search(r"^name:\s*(.+?)\s*$", text, re.M)
    if m and m.group(1) != name:
        text = text[:m.start(1)] + name + text[m.end(1):]
        skill_md.write_text(text, encoding="utf-8")
        notes.append(f"frontmatter name {m.group(1)} → {name}")
    for nested in sorted(dest.rglob("SKILL.md")):
        if nested.parent != dest:  # an installer would treat it as a second skill
            nested.rename(nested.with_name("guide.md"))
            notes.append(f"{nested.relative_to(dest)} → guide.md")
    lic = next((p.name for p in sorted(dest.iterdir()) if p.name.upper().startswith(("LICENSE", "LICENCE", "COPYING"))), None)
    mp = dest / "manifest.json"
    try:
        manifest = json.loads(mp.read_text(encoding="utf-8")) if mp.exists() else {}
    except ValueError:
        manifest = {}
    desc = re.search(r"^description:\s*(.+?)\s*$", text, re.M)
    manifest.update(name=name, framework="Aizen", kind=manifest.get("kind", "entry"),
                    source={"url": source, "ref": ref, "license": lic or "none found — check before publishing"})
    manifest.setdefault("version", "1.0.0")
    manifest.setdefault("description", (desc.group(1) if desc else name).split(". ")[0][:200])
    order = ("name", "version", "description", "framework", "kind", "source")
    manifest = {k: manifest[k] for k in order} | {k: v for k, v in manifest.items() if k not in order}
    mp.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    notes.append(f"manifest.json (source, licence: {lic or 'none found'})")
    return notes


def clone(source: str, name: str, repo: Path) -> tuple[Path, list[str]]:
    dest = repo / "skills" / name
    if dest.exists():
        raise FileExistsError(f"{dest} already exists — choose another name, or remove it yourself first")
    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp) / name
        local = Path(source)
        if local.is_dir():
            shutil.copytree(local, stage, ignore=shutil.ignore_patterns(*JUNK))
            ref = "local"
        else:
            m = GITHUB.match(source)
            if not m:
                raise ValueError("source must be a local folder or https://github.com/<owner>/<repo>/tree/<ref>/<path>")
            owner, rep, ref, path = m.groups()
            stage.mkdir()
            fetch_github(f"https://api.github.com/repos/{owner}/{rep}/contents/{path}?ref={ref}", stage)
        if not (stage / "SKILL.md").is_file():
            raise ValueError("no SKILL.md at the source root — point at the skill folder itself")
        base = repo / ".aizen" / "cache" / "import" / name / "baseline"
        if base.exists():
            shutil.rmtree(base)  # our own scratch copy from an earlier run
        shutil.copytree(stage, base)
        notes = aizenize(stage, name, source, ref)
        shutil.copytree(stage, dest)
    return dest, notes


def main(argv=None) -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description="Copy a skill into Aizen-Skills in the Aizen structure.")
    ap.add_argument("source", nargs="?", help="GitHub tree URL or local skill folder")
    ap.add_argument("name", nargs="?", help="destination skill name (lowercase-hyphen)")
    ap.add_argument("--repo", help="Aizen-Skills checkout (default: auto-detect)")
    ap.add_argument("--selfcheck", action="store_true")
    a = ap.parse_args(argv)
    if a.selfcheck:
        return _selfcheck()
    if not a.source or not a.name:
        ap.error("source and name are required")
    if not NAME.match(a.name):
        ap.error("name: lowercase letters, digits and single hyphens, e.g. pdf-reader")
    repo = find_repo(a.repo)
    if not repo:
        print("Aizen-Skills repo not found — pass --repo <path to the checkout with bin/cli.js>", file=sys.stderr)
        return 1
    try:
        dest, notes = clone(a.source, a.name, repo)
    except (FileExistsError, ValueError, OSError, urllib.error.URLError) as e:
        print(f"refused: {e}", file=sys.stderr)
        return 1
    files = sum(1 for p in dest.rglob("*") if p.is_file())
    print(f"cloned {a.source} → {dest} ({files} files)")
    print("\n".join(f"  - {n}" for n in notes))
    print(f"baseline: {repo / '.aizen' / 'cache' / 'import' / a.name / 'baseline'}")
    print("next: interview → customize → A/B test → docs rows → npm test → sync → commit")
    return 0


def _selfcheck() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        (repo / "bin").mkdir(parents=True)
        (repo / "bin" / "cli.js").touch()
        (repo / "skills").mkdir()
        src = Path(tmp) / "upstream-pdf"
        (src / "scripts" / "__pycache__").mkdir(parents=True)
        (src / "SKILL.md").write_text("---\nname: pdf\ndescription: Read PDFs. Use when x.\n---\n# PDF\n", encoding="utf-8")
        (src / "LICENSE.txt").write_text("MIT", encoding="utf-8")
        (src / "scripts" / "run.py").write_text("print(1)\n", encoding="utf-8")
        dest, _ = clone(str(src), "pdf-reader", repo)
        assert "name: pdf-reader" in (dest / "SKILL.md").read_text(encoding="utf-8")
        man = json.loads((dest / "manifest.json").read_text(encoding="utf-8"))
        assert man["name"] == "pdf-reader" and man["source"]["license"] == "LICENSE.txt" and man["version"] == "1.0.0"
        assert man["kind"] == "entry" and not (dest / "rules").exists(), "no empty parts are added"
        assert not (dest / "scripts" / "__pycache__").exists()
        assert "name: pdf\n" in (repo / ".aizen" / "cache" / "import" / "pdf-reader" / "baseline" / "SKILL.md").read_text(encoding="utf-8")
        for bad in ((str(src), "pdf-reader"), (str(Path(tmp) / "nope"), "x-y")):
            try:
                clone(bad[0], bad[1], repo)
                raise AssertionError(f"must refuse {bad}")
            except (FileExistsError, ValueError):
                pass
        assert GITHUB.match("https://github.com/anthropics/skills/tree/main/skills/pdf").groups()[2] == "main"
    print("fetch_skill.py self-check OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
