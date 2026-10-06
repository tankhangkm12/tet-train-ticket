# Challenge — where a second viewpoint pays (v25)

A tool, not ceremony. Challenge only the uncertain or consequential parts. Risk modules (money/stock/quota,
state machines, several actors on one record, races, external calls failing midway, irreversible actions, public
contracts, schema, production, secrets): the independent `reviewer` pass plus the `redteam` reviewer
(`references/flow/method.md` S6).

## 1. Who challenges what

| Artifact | Owner | Challenged by |
|---|---|---|
| Requirements, design docs, plan | planner | reviewer (plan / design lens); the devs who consume it, in their report |
| API contract, schema | planner or `dev` (db) | the `dev` units on both sides of the seam · tester |
| Code, migrations, UI | `dev` | tester · reviewer |
| Tests | tester | reviewer |
| Infra diff | devops | reviewer (infra lens) |
| Review findings | reviewer | the code's owner, in the fix round |

## 2. The duty — before consuming an upstream artifact

Write **2–4 challenges**, each **concrete** (section, file, line or id), **falsifiable** (situation → wrong
outcome, or a cost that lands later) and **actionable** (an alternative and its cost). No failure scenario → it
is a question; ask it as one. Found nothing → say what you attacked: *"Không phản đối HLD §4–§7; đã kiểm tra
luồng hủy với BR-02, quyền sở hữu bảng `orders`, 3 call đồng bộ về timeout."*

## 3. The exchange — two rounds, then the owner

Round 1: The owner answers each — **ACCEPT** (what changes, file + section) · **REJECT** (evidence) ·
**ESCALATE** (a business call). Round 2: open items only, one final position each — the predicted failure and
what evidence would drop the objection. Then stop; open items go to the owner — during planning with the module they belong to; after approval
only when they block (`BLOCKED`), otherwise in the final report:

```
| # | Item | Position A (role) | Position B (role) | Cost if A wrong | Cost if B wrong |
```

Silence is not agreement · no resolution by seniority or model · never split the difference on a fact — find
out · neither side checked → `[unverified]`, escalate · the challenger never edits the artifact.

## 4. Record

Rows go in the role's report under `## Challenges`; the coordinator raises open ones with the module they belong to. An ACCEPTED
challenge that changes a document is closed by the file changing, not by the conversation.

Only one agent running: challenge your own output once in writing — the two or three ways it could be wrong and
what would show it — and label it `[self-challenged]` (weaker than independent).
