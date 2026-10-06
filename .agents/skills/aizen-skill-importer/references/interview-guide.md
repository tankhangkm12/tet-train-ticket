# Interview guide — from "a copy" to "the user's skill"

The goal is not a copy but a skill that fits how the user works. Do the homework first, then ask few, sharp
questions, each with your proposal so the user can answer "ok".

## 1. Homework (silent)

- Read `SKILL.md`, every file in `rules/`, `references/`, `scripts/`, `agents/` of the copy.
- Write down for yourself: its job, its steps, its output, the tools/libraries it assumes, what it asks the user,
  what it does without asking, and overlaps with skills already in the repo (read their descriptions).

## 2. Questions (3–4, one round)

Pick the ones with the biggest gap between the original and the user's needs:

| Area | Ask like this (always with a proposal) |
|---|---|
| Process | "It runs A → B → C. I propose dropping B (you do it in CI) and adding D (review before writing). OK?" |
| Rules | "It writes files without asking. I propose: confirm before overwrite, never push. Any naming or library rule to add?" |
| Tools | "It needs `pdfplumber`. I propose a stdlib fallback and asking before installing. OK?" |
| Output | "It returns a long chat answer. I propose a file `<x>.md` with sections …. OK?" |
| Language / scope | "Trigger words in Vietnamese too, and 'Not for' pointing to `<existing skill>`?" |
| **Sample task (always)** | "Give me one real task, e.g. 'đọc file X.pdf và tóm tắt theo mẫu Y'. Both versions will run it, and a judge compares them." |

## 3. Answers → files

| The user wants | Change |
|---|---|
| a different process | the workflow in `SKILL.md` |
| a hard limit (must / never / ask first) | `rules/<topic>.md` |
| domain knowledge, conventions, examples | `references/<topic>.md` + a "when to read" row in `SKILL.md` |
| repeatable or exact logic | `scripts/<x>.py` (stdlib, `--help`, `--selfcheck`) |
| templates | `assets/` |
| other trigger words / boundaries | `description` in the frontmatter |

## 4. Report back

What changed per file, what was removed and why, the A/B verdict, and anything the user asked for that you did
not do (`Deviations:`).
