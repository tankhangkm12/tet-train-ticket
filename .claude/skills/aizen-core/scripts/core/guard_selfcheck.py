# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Self-check for guard.py and project.py — `python guard.py --selfcheck` / `python project.py --selfcheck`.

Builds throw-away git projects and walks a run of aizen-build and of a file-producing skill through the hooks.
"""
from __future__ import annotations

import contextlib
import io
import subprocess
import tempfile
import sys
from pathlib import Path

import guard as G
import project as P


def sh(ws, *args):
    subprocess.run(["git", "-C", str(ws), "-c", "user.email=a@b", "-c", "user.name=a", *args],
                   check=True, capture_output=True)


def quiet(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return fn(*a, **k)


def repo(tmp: str) -> Path:
    ws = Path(tmp)
    sh(ws, "init", "-q", "-b", "main")
    (ws / "README.md").write_text("x")
    sh(ws, "add", ".")
    sh(ws, "commit", "-q", "-m", "base")
    quiet(G.scaffold, ws)
    return ws


def claude(ws, tool, inp, agent=None, resp=None):
    p = {"session_id": "S1", "cwd": str(ws), "tool_name": tool, "tool_input": inp}
    if agent:
        p["agent_id"] = agent
    if resp is not None:
        p["tool_response"] = resp
    return p


def stop(ws, agent=None):
    p = {"session_id": "S1", "cwd": str(ws)}
    if agent:
        p["agent_id"] = agent
    return G.hook("stop", "claude", p)


def build_run() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        ws = repo(tmp)
        base = G.git(ws, "rev-parse", "HEAD")
        T = "T-1"
        rd = G.az(ws) / "runs" / T
        G.write_json(rd / "run.json", {"run": T, "skill": "aizen-build", "goal": "g", "status": "planning", "round": 0,
                                       "agreed": {}, "decision": None, "outputs": [], "created": G.now(), "log": []})
        (rd / "plan.md").write_text(f"# {T}\n> Plan v1 · Base: `main` @ `{base[:7]}`\n## Scope\n"
                                    "## Module api — API   kind be\nFiles (write set): `src/api/**`\n"
                                    "## Module measure — read-only\nFiles (write set): —\n## Delivery\n")
        # pre: no code before approval; guard-owned files never; the owner approves backlog items
        out, _ = G.hook("pre", "claude", claude(ws, "Edit", {"file_path": str(ws / "src/api/a.py")}))
        assert out["hookSpecificOutput"]["permissionDecision"] == "deny", out
        assert G.hook("pre", "claude", claude(ws, "Write", {"file_path": str(rd / "plan.md")}))[0] is None
        assert G.hook("pre", "claude", claude(ws, "Edit", {"file_path": str(rd / "run.json")}))[0]
        assert G.hook("pre", "claude", claude(ws, "Write", {"file_path": str(ws / ".aizen/PROJECT.md")}))[0]
        assert G.hook("pre", "claude", claude(ws, "Bash", {"command": "echo {} > .aizen/runs/T-1/evidence/api.json"}))[0]
        assert G.hook("pre", "claude", claude(ws, "Bash", {"command": "python guard.py backlog approve BL-01"}))[0]
        assert G.hook("pre", "claude", claude(ws, "Edit", {"file_path": str(ws / ".aizen/backlog.md"),
                                                           "new_string": "| BL-01 | x | aizen-build | approved | — | — |"}))[0]
        agy = {"conversationId": "C1", "workspacePaths": [str(ws)],
               "toolCall": {"name": "write_to_file", "args": {"TargetFile": str(ws / "src/api/a.py")}}}
        assert G.hook("pre", "agy", agy)[0]["decision"] == "deny"
        # post: ledger + coordinator from `state.py init`
        G.hook("post", "claude", claude(ws, "Bash", {"command": f'python "/x/state.py" init --task {T} --goal g'}))
        assert G.guard_state(ws, T)["coordinator"] == "S1" and len(G.ledger(ws, T)) == 1
        assert stop(ws)[0] is None  # planning: asking the owner is the job
        # approved → write sets enforced in worktrees
        run = G.read_json(rd / "run.json", {})
        run.update(status="building", decision="ok")
        G.write_json(rd / "run.json", run)
        assert G.hook("pre", "claude", claude(ws, "Edit", {"file_path": str(ws / f".aizen/worktrees/{T}-api/src/api/a.py")}))[0] is None
        out, _ = G.hook("pre", "claude", claude(ws, "Edit", {"file_path": str(ws / f".aizen/worktrees/{T}-api/src/b/x.py")}))
        assert "write set of module api" in out["hookSpecificOutput"]["permissionDecisionReason"]
        # the unit branch, with one file outside its write set
        sh(ws, "checkout", "-q", "-b", f"feature/{T}-api")
        for f in ("src/api/a.py", "src/util/extra.py"):
            (ws / f).parent.mkdir(parents=True, exist_ok=True)
            (ws / f).write_text("x")
        sh(ws, "add", "src")
        sh(ws, "commit", "-q", "-m", "api")
        unit = G.git(ws, "rev-parse", "HEAD")
        sh(ws, "checkout", "-q", "main")
        out, why = stop(ws)
        assert out["decision"] == "block" and "[check-api]" in why and "[review]" in why and "measure" not in why, why
        assert "src/util/extra.py" in why and "[knowledge]" in why, why
        assert stop(ws, agent="sub")[0] is None  # a sub-agent stopping
        G.hook("post", "claude", claude(ws, "Bash", {"command": "ls"}))
        assert G.hook("stop", "agy", {"conversationId": "S1", "workspacePaths": [str(ws)]})[0]["decision"] == "continue"
        # evidence at the tip; reports from the roles' own sessions with real citations
        G.write_json(rd / "evidence" / "api.json", {"result": "pass", "sha": unit[:12], "dirty": False})
        rep = rd / "reports"
        rep.mkdir()

        def report(agent, name, text):
            (rep / name).write_text(text)
            G.hook("post", "claude", claude(ws, "Write", {"file_path": str(rep / name)}, agent=agent))

        report("tst", "test.md", f"all green @ {unit[:7]}")
        report(None, "review.md", f"@ {unit[:7]} src/api/a.py:1\nVerdict: PASS\n")
        assert any("written by the coordinator" in i for i in G.evaluate(ws, T).open)
        report("rev", "review.md", f"@ {unit[:7]} src/api/a.py:1\nVerdict: CHANGES_REQUIRED\n")
        assert any("verdict CHANGES_REQUIRED" in i for i in G.evaluate(ws, T).open)
        report("rev", "review.md", f"@ {unit[:7]}: src/api/a.py:99\nVerdict: PASS\n")
        assert any("src/api/a.py:99" in i for i in G.evaluate(ws, T).open)
        G.hook("post", "claude", claude(ws, "Edit", {"file_path": str(ws / f".aizen/worktrees/{T}-api/src/api/a.py")}, agent="dev1"))
        report("dev1", "review.md", f"@ {unit[:7]}: src/api/a.py:1\nVerdict: PASS\n")
        assert any("also wrote code" in i for i in G.evaluate(ws, T).open)
        report("rev", "review.md", f"@ {unit[:7]}: src/api/a.py:1\nVerdict: PASS\n")
        left = G.evaluate(ws, T).open
        assert {i.split("]")[0] for i in left} == {"[scope", "[knowledge", "[pr-body"}, left
        # knowledge updated by the run; scope waived with evidence, accepted by the reviewer
        (ws / ".aizen/knowledge/decisions.md").write_text("D-01 coupon api\n")
        G.hook("post", "claude", claude(ws, "Write", {"file_path": str(ws / ".aizen/knowledge/decisions.md")}))
        assert quiet(G.cmd_waive, ws, T, "review", "the reviewer agreed it is fine", "x" * 12) == 2
        assert quiet(G.cmd_waive, ws, T, "scope", "shared helper the owner asked for", "ok") == 2
        (ws / ".aizen/knowledge/owner-note.md").write_text("owner: helper goes to src/util")
        assert quiet(G.cmd_waive, ws, T, "scope", "shared helper the owner asked for", ".aizen/knowledge/owner-note.md") == 0
        assert any("not judged yet" in i for i in G.evaluate(ws, T).open)
        report("rev", "review.md", f"@ {unit[:7]}: src/api/a.py:1\nwaiver scope: rejected — no\nVerdict: PASS\n")
        assert any("rejected" in i for i in G.evaluate(ws, T).open)
        report("rev", "review.md", f"@ {unit[:7]}: src/api/a.py:1\nwaiver scope: accepted — owner note\nVerdict: PASS\n")
        assert {i.split("]")[0] for i in G.evaluate(ws, T).open} == {"[pr-body", "[waivers"}, G.evaluate(ws, T).open
        (rep / "pr-body.md").write_text("summary\n")
        assert any("## Waived" in i for i in G.evaluate(ws, T).open)
        (rep / "pr-body.md").write_text("## Waived\n- scope: owner note\n")
        # stop → everything passes → done, archived; pre-push lets the branch through
        assert stop(ws)[0] is None
        assert (G.az(ws) / "archive" / T / "run.json").is_file() and G.all_runs(ws)[T]["status"] == "done"
        push = f"refs/heads/feature/{T}-api {unit} refs/heads/feature/{T}-api {'0' * 40}\n"
        assert quiet(G.cmd_prepush, ws, push) == 0
        # integration branch needs its own machine evidence; a stale unit evidence reopens the item
        sh(ws, "branch", f"int/{T}", f"feature/{T}-api")
        assert any(i.startswith("[check-int]") for i in G.evaluate(ws, T).open)
        assert quiet(G.cmd_prepush, ws, push) == 1
        sh(ws, "branch", "-D", f"int/{T}")
        assert G.glob_rx("src/api/**").match("src/api/x/y.py") and not G.glob_rx("src/api/**").match("src/apix.py")


def file_run() -> None:
    """A file-producing skill: sheet, rules, verifier, waivers, escalation — through aizen-tech-learning's contract."""
    with tempfile.TemporaryDirectory() as tmp:
        ws = repo(tmp)
        S = "aizen-tech-learning"

        class A:
            skill, goal, run, backlog, output, go = S, "Redis 7.2 cache", "TL-1", None, None, False
        # writing the output before a run exists / before go → denied
        note = ws / "tech-tree" / "redis.md"
        assert G.hook("pre", "claude", claude(ws, "Write", {"file_path": str(note)}))[0]
        assert quiet(G.cmd_start, ws, A) == 0
        G.hook("post", "claude", claude(ws, "Bash", {"command": 'python guard.py start --skill aizen-tech-learning --goal x'}))
        assert G.guard_state(ws, "TL-1")["coordinator"] == "S1"
        assert G.hook("pre", "claude", claude(ws, "Write", {"file_path": str(note)}))[0]
        assert stop(ws)[0] is None  # planning
        quiet(G.set_status, ws, "TL-1", "working", "owner: ok", decision="ok")
        assert G.hook("pre", "claude", claude(ws, "Write", {"file_path": str(note)}))[0] is None
        # the note: one diagram too big, one unlabelled number
        big = "flowchart LR\n" + "\n".join(f"  N{i} --> N{i + 1}" for i in range(16))
        small = "flowchart LR\n  C1 --> C2"
        note.parent.mkdir()
        note.write_text(f"# Redis\n\nGET costs 1 syscall per request.\n\n```mermaid\n{big}\n```\n"
                        + "".join(f"\n```mermaid\n{small}\n```\n" for _ in range(3)))
        G.hook("post", "claude", claude(ws, "Write", {"file_path": str(note)}))
        G.hook("post", "claude", claude(ws, "Bash", {"command": "python3 check_tree.py tech-tree/redis.md"},
                                        resp={"stdout": "check_tree: PASS", "stderr": ""}))
        res = G.evaluate(ws, "TL-1")
        ids = {i.split("]")[0][1:] for i in res.open}
        assert {"sources", "write", "check", "publish", "diagram-size", "claims-labelled", "tree"} <= ids, res.open
        # fill the sheet: a tick without evidence fails, fake evidence fails, real evidence passes
        sheet = G.run_dir(ws, "TL-1") / "sheet.md"

        def row(sid, done, ev):
            lines = [f"| {sid} | {done} | {ev} |" if ln.startswith(f"| {sid} |") else ln
                     for ln in sheet.read_text().splitlines()]
            sheet.write_text("\n".join(lines) + "\n")

        row("sources", "[x]", "url:https://redis.io/docs")
        row("write", "[x]", "")
        row("check", "[x]", "cmd:pytest -q")
        res = G.evaluate(ws, "TL-1")
        assert any(i.startswith("[sources]") and "not cited" in i for i in res.open), res.open
        assert any(i.startswith("[write]") and "without evidence" in i for i in res.open)
        assert any(i.startswith("[check]") and "never run" in i for i in res.open)
        note.write_text(note.read_text().replace("1 syscall per request.", "1 syscall per request [verified] "
                                                 "https://redis.io/docs").replace(big, small))
        G.hook("post", "claude", claude(ws, "Write", {"file_path": str(note)}))
        row("write", "[x]", "file:tech-tree/redis.md")
        row("check", "[x]", 'cmd:"check_tree.py tech-tree/redis.md" out:"check_tree: PASS"')
        (ws / ".aizen/knowledge/notion.txt").write_text("notion connector missing — HTTP 401 on create")
        assert quiet(G.cmd_waive, ws, "TL-1", "publish", "Notion is not connected here", ".aizen/knowledge/notion.txt") == 0
        res = G.evaluate(ws, "TL-1")
        ids = {i.split("]")[0][1:] for i in res.open}
        assert ids <= {"tree", "waiver publish"}, res.open  # check_tree.py rejects this toy note; waiver unjudged
        # the verifier: missing, then self-written, then a real one under the threshold, then passing
        c = G.contract(S)
        c["rules"] = [r for r in c["rules"] if r["id"] != "tree"]
        G.contract = (lambda orig: (lambda s: c if s == S else orig(s)))(G.contract)
        res = G.evaluate(ws, "TL-1")
        assert any(i.startswith("[waiver publish]") for i in res.open) and any("no verdict.json" in i for i in res.open)
        vpath = G.run_dir(ws, "TL-1") / "verdict.json"

        def verdict(agent, passes, waiver="accepted"):
            items = [{"id": e["id"], "pass": i < passes, "evidence": "tech-tree/redis.md:1" if i < passes else "",
                      "note": "" if i < passes else "missing"} for i, e in enumerate(c["expectations"])]
            G.write_json(vpath, {"run": "TL-1", "items": items, "waivers": {"publish": waiver}})
            G.hook("post", "claude", claude(ws, "Write", {"file_path": str(vpath)}, agent=agent))

        verdict(None, 6)
        assert any("did the work" in i for i in G.evaluate(ws, "TL-1").open)
        verdict("ver", 4)
        assert any("67% < 80%" in i for i in G.evaluate(ws, "TL-1").open), G.evaluate(ws, "TL-1").open
        verdict("ver", 6, waiver="rejected")
        assert any("[waiver publish] rejected" in i for i in G.evaluate(ws, "TL-1").open)
        verdict("ver", 6)
        assert G.evaluate(ws, "TL-1").open == []
        note.write_text(note.read_text() + "\nmore\n")
        G.hook("post", "claude", claude(ws, "Edit", {"file_path": str(note)}))
        assert any("changed after the verdict" in i for i in G.evaluate(ws, "TL-1").open)
        verdict("ver", 6)
        assert stop(ws)[0] is None and G.all_runs(ws)["TL-1"]["status"] == "done"
        assert (G.az(ws) / "archive" / "TL-1").is_dir()


def escalation_and_backlog() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        ws = repo(tmp)
        S = "aizen-video-to-skill"

        class A:
            skill, goal, run, output, go = S, "video", "V-1", None, True
            backlog = "BL-01"
        assert quiet(G.cmd_start, ws, A) == 2  # no such backlog item
        quiet(P.backlog_cli, ws, type("x", (), {"action": "add", "title": "turn talk into a skill", "skill": S, "after": "", "id": None}))
        assert P.can_start(ws, "BL-01") and "proposed" in P.can_start(ws, "BL-01")
        quiet(P.backlog_cli, ws, type("x", (), {"action": "approve", "id": "BL-01", "title": None, "skill": S, "after": ""}))
        assert quiet(G.cmd_start, ws, A) == 0 and P.backlog(ws)[0]["status"] == "doing"
        G.hook("post", "claude", claude(ws, "Bash", {"command": "python guard.py start --skill x --goal y"}))
        assert stop(ws)[0]["decision"] == "block"
        assert stop(ws)[0]["decision"] == "block"
        assert stop(ws)[0] is None and G.all_runs(ws)["V-1"]["status"] == "blocked"
        proj = (G.az(ws) / "PROJECT.md").read_text()
        assert "⛔ blocked" in proj and "V-1" in proj and "## 13. Nguồn" in proj and "## Mục lục" in proj


def migrate_and_install() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp)
        sh(ws, "init", "-q", "-b", "main")
        (ws / "README.md").write_text("x")
        sh(ws, "add", ".")
        sh(ws, "commit", "-q", "-m", "base")
        old = ws / ".aizen"
        (old / "tasks" / "OLD-1").mkdir(parents=True)
        G.write_json(old / "tasks" / "OLD-1" / "run.json", {"task": "OLD-1", "goal": "g", "status": "done", "round": 0})
        (old / "plans").mkdir()
        (old / "plans" / "OLD-1.md").write_text("# plan")
        (old / "reports" / "OLD-1").mkdir(parents=True)
        (old / "reports" / "OLD-1" / "evidence-api.json").write_text("{}")
        (old / "reports" / "OLD-1" / "review.md").write_text("ok")
        (old / "docs" / "system").mkdir(parents=True)
        (old / "docs" / "system" / "architecture.md").write_text("# Architecture\n\n## Parts\nAPI + DB\n")
        (old / "docs" / "DECISIONS.md").write_text("D-01 use Postgres\n")
        (old / "conventions.md").write_text("# Conventions\nnpm test\n")
        quiet(G.cmd_install, ws)
        rd = old / "runs" / "OLD-1"
        assert (rd / "plan.md").is_file() and (rd / "evidence" / "api.json").is_file() and (rd / "reports" / "review.md").is_file()
        assert G.read_json(rd / "run.json", {})["skill"] == "aizen-build" and not (old / "tasks").exists()
        assert (old / "knowledge" / "decisions.md").is_file() and (old / "config" / "conventions.md").is_file()
        proj = (old / "PROJECT.md").read_text()
        assert "\n### Parts" not in proj and "\n#### Parts" in proj and "D-01 use Postgres" in proj and "npm test" in proj
        (ws / ".agents" / "skills").mkdir(parents=True)
        for _ in range(2):
            quiet(G.cmd_install, ws)
        cs = G.read_json(ws / ".claude" / "settings.local.json", {})
        stop_cmd = cs["hooks"]["Stop"][0]["hooks"][0]["command"]
        assert len(cs["hooks"]["Stop"]) == 1 and "/aizen-core/scripts/core/guard.py" in stop_cmd
        # hooks run through uv — never a Python path baked in at install time
        agy = G.read_json(ws / ".agents" / "hooks.json", {})["aizen-guard"]
        assert stop_cmd.startswith("uv run --quiet --script ") and sys.executable not in stop_cmd
        assert agy["PreToolUse"][0]["hooks"][0]["command"].startswith("uv run --quiet --script ")
        assert "exec uv run --quiet --script " in (ws / ".git" / "hooks" / "pre-push").read_text()
        rule = ws / ".agents" / "rules" / "aizen-working-principles.md"
        assert rule.read_text(encoding="utf-8").startswith("---\ntrigger: always_on\n---\n")
        assert ".aizen/" in (ws / ".git" / "info" / "exclude").read_text()


def text_rules() -> None:
    seq = "sequenceDiagram\n  participant A\n  A->>B: x\n  B-->>C: y"
    assert G.mermaid_nodes(seq) == 3
    assert G.mermaid_nodes('flowchart LR\n  C1["C1 loop"] -->|req| C2(cache)\n  subgraph k\n  C3\n  end') == 3
    t = "Caption one\ncaption two\n\n```mermaid\nflowchart LR\n A-->B\n```\n"
    assert G.caption_lines(t, t.index("```")) == 0
    assert G.unlabelled_claims("p99 is 2 ms\nok [verified] 3 ms\nsee https://x 4 ms\n| a | 5 ms |", G.read_json(G.DEFAULT, {})["labels"]) \
        == ["p99 is 2 ms", "| a | 5 ms |"]
    assert G.citations("see a/b.py:12 and https://x.io/y.md:3 at 10:30") == [("a/b.py", 12)]


def run() -> None:
    text_rules()
    build_run()
    file_run()
    escalation_and_backlog()
    migrate_and_install()
    print("guard.py self-check OK")


def run_project() -> None:
    escalation_and_backlog()
    migrate_and_install()
    print("project.py self-check OK")
