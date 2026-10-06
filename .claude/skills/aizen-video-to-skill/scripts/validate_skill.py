#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Validate a generated skill folder against the standard layout.

Usage: uv run validate_skill.py <skill-folder>
Checks: SKILL.md exists, frontmatter has name+description, name is kebab-case
and matches the folder, description is meaningful, body length is sane,
referenced files exist, no leftover template placeholders.
"""
import os
import re
import sys


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    folder = os.path.abspath(sys.argv[1])
    errors, warns = [], []
    skill = os.path.join(folder, "SKILL.md")
    if not os.path.isfile(skill):
        print("FAIL: SKILL.md not found")
        sys.exit(1)
    text = open(skill, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        print("FAIL: missing YAML frontmatter (--- ... ---)")
        sys.exit(1)
    fm, body = m.groups()
    fields = dict(re.findall(r"^(\w[\w-]*):\s*(.*)$", fm, re.M))
    name, desc = fields.get("name", "").strip(), fields.get("description", "").strip()

    if not name:
        errors.append("frontmatter: 'name' missing")
    elif not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name):
        errors.append(f"name '{name}' must be kebab-case")
    elif name != os.path.basename(folder):
        warns.append(f"name '{name}' differs from folder '{os.path.basename(folder)}'")
    if len(desc) < 60:
        errors.append("description too short: say what it does AND when to use it")
    if len(desc) > 1024:
        errors.append("description over 1024 characters")
    if "<" in desc or ">" in desc:
        errors.append("description must not contain angle brackets")
    n_lines = len(body.splitlines())
    if n_lines > 500:
        warns.append(f"SKILL.md body is {n_lines} lines; move detail into references/")
    if re.search(r"TODO|FIXME|\[\[.*?\]\]|<fill", text, re.I):
        errors.append("leftover placeholder text (TODO/FIXME/[[...]])")

    for ref in set(re.findall(r"`((?:scripts|references|assets)/[^`\s]+)`", body)):
        if not os.path.exists(os.path.join(folder, ref.rstrip(".,"))):
            errors.append(f"referenced file missing: {ref}")

    for w in warns:
        print("WARN:", w)
    for e in errors:
        print("FAIL:", e)
    if errors:
        sys.exit(1)
    print(f"OK: {name} ({n_lines} body lines)")


if __name__ == "__main__":
    main()
