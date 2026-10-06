#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""to_notion.py — turn a checked aizen-tech-learning note into Notion-flavored Markdown for notion-create-pages.

    uv run <SKILL_DIR>/scripts/to_notion.py <note.md> [--out <file>]
    uv run <SKILL_DIR>/scripts/to_notion.py --selfcheck

Prints JSON {"title": ..., "out": ...}: the first '# ' heading becomes the page title (removed from the body);
pipe tables become <table header-row="true">; bare URLs become links; characters Notion treats as markup
(< > { } $ ~ ^ |) are escaped outside code. Code blocks (mermaid included) and inline code stay literal.
Default --out: <note>.notion.md next to the note. Exit code: 0 done, 2 usage error. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ESC = re.compile(r"([<>{}$~^|])")
URL = re.compile(r"(?<!\()(?<!\]\()https?://[^\s)<>`]+")
CODE = re.compile(r"(`[^`]*`|\[[^\]]*\]\([^)]*\))")  # inline code and existing links stay as they are


def inline(text: str) -> str:
    out = []
    for i, part in enumerate(CODE.split(text)):
        if i % 2:
            out.append(part)
            continue
        urls = [u.rstrip(".,;") for u in URL.findall(part)]
        for n, u in enumerate(urls):  # placeholders so escaping never touches a URL
            part = part.replace(u, f"\0{n}\0", 1)
        part = ESC.sub(r"\\\1", part)
        out.append(re.sub(r"\0(\d+)\0", lambda m: f"[{urls[int(m.group(1))]}]({urls[int(m.group(1))]})", part))
    return "".join(out)


def cells(row: str) -> list[str]:
    parts, cur, code = [], "", False
    for ch in row.strip().strip("|"):
        if ch == "`":
            code = not code
        if ch == "|" and not code:
            parts.append(cur.strip())
            cur = ""
        else:
            cur += ch
    return parts + [cur.strip()]


def convert(md: str) -> tuple[str, str]:
    title, out, table, fence = "", [], [], False

    def flush():
        if table:
            out.append('<table header-row="true">')
            for r in table:
                if not re.fullmatch(r"\|?[\s:|-]+\|?", r.strip()):
                    out.append("\t<tr>")
                    out.extend(f"\t\t<td>{inline(c)}</td>" for c in cells(r))
                    out.append("\t</tr>")
            out.append("</table>")
            table.clear()

    for line in md.splitlines():
        if line.startswith("```"):
            flush()
            fence = not fence
            out.append(line)
        elif fence:
            out.append(line)
        elif line.strip().startswith("|"):
            table.append(line)
        else:
            flush()
            if not title and line.startswith("# "):
                title = line[2:].strip()
            elif re.match(r"(#{1,4} |> |- |\d+\. )", line):
                head, rest = re.match(r"(#{1,4} |> |- |\d+\. )(.*)", line).groups()
                out.append(head + inline(rest))
            else:
                out.append(inline(line))
    flush()
    return title, "\n".join(out).strip() + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Convert a aizen-tech-learning note to Notion-flavored Markdown.")
    ap.add_argument("note", nargs="?")
    ap.add_argument("--out")
    ap.add_argument("--selfcheck", action="store_true")
    a = ap.parse_args(argv)
    if a.selfcheck:
        return _selfcheck()
    if not a.note or not Path(a.note).is_file():
        ap.error("note file is required")
    src = Path(a.note)
    title, body = convert(src.read_text(encoding="utf-8"))
    out = Path(a.out) if a.out else src.with_suffix(".notion.md")
    out.write_text(body, encoding="utf-8")
    print(json.dumps({"title": title, "out": str(out)}, ensure_ascii=False))
    return 0


def _selfcheck() -> int:
    md = ("# Redis 7.2 — cache\n> ~31 B · c->buf\n## L2\nSee https://x.io/a. and [d](https://y.io)\n"
          "| Layer | A | B |\n|---|---|---|\n| L2 | `a|b` 1 copy | {x} $1 |\n```mermaid\nA[\"x (y)\"] --> B\n```\n")
    title, body = convert(md)
    assert title == "Redis 7.2 — cache" and not body.startswith("# ")
    assert "> \\~31 B · c-\\>buf" in body, body
    assert "[https://x.io/a](https://x.io/a)." in body and "[d](https://y.io)" in body, body
    assert '<table header-row="true">' in body and "<td>`a|b` 1 copy</td>" in body and "<td>\\{x\\} \\$1</td>" in body
    assert "---" not in body.split("<table")[1].split("</table>")[0]
    assert 'A["x (y)"] --> B' in body
    print("to_notion.py self-check OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
