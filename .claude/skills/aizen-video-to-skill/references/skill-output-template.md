# Standard layout for a skill generated from a video

## Contents
1. Folder layout
2. Frontmatter rules
3. SKILL.md skeleton
4. Scripts guidance
5. source.md

## 1. Folder layout

```
<new-skill-name>/            kebab-case, specific (e.g. docker-compose-debugging)
├── SKILL.md                 required; instructions, < ~500 lines
├── scripts/                 optional; deterministic, runnable helpers
├── references/              optional; deeper docs the agent loads on demand
│   └── source.md            provenance of the video (always include)
└── assets/                  optional; templates or files used in outputs
```

Keep it portable: no absolute paths, no secrets, no tool-specific assumptions beyond what the scripts declare. Any agent that can read Markdown and run shell commands should be able to use it.

## 2. Frontmatter rules

```yaml
---
name: kebab-case-name
description: What it does + when to use it. Mention concrete trigger phrases and contexts. Slightly pushy so agents do not under-trigger. 1 to 3 sentences, under 1024 chars, no angle brackets.
---
```

The description is the only thing an agent sees before deciding to load the skill, so all "when to use" information belongs there, not in the body.

## 3. SKILL.md skeleton

```markdown
# <Title>

One paragraph: what problem this solves and the outcome.

## When to use / not to use
(Short; the main triggers are already in the description.)

## Workflow
1. Step, with the reason it matters
2. ...

## Key rules and gotchas
(The non-obvious things the video emphasised, each with its reason.)

## Examples
**Example 1:** Input -> Output

## Resources
- `scripts/<name>.py`: when to run it and what it returns
- `references/<name>.md`: when to read it
```

Writing style: imperative voice, explain *why*, prefer general principles over narrow examples taken from the video, drop filler, sponsor segments and tangents.

## 4. Scripts guidance

Add a script only when a step is deterministic and repeated (conversion, validation, scaffolding). Each script needs a `--help`, clear error messages, no hidden installs, and must be listed in SKILL.md with when to use it. If the video shows commands, verify they work before putting them in a script; if you cannot verify, say so in SKILL.md.

## 5. references/source.md

```markdown
# Source
- Video: <title> - <URL or filename>
- Creator/channel: <if known>
- Extracted: <date>, method: <manifest.method>, language: <manifest.language>
- Transcript warnings: <manifest.warnings or "none">
- Scope: which parts of the video the skill covers, and what was left out
```

Do not paste the full transcript or long verbatim passages; the skill should be your distilled version.
