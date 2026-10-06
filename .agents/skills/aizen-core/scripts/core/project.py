#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""project.py — compile .aizen/PROJECT.md, the one file the owner reads to understand and steer the project (v25).

    uv run <CORE_DIR>/scripts/core/project.py [--workspace .]     # rebuild now (the guard also does it on every change)
    uv run <CORE_DIR>/scripts/core/project.py --selfcheck

PROJECT.md is compiled, never edited: the content comes from .aizen/knowledge/ (system, modules, decisions,
lessons), .aizen/config/conventions.md, .aizen/backlog.md and .aizen/runs|archive/. Change the source, the map
follows. Also owns .aizen/backlog.md: `guard.py backlog add|approve|drop|list`.
Python ≥ 3.9, standard library only.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BACKLOG_HEAD = """# Backlog — việc sắp làm

Agent chỉ được đề xuất (`proposed`); chỉ owner duyệt: `aizen backlog approve BL-nn` (hook chặn agent tự duyệt).
Trạng thái: proposed → approved → doing → done · dropped. Cột "Sau" = việc phải xong trước.

| ID | Việc | Skill | Trạng thái | Sau | Run |
|---|---|---|---|---|---|
"""
ROW = re.compile(r"^\|\s*(BL-\d+)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*$")


def g():
    sys.path.insert(0, str(HERE))
    import guard  # noqa: PLC0415
    return guard


# ── backlog ──────────────────────────────────────────────────────────────────────────────────────────────

def backlog_path(ws: Path) -> Path:
    return ws / ".aizen" / "backlog.md"


def ensure_backlog(ws: Path) -> None:
    p = backlog_path(ws)
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(BACKLOG_HEAD, encoding="utf-8")


def backlog(ws: Path) -> list[dict]:
    p = backlog_path(ws)
    if not p.is_file():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        m = ROW.match(line)
        if m:
            out.append(dict(zip(("id", "title", "skill", "status", "after", "run"), m.groups())))
    return out


def save_backlog(ws: Path, items: list[dict]) -> None:
    ensure_backlog(ws)
    text = backlog_path(ws).read_text(encoding="utf-8")
    head = text.split("\n| BL-", 1)[0].rstrip("\n") + "\n"
    if "| ID |" not in head:
        head = BACKLOG_HEAD
    rows = "".join(f"| {i['id']} | {i['title']} | {i['skill']} | {i['status']} | {i['after'] or '—'} | {i['run'] or '—'} |\n"
                   for i in items)
    g().write_text(backlog_path(ws), head + rows)


def set_backlog(ws: Path, bid: str, status: str, run: str = "") -> None:
    items = backlog(ws)
    for i in items:
        if i["id"] == bid:
            i["status"] = status
            if run:
                i["run"] = run
    save_backlog(ws, items)


def can_start(ws: Path, bid: str) -> str | None:
    items = {i["id"]: i for i in backlog(ws)}
    it = items.get(bid)
    if not it:
        return f"no {bid} in .aizen/backlog.md"
    if it["status"] != "approved":
        return f"{bid} is {it['status']} — only items the owner approved can start"
    waiting = [d for d in re.findall(r"BL-\d+", it["after"]) if items.get(d, {}).get("status") != "done"]
    return f"{bid} waits for {', '.join(waiting)}" if waiting else None


def backlog_cli(ws: Path, a) -> int:
    items = backlog(ws)
    if a.action == "list":
        for i in items:
            print(f"{i['id']}  {i['status']:9} {i['skill']:22} {i['title']}" + (f"  (after {i['after']})" if i['after'] not in ('', '—') else ""))
        return 0
    if a.action == "add":
        if not a.title:
            print("--title is required", file=sys.stderr)
            return 2
        n = max([int(i["id"][3:]) for i in items] or [0]) + 1
        items.append({"id": f"BL-{n:02d}", "title": a.title.replace("|", "/"), "skill": a.skill, "status": "proposed",
                      "after": a.after or "—", "run": "—"})
        save_backlog(ws, items)
        print(f"BL-{n:02d} proposed — the owner approves it with `aizen backlog approve BL-{n:02d}`")
    else:
        if not any(i["id"] == a.id for i in items):
            print(f"no {a.id}", file=sys.stderr)
            return 2
        set_backlog(ws, a.id, "approved" if a.action == "approve" else "dropped")
        print(f"{a.id} {'approved' if a.action == 'approve' else 'dropped'}")
    build(ws)
    return 0


# ── PROJECT.md ───────────────────────────────────────────────────────────────────────────────────────────

def demote(text: str, by: int = 2) -> str:
    """Inline a source file: drop its first `# title`, push its headings down so they nest under ours."""
    lines = text.strip().splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    out, fence = [], False
    for line in lines:
        if line.startswith("```"):
            fence = not fence
        if not fence and re.match(r"^#{1,6}\s", line):
            line = "#" * min(6, len(line) - len(line.lstrip("#")) + by) + line[len(line) - len(line.lstrip("#")):]
        out.append(line)
    return "\n".join(out).strip()


def inline(ws: Path, rel: str, missing: str) -> tuple[str, bool]:
    p = ws / ".aizen" / rel
    if p.is_file() and p.read_text(encoding="utf-8").strip():
        return demote(p.read_text(encoding="utf-8")) + f"\n\n<sub>Nguồn: `.aizen/{rel}`</sub>", True
    return f"_Chưa có — {missing}. Nguồn sẽ là `.aizen/{rel}`._", False


def first(ws: Path, *rels: str) -> str:
    return next((r for r in rels if (ws / ".aizen" / r).is_file()), rels[0])


def sheet_summary(ws: Path, run: str) -> tuple[int, int, list[str]]:
    p = g().run_dir(ws, run) / "sheet.md"
    if not p.is_file():
        return 0, 0, []
    rows = [line for line in p.read_text(encoding="utf-8").split("## Checks", 1)[-1].splitlines() if line.startswith("| ")]
    ok = sum("✅" in r for r in rows)
    bad = [r.split("|")[1].strip() for r in rows if "❌" in r]
    return ok, ok + len(bad), bad


def build(ws: Path) -> Path:
    G = g()
    a = ws / ".aizen"
    name = ws.resolve().name
    sha = G.git(ws, "rev-parse", "--short", "HEAD") or "—"
    runs = G.all_runs(ws)
    items = backlog(ws)
    toc = ["Cần bạn ngay", "Tổng quan", "Kiến trúc", "Luồng nghiệp vụ", "Module", "Dữ liệu", "Hạ tầng", "Quy ước",
           "Quyết định", "Bài học", "Quy trình agent", "Việc của agent", "Cách điều khiển", "Nguồn"]
    anchor = lambda i, t: f"{i}-" + re.sub(r"[^\w-]", "", t.lower().replace(" ", "-"))  # noqa: E731
    out = [f"# {name} — bản đồ dự án", "",
           f"> Máy biên soạn lúc {dt.datetime.now():%Y-%m-%d %H:%M} · commit `{sha}` · **không sửa tay** — sửa file nguồn "
           "(mục 13), file này tự cập nhật.", "", "## Mục lục", ""]
    out += [f"{i}. [{t}](#{anchor(i, t)})" for i, t in enumerate(toc)]
    sources = []

    # 0 — needs you
    need = []
    for rid, r in runs.items():
        loc = f"`{G.run_dir(ws, rid).relative_to(ws).as_posix()}/state.md`"
        if r["status"] == "blocked":
            last = (r.get("log") or [""])[-1]
            need.append(f"| {rid} | ⛔ blocked — {last[20:180]} | {loc} |")
        elif r["status"] == "waiting":
            need.append(f"| {rid} | ❓ chờ bạn trả lời: {r.get('question', '')} | trả lời trong chat → agent chạy `go` |")
        elif r["status"] == "planning":
            need.append(f"| {rid} | 📝 chờ bạn xác nhận phạm vi / plan | {loc} |")
    for i in items:
        if i["status"] == "proposed":
            need.append(f"| {i['id']} | 🗂 việc đề xuất chờ duyệt: {i['title']} | `aizen backlog approve {i['id']}` |")
    pp = G.read_json(a / "cache" / "prepush.json", {})
    if pp:
        need.append(f"| {pp.get('run')} | 🚫 push `{pp.get('ref')}` bị chặn: {'; '.join(pp.get('open', []))[:160]} | `aizen guard check --run {pp.get('run')}` |")
    out += ["", "## 0. Cần bạn ngay", ""]
    out += (["| Việc | Cần gì | Xem / làm |", "|---|---|---|", *need] if need else ["Không có gì cần bạn lúc này."])

    # 1–9 — understanding the project
    sec = [
        ("1. Tổng quan", [(first(ws, "knowledge/system/overview.md", "knowledge/system/system-map.md", "knowledge/system/idea.md"),
                           "mục tiêu, phạm vi, người dùng, stack"),
                          ("knowledge/system/requirements.md", "yêu cầu")]),
        ("2. Kiến trúc", [("knowledge/system/architecture.md", "sơ đồ C4, thành phần, luồng dữ liệu"),
                          ("knowledge/system/security.md", "mô hình bảo mật")]),
        ("3. Luồng nghiệp vụ", [("knowledge/system/flows.md", "sequence diagram từng luồng chính")]),
        ("5. Dữ liệu", [("knowledge/system/data.md", "ERD, bảng chính, migration")]),
        ("6. Hạ tầng", [("knowledge/system/infrastructure.md", "môi trường, CI/CD, deploy, rollback")]),
        ("7. Quy ước", [("config/conventions.md", "quy ước code, đặt tên, git, lệnh build/test/lint")]),
        ("8. Quyết định", [("knowledge/decisions.md", "D-nn: quyết định, lý do, ngày")]),
        ("9. Bài học", [("knowledge/lessons.md", "L-nn sau mỗi run")]),
    ]
    used = set()
    for title, parts in sec[:3]:
        out += ["", f"## {title}", ""]
        for rel, miss in parts:
            body, ok = inline(ws, rel, miss)
            used.add(rel)
            sources.append((title, rel, ok))
            if ok or rel.endswith(("overview.md", "architecture.md", "flows.md", "system-map.md", "idea.md")):
                out += [body, ""]
        if title.startswith("2."):
            extra = [p for p in sorted((a / "knowledge" / "system").glob("*.md"))
                     if f"knowledge/system/{p.name}" not in {r for _, ps in sec for r, _ in ps} | used
                     and p.name not in ("overview.md", "system-map.md", "idea.md")]
            for p in extra:
                rel = f"knowledge/system/{p.name}"
                out += [f"### {p.stem}", "", demote(p.read_text(encoding="utf-8"), 3), ""]
                sources.append((title, rel, True))
    out += ["", "## 4. Module", ""]
    mods = sorted(d for d in (a / "knowledge" / "modules").glob("*") if d.is_dir()) if (a / "knowledge" / "modules").is_dir() else []
    if not mods:
        out.append("_Chưa có module nào được ghi — nguồn: `.aizen/knowledge/modules/<module>/`._")
    for d in mods:
        out += [f"### {d.name}", ""]
        for f in sorted(d.glob("*.md")):
            out += [demote(f.read_text(encoding="utf-8"), 3), f"\n<sub>Nguồn: `.aizen/knowledge/modules/{d.name}/{f.name}`</sub>", ""]
            sources.append(("4. Module", f"knowledge/modules/{d.name}/{f.name}", True))
    for title, parts in sec[3:]:
        out += ["", f"## {title}", ""]
        for rel, miss in parts:
            body, ok = inline(ws, rel, miss)
            sources.append((title, rel, ok))
            out += [body, ""]

    # 10 — how agents work here
    out += ["", "## 10. Quy trình agent", "",
            "Mọi skill chạy theo một hợp đồng chung; agent không tự quyết khi nào xong — cổng (guard) quyết từ bằng chứng.", "",
            "```mermaid", "flowchart LR",
            "  BL[\"backlog: approved\"] --> S[\"start: run + sheet\"] --> P{\"cần owner xác nhận?\"}",
            "  P -- có --> W[\"planning / waiting\"] --> GO[\"go / approve\"] --> K",
            "  P -- không --> K[\"làm việc · hook ghi ledger, chặn file cấm\"]",
            "  K --> G{\"Stop gate: sheet · rules · verifier\"}",
            "  G -- thiếu --> K",
            "  G -- hết vòng --> B[\"blocked → Cần bạn\"]",
            "  G -- đạt --> D[\"done → archive · backlog done · PROJECT.md\"] --> PP[\"git pre-push\"]",
            "```", "",
            "| Skill | Bước bạn thấy trong sheet | Kiểm tự động | Giám khảo |", "|---|---|---|---|"]
    for sk in G.entry_skills():
        c = G.contract(sk)
        if c.get("mode") == "none":
            out.append(f"| {sk} | — | không gate (không xuất file) | — |")
            continue
        v = c.get("verifier", {})
        out.append(f"| {sk} | {', '.join(s['id'] for s in c.get('steps', [])) or 'máy tự điền'} | "
                   f"{', '.join(r.get('id', r['type']) for r in c.get('rules', []))} | "
                   + (f"≥ {v.get('threshold', .8):.0%} của {len(c.get('expectations', []))} tiêu chí" if v.get("required")
                      else "reviewer độc lập (review.md)" if sk == "aizen-build" else "owner duyệt checkpoint" if sk == "aizen-init"
                      else "không") + " |")

    # 11 — work
    out += ["", "## 11. Việc của agent", "", "### 11.1 Đang làm", ""]
    doing = [(k, r) for k, r in runs.items() if r["status"] not in G.FINAL]
    if doing:
        out += ["| Run | Skill | Việc | Trạng thái | Checklist | Thiếu |", "|---|---|---|---|---|---|"]
        for k, r in doing:
            ok, total, bad = sheet_summary(ws, k)
            out.append(f"| [{k}]({G.run_dir(ws, k).relative_to(ws / '.aizen').as_posix()}/sheet.md) | {r['skill']} | "
                       f"{r.get('goal', '')[:60]} | {r['status']} | {ok}/{total} | {', '.join(bad[:4]) or '—'} |")
    else:
        out.append("Không có run nào đang chạy.")
    out += ["", "### 11.2 Sắp làm", ""]
    upcoming = [i for i in items if i["status"] in ("proposed", "approved", "doing")]
    out += (["| ID | Việc | Skill | Trạng thái | Sau | Run |", "|---|---|---|---|---|---|"]
            + [f"| {i['id']} | {i['title']} | {i['skill']} | {i['status']} | {i['after']} | {i['run']} |" for i in upcoming]
            if upcoming else ["Backlog trống — thêm việc: `aizen backlog add --title \"…\" --skill …`."])
    out += ["", "### 11.3 Đã làm", ""]
    finished = sorted(((k, r) for k, r in runs.items() if r["status"] in G.FINAL),
                      key=lambda kr: kr[1].get("log", [""])[-1] if kr[1].get("log") else "", reverse=True)[:30]
    if finished:
        out += ["| Run | Skill | Việc | Kết quả | Miễn bước | Xong lúc |", "|---|---|---|---|---|---|"]
        for k, r in finished:
            wv = ", ".join(G.read_json(G.run_dir(ws, k) / "waivers.json", {})) or "—"
            res = "✅ done" if r["status"] == "done" else f"⏹ dừng: {r.get('stop_reason', '')[:60]}"
            when = (r.get("log") or [" "])[-1][:16]
            out.append(f"| [{k}]({G.run_dir(ws, k).relative_to(ws / '.aizen').as_posix()}/state.md) | {r['skill']} | "
                       f"{r.get('goal', '')[:60]} | {res} | {wv} | {when} |")
    else:
        out.append("Chưa có run nào xong.")

    # 12 — controls
    out += ["", "## 12. Cách điều khiển", "",
            "| Bạn muốn | Làm |", "|---|---|",
            "| Giao việc mới | nói trong chat, hoặc `aizen backlog add --title \"…\" --skill <skill>` |",
            "| Duyệt / bỏ việc | `aizen backlog approve BL-nn` · `aizen backlog drop BL-nn` (chỉ bạn — hook chặn agent) |",
            "| Xem vì sao một run chưa xong | `aizen guard check --run <RUN>` hoặc mở `runs/<RUN>/sheet.md` |",
            "| Trả lời câu hỏi của agent | trả lời trong chat; agent ghi lại bằng `guard.py go` |",
            "| Dừng một run | `aizen guard stop --run <RUN> --reason \"…\"` |",
            "| Bỏ qua một bước có lý do | agent: `guard.py waive … --evidence …`; chỉ tính khi giám khảo chấp nhận |",
            "| Sửa nội dung bản đồ này | sửa file nguồn ở mục 13, rồi `aizen project` |",
            "| Bắt buộc mọi sửa code phải có run | `\"require_task\": true` trong `.aizen/config/guard.json` |",
            "| Chia sẻ knowledge + bản đồ với team | `\"share_knowledge\": true` trong `.aizen/config/guard.json`, chạy lại `aizen guard install` |"]

    # 13 — sources
    out += ["", "## 13. Nguồn", "", "| Mục | File nguồn | Có? |", "|---|---|---|"]
    out += [f"| {t} | `.aizen/{r}` | {'✅' if ok else '—'} |" for t, r, ok in sources]
    out += ["| 11 | `.aizen/backlog.md`, `.aizen/runs/`, `.aizen/archive/` | ✅ |", ""]
    p = a / "PROJECT.md"
    G.write_text(p, "\n".join(out))
    return p


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workspace", default=".")
    ap.add_argument("--selfcheck", action="store_true")
    a = ap.parse_args(argv)
    if a.selfcheck:
        import guard_selfcheck  # noqa: PLC0415
        guard_selfcheck.run_project()
        return 0
    ws = g().find_ws(Path(a.workspace))
    if ws is None:
        print("no .aizen/ here — run `aizen guard install` first", file=sys.stderr)
        return 2
    print(build(ws))
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(HERE))
    sys.exit(main())
