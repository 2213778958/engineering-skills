# PROCESS.md

Local latch in the landing checkout (`master/` or `root/`), not the imported container root. Path: `<checkout>/docs/agents/PROCESS.md`. Do not write the origin repo. Do not put these fields in `AGENTS.md`.

## Rules

- `mode` / `until`: process templates.md **Stop** tables are source of truth. Missing `until:` → `none`. Planning manage writes `until` only when the user names a stop. 决策 that changes tickets or edges must rewrite spec `engineering:graph`.
- `planning` implement creates git worktrees under the Canvas container `worktree/` (canvas.md) **before 分发**. `acceptance` implement removes after merge. Do not POST Canvas `worktree: true`. Do not put a tree path in `working_dir`.
- Planning is a **department**. The window is **manage**. ACP is the Cursor bridge, not a role. 推进 / 领票 / 主管 / 继续工程 → planning manage (`template: planning`, main `issue: none`). Planning **manage** **分发** graph tickets to **other** departments (`delivery` / `acceptance` / `arbitration` / `human`) or runs **决策** (staff `planning implement` + `planning review`; do not run patch). After 分发, stop. Do not watch. Duties: process templates.md **职责表**.
- **Other departments** = delivery / acceptance / arbitration / human (`spawn.py` child). One tree `issue:`. That **manage** staffs **employees** per 职责表; wait for receipts; sessions **notify** the planning parent. human does not staff implement/review/verify. Human **manage** talks to the user: how to test and accept, and help; wait for pass/fail. Planning **manage** also talks to the user (推进 / mode / MODELS). Do not `spawn.py` for implement / review / verify.
- **Employee** = implement / review / verify / extract. Delegate only. Not a conversation window. Manage is the department window, not a Task.
- Main checkout `PROCESS.md` holds `mode` / `contract` / `until` / test commands, `template: planning`, `issue: none`. The ticket tree copy holds this ticket's `issue` / department `template`.
- Model presets: `docs/agents/MODELS.md` (see models-stub). `MODELS.md` is tracked; `PROCESS.md` is not.
- `contract: ready` = initialized. `contract: none` = not initialized.
- After ask-and-write, later starts follow the file. Change `mode` only when the user explicitly asks.
- init does not ask `template`. process fills tree `template` / `issue` on 分发.
- process must not write `contract: ready`. Do not refill `MODELS.md` unless the user changes a row. Do not `git add` `PROCESS.md`.

## Key points: who writes which field

| Who | When | Does |
|---|---|---|
| init **plan** | `mode` empty or file missing | Ask once semi-auto/full-auto; write `mode:`. `contract: ready`. Grill test commands into `verify:` / `accept:`; unconfirmed → `none` |
| init **normalize migrate** | same | same |
| init **not-normalized migrate** | may create the file | leave `mode:` empty, `contract: none`; do not ask semi/full auto |
| init **patch** | `contract: ready` | do not ask, do not change `mode` / `contract`. May fill `verify:` / `accept:` |
| init sees existing `manual`/`auto` | plan / normalize | do not ask, do not overwrite `mode`. Still write `contract: ready` |
| process | planning conversation has not confirmed yet, not 回传 | if `until:` missing write `until: none`; print `mode` / `until` / `merge` / `verify` / `accept` + MODELS; wait; do not 推进 yet |
| process | user confirmed this conversation | follow the file |
| process | `mode` empty and `contract: ready` | session-start confirm writes it (semi-auto=`manual`, full-auto=`auto`) |
| process | `contract` is not `ready` | stop, go to init plan |
| process | user explicitly asks to change | change `mode` / `until` / `merge`, write it |

## Steps: file contents

```
mode: manual | auto
contract: none | ready
verify: <command | none>
accept: <command | none>
template: planning | delivery | acceptance | arbitration | human
issue: <n or none>
updated: <ISO-8601>
merge: auto | human
until: none | #<n> | delivery | acceptance | human | arbitration
```

If the file is missing and must be created: write the keys above. `template:` empty. `issue: none`. `merge: human`. `until: none`. `verify:` / `accept:` per the table. `contract:` / `mode:` per the table.
