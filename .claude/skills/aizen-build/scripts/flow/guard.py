#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""guard.py moved to aizen-core (scripts/core/guard.py) in v25 — one engine for every skill.

This shim keeps hooks installed by v24 working: it runs the core guard with the same arguments.
Re-run `node bin/cli.js sync --project` (or `aizen guard install`) to point the hooks at the new path.
"""
import runpy
import sys
from pathlib import Path

CORE = Path(__file__).resolve().parents[3] / "aizen-core" / "scripts" / "core" / "guard.py"

if __name__ == "__main__":
    if not CORE.is_file():
        print(f"aizen-core guard not found at {CORE} — run `node bin/cli.js sync`", file=sys.stderr)
        sys.exit(0 if sys.argv[1:2] == ["hook"] else 2)
    sys.argv[0] = str(CORE)
    sys.path.insert(0, str(CORE.parent))
    runpy.run_path(str(CORE), run_name="__main__")
