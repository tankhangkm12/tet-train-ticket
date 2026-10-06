#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""guard.py — one engine that holds every Aizen skill to its contract (v25).

The agent does not decide when its work is finished; this script does, from artifacts someone else can check.

    G=<CORE_DIR>/scripts/core/guard.py
    uv run $G start  --skill aizen-tech-learning --goal "Redis 7.2 for a 100k GET/s cache" [--backlog BL-05]
                     [--output tech-tree/redis.md] [--run ID] [--go]
    uv run $G ask    --run R --question "workload: 100k GET/s, 1 KB values?"    # waiting for the owner, may stop
    uv run $G go     --run R --text "<the owner's answer>"                      # planning/waiting → working
    uv run $G check  --run R            # the checklist as the gate sees it (exit 0 pass, 1 open items)
    uv run $G waive  --run R --step publish --reason "…" --evidence <file | one line of real output>
    uv run $G verify-brief --run R      # what the independent verifier must judge, and the verdict.json format
    uv run $G done   --run R            # same as the gate at a stop: pass → done, archived, backlog updated
    uv run $G stop   --run R --reason "…"                                       # abandon (shown to the owner)
    uv run $G backlog add --title "…" --skill aizen-build [--after BL-04] | approve BL-05 | drop BL-05
    uv run $G install [--workspace .]   # hooks (via uv) for Claude Code + Antigravity + git pre-push, session rules —
                                        # this project only; after `npx skills add` this is the one setup step
    uv run $G migrate                   # move an older .aizen/ layout into this one
    uv run $G hook pre|post|stop --agent claude|agy   # called by the harness, JSON payload on stdin
    uv run $G prepush                   # git pre-push: a run's branches push only when its checklist passes

Contract = assets/core/contract.default.json merged with the `contract` of the skill's manifest.json:
  steps         rows of runs/<RUN>/sheet.md the agent fills — `| id | [x] | file:… cmd:… sha:… out:… url:… |`;
                each evidence token is checked (file exists and is new, the command is in the ledger and passed,
                the commit exists, the output line was really printed, the URL is cited in the output).
  outputs       globs of the files the run produces ({run} is the run id); `start --output` overrides.
  rules         deterministic checks: count · per_block · labels · sections · regex · command — and for
                aizen-build approved · evidence · report · scope · knowledge.
  expectations  what the independent verifier judges, one id each; verdict.json from a session that did not
                write the outputs, every pass citing `path:line`, pass rate ≥ verifier.threshold.
Anything open at a stop → the agent continues with the exact list; three stops in a row without new work, or
verifier.rounds failed verdicts → status blocked, the owner decides. Hooks fail open; pre-push fails closed.
Python ≥ 3.9, standard library only.
"""
from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CORE = HERE.parents[1]                      # skills/aizen-core
SKILLS = CORE.parent                        # skills/
DEFAULT = CORE / "assets" / "core" / "contract.default.json"
STATE_PY = SKILLS / "aizen-build" / "scripts" / "flow" / "state.py"
FREE = ("planning", "waiting", "blocked", "stopped")   # the gate lets the agent stop here
FINAL = ("done", "stopped")
MAX_IDLE, MAX_BLOCKS = 2, 10
EVIDENCE_TYPES = ("file", "cmd", "sha", "out", "url")
SHA = re.compile(r"\b[0-9a-f]{7,40}\b")
VERDICT = re.compile(r"verdict\W{0,10}(PASS|CHANGES[_ ]REQUIRED|INCOMPLETE)", re.I)
CLAUDE_WRITE = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
AGY_WRITE = re.compile(r"write|edit|replace|create|delete|remove|move|rename", re.I)
SHELL_TOOLS = {"Bash", "run_command", "run_terminal_command", "shell", "execute_command"}
PROTECTED = re.compile(r"(^|/)\.aizen/(PROJECT\.md$|(runs|archive)/[^/]+/(run\.json|ledger\.jsonl|guard\.json"
                       r"|waivers\.json|evidence/.*)$)")
PROTECTED_NAMES = ("run.json", "ledger.jsonl", "guard.json", "waivers.json", "/evidence/", "PROJECT.md")
MUTATES = re.compile(r">|\btee\b|\bsed\s+-i|\brm\b|\bmv\b|\bcp\b|\btruncate\b|\bdd\b|write_text|open\(|Set-Content"
                     r"|Out-File|Remove-Item|Move-Item|Copy-Item")
OWN_SCRIPTS = re.compile(r"(guard|state|check|project)\.py")
APPROVED = re.compile(r"\|\s*(approved|đã duyệt)\s*\|", re.I)


# ── time, files ──────────────────────────────────────────────────────────────────────────────────────────

def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def local_now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def read_json(p: Path, default):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def write_json(p: Path, data) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(f".{p.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, p)


def write_text(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(f".{p.name}.{os.getpid()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, p)


# ── layout (references/core/workspace.md) ────────────────────────────────────────────────────────────────

def find_ws(start: Path) -> Path | None:
    """The main checkout: the nearest folder holding .aizen/, also from inside .aizen/worktrees/<…>/."""
    p = start.resolve()
    parts = p.parts
    for marker in (".aizen", ".worktrees"):
        if marker in parts:
            p = Path(*parts[:parts.index(marker)])
            break
    for d in (p, *p.parents):
        if (d / ".aizen").is_dir():
            return d
    return None


def az(ws: Path) -> Path:
    return ws / ".aizen"


def run_dir(ws: Path, run: str) -> Path:
    live = az(ws) / "runs" / run
    old = az(ws) / "archive" / run
    return old if not live.exists() and old.exists() else live


def all_runs(ws: Path, archived: bool = True) -> dict[str, dict]:
    out = {}
    for sub in ("runs", "archive") if archived else ("runs",):
        for rj in sorted((az(ws) / sub).glob("*/run.json")):
            r = read_json(rj, None)
            if isinstance(r, dict) and r.get("status"):
                r.setdefault("run", rj.parent.name)
                r.setdefault("skill", "aizen-build")
                out.setdefault(rj.parent.name, r)
    return out


def guard_state(ws: Path, run: str) -> dict:
    return read_json(run_dir(ws, run) / "guard.json", {})


def save_guard(ws: Path, run: str, g: dict) -> None:
    write_json(run_dir(ws, run) / "guard.json", g)


def live(ws: Path) -> dict[str, dict]:
    return {k: r for k, r in all_runs(ws, archived=False).items() if r["status"] not in FINAL}


def watched(ws: Path) -> dict[str, dict]:
    """Runs the Stop gate looks after: unfinished ones, and `done` ones it saw being built but never passed."""
    out = {}
    for k, r in all_runs(ws, archived=False).items():
        g = guard_state(ws, k)
        if r["status"] not in FINAL or (r["status"] == "done" and g and not g.get("passed")):
            out[k] = r
    return out


def config(ws: Path) -> dict:
    return read_json(az(ws) / "config" / "guard.json", {})


def is_code(path: str) -> bool:
    """A project file a commit would carry (worktrees count; the rest of .aizen/ does not)."""
    if path.startswith(".git/"):
        return False
    return not path.startswith(".aizen/") or path.startswith(".aizen/worktrees/")


WT = re.compile(r"^\.aizen/worktrees/([^/]+)/(.+)$")


def norm(path: str) -> str:
    """A run keeps its ledger keys after it moves to archive/."""
    return re.sub(r"^\.aizen/archive/", ".aizen/runs/", path)


# ── contracts ────────────────────────────────────────────────────────────────────────────────────────────

def manifest(skill: str) -> dict:
    return read_json(SKILLS / skill / "manifest.json", {})


def contract(skill: str) -> dict:
    """contract.default.json merged with the skill's: rules by id, verifier by key, the rest replaced."""
    base = read_json(DEFAULT, {})
    own = manifest(skill).get("contract") or {}
    if own.get("mode") == "none":
        return {"mode": "none", "steps": [], "rules": [], "outputs": [], "verifier": {"required": False}}
    rules = {r["id"]: r for r in base.get("rules", [])}
    for r in own.get("rules", []):
        rules[r["id"]] = {**rules.get(r["id"], {}), **r}
    merged = {**base, **{k: v for k, v in own.items() if k not in ("rules", "verifier")}}
    merged["rules"] = [r for r in rules.values() if not r.get("off")]
    merged["verifier"] = {**base.get("verifier", {}), **own.get("verifier", {})}
    merged.setdefault("steps", [])
    merged.setdefault("outputs", [])
    merged.setdefault("expectations", [])
    return merged


def entry_skills() -> list[str]:
    return sorted(p.parent.name for p in SKILLS.glob("*/manifest.json")
                  if read_json(p, {}).get("kind") == "entry")


# ── the plan (aizen-build): modules and write sets ───────────────────────────────────────────────────────

MODULE = re.compile(r"^## Module\s+`?([A-Za-z0-9._-]+)`?(.*)$", re.M)
WRITE_SET = re.compile(r"^\s*Files\s*\(write set\)\s*:\s*(.+)$", re.M | re.I)
BASE = re.compile(r"Base:\s*`?([^`\s@]+)`?\s*@\s*`?([0-9a-f]{7,40})`?")
NONE = {"", "-", "—", "none", "n/a", "(none)"}


def plan(ws: Path, run: str) -> tuple[dict[str, list[str]], str | None, set[str]]:
    """{module: write-set globs} (retired ~~id~~ excluded), the base SHA, and the modules of kind `ui`."""
    p = run_dir(ws, run) / "plan.md"
    if not p.is_file():
        return {}, None, set()
    text = p.read_text(encoding="utf-8")
    heads = list(MODULE.finditer(text))
    modules, ui = {}, set()
    for i, m in enumerate(heads):
        body = text[m.end():heads[i + 1].start() if i + 1 < len(heads) else len(text)].split("\n## ", 1)[0]
        line = WRITE_SET.search(body)
        raw = line.group(1) if line else ""
        globs = re.findall(r"`([^`]+)`", raw) or [g for g in re.split(r"[,\s]+", raw) if g]
        modules[m.group(1)] = [g.strip().lstrip("./") for g in globs if g.strip().lower() not in NONE]
        if re.search(r"\bkind\s+ui\b", m.group(2)):
            ui.add(m.group(1))
    base = BASE.search(text)
    return modules, base.group(2) if base else None, ui


def glob_rx(g: str) -> re.Pattern:
    out, i = "", 0
    while i < len(g):
        if g.startswith("**", i):
            out += ".*"
            i += 2
            if g.startswith("/", i):
                i += 1
        elif g[i] == "*":
            out += "[^/]*"
            i += 1
        elif g[i] == "?":
            out += "[^/]"
            i += 1
        else:
            out += re.escape(g[i])
            i += 1
    return re.compile(f"^{out}(/.*)?$" if not g.endswith("*") else f"^{out}$")


def in_set(path: str, globs: list[str]) -> bool:
    return any(glob_rx(g).match(path) for g in globs)


def unit_of(run: str, folder: str, modules: dict) -> str | None:
    """`.aizen/worktrees/<RUN>-<unit>/…` → unit."""
    return folder[len(run) + 1:] if folder.startswith(run + "-") and folder[len(run) + 1:] in modules else None


# ── git ──────────────────────────────────────────────────────────────────────────────────────────────────

def git(ws: Path, *args: str) -> str:
    try:
        r = subprocess.run(["git", "-C", str(ws), *args], capture_output=True, text=True, timeout=30)
        return r.stdout.strip() if r.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def tip(ws: Path, branch: str) -> str:
    return git(ws, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}")


def show(ws: Path, rev: str, path: str) -> list[str] | None:
    """Lines of `path` at commit `rev` (the working tree when rev is empty); None when it does not exist there."""
    if rev:
        try:
            r = subprocess.run(["git", "-C", str(ws), "show", f"{rev}:{path}"], capture_output=True, timeout=30)
        except (OSError, subprocess.SubprocessError):
            return None
        return r.stdout.decode("utf-8", "replace").splitlines() if r.returncode == 0 else None
    f = ws / path
    return f.read_text(encoding="utf-8", errors="replace").splitlines() if f.is_file() else None


# ── ledger ───────────────────────────────────────────────────────────────────────────────────────────────

def ledger(ws: Path, run: str) -> list[dict]:
    p = run_dir(ws, run) / "ledger.jsonl"
    out = []
    if p.is_file():
        for line in p.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
    return out


def append(ws: Path, run: str, entry: dict) -> None:
    p = run_dir(ws, run) / "ledger.jsonl"
    prev = ""
    if p.is_file():
        lines = p.read_text(encoding="utf-8").splitlines()
        prev = hashlib.sha256(lines[-1].encode()).hexdigest()[:16] if lines else ""
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps({**entry, "prev": prev}, ensure_ascii=False) + "\n")


def writers(ws: Path, run: str) -> tuple[dict[str, tuple[str, int]], set[str]]:
    """{file: (who wrote it last, ledger index)} and the writers of code / output files — hooks are the witness."""
    last, code = {}, set()
    for i, e in enumerate(ledger(ws, run)):
        who = e.get("writer") or e.get("session", "")
        for f in e.get("files", []):
            last[norm(f)] = (who, i)
            if is_code(f):
                code.add(who)
        cmd = e.get("cmd", "")
        if re.search(r">|\btee\b|Set-Content|Out-File|write_text", cmd):
            for name in re.findall(r"\.aizen/(?:runs|archive)/[^\s'\"]+\.(?:md|json)", cmd):
                last[norm(name)] = (who, i)
    return last, code


# ── citations ────────────────────────────────────────────────────────────────────────────────────────────

CITE = re.compile(r"(?<![\w/.-])((?:[\w.-]+/)*[\w.-]+\.[A-Za-z0-9]+):(\d+)(?:-(\d+))?\b")


def citations(text: str) -> list[tuple[str, int]]:
    """`path:line` references in a report (URLs and times like 10:30 excluded)."""
    out = []
    for m in CITE.finditer(text):
        if "://" in text[max(0, m.start() - 8):m.start()] or m.group(1).replace(".", "").isdigit():
            continue
        out.append((m.group(1).lstrip("./"), int(m.group(3) or m.group(2))))
    return out


def bad_citations(ws: Path, refs: list[tuple[str, int]], rev: str) -> list[str]:
    bad = []
    for path, line in refs:
        lines = show(ws, "" if path.startswith(".aizen/") or not rev else rev, path)
        if lines is None and rev:
            lines = show(ws, "", path)
        if lines is None or line < 1 or line > len(lines):
            bad.append(f"{path}:{line}")
    return bad


# ── outputs and text rules ───────────────────────────────────────────────────────────────────────────────

def output_files(ws: Path, run: dict) -> list[Path]:
    files: list[Path] = []
    for g in run.get("outputs", []):
        g = g.replace("{run}", run["run"])
        files += [p for p in sorted(ws.glob(g)) if p.is_file() and p not in files]
    return files


FENCE = re.compile(r"^```(\w*)[^\n]*\n(.*?)^```", re.M | re.S)


def mermaid_blocks(text: str) -> list[tuple[int, str]]:
    return [(m.start(), m.group(2)) for m in FENCE.finditer(text) if m.group(1).lower() == "mermaid"]


def mermaid_nodes(block: str) -> int:
    first = block.strip().splitlines()[0] if block.strip() else ""
    if first.startswith("sequenceDiagram"):
        names = set(re.findall(r"^\s*(?:participant|actor)\s+([\w-]+)", block, re.M))
        for a, b in re.findall(r"^\s*(\w+)\s*--?[)x>]*>?>?[+-]?\s*(\w+)\s*:", block, re.M):
            names |= {a, b}
        return len(names)
    names = set()
    for line in block.splitlines()[1:]:
        line = re.sub(r"%%.*", "", line).strip()
        if not line or re.match(r"^(subgraph|end|classDef|class|style|linkStyle|direction|click)\b", line):
            continue
        line = re.sub(r"\[[^\]]*\]|\([^)]*\)|\{[^}]*\}|\"[^\"]*\"|\|[^|]*\|", "", line)
        names |= set(re.findall(r"(?<![\w-])([A-Za-z_][\w]*)(?![\w-])", re.sub(r"[-=.]+[>ox]?|&", " ", line)))
    return len(names - {"TB", "TD", "BT", "RL", "LR"})


def caption_lines(text: str, start: int) -> int:
    before = text[:start].split("\n")[:-1]
    n = 0
    for line in reversed(before):
        if not line.strip() or line.startswith("#") or line.startswith("```"):
            break
        n += 1
    return n


NUMBER = re.compile(r"\b\d[\d.,]*\s?(%|x|×|ms|µs|us|ns|s\b|sec|KB|MB|GB|TB|kB|k\b|K\b|M\b|rps|qps|ops|req/s|/s|"
                    r"times|lần|syscalls?|copies|bản sao|RTT|round-trips?)", re.I)


def unlabelled_claims(text: str, labels: list[str]) -> list[str]:
    body = FENCE.sub("", text)
    tags = re.compile(r"\[(%s)\]" % "|".join(map(re.escape, labels)), re.I)
    out = []
    for line in body.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or set(s) <= set("|-: ") or s.startswith(">"):
            continue
        if NUMBER.search(s) and not tags.search(s) and "http" not in s:
            out.append(s[:90])
    return out


# ── the checklist ────────────────────────────────────────────────────────────────────────────────────────

class Result:
    def __init__(self):
        self.open: list[str] = []
        self.waived: list[str] = []
        self.rows: list[tuple[str, str, str]] = []   # (id, ok|open|waived, detail)

    def add(self, sid: str, ok: bool, detail: str, waivable: bool = False, waivers: dict | None = None):
        if ok:
            self.rows.append((sid, "ok", detail))
        elif waivable and waivers is not None and sid in waivers:
            self.waived.append(sid)
            self.rows.append((sid, "waived", waivers[sid].get("reason", "")))
        else:
            self.open.append(f"[{sid}] {detail}")
            self.rows.append((sid, "open", detail))


STEP_ROW = re.compile(r"^\|\s*`?([A-Za-z0-9._{}-]+)`?\s*\|\s*([^|]*)\|\s*([^|]*?)\s*\|")
TOKEN = re.compile(r"\b(file|cmd|sha|out|url):\s*(`[^`]+`|\"[^\"]+\"|\S+)")


def sheet_rows(ws: Path, run: str) -> dict[str, tuple[str, str]]:
    p = run_dir(ws, run) / "sheet.md"
    if not p.is_file():
        return {}
    text = p.read_text(encoding="utf-8")
    part = text.split("## Checks", 1)[0]
    rows = {}
    for line in part.splitlines():
        m = STEP_ROW.match(line)
        if m and m.group(1).lower() not in ("step", "bước", "id"):
            rows[m.group(1)] = (m.group(2).strip(), m.group(3).strip())
    return rows


def check_token(ws: Path, run: dict, kind: str, value: str, entries: list[dict], outputs: list[Path]) -> str | None:
    """None when the evidence holds, else why not."""
    value = value.strip("`\"' ")
    if kind == "file":
        p = (ws / value) if not Path(value).is_absolute() else Path(value)
        if not p.is_file() or p.stat().st_size == 0:
            return f"file:{value} does not exist or is empty"
        created = run.get("created")
        if created:
            born = dt.datetime.fromisoformat(created).timestamp()
            if p.stat().st_mtime + 5 < born:
                return f"file:{value} is older than this run"
        return None
    if kind == "cmd":
        want = " ".join(value.split())
        hits = [e for e in entries if want and want in " ".join(e.get("cmd", "").split())]
        if not hits:
            return f"cmd:{value} was never run in this run (no ledger record)"
        if all(e.get("failed") for e in hits):
            return f"cmd:{value} failed every time it ran"
        return None
    if kind == "sha":
        return None if git(ws, "rev-parse", "--verify", "--quiet", value + "^{commit}") else f"sha:{value} is not a commit"
    if kind == "out":
        if any(value in e.get("out", "") for e in entries):
            return None
        for f in (run_dir(ws, run["run"]) / "evidence").glob("*"):
            if f.is_file() and value in f.read_text(encoding="utf-8", errors="replace"):
                return None
        return f'out:"{value[:40]}" was not printed by any recorded command'
    if kind == "url":
        if not re.match(r"^https?://\S+$", value):
            return f"url:{value} is not a URL"
        if not any(value in f.read_text(encoding="utf-8", errors="replace") for f in outputs):
            return f"url:{value} is not cited in the output"
        return None
    return f"{kind}: unknown evidence type"


def evaluate(ws: Path, run_id: str, finishing: bool = True) -> Result:
    res = Result()
    run = all_runs(ws).get(run_id)
    if run is None:
        res.open.append(f"no run {run_id} in {ws}")
        return res
    c = contract(run["skill"])
    rd = run_dir(ws, run_id)
    waivers = read_json(rd / "waivers.json", {})
    entries = ledger(ws, run_id)
    outputs = output_files(ws, run)
    coordinator = guard_state(ws, run_id).get("coordinator")
    last_writer, code_writers = writers(ws, run_id)
    modules, base, _ = plan(ws, run_id)
    unit_tip = {u: tip(ws, f"feature/{run_id}-{u}") for u in modules}
    int_tip = tip(ws, f"int/{run_id}")
    built = [t for t in unit_tip.values() if t]
    final_tip = int_tip or (built[0] if len(built) == 1 else "")
    reports = rd / "reports"
    review_text = "\n".join(f.read_text(encoding="utf-8", errors="replace") for f in sorted(reports.glob("review*.md")))

    # 1. the sheet the agent filled
    rows = sheet_rows(ws, run_id)
    for st in c.get("steps", []):
        sid, waivable = st["id"], bool(st.get("waivable"))
        if st.get("when") == "finish" and not finishing:
            continue
        done, cell = rows.get(sid, ("", ""))
        if not re.search(r"\[x\]|^x$|✓|yes|done|xong", done, re.I):
            res.add(sid, False, "not ticked in sheet.md", waivable, waivers)
            continue
        tokens = TOKEN.findall(cell)
        allowed = st.get("evidence", list(EVIDENCE_TYPES))
        if not tokens:
            res.add(sid, False, f"ticked without evidence — write {' / '.join(t + ':…' for t in allowed)} in its row",
                    waivable, waivers)
            continue
        errs = [f"{k}: not accepted for this step (use {', '.join(allowed)})" if k not in allowed
                else check_token(ws, run, k, v, entries, outputs) for k, v in tokens]
        errs = [e for e in errs if e]
        res.add(sid, not errs, "; ".join(errs) or ", ".join(f"{k}:{v.strip('`')[:40]}" for k, v in tokens),
                waivable, waivers)

    # 2. deterministic rules
    def evidence(sid, waivable, path, want, cmd, what):
        cmd, where = cmd
        ev = read_json(path, None)
        if not isinstance(ev, dict):
            res.add(sid, False, f"no evidence for {what} — run `{cmd}` {where}", waivable, waivers)
        elif ev.get("result") != "pass":
            res.add(sid, False, f"{what}: check.py result is {str(ev.get('result')).upper()} — fix, re-run `{cmd}` {where}",
                    waivable, waivers)
        elif want and not (want.startswith(str(ev.get("sha", ""))[:7]) and not ev.get("dirty")):
            res.add(sid, False, f"{what}: evidence is for {str(ev.get('sha'))[:7]}"
                    f"{' (dirty tree)' if ev.get('dirty') else ''}, branch tip is {want[:7]} — commit, re-run `{cmd}` {where}",
                    waivable, waivers)
        else:
            res.add(sid, True, f"{what} PASS @ {str(ev.get('sha'))[:7]}")

    if c.get("outputs") and not outputs:
        res.add("outputs", False, f"no output file matching {', '.join(run.get('outputs') or c['outputs'])}")
    for r in c.get("rules", []):
        kind, rid, waivable = r.get("type"), r.get("id", r.get("type")), bool(r.get("waivable"))
        if r.get("when") == "finish" and not finishing:
            continue
        add = lambda ok, detail, sid=rid: res.add(sid, ok, detail, waivable, waivers)  # noqa: E731
        texts = {f: f.read_text(encoding="utf-8", errors="replace") for f in outputs if f.suffix.lower() in (".md", ".mdx", ".txt")}
        if kind == "approved":
            ok = bool(run.get("decision")) and bool(modules)
            add(ok, "plan approved" if ok else
                "plan not approved or has no `## Module` — confirm every part with the owner, then `state.py approve`")
        elif kind == "evidence" and r.get("final"):
            if int_tip:
                evidence(rid, waivable, rd / r["path"], int_tip,
                         (f"check.py --task {run_id} --unit int", f"in the int/{run_id} worktree"), f"int/{run_id}")
        elif kind == "evidence":
            for u, globs in modules.items():
                if globs:
                    evidence(rid.replace("{unit}", u), waivable, rd / r["path"].replace("{unit}", u), unit_tip[u],
                             (f"check.py --task {run_id} --unit {u}", "in its worktree"), f"module {u}")
        elif kind == "report":
            files = sorted(reports.glob(r["glob"]))
            if not files:
                add(False, f"no reports/{r['glob']} — {r.get('hint', 'write it')}")
                continue
            probs = []
            ftexts = {f: f.read_text(encoding="utf-8", errors="replace") for f in files}
            if r.get("fresh") and final_tip:
                stale = [f.name for f, t in ftexts.items() if not any(final_tip.startswith(x) for x in SHA.findall(t))]
                if stale:
                    probs.append(f"{', '.join(stale)} do not name the current tip {final_tip[:7]} — re-run that pass")
            if r.get("by"):
                for f in files:
                    who = last_writer.get(norm(f.relative_to(ws).as_posix()), (None, 0))[0]
                    if not coordinator:
                        probs.append("who wrote it is unknown (no coordinator in the ledger) — the run must start "
                                     "while the guard hooks are installed")
                        break
                    if who is None:
                        probs.append(f"{f.name}: no ledger record of who wrote it — the {r['by']} writes it itself")
                    elif who == coordinator:
                        probs.append(f"{f.name} was written by the coordinator — dispatch the {r['by']}")
                    elif r.get("not_author") and who in code_writers:
                        probs.append(f"{f.name}: its author also wrote code in this run — dispatch a fresh {r['by']}")
            if r.get("verdict"):
                for f, t in ftexts.items():
                    v = VERDICT.findall(t)
                    got = v[-1].upper().replace(" ", "_") if v else "none"
                    if got != r["verdict"]:
                        nxt = ("fix loop: `state.py round`, re-dispatch the owning devs with the finding ids"
                               if run.get("round", 0) < 2 else
                               "fix-loop limit reached: `state.py status --set blocked`, give the owner options")
                        probs.append(f"{f.name}: verdict {got}, need {r['verdict']} — {nxt}")
            if r.get("citations"):
                for f, t in ftexts.items():
                    refs = citations(t)
                    if len(refs) < r["citations"]:
                        probs.append(f"{f.name}: no `path:line` evidence")
                    elif bad_citations(ws, refs, final_tip):
                        probs.append(f"{f.name}: cited lines not found: {', '.join(bad_citations(ws, refs, final_tip)[:6])}")
            add(not probs, "; ".join(probs) or ", ".join(f.name for f in files))
        elif kind == "scope":
            union = [g for gs in modules.values() for g in gs]
            outside: set[str] = set()
            if base and git(ws, "rev-parse", "--verify", "--quiet", base + "^{commit}"):
                for u, t in unit_tip.items():
                    if t:
                        outside |= {f for f in git(ws, "diff", "--name-only", f"{base}...{t}").splitlines()
                                    if f and is_code(f) and not in_set(f, modules[u])}
                if int_tip:
                    outside |= {f for f in git(ws, "diff", "--name-only", f"{base}...{int_tip}").splitlines()
                                if f and is_code(f) and not in_set(f, union)}
            for e in entries:
                for f in e.get("files", []):
                    m = WT.match(f)
                    u = unit_of(run_id, m.group(1), modules) if m else None
                    if u and not in_set(m.group(2), modules[u]):
                        outside.add(m.group(2))
                    elif not m and is_code(f) and union and not in_set(f, union):
                        outside.add(f)
            shown = sorted(outside)
            add(not shown, f"changed outside the approved write sets: {', '.join(shown[:8])}"
                f"{' …' if len(shown) > 8 else ''} — revert, or re-confirm the module with the owner"
                if shown else "every change inside its write set")
        elif kind == "knowledge":
            changed = bool(code_writers) or any(unit_tip.values())
            wrote = any(f.startswith(".aizen/knowledge/") for e in entries for f in e.get("files", []))
            add(not changed or wrote, "knowledge/ updated" if wrote or not changed else
                "code changed but .aizen/knowledge/ was not updated — record new decisions (decisions.md), module "
                "design/API/data changes (modules/<m>/) and lessons; or waive with evidence that nothing changed")
        elif kind == "command":
            cmd = r["run"]
            out_list = [p for p in outputs] or [None]
            if out_list == [None] and re.search(r"\{output(_dir)?\}", cmd):
                continue  # nothing to check yet: the `outputs` item already says so
            for o in out_list:
                full = (cmd.replace("{skill_dir}", str(SKILLS / run["skill"])).replace("{core_dir}", str(CORE))
                        .replace("{ws}", str(ws)).replace("{run}", run_id)
                        .replace("{output}", str(o) if o else "").replace("{output_dir}", str(o.parent) if o else ""))
                ok, tail = run_rule(ws, run_id, rid, full, outputs)
                add(ok, f"`{r['run'].split()[0]} …` passed" if ok else f"`{full}` failed: {tail}",
                    rid if len(out_list) == 1 else f"{rid}:{o.name}")
        elif kind == "count":
            for f, t in texts.items():
                n = len(mermaid_blocks(t)) if r["what"] == "mermaid" else len(re.findall(r.get("pattern", "$^"), t, re.M))
                ok = n >= r.get("min", 0) and n <= r.get("max", 10 ** 9)
                add(ok, f"{f.name}: {n} {r['what']} (need {r.get('min', 0)}–{r.get('max', '∞')})")
        elif kind == "per_block":
            for f, t in texts.items():
                bad = []
                for i, (start, blk) in enumerate(mermaid_blocks(t), 1):
                    n = mermaid_nodes(blk) if r["what"] == "mermaid_nodes" else caption_lines(t, start)
                    if n > r["max"]:
                        bad.append(f"diagram {i}: {n}")
                add(not bad, f"{f.name}: {r['what']} > {r['max']} in {', '.join(bad)}" if bad
                    else f"{f.name}: every diagram ≤ {r['max']} {r['what']}")
        elif kind == "labels":
            for f, t in texts.items():
                bad = unlabelled_claims(t, c.get("labels", []))
                add(not bad, f"{f.name}: {len(bad)} number claim(s) without a label or source, e.g. “{bad[0]}”"
                    if bad else f"{f.name}: claims labelled")
        elif kind == "sections":
            for f, t in texts.items():
                heads = [h.strip().lower() for h in re.findall(r"^#{1,6}\s+(.+)$", t, re.M)]
                miss = [s for s in r["names"] if not any(h.startswith(s.lower()) for h in heads)]
                add(not miss, f"{f.name}: missing sections {', '.join(miss)}" if miss else f"{f.name}: sections ok")
        elif kind == "regex":
            for f, t in texts.items():
                found = re.search(r["pattern"], t, re.M)
                ok = bool(found) if r.get("must", True) else not found
                add(ok, f"{f.name}: {r.get('hint', r['pattern'])}")

    # 3. waivers: evidence intact, judged by someone else
    verdict = read_json(rd / "verdict.json", {})
    for w in list(res.waived):
        rec = waivers.get(w, {})
        if rec.get("evidence_file"):
            p = ws / rec["evidence_file"]
            if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != rec.get("sha256"):
                res.open.append(f"[waiver {w}] its evidence {rec['evidence_file']} changed or is gone — waive again")
                continue
        judged = (verdict.get("waivers") or {}).get(w, "")
        m = re.findall(rf"waiver\s+`?{re.escape(w)}`?\s*:\s*\**\s*(accepted|rejected)", review_text, re.I)
        judged = judged or (m[-1] if m else "")
        if not judged:
            res.open.append(f"[waiver {w}] not judged yet — the verifier (or reviewer) writes `{w}: accepted|rejected`")
        elif judged.lower() == "rejected":
            res.open.append(f"[waiver {w}] rejected — do the step")

    # 4. the independent verifier, once nothing deterministic is open
    v = c.get("verifier", {})
    if v.get("required") and finishing and all("not judged yet" in i for i in res.open):
        verify(ws, run, c, res, last_writer, code_writers, coordinator, final_tip)

    # 5. at the end of an aizen-build run: waived steps listed for the reader of the PR
    if finishing and res.waived and (rd / "reports").is_dir() and run["skill"] == "aizen-build":
        body = (rd / "reports" / "pr-body.md")
        text = body.read_text(encoding="utf-8") if body.is_file() else ""
        missing = [w for w in res.waived if w not in text]
        if missing:
            res.open.append(f"[waivers] list the waived steps in reports/pr-body.md (## Waived): {', '.join(missing)}")
    return res


def verify(ws, run, c, res, last_writer, code_writers, coordinator, final_tip) -> None:
    rd = run_dir(ws, run["run"])
    p = rd / "verdict.json"
    key = norm(p.relative_to(ws).as_posix())
    exp = {e["id"]: e for e in c.get("expectations", [])}
    if not p.is_file():
        res.add("verifier", False, f"no verdict.json — dispatch a fresh verifier: `guard.py verify-brief --run {run['run']}`")
        return
    who, idx = last_writer.get(key, (None, -1))
    out_keys = {norm(f.relative_to(ws).as_posix()) for f in output_files(ws, run)}
    authors = set(code_writers) | {w for f, (w, _) in last_writer.items() if f in out_keys}
    last_output_write = max([i for f, (_, i) in last_writer.items() if f in out_keys or is_code(f)], default=-1)
    probs = []
    if who is None:
        probs.append("no ledger record of who wrote verdict.json — the verifier writes it with its file tool")
    elif who == coordinator or who in authors:
        probs.append("verdict.json was written by the agent that did the work — dispatch a fresh verifier")
    elif idx < last_output_write:
        probs.append("the outputs changed after the verdict — dispatch the verifier again")
    data = read_json(p, {})
    items = {i.get("id"): i for i in data.get("items", []) if isinstance(i, dict)}
    missing = [e for e in exp if e not in items]
    if missing:
        probs.append(f"verdict.json does not judge {', '.join(missing)}")
    passed, failed = [], []
    for eid in exp:
        it = items.get(eid)
        if not it:
            continue
        refs = citations(str(it.get("evidence", "")))
        if it.get("pass") and not refs:
            failed.append(f"{eid} (passed without `path:line`)")
        elif it.get("pass") and bad_citations(ws, refs, final_tip):
            failed.append(f"{eid} (cites missing lines {', '.join(bad_citations(ws, refs, final_tip)[:3])})")
        elif it.get("pass"):
            passed.append(eid)
        else:
            failed.append(f"{eid}: {str(it.get('note', ''))[:120]}")
    ratio = len(passed) / len(exp) if exp else 1.0
    need = c["verifier"].get("threshold", 0.8)
    if not probs and ratio < need:
        g = guard_state(ws, run["run"])
        digest = hashlib.sha256(p.read_bytes()).hexdigest()[:12]
        seen = g.setdefault("failed_verdicts", [])
        if digest not in seen:
            seen.append(digest)
            save_guard(ws, run["run"], g)
        probs.append(f"verifier: {len(passed)}/{len(exp)} = {ratio:.0%} < {need:.0%} — fix: " + " · ".join(failed[:6])
                     + " — then dispatch the verifier again")
    res.add("verifier", not probs, "; ".join(probs) or f"{len(passed)}/{len(exp)} = {ratio:.0%} ≥ {need:.0%}")


def run_rule(ws: Path, run: str, rid: str, cmd: str, outputs: list[Path]) -> tuple[bool, str]:
    """Run a `command` rule once per state of the outputs; the result is kept as evidence."""
    digest = hashlib.sha256((cmd + "".join(f"{o}:{o.stat().st_mtime_ns}" for o in outputs if o.exists()))
                            .encode()).hexdigest()[:16]
    p = run_dir(ws, run) / "evidence" / f"rule-{re.sub(r'[^A-Za-z0-9._-]', '_', rid)}.json"
    old = read_json(p, {})
    if old.get("digest") == digest:
        return old.get("exit") == 0, old.get("tail", "")
    try:
        r = subprocess.run(cmd, shell=True, cwd=ws, capture_output=True, text=True, timeout=300,
                           encoding="utf-8", errors="replace")
        code, out = r.returncode, (r.stdout or "") + (r.stderr or "")
    except (OSError, subprocess.SubprocessError) as e:
        code, out = 127, str(e)
    tail = " | ".join(out.strip().splitlines()[-4:])[:400]
    write_json(p, {"rule": rid, "cmd": cmd, "exit": code, "tail": tail, "digest": digest, "ts": now()})
    return code == 0, tail


# ── sheet view ───────────────────────────────────────────────────────────────────────────────────────────

def write_sheet(ws: Path, run_id: str, res: Result | None = None) -> None:
    """Steps table (the agent fills; kept as written) + Checks table (rewritten by the guard)."""
    run = all_runs(ws).get(run_id)
    if not run:
        return
    c = contract(run["skill"])
    p = run_dir(ws, run_id) / "sheet.md"
    rows = sheet_rows(ws, run_id)
    lines = [f"# Sheet — {run_id} ({run['skill']})", "",
             f"Goal: {run.get('goal', '')}", "",
             "## Steps — you fill: tick `[x]` and put evidence the guard can check",
             "Evidence: `file:<path>` · `cmd:<command you ran>` · `sha:<commit>` · `out:\"<a line it printed>\"` · "
             "`url:<source cited in the output>`. A tick without evidence, or evidence that does not check out, fails.",
             "", "| Step | Done | Evidence | What counts |", "|---|---|---|---|"]
    for st in c.get("steps", []):
        done, cell = rows.get(st["id"], ("[ ]", ""))
        what = " · ".join(f"{t}:" for t in st.get("evidence", EVIDENCE_TYPES)) + (f" — {st['hint']}" if st.get("hint") else "")
        lines.append(f"| {st['id']} | {done or '[ ]'} | {cell or ''} | {what.replace('|', '/')} |")
    if not c.get("steps"):
        lines.append("| — | — | — | this skill's steps are proven by the checks below |")
    lines += ["", f"## Checks — written by the guard {local_now()}", "", "| Check | Result | Detail |", "|---|---|---|"]
    for sid, state, detail in (res.rows if res else []):
        mark = {"ok": "✅", "open": "❌", "waived": "⚪ waived"}[state]
        lines.append(f"| {sid} | {mark} | {detail.replace('|', '/')[:200]} |")
    write_text(p, "\n".join(lines) + "\n")


# ── run lifecycle ────────────────────────────────────────────────────────────────────────────────────────

def slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:24].strip("-") or "run"


def refresh(ws: Path) -> None:
    """Rebuild .aizen/PROJECT.md; never let it break the caller."""
    try:
        sys.path.insert(0, str(HERE))
        import project  # noqa: PLC0415
        project.build(ws)
    except Exception as e:  # noqa: BLE001
        print(f"(PROJECT.md not rebuilt: {e})", file=sys.stderr)


def log(run: dict, text: str) -> None:
    run.setdefault("log", []).append(f"{local_now()} {text}")


def save_run(ws: Path, run: dict) -> None:
    """run.json; aizen-build runs also get their state.md from state.py's own writer."""
    rid = run["run"]
    if run.get("skill") == "aizen-build" and STATE_PY.is_file():
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("aizen_state", STATE_PY)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            mod.save(ws, rid, run)
            return
        except Exception:  # noqa: BLE001
            pass
    write_json(run_dir(ws, rid) / "run.json", run)
    write_text(run_dir(ws, rid) / "state.md",
               f"# {rid} — {run['status']}\n\nSkill: {run['skill']}\nGoal: {run.get('goal', '')}\n"
               f"Backlog: {run.get('backlog') or '—'}\nOutputs: {', '.join(run.get('outputs', [])) or '—'}\n\n"
               f"## Owner\n{run.get('decision') or '(not confirmed yet)'}\n\n"
               f"## Waiting for the owner\n{run.get('question') or '—'}\n\n"
               "## Log\n" + "\n".join(f"- {e}" for e in run.get("log", [])) + "\n")


def cmd_start(ws: Path, a) -> int:
    if a.skill == "aizen-build":
        print("aizen-build starts with `state.py init --task <ID> --goal …` (it creates the same run)", file=sys.stderr)
        return 2
    if a.skill not in entry_skills():
        print(f"unknown entry skill {a.skill} — one of: {', '.join(entry_skills())}", file=sys.stderr)
        return 2
    c = contract(a.skill)
    rid = a.run or f"{a.skill.replace('aizen-', '')}-{dt.date.today():%Y%m%d}-{slug(a.goal)}"
    if not re.match(r"^[A-Za-z0-9._-]+$", rid):
        print(f"invalid run id {rid!r}", file=sys.stderr)
        return 2
    if (az(ws) / "runs" / rid).exists() or (az(ws) / "archive" / rid).exists():
        print(f"run {rid} exists — `check --run {rid}`", file=sys.stderr)
        return 2
    if a.backlog:
        sys.path.insert(0, str(HERE))
        import project  # noqa: PLC0415
        why = project.can_start(ws, a.backlog)
        if why:
            print(why, file=sys.stderr)
            return 2
    run = {"run": rid, "skill": a.skill, "goal": a.goal, "status": "working" if a.go else "planning", "round": 0,
           "backlog": a.backlog, "outputs": a.output or c.get("outputs", []), "decision": "started with --go" if a.go else None,
           "created": now(), "log": []}
    log(run, f"start {a.skill}" + (f" for {a.backlog}" if a.backlog else ""))
    save_run(ws, run)
    write_sheet(ws, rid)
    if a.backlog:
        import project  # noqa: PLC0415
        project.set_backlog(ws, a.backlog, "doing", rid)
    exclude_local(ws)
    refresh(ws)
    print(f"run {rid} · {run['status']} · sheet: {(run_dir(ws, rid) / 'sheet.md').relative_to(ws).as_posix()}")
    if run["status"] == "planning":
        print(f"confirm the goal with the owner, then: guard.py go --run {rid} --text \"<their answer>\"")
    return 0


def set_status(ws: Path, rid: str, status: str, text: str, **extra) -> int:
    run = all_runs(ws).get(rid)
    if not run:
        print(f"no run {rid}", file=sys.stderr)
        return 2
    run.update(status=status, **extra)
    log(run, text)
    save_run(ws, run)
    refresh(ws)
    return 0


def cmd_done(ws: Path, rid: str, quiet: bool = False) -> tuple[bool, Result]:
    """The only way a run becomes `done`: every check passes. Then archive and close its backlog item."""
    res = evaluate(ws, rid, finishing=True)
    write_sheet(ws, rid, res)
    if res.open:
        if not quiet:
            for i in res.open:
                print(f"OPEN    {i}")
        return False, res
    run = all_runs(ws)[rid]
    g = guard_state(ws, rid)
    g.update(passed=True, blocks=0, idle=0)
    save_guard(ws, rid, g)
    if run["status"] != "done":
        run["status"] = "done"
        log(run, "guard: every check passed — done")
        save_run(ws, run)
    if run.get("backlog"):
        sys.path.insert(0, str(HERE))
        import project  # noqa: PLC0415
        project.set_backlog(ws, run["backlog"], "done", rid)
    src = az(ws) / "runs" / rid
    if src.exists() and run["skill"] != "aizen-init":
        dst = az(ws) / "archive" / rid
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.exists():
            shutil.move(str(src), str(dst))
    refresh(ws)
    if not quiet:
        print(f"{rid}: done · archived")
    return True, res


def cmd_waive(ws: Path, rid: str, step: str, reason: str, evidence: str) -> int:
    run = all_runs(ws).get(rid)
    if not run:
        print(f"no run {rid}", file=sys.stderr)
        return 2
    c = contract(run["skill"])
    items = {s["id"]: s for s in c.get("steps", [])} | {r.get("id", r.get("type")): r for r in c.get("rules", [])}
    key = step if step in items else re.sub(r"-[A-Za-z0-9._]+$", "-{unit}", step)
    if key not in items:
        print(f"unknown step {step} — one of: {', '.join(sorted(k for k, v in items.items() if v.get('waivable')))}",
              file=sys.stderr)
        return 2
    if not items[key].get("waivable"):
        print(f"{step} cannot be waived", file=sys.stderr)
        return 2
    if len(reason.strip()) < 15:
        print("give a real reason (≥ 15 characters)", file=sys.stderr)
        return 2
    rec = {"reason": reason.strip(), "ts": now()}
    f = ws / evidence if evidence else None
    if f and f.is_file():
        rec.update(evidence_file=f.resolve().relative_to(ws.resolve()).as_posix(),
                   sha256=hashlib.sha256(f.read_bytes()).hexdigest())
    elif len(evidence.strip()) >= 10:
        rec["evidence"] = evidence.strip()
    else:
        print("--evidence: a file in the project (hashed) or one line of real output/commit/hash (≥ 10 characters)",
              file=sys.stderr)
        return 2
    p = run_dir(ws, rid) / "waivers.json"
    w = read_json(p, {})
    w[step] = rec
    write_json(p, w)
    refresh(ws)
    print(f"waived {step} — counts once the verifier (or reviewer) writes `{step}: accepted`")
    return 0


def cmd_verify_brief(ws: Path, rid: str) -> int:
    run = all_runs(ws).get(rid)
    if not run:
        print(f"no run {rid}", file=sys.stderr)
        return 2
    c = contract(run["skill"])
    rd = run_dir(ws, rid)
    waivers = read_json(rd / "waivers.json", {})
    outs = [f.relative_to(ws).as_posix() for f in output_files(ws, run)]
    print((CORE / "references" / "core" / "verifier.md").read_text(encoding="utf-8").split("<!-- brief -->", 1)[-1].strip())
    print(f"\n## This run\nRUN={rid}  SKILL={run['skill']}  GOAL={run.get('goal', '')}")
    print(f"Outputs to judge: {', '.join(outs) or '(see the run folder)'}")
    print(f"Write your verdict to: {(rd / 'verdict.json').relative_to(ws).as_posix()}")
    print(f"Threshold: {c['verifier'].get('threshold', 0.8):.0%} of the expectations below\n\n## Expectations")
    for e in c.get("expectations", []):
        print(f"- {e['id']}: {e['text']}")
    if waivers:
        print("\n## Waived steps to judge (accepted | rejected)")
        for k, v in waivers.items():
            print(f"- {k}: {v.get('reason')} · evidence: {v.get('evidence_file') or v.get('evidence')}")
    return 0


# ── hooks ────────────────────────────────────────────────────────────────────────────────────────────────

def rel(ws: Path, f: str, cwd: Path) -> str:
    p = Path(f)
    p = p if p.is_absolute() else cwd / p
    try:
        return p.resolve().relative_to(ws.resolve()).as_posix()
    except ValueError:
        return p.as_posix()


def parse(agent: str, payload: dict) -> dict:
    """Normalise a Claude Code or Antigravity payload."""
    if agent == "claude":
        tool = payload.get("tool_name", "")
        args = payload.get("tool_input") or {}
        session = payload.get("session_id", "")
        writer = session + (f"/{payload['agent_id']}" if payload.get("agent_id") else "")
        cwd = payload.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        writes = tool in CLAUDE_WRITE
        files = [args[k] for k in ("file_path", "notebook_path") if isinstance(args.get(k), str)]
        resp = payload.get("tool_response") or {}
        resp = resp if isinstance(resp, dict) else {"stdout": str(resp)}
        out = str(resp.get("stdout", "")) + str(resp.get("stderr", ""))
        code = resp.get("exit_code", resp.get("exitCode", resp.get("returnCode")))
        failed = bool(resp.get("interrupted")) or bool(resp.get("is_error")) or (code not in (None, 0))
        new_text = " ".join(str(args.get(k, "")) for k in ("content", "new_string")) + \
            " ".join(str(e.get("new_string", "")) for e in args.get("edits", []) if isinstance(e, dict))
    else:
        call = payload.get("toolCall") or {}
        tool = call.get("name", "")
        args = call.get("args") or {}
        session = payload.get("conversationId", "")
        writer = session  # an Antigravity sub-agent runs in its own conversation
        paths = payload.get("workspacePaths") or []
        cwd = args.get("Cwd") or (paths[0] if paths else os.getcwd())
        writes = bool(AGY_WRITE.search(tool)) and tool not in SHELL_TOOLS
        files = []
        for k, v in args.items():
            if re.search(r"file|path|target", k, re.I) and k.lower() != "cwd":
                files += [v] if isinstance(v, str) else [x for x in v if isinstance(x, str)] if isinstance(v, list) else []
        out, failed = "", bool(payload.get("error"))
        new_text = " ".join(str(v) for k, v in args.items() if isinstance(v, str) and not re.search(r"file|path", k, re.I))
    cmd = next((args[k] for k in ("command", "CommandLine", "commandLine", "cmd") if isinstance(args.get(k), str)), "")
    return {"tool": tool, "session": session, "writer": writer, "cwd": Path(cwd), "writes": writes, "files": files,
            "cmd": cmd, "out": out[-2000:], "failed": failed, "new_text": new_text, "error": str(payload.get("error") or "")[:200]}


def deny_reason(ws: Path, ev: dict, files: list[str]) -> str | None:
    if ev["writes"] and any(PROTECTED.search(f) for f in files):
        return ("guard-owned file (run.json, ledger, waivers, evidence, PROJECT.md): only the Aizen scripts write it "
                "— run the script instead")
    cmd = ev["cmd"]
    if cmd and re.search(r"\bbacklog\s+approve\b", cmd):
        return "only the owner approves backlog items (`aizen backlog approve` in their own terminal)"
    if cmd and not OWN_SCRIPTS.search(cmd) and ".aizen" in cmd and any(n in cmd for n in PROTECTED_NAMES) \
            and MUTATES.search(cmd):
        return "this command would change a guard-owned file under .aizen/ — use the Aizen scripts"
    if not ev["writes"]:
        return None
    if any(f == ".aizen/backlog.md" for f in files) and APPROVED.search(ev["new_text"] or ""):
        return "you may propose backlog items (status `proposed`); only the owner approves them"
    runs = live(ws)
    code = [f for f in files if is_code(f)]
    for rid, run in runs.items():
        outs = [g.replace("{run}", rid) for g in run.get("outputs", [])]
        if run["status"] in ("planning", "waiting") and not run.get("decision"):
            if run["skill"] == "aizen-build":
                modules, _, ui = plan(ws, rid)
                early = [f for f in code if not any(WT.match(f) and WT.match(f).group(1) == f"{rid}-{u}" for u in ui)]
                others = any(r["skill"] == "aizen-build" and r.get("decision") for r in runs.values())
                if early and not others:
                    return (f"run {rid}: the plan is not approved — no code before `state.py approve` (abandoned? "
                            f"`guard.py stop --run {rid} --reason …`)")
            elif any(fnmatch.fnmatch(f, g) for f in files for g in outs):
                return f"run {rid} is still {run['status']} — confirm with the owner, then `guard.py go --run {rid}`"
        if run["skill"] == "aizen-build":
            modules, _, _ = plan(ws, rid)
            for f in code:
                m = WT.match(f)
                u = unit_of(rid, m.group(1), modules) if m else None
                if u and modules[u] and not in_set(m.group(2), modules[u]):
                    return (f"{m.group(2)} is outside the write set of module {u} ({', '.join(modules[u])}) — "
                            "list it under HANDOFF: in your report, or return BLOCKED")
    for skill in entry_skills():
        for g in contract(skill).get("outputs", []):
            if "{" not in g and any(fnmatch.fnmatch(f, g) for f in files) and \
                    not any(r["skill"] == skill and r["status"] not in ("planning", "waiting") for r in runs.values()):
                return (f"{', '.join(files)} is an output of {skill} — start a run first: "
                        f"guard.py start --skill {skill} --goal \"…\"")
    if config(ws).get("require_task") and code and not any(r.get("decision") for r in runs.values()):
        return "this project requires an approved Aizen run before code changes (.aizen/config/guard.json)"
    return None


def hook(event: str, agent: str, payload: dict) -> tuple[dict | None, str]:
    ev = parse(agent, payload)
    ws = find_ws(ev["cwd"])
    if ws is None:
        return None, "no .aizen/"
    files = [rel(ws, f, ev["cwd"]) for f in ev["files"]]

    if event == "pre":
        reason = deny_reason(ws, ev, files)
        if not reason:
            return None, "allow"
        reason = "Aizen guard: " + reason
        if agent == "claude":
            return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                           "permissionDecisionReason": reason}}, reason
        return {"decision": "deny", "reason": reason}, reason

    if event == "post":
        if not (ev["writes"] or ev["cmd"]):
            return None, "skip"
        starting = re.search(r"(guard\.py[\"']?\s+start|state\.py[\"']?\s+init)\b", ev["cmd"])
        for rid, run in live(ws).items():
            append(ws, rid, {"ts": now(), "agent": agent, "writer": ev["writer"], "tool": ev["tool"],
                             "files": files if ev["writes"] else [], "cmd": ev["cmd"][:400], "out": ev["out"],
                             "failed": ev["failed"], "error": ev["error"]})
            g = guard_state(ws, rid)
            if starting and not g.get("coordinator"):
                created = run.get("created")
                fresh = not created or (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(created)).total_seconds() < 300
                if fresh:
                    g["coordinator"] = ev["writer"]
                    save_guard(ws, rid, g)
        if OWN_SCRIPTS.search(ev["cmd"]):
            refresh(ws)
        return None, "recorded"

    # stop
    blocks = []
    for rid, run in watched(ws).items():
        g = guard_state(ws, rid)
        if g.get("coordinator") and ev["writer"] and g["coordinator"] != ev["writer"]:
            continue  # a sub-agent stopping, not the coordinator
        if run["status"] in FREE:
            continue
        ok, res = cmd_done(ws, rid, quiet=True)
        if ok:
            continue
        size = len(ledger(ws, rid))
        g = guard_state(ws, rid)
        g["idle"] = g.get("idle", 0) + 1 if size == g.get("ledger_size", -1) else 0
        g.update(blocks=g.get("blocks", 0) + 1, ledger_size=size)
        rounds = contract(run["skill"]).get("verifier", {}).get("rounds", 2)
        if g["idle"] >= MAX_IDLE or g["blocks"] >= MAX_BLOCKS or len(g.get("failed_verdicts", [])) > rounds:
            g.update(blocks=0, idle=0)
            save_guard(ws, rid, g)
            set_status(ws, rid, "blocked", "guard: stopped retrying — open: " + "; ".join(res.open)[:500])
            continue
        save_guard(ws, rid, g)
        blocks.append(message(rid, res.open))
    if not blocks:
        return None, "stop allowed"
    reason = "\n\n".join(blocks)
    return ({"decision": "block", "reason": reason} if agent == "claude"
            else {"decision": "continue", "reason": reason}), reason


def message(rid: str, open_items: list[str]) -> str:
    g = Path(__file__).resolve().as_posix()
    return (f"Aizen guard: run {rid} is not finished — do not stop yet. Open items:\n"
            + "\n".join(f"- {i}" for i in open_items)
            + f"\nDo exactly these, nothing more. The sheet: .aizen/runs/{rid}/sheet.md. A step that truly does not "
              f'apply: uv run "{g}" waive --run {rid} --step <id> --reason "<why>" --evidence <file | real output>. '
              f'Need the owner: uv run "{g}" ask --run {rid} --question "<one question>".')


# ── git pre-push ─────────────────────────────────────────────────────────────────────────────────────────

def cmd_prepush(ws: Path, stdin: str) -> int:
    names = set(all_runs(ws))
    failed = 0
    for line in stdin.splitlines():
        parts = line.split()
        if len(parts) < 2 or set(parts[1]) == {"0"}:
            continue
        ref = parts[0].replace("refs/heads/", "")
        rid = None
        if ref.startswith("int/") and ref[4:] in names:
            rid = ref[4:]
        elif ref.startswith("feature/"):
            rid = max((n for n in names if ref[8:].startswith(n + "-")), key=len, default=None)
        if not rid:
            continue
        run = all_runs(ws)[rid]
        res = evaluate(ws, rid)
        if run["status"] != "done":
            res.open.insert(0, f"[status] run is {run['status']}, not done")
        if res.open:
            failed += 1
            print(f"Aizen guard: {ref} not pushed — run {rid}:\n" + "\n".join(f"  - {i}" for i in res.open), file=sys.stderr)
            write_json(az(ws) / "cache" / "prepush.json", {"ts": now(), "ref": ref, "run": rid, "open": res.open})
    return 1 if failed else 0


# ── install, migrate ─────────────────────────────────────────────────────────────────────────────────────

def exclude_local(ws: Path) -> list[str]:
    common = git(ws, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if not common:
        return []
    share = config(ws).get("share_knowledge")
    want = ([".aizen/*", "!.aizen/knowledge/", "!.aizen/PROJECT.md"] if share else [".aizen/"]) + \
        [".claude/settings.local.json", ".agents/hooks.json"]
    exclude = Path(common) / "info" / "exclude"
    have = exclude.read_text(encoding="utf-8").splitlines() if exclude.is_file() else []
    if share and ".aizen/" in have:
        have = [h for h in have if h != ".aizen/"]
        write_text(exclude, "\n".join(have) + "\n")
    add = [e for e in want if e not in have]
    if add:
        exclude.parent.mkdir(parents=True, exist_ok=True)
        with exclude.open("a", encoding="utf-8") as f:
            f.write(("\n" if have and have[-1] else "") + "\n".join(add) + "\n")
    return add


def cmd_migrate(ws: Path) -> list[str]:
    """Move the v24 layout (.aizen/tasks, plans, reports, docs, init, .worktrees, .aizen-work) into v25."""
    a, done = az(ws), []

    def mv(src: Path, dst: Path) -> None:
        if src.exists() and not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            done.append(f"{src.relative_to(ws)} → {dst.relative_to(ws)}")

    for t in sorted((a / "tasks").glob("*")) if (a / "tasks").is_dir() else []:
        rd = a / "runs" / t.name
        for f in t.iterdir():
            mv(f, rd / f.name)
        mv(a / "plans" / f"{t.name}.md", rd / "plan.md")
        rep = a / "reports" / t.name
        if rep.is_dir():
            for f in rep.iterdir():
                m = re.match(r"^evidence(?:-(.+))?\.json$", f.name)
                mv(f, rd / "evidence" / f"{m.group(1) or 'main'}.json" if m else rd / "reports" / f.name)
        run = read_json(rd / "run.json", None)
        if isinstance(run, dict):
            run.setdefault("run", t.name)
            run.setdefault("skill", "aizen-build")
            run.setdefault("outputs", [])
            write_json(rd / "run.json", run)
    mv(a / "init", a / "runs" / "init")
    for name, dst in (("docs", "knowledge"), ("lessons.md", "knowledge/lessons.md"),
                      ("conventions.md", "config/conventions.md"), ("guard.json", "config/guard.json")):
        mv(a / name, a / dst)
    mv(a / "knowledge" / "DECISIONS.md", a / "knowledge" / "decisions.md")
    mv(ws / ".aizen-work" / "feedback", a / "knowledge" / "feedback")
    for old in sorted((ws / ".aizen-work").glob("*")) if (ws / ".aizen-work").is_dir() else []:
        mv(old, a / "cache" / "eval" / old.name)
    if (ws / ".worktrees").is_dir():
        for w in sorted((ws / ".worktrees").iterdir()):
            task = next((t for t in sorted(all_runs(ws), key=len, reverse=True)
                         if subprocess.run(["git", "-C", str(w), "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True,
                                           text=True).stdout.strip().startswith(f"feature/{t}-")), None)
            dst = a / "worktrees" / (f"{task}-{w.name}" if task else w.name)
            dst.parent.mkdir(parents=True, exist_ok=True)
            if subprocess.run(["git", "-C", str(ws), "worktree", "move", str(w), str(dst)], capture_output=True).returncode == 0:
                done.append(f".worktrees/{w.name} → {dst.relative_to(ws)}")
            else:
                done.append(f"! .worktrees/{w.name} not moved (uncommitted changes?) — `git worktree move` it yourself")
    for d in ("tasks", "plans", "reports"):
        p = a / d
        if p.is_dir() and not any(f.is_file() for f in p.rglob("*")):
            shutil.rmtree(p)
    return done


def scaffold(ws: Path) -> None:
    a = az(ws)
    for d in ("config", "knowledge/system", "knowledge/modules", "runs", "archive", "worktrees", "cache", "backups"):
        (a / d).mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(HERE))
    import project  # noqa: PLC0415
    project.ensure_backlog(ws)
    if not (a / "config" / "guard.json").exists():
        write_json(a / "config" / "guard.json", {"require_task": False, "share_knowledge": False})


UV_HINT = ("uv not found on PATH. Aizen runs its scripts with uv (it fetches Python by itself):\n"
           "  Windows: winget install astral-sh.uv   ·   macOS/Linux: curl -LsSf https://astral.sh/uv/install.sh | sh\n"
           "then open a new terminal (restart the agent app) and run this install again.")


def guard_entry(ws: Path) -> str:
    """Path of this script as the project sees it — the copy under the project's skill folder, not the place a
    junction resolves to — so hooks keep working after the source repo moves (moving the project: install again)."""
    for base in (".agents/skills", ".claude/skills"):
        p = ws / base / "aizen-core" / "scripts" / "core" / "guard.py"
        if p.is_file():
            return p.absolute().as_posix()
    return Path(__file__).resolve().as_posix()


def install_rules(ws: Path) -> list[str]:
    """Session rules shipped in aizen-core/rules → each agent the project has skills for. Antigravity needs a
    `trigger` front-matter or it ignores the file; Claude Code reads plain Markdown."""
    src = sorted((HERE.parent.parent / "rules").glob("*.md"))
    done = []
    for skills, rules, head in ((".agents/skills", ".agents/rules", "---\ntrigger: always_on\n---\n"),
                                (".claude/skills", ".claude/rules", "")):
        if not (ws / skills).is_dir() or not src:
            continue
        d = ws / rules
        d.mkdir(parents=True, exist_ok=True)
        for f in src:
            (d / f"aizen-{f.name}").write_text(head + f.read_text(encoding="utf-8"), encoding="utf-8")
        done.append(f"{rules}/ ({len(src)})")
    return done


def cmd_install(ws: Path) -> int:
    ws = ws.resolve()
    if not shutil.which("uv"):
        print(f"✗ {UV_HINT}", file=sys.stderr)
        return 3
    me = guard_entry(ws)
    call = lambda ev, agent: f'uv run --quiet --script "{me}" hook {ev} --agent {agent}'  # noqa: E731
    moved = cmd_migrate(ws) if (ws / ".aizen").is_dir() else []
    scaffold(ws)
    for m in moved:
        print(f"↪ {m}")

    cp = ws / ".claude" / "settings.local.json"
    cs = read_json(cp, {})
    hooks = cs.setdefault("hooks", {})
    for event, matcher, ev in (("PreToolUse", "Write|Edit|MultiEdit|NotebookEdit|Bash", "pre"),
                               ("PostToolUse", "Write|Edit|MultiEdit|NotebookEdit|Bash", "post"),
                               ("Stop", None, "stop")):
        keep = [h for h in hooks.get(event, []) if not any("guard.py" in x.get("command", "") and " hook " in x.get("command", "")
                                                          for x in h.get("hooks", []))]
        entry = {"hooks": [{"type": "command", "command": call(ev, "claude"), "timeout": 120}]}
        hooks[event] = keep + [{"matcher": matcher, **entry} if matcher else entry]
    write_json(cp, cs)
    ap_ = ws / ".agents" / "hooks.json"
    ag = read_json(ap_, {})
    ag["aizen-guard"] = {
        "enabled": True,
        "PreToolUse": [{"matcher": "*", "hooks": [{"type": "command", "command": call("pre", "agy"), "timeout": 30}]}],
        "PostToolUse": [{"matcher": "*", "hooks": [{"type": "command", "command": call("post", "agy"), "timeout": 30}]}],
        "Stop": [{"hooks": [{"type": "command", "command": call("stop", "agy"), "timeout": 120}]}],
    }
    write_json(ap_, ag)
    print(f"✓ Claude Code hooks → {cp}")
    print(f"✓ Antigravity hooks → {ap_}")
    for r in install_rules(ws):
        print(f"✓ session rules → {r}")
    refresh(ws)
    print(f"✓ project map → {az(ws) / 'PROJECT.md'}")
    hooks_dir = git(ws, "rev-parse", "--path-format=absolute", "--git-path", "hooks")
    if not hooks_dir:
        print("· not a git repository — no pre-push hook")
        return 0
    exclude_local(ws)
    pp = Path(hooks_dir) / "pre-push"
    script = f'#!/bin/sh\n# aizen-guard\nexec uv run --quiet --script "{me}" prepush --workspace "$(git rev-parse --show-toplevel)"\n'
    if pp.is_file() and "aizen-guard" not in pp.read_text(encoding="utf-8", errors="replace"):
        print(f"! {pp} exists and is not Aizen's — add this line to it yourself:\n  {script.splitlines()[-1]}")
    else:
        pp.parent.mkdir(parents=True, exist_ok=True)
        pp.write_text(script, encoding="utf-8")
        pp.chmod(0o755)
        print(f"✓ git pre-push → {pp}")
    return 0


# ── CLI ──────────────────────────────────────────────────────────────────────────────────────────────────

def main(argv=None) -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    h = sub.add_parser("hook")
    h.add_argument("event", choices=("pre", "post", "stop"))
    h.add_argument("--agent", choices=("claude", "agy"), required=True)
    p = {n: sub.add_parser(n) for n in ("start", "ask", "go", "check", "waive", "verify-brief", "done", "stop",
                                        "backlog", "install", "migrate", "prepush")}
    for n, q in p.items():
        q.add_argument("--workspace", default=".")
        if n in ("ask", "go", "check", "waive", "verify-brief", "done", "stop"):
            q.add_argument("--run", "--task", dest="run", required=True)
    p["start"].add_argument("--skill", required=True)
    p["start"].add_argument("--goal", required=True)
    p["start"].add_argument("--run")
    p["start"].add_argument("--backlog")
    p["start"].add_argument("--output", action="append", help="output file or glob (repeatable)")
    p["start"].add_argument("--go", action="store_true", help="nothing to confirm with the owner: start working")
    p["ask"].add_argument("--question", required=True)
    p["go"].add_argument("--text", required=True)
    p["stop"].add_argument("--reason", required=True)
    for k in ("--step", "--reason", "--evidence"):
        p["waive"].add_argument(k, required=True)
    p["backlog"].add_argument("action", choices=("add", "approve", "drop", "list"))
    p["backlog"].add_argument("id", nargs="?")
    p["backlog"].add_argument("--title")
    p["backlog"].add_argument("--skill", default="aizen-build")
    p["backlog"].add_argument("--after", default="")
    a = ap.parse_args(argv)

    if a.cmd == "hook":
        try:
            raw = sys.stdin.read()
            out, _ = hook(a.event, a.agent, json.loads(raw) if raw.strip() else {})
        except Exception as e:  # noqa: BLE001 — fail open
            print(f"aizen guard error (allowed): {e}", file=sys.stderr)
            out = None
        if out is not None:
            print(json.dumps(out, ensure_ascii=False))
        elif a.agent == "agy":
            print("{}")
        return 0
    ws = Path(a.workspace)
    if a.cmd == "install":
        return cmd_install(ws)
    root = find_ws(ws)
    if a.cmd == "prepush":
        return cmd_prepush(root, sys.stdin.read()) if root else 0
    if a.cmd == "start" and root is None:
        root = ws.resolve()
        scaffold(root)
    if root is None:
        print(f"no .aizen/ at or above {ws.resolve()} — run `guard.py install` first", file=sys.stderr)
        return 2
    if a.cmd == "migrate":
        for m in cmd_migrate(root):
            print(m)
        scaffold(root)
        refresh(root)
        return 0
    if a.cmd == "start":
        return cmd_start(root, a)
    if a.cmd == "ask":
        return set_status(root, a.run, "waiting", f"asked the owner: {a.question}", question=a.question)
    if a.cmd == "go":
        run = all_runs(root).get(a.run)
        if run and run["skill"] == "aizen-build":
            print("aizen-build is approved with `state.py approve`", file=sys.stderr)
            return 2
        return set_status(root, a.run, "working", f"owner: {a.text}", decision=f"{local_now()} {a.text}", question=None)
    if a.cmd == "stop":
        return set_status(root, a.run, "stopped", f"stopped: {a.reason}", stop_reason=a.reason)
    if a.cmd == "check":
        res = evaluate(root, a.run)
        write_sheet(root, a.run, res)
        for sid, state, detail in res.rows:
            print(f"{state.upper():7} {sid}: {detail}")
        for i in res.open:
            if not any(i.startswith(f"[{sid}]") for sid, s, _ in res.rows if s == "open"):
                print(f"OPEN    {i}")
        print(f"{a.run}: {'PASS' if not res.open else f'{len(res.open)} open item(s)'}")
        return 0 if not res.open else 1
    if a.cmd == "waive":
        return cmd_waive(root, a.run, a.step, a.reason, a.evidence)
    if a.cmd == "verify-brief":
        return cmd_verify_brief(root, a.run)
    if a.cmd == "done":
        return 0 if cmd_done(root, a.run)[0] else 1
    sys.path.insert(0, str(HERE))
    import project  # noqa: PLC0415
    return project.backlog_cli(root, a)


if __name__ == "__main__":
    if sys.argv[1:] == ["--selfcheck"]:
        sys.path.insert(0, str(HERE))
        import guard_selfcheck  # noqa: PLC0415
        guard_selfcheck.run()
    else:
        sys.exit(main())
