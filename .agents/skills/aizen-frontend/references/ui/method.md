# UI design — steps (v24)

Used by `dev` with `KIND=ui` (design files, not repo code). UI design is **design**: it runs before
`state.py approve`, and the owner confirms each stage through the coordinator (like a module).

## Rules

1. **Tool asked once, then recorded** (Penpot, Figma or Markdown — `tool-choice.md`); writes to Penpot/Figma are A3.
2. **Low-fidelity first.** Flows and wireframes approved before colour or polish.
3. **Every state is designed** per `SCR` (loading, empty, partial, each error, permission-denied, offline,
   submitting, success) or explicitly "uses shared pattern X".
4. **Tokens, not values** (`tokens-components.md`). A raw hex or pixel value on a screen is a defect.
5. **Names match the code** — `CMP`/`SCR` ids the frontend will use.
6. **Accessible by construction** — WCAG 2.2 AA, contrast measured (`references/frontend/accessibility.md`,
   `scripts/frontend/uikit.py`).
7. **Real content** — long Vietnamese names, 0/1/many items, long money values, slow network.
8. **Gaps go upstream** — data the contract lacks → gap row, never a quiet invention.
9. Style guides (`references/frontend/style/`) and inspiration give direction, never another brand's identity.
10. **Options before polish** — 2–3 genuinely different directions for a new flow.

## Steps

- **U0 Locate** brand/design system, requirements, frontend doc, contract, decisions.
- **U1 Challenge** — dead-end journeys, states no screen shows, actions without feedback, error codes without message.
- **U2 Flows + wireframes** per journey (`design-process.md` §2) → the owner approves the structure.
- **U3 Tokens and components** (`assets/ui/design-tokens.json`): anatomy, variants, sizes, states.
- **U4 Screens** high-fidelity per `SCR` × state × breakpoint.
- **U5 Check** accessibility with numbers; `references/frontend/web-interface-guidelines.md`; exit gate in
  `design-process.md` §5 row by row.
- **U6 Hand off** (`handoff.md`): `<app>-ui.md` from `assets/ui/ui.md`, exports per `SCR` × state in `ui-exports/`,
  gap list.

Small request (one screen/component): U0 → change → U5 for what changed → export → report.
All guides in `references/ui/` unless a path says otherwise.
