# Rules

1. Current repo = landing checkout (`master/` or `root/` under the imported container). Canvas cwd is imported. Detect per `engineering-init` canvas.md. Sessions `spawn.py --mode this` **before** `cd` checkout. Then `cd` that checkout before `PROCESS.md` / `gh` / landing `git`. Do not read `<imported>/docs/agents/`. `PROCESS.md` `contract:` is not `ready` → stop, go to `engineering-init` **plan** (or normalize migrate). Do not write the origin repo. Do not write process / current ticket / `mode` into `AGENTS.md`.
2. Layers as the table. Planning is a department. A department hop does not become another department in the same window. An employee is not handed off.
3. On the main checkout, read `docs/agents/PROCESS.md` first. Missing there → create per `engineering-init` process-stub, `contract: none`, then stop for init. Do not glob. `contract: ready` but no `docs/agents/MODELS.md` on that checkout → stop, init must fill the model table.
4. **`mode` / `until` latch.** File values stay. Missing `until:` → write `until: none`. Empty `mode` and `contract: ready` → the session-start confirm asks (semi-auto=`manual`, full-auto=`auto`) and writes. Planning session start (Entry) confirms `mode` / `until` / `merge` / `verify` / `accept` plus MODELS before any advance when this conversation has not confirmed yet. Later turns: change `mode` / `until` / `merge` only when the user explicitly asks. User names a stop → write `until:`. User clears it → `none`. Do not invent. Create/remove trees: rule 16. After a handoff, stop (do not watch). After decide receipts and after report back: templates.md **Stop** tables only. Hard stop wins. Same class of pullable tickets → smallest issue number. After a **close**: first what that close unblocked (`human` then acceptance); none → hop table.
5. **`template`.** Main checkout: always `planning`. Empty → write `planning`. User named `delivery` / `acceptance` as the **entry** → still `planning`. Hop names live only on the **ticket tree**. Occupied tree `issue:` on another department window → do not reset that tree to planning.
6. Planning **manage** **hand off** via sessions `spawn.py --mode dispatch` (**other** department). Then stop. Do not `openhands-watch`. That department's manage staffs employees via `engineering-routing` **delegate**; wait until each receipt is in that window. Research / datasheet reading only via `engineering-research` (role `research`), staffable by the delivery, acceptance or planning manage; default home is the delivery implement ticket; human and arbitration never staff research. Do not copy POST. Do not write `dispatch_session.py`. Planning decide staffs only `planning implement` / `planning review` / `research` (research as planning input). Do not Task delivery / acceptance / arbitration from planning. MODELS `dispatch` on employee rows → ignore; still delegate. No Task on the department bridge → fail; do not spawn an employee conversation. Do not GET child `/events/search`.
7. Employee kinds only from templates.md **duty table**: table "no" = must not staff; "yes" = must staff via that role as **delegate**. Only that department's **manage** staffs them. Manage is the window, not a Task.
8. One implement ticket = **exactly one** working-contains node. Multiple modules → stop, init must split. Do not open extra GitHub tickets for employees.
9. Ticket labels: `ready-for-human` only with `human`; `ready-for-agent` never `human`. Mismatch → stop.
10. Employee prompt contains only: ticket URL, **ticket-tree `cd` path first (prompt only, not Canvas `working_dir`)**, allowlist, constraints, done criteria, receipt shape, one line "follow repo `AGENTS.md` / `CONTEXT.md` / `docs/adr/` if present; do not ask semi-auto or full-auto; do not git push; do not `gh pr`". Only exception: the research synthesis subagent pushes the external `research/` git repo (never the code repo). `planning` implement may read `PROCESS.md` and run `engineering-init` **patch**; must not write `mode` / main `template`. Other employees must not read or edit PROCESS.md. Add a HANDOFF path line only if `HANDOFF.md` exists. Opening a child conversation for an employee → **fail**.
11. `HANDOFF.md` default do not create. Allowed: crash and ticket still open; this **department** window hit **300** and ticket still open; hardware on-site. Employees do not use 300. Other department at 300 → write HANDOFF; the next planning advance **hands off** to the same department on that ticket. Planning department at 300 during decide → write HANDOFF; next advance continues **decide**.
12. Human send-back: the **human** department (3a) reopens the previous implement ticket. Read `engineering-init` contract. Do not turn a gate ticket into `ready-for-agent`. Planning implement / patch must not reopen on human fail.
13. **One department window, one ticket.** Tree `issue:` is one number. Planning main `issue:` is `none`. Parallel line = another handoff (another advance on planning) or another planning window. Do not write two issues on one tree `PROCESS.md`.
14. **Do not pull downstream while upstream is still blocking.** `blockedBy` still has open → do not hand off, do not work. User named it → still stop; report the blocking upstream. Unblock = those tickets are **closed**. Do not unblock with `remove-blocked-by`.
15. **PR only on a graph acceptance ticket.** Body contains `engineering:pr`. Not holding that ticket → no `gh pr`. Implement and gate tickets must not open/merge PRs. Do not switch the same ticket to acceptance.
16. **worktree.** Read and run [worktree.md](worktree.md). `planning` implement creates the tree before handoff. `acceptance` implement merges heads and removes trees after merge. Trees go under the Canvas container `worktree/`. Not wrapped → stop, init canvas.md. Do not POST sessions `worktree: true`. Do not POST a tree path as `working_dir`. Do not POST an **employee** conversation. Other department window = `spawn.py` dispatch. Manage must not run `git worktree`. Before handoff on an existing tree, `planning` implement runs the drift audit per worktree.md rule 9.
17. **`MODELS` latch.** Planning session start (Entry): print `docs/agents/MODELS.md` with the PROCESS fields; wait for confirm. Later turns: print the table; do not wait unless `confirmed:` is not `yes`. User confirms → `confirmed: yes`. User changes a cell → write and `confirmed: yes`. Follow the **targets**. Format is the n×m grid in models-stub (department × manage/implement/review/verify). Employee cells: use that cell's target; ignore a `dispatch` link. Planning manage cell: `stay`. Other department manage cells: `dispatch` + spawnable profile; hand off uses that target. File has `supervisor` and no `planning` → treat that as planning manage `stay`. Missing other-department manage cell → hand off uses this conversation's spawnable profile. Do not refill the table unless the user changes a cell. Other departments: do not ask; follow targets.
18. **Employees (forced).** Roles `planning implement` / `planning review` / `delivery implement` / `delivery review` / `delivery verify` / `acceptance implement` / `acceptance review` / `acceptance verify` / `arbitration implement` / `arbitration review` / `arbitration verify` / `research` = **delegate**, and only from the matching **department manage**. `research` (datasheet reading included) may be staffed by the delivery, acceptance or planning manage; the default home is the delivery implement ticket; human and arbitration never staff it. MODELS says `dispatch` on those cells → ignore; still delegate. No Task → fail; do not spawn an employee conversation. Wait until each receipt is in this conversation. Background Task → **fail**. Receipt missing → **fail**; do not finish. Manage must not do that work in the window.

19. **Same-ticket department continuation.** The next hop is a department already dispatched for this ticket (typical after arbitration sends the ticket back) → resume the original department manage conversation: sessions `spawn.py --mode resume` with `--target-id` (the exact child id recorded at handoff) + `--ticket` + `--request-id` (stable request identity). Do not `--mode dispatch` and do not `--mode open` a new window for that ticket + department. Do not infer the target from an old conversation id. Do not resume or reuse an employee conversation; the target is the department **manage** window. Receipts, reconciliation, and preservation: templates.md **Department resume**. Review findings still return to the original implement employee per templates.md **Review disposition**; that flow is separate.

## Key points

Manage windows must not: edit product files, run patch, merge heads, open PDFs, paste datasheets / other modules' source, open an employee conversation window, `GET` child-session events, change contains/uses, clone the origin repo, `gh` the origin repo. Touching product paths in the editor / whole-repo format → **fail**.

Duties: templates.md **duty table**.

| Action | Who | Not who |
|---|---|---|
| Hand off a ticket | planning **manage** only | other departments; implement/review/verify |
| Decide technical work (patch: body, `blocked-by`, fix tickets, pause/resume, fill tests, apply verdict) | `planning` **implement** (`engineering-init` **patch**). From arbitration → apply the written verdict only | planning manage; other departments; do not judge the verdict |
| Write the arbitration verdict comment | `arbitration` **manage** (after employee receipts) | planning, delivery, human; implement writes the opinion only |
| Open / merge PR | `acceptance` **manage**, and current ticket body has `engineering:pr` | implement tickets, gates, planning; acceptance implement does git merge only |
| Close implement ticket | `delivery` **manage** after push | planning, implement/review/verify, gate/acceptance tickets |
| Close gate / sink | `human` **manage**: person said the phenomenon passed | do not reopen it as implement work |
| Talk to the user | planning **manage** (session-start confirm: PROCESS modes + MODELS; advance / mode / `until` / `merge`); human **manage** (how to test and accept, and help) | delivery, acceptance, arbitration; employees |
| Close acceptance | `acceptance` **manage** merged or the user said it merged | delivery, human, planning |
| `git commit` (product) | `delivery` implement only | review, verify, manage, planning implement, arbitration implement |
| `git push` | `delivery` **manage** only, and only after delivery verify passed (code repo); research synthesis subagent for the external `research/` repo only | other employees; planning; do not push the code repo's default branch |
| Pause downstream / register bugfix tickets / resume and notify pull | `planning` **implement** during decide. Pause hangs on the **last acceptance** of the bugfix chain | planning manage; the delivery department that found the bug |
| Reproduce + arbitration opinion | `arbitration` implement; review reviews the opinion; `verify:` present → arbitration verify | debug, edit product code, open/merge PR |
| Create git worktree | `planning` implement before handoff, per worktree.md | manage; other departments; do not POST `worktree: true` |
| Merge heads / remove git worktree | `acceptance` implement, per worktree.md | manage; planning |

**Enter `arbitration` only on these three paths. No other receipt may hand off to arbitration.**

1. **Disputed review finding:** `partial` / `dispute` under templates.md **Review disposition**, or `dispute-repeated` from its `post-rework-disposition` state. Arbitrate only the disputed finding IDs selected by that flow.
2. **Implement challenge:** implement explicitly challenges the contract or upstream (`Challenge: upstream #<n>` or `contract`). Review-originated challenges follow the disposition flow above.
3. **User challenge:** the user challenges this ticket's implementation.

An ordinary implement `Result: pass` plus blocking review `Result: fail` is not arbitration; follow templates.md **Review disposition** first. Direct arbitration is only implement challenges and user challenges. **Verify is not a trigger.** Delivery/acceptance verify has no `Challenge` field. `verify:`/`accept:` fail → send implement back or isolate; do not hand off 3b. Command green with extra notes → write a ticket comment; delivery may still pass. If verify writes `Challenge` anyway → treat it as `Notes`; do not enter 3b.

**Not arbitration:** verify=`fail` → send implement back. implement=`fail` and paths 2–3 did not fire → delivery failed.

**Reproduce ≠ debug.** Arbitration may only reproduce.

**Already judged:** delivery must not resubmit a rejected implementation unchanged or repeat the same-finding rework loop. planning must not change the verdict.

## PROCESS.md

Path: ticket tree `docs/agents/PROCESS.md` holds `template` (department hop) + `issue`. Main checkout holds `mode` / `contract` / `verify` / `accept` / `merge` / `until` and `template: planning`, `issue: none`. Employees must not read or edit PROCESS.md.

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

| Field | Meaning |
|---|---|
| `mode` | `manual` / `auto`. When to continue: templates.md **Stop** tables |
| `until` | extra stop. `none` = no extra stop. Planning manage writes it. Missing → `none` |
| `contract` | `ready`=initialized. Else stop for init |
| `verify` / `accept` | delivery light / acceptance full+hooks. `none` → do not invent a command |
| `issue` | department tree only: the one ticket in that window. Planning main file: `none` |
| `merge` | after the acceptance PR, whether to merge to the default branch. Default `human`=open then `wait-merge`. **Not** `mode:` |

`verify: none` → delivery verify writes `Verify: none`. `accept: none` → acceptance may still open a PR; receipt `Verify: none`.

## MODELS.md

Path: `docs/agents/MODELS.md` (follows the default branch; do not invent a copy on the ticket tree). Format: `engineering-init` models-stub n×m grid. Missing → stop, init must fill. Planning session start prints the table with PROCESS fields and waits (rule 17 / Entry). Later turns print; wait only if `confirmed:` is not `yes`. Planning **manage** decide uses the planning manage cell (`stay`) then staffs the planning implement / review cells. hand off uses the **other** department manage cell then sessions **dispatch**. Employee staffing uses that department's implement / review / verify cell then sessions **delegate**.
