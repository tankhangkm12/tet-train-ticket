# Publishing a generated skill to a git repository

Target repository named by the user: https://github.com/tankhangkm12/Aizen-Skills (confirm it is still the intended target before any action).

## Hard gate: approval first

Nothing is committed, pushed, or opened as a PR until the user has reviewed the exact changes and replied with an explicit yes. A "yes" to the skill content is not a "yes" to publishing; ask separately. If any detail is unknown (branch, commit message style, folder location, who owns `AGENT.md`), ask; do not infer.

## Steps

1. **Check access.** Confirm a git connection exists (GitHub connector, `gh`, or git credentials). If none, tell the user and stop; offer to hand over the folder instead. Never request or handle the user's tokens/passwords in chat.
2. **Read the repo before proposing.** Inspect the existing layout (where skills live, naming, README) and read the current `AGENT.md` in full. Match existing conventions.
3. **Prepare a preview**, shown to the user:
   - Files to add: full tree of `<repo>/<skills-dir>/<new-skill-name>/...`
   - Files to change: a unified diff of `AGENT.md` (and README if relevant)
   - Target branch and proposed commit message
4. **Wait for approval.** Prefer a new branch + pull request over pushing to the default branch, unless the user says otherwise.
5. **Apply exactly what was approved**, nothing more. Report the commit/PR link afterwards.

## AGENT.md update

`AGENT.md` is how an agent learns when to read a skill. Add a short, scannable entry per skill; do not rewrite existing content. Suggested entry, adapted to the file's existing style:

```markdown
### <new-skill-name>
- Read `<skills-dir>/<new-skill-name>/SKILL.md` when: <trigger conditions, same spirit as the skill description>
- Do not use for: <near-misses>
```

If `AGENT.md` has no skills index, propose adding a "Skills" section and show it in the diff; do not create it silently.

## Safety checks before showing the preview

- No secrets, tokens, cookies or personal data in any file.
- No large binaries (mp3/video/model files); remove `audio.mp3` and work folders.
- No long verbatim transcript text; transcript stays out of the repo unless the user asks.
- `uv run scripts/validate_skill.py <folder>` passes.
