#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""check_tree.py — check a aizen-tech-learning note before it is published (references/tree-template.md).

    uv run <SKILL_DIR>/scripts/check_tree.py <note.md> [--min-alternatives 2]
    uv run <SKILL_DIR>/scripts/check_tree.py --selfcheck

Fails when: a section is missing · the component map has no flowchart or < 2 components · a component ID is used
but not defined, or defined but never used outside the map · a layer (L1–L5) lacks a mermaid diagram,
"Why it is efficient here", "Observe" or a source URL (unless it says "Not relevant: <reason>") · the comparison
has too few alternatives, fewer diagrams than alternatives, no source, or a cell that is only an adjective.
Exit code: 0 pass, 1 problems found, 2 usage error. Standard library only.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SECTIONS = ("Thesis", "Component map", "L1", "L2", "L3", "L4", "L5", "Core algorithm", "Comparison",
            "In practice", "Sources")
LAYERS = ("L1", "L2", "L3", "L4", "L5")
CID = re.compile(r"\bC\d+\b")
URL = re.compile(r"https?://\S+")
SKIP = re.compile(r"(Not relevant|Không liên quan)\s*:\s*\S", re.I)
MERMAID = re.compile(r"^```mermaid\b", re.M)
ADJECTIVES = {"fast", "slow", "faster", "slower", "good", "bad", "better", "worse", "high", "low", "medium",
              "easy", "hard", "simple", "complex", "yes", "no", "✓", "✗", "nhanh", "chậm", "tốt", "kém", "cao",
              "thấp", "trung bình", "dễ", "khó", "đơn giản", "phức tạp", "có", "không"}


def split(text: str) -> dict[str, str]:
    """'## <heading>' blocks keyed by the SECTIONS entry the heading starts with."""
    out, key = {}, None
    for line in text.splitlines():
        if line.startswith("## "):
            head = line[3:].strip().lower()
            key = next((s for s in SECTIONS if head.startswith(s.lower())), None)
            if key:
                out[key] = ""
            continue
        if key:
            out[key] += line + "\n"
    return out


def check(text: str, min_alt: int = 2) -> list[str]:
    s = split(text)
    errs = [f"missing section '## {k}…'" for k in SECTIONS if k not in s]
    cmap = s.get("Component map", "")
    defined = set(CID.findall(cmap))
    if "Component map" in s:
        if not re.search(r"```mermaid\s*\n\s*(flowchart|graph)\b", cmap):
            errs.append("Component map: no mermaid flowchart")
        if len(defined) < 2:
            errs.append("Component map: define at least 2 components as C1, C2, …")
    rest = "\n".join(v for k, v in s.items() if k != "Component map")
    used = set(CID.findall(rest))
    errs += [f"{c} is used but not defined in the component map" for c in sorted(used - defined)]
    errs += [f"{c} is defined but never used after the map — link it or drop it" for c in sorted(defined - used)]
    for k in LAYERS:
        body = s.get(k)
        if body is None or SKIP.search(body):
            continue
        for need, ok in (("a mermaid diagram", MERMAID.search(body)),
                         ("'Why it is efficient here'", re.search(r"why it is efficient here", body, re.I)),
                         ("'Observe' (a command to see it yourself)", re.search(r"\bobserve\b", body, re.I)),
                         ("a source URL", URL.search(body)),
                         ("a component ID (C1…)", CID.search(body))):
            if not ok:
                errs.append(f"{k}: needs {need}, or 'Not relevant: <reason>'")
    if "Core algorithm" in s and not URL.search(s["Core algorithm"]):
        errs.append("Core algorithm: needs a source URL")
    comp = s.get("Comparison")
    if comp is not None:
        rows = [r for r in comp.splitlines() if r.strip().startswith("|")]
        header = [c.strip() for c in rows[0].strip().strip("|").split("|")] if rows else []
        alts = len(header) - 2  # first column = layer/aspect, second = the technology itself
        if alts < min_alt:
            errs.append(f"Comparison: table needs the technology + ≥ {min_alt} alternatives as columns (found {max(alts, 0)})")
        if len(MERMAID.findall(comp)) < max(alts, min_alt):
            errs.append("Comparison: one mermaid diagram per alternative — compare architectures, not opinions")
        if not URL.search(comp):
            errs.append("Comparison: needs source URLs")
        for r in rows[2:]:
            for cell in [c.strip() for c in r.strip().strip("|").split("|")][1:]:
                if cell.lower().strip(" .*") in ADJECTIVES:
                    errs.append(f"Comparison: cell '{cell}' is an adjective — state the mechanism and its cost")
    if "Sources" in s and len(URL.findall(s["Sources"])) < 3:
        errs.append("Sources: list at least 3 URLs (docs, source code, papers) with versions")
    return errs


def main(argv=None) -> int:
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description="Check a aizen-tech-learning note before publishing.")
    ap.add_argument("note", nargs="?", help="the markdown note")
    ap.add_argument("--min-alternatives", type=int, default=2)
    ap.add_argument("--selfcheck", action="store_true")
    a = ap.parse_args(argv)
    if a.selfcheck:
        return _selfcheck()
    if not a.note:
        ap.error("note is required")
    p = Path(a.note)
    if not p.is_file():
        print(f"not found: {p}", file=sys.stderr)
        return 2
    errs = check(p.read_text(encoding="utf-8"), a.min_alternatives)
    for e in errs:
        print(f"  ✗ {e}")
    print(f"{p}: {'PASS' if not errs else f'{len(errs)} problem(s)'}")
    return 1 if errs else 0


GOOD = """# Redis 7.2
## Thesis
In-memory, single-threaded command execution in C1.
## Component map
- C1 event loop · C2 keyspace dict
```mermaid
flowchart LR
  client -->|RESP over TCP| C1 --> C2
```
## L1 Application
Not relevant: covered by L2.
## L2 Runtime
```mermaid
sequenceDiagram
  C1->>C2: lookup O(1)
```
**Why it is efficient here:** C2 is a hash table, O(1) per GET, no locks.
**Observe:** `redis-cli --latency`
Source: https://github.com/redis/redis/blob/7.2/src/dict.c
## L3 OS/kernel
```mermaid
sequenceDiagram
  C1->>kernel: epoll_wait
```
**Why it is efficient here:** one epoll_wait serves many sockets for C1.
**Observe:** `strace -c -p <pid>`
https://github.com/redis/redis/blob/7.2/src/ae_epoll.c
## L4 Network
Không liên quan: same host in this workload.
## L5 Hardware
Not relevant: no NUMA effect at this size.
## Core algorithm
Incremental rehash in C2. https://github.com/redis/redis/blob/7.2/src/dict.c
## Comparison
| Layer | Redis | Memcached | Hazelcast |
|---|---|---|---|
| L2 | 1 thread, no locks | N threads, slab locks | JVM, partitioned |
```mermaid
flowchart LR
  c --> mc[threads]
```
```mermaid
flowchart LR
  c --> hz[partitions]
```
https://github.com/memcached/memcached/blob/master/thread.c
## In practice
`redis-server --maxmemory 1gb`
## Sources
- https://redis.io/docs/ - https://github.com/redis/redis - https://memcached.org/
"""


def _selfcheck() -> int:
    assert check(GOOD) == [], check(GOOD)
    bad = GOOD.replace("C1->>C2: lookup O(1)", "C1->>C9: lookup")  # undefined ID
    assert any("C9 is used but not defined" in e for e in check(bad))
    bad = GOOD.replace("Not relevant: covered by L2.", "Just text.")  # layer without diagram or reason
    assert any(e.startswith("L1: needs a mermaid") for e in check(bad))
    bad = GOOD.replace("| 1 thread, no locks |", "| fast |")
    assert any("adjective" in e for e in check(bad))
    bad = GOOD.replace("| Hazelcast |", "|").replace("| JVM, partitioned |", "|").replace("|---|---|---|---|", "|---|---|---|")
    assert any("≥ 2 alternatives" in e for e in check(bad)) and check(bad, min_alt=1) == []
    assert any("missing section '## Sources" in e for e in check(GOOD.split("## Sources")[0]))
    assert any("C2 is defined but never used" in e for e in check(GOOD.replace("C2", "Cx").replace("- C1 event loop · Cx", "- C1 event loop · C2")))
    print("check_tree.py self-check OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
