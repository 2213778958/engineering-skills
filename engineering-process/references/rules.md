# Rules

1. Current repo = landing checkout (`master/` or `root/` under the imported container). Canvas cwd is imported. Detect per `engineering-init` canvas.md. Sessions `spawn.py --mode this` **before** `cd` checkout. Then `cd` that checkout before `PROCESS.md` / `gh` / landing `git`. Do not read `<imported>/docs/agents/`. `PROCESS.md` `contract:` is not `ready` → stop, go to `engineering-init` **plan** (or normalize migrate). Do not write the origin repo. Do not write process / current ticket / `mode` into `AGENTS.md`.
2. Layers as the table. Planning is a department. A department hop does not become another department in the same window. An employee is not 分发'd.
3. On the main checkout, read `docs/agents/PROCESS.md` first. Missing there → create per `engineering-init` process-stub, `contract: none`, then stop for init. Do not glob. `contract: ready` but no `docs/agents/MODELS.md` on that checkout → stop, init must fill the model table.
4. **`mode` / `until` latch.** File values stay. Missing `until:` → write `until: none`. Empty `mode` and `contract: ready` → the session-start confirm asks (semi-auto=`manual`, full-auto=`auto`) and writes. Planning session start (Entry) confirms `mode` / `until` / `merge` / `verify` / `accept` plus MODELS before any 推进 when this conversation has not confirmed yet. Later turns: change `mode` / `until` / `merge` only when the user explicitly asks. User names a stop → write `until:`. User clears it → `none`. Do not invent. Create/remove trees: rule 16. After a 分发, stop (do not watch). After 决策 receipts and after 回传: templates.md **Stop** tables only. Hard stop wins. Same class of pullable tickets → smallest issue number. After a **close**: first what that close unblocked (`human` then acceptance); none → hop table.
5. **`template`.** Main checkout: always `planning`. Empty → write `planning`. User named `delivery` / `acceptance` as the **entry** → still `planning`. Hop names live only on the **ticket tree**. Occupied tree `issue:` on another department window → do not reset that tree to planning.
6. Planning **manage** **分发** via sessions `spawn.py --mode dispatch` (**other** department), then stops. That department's manage staffs employees only by reading and running `engineering-routing`; wait until each receipt is in that window. For research or datasheet work inside delivery, staff `datasheet extract` by reading and running `engineering-routing`; that employee reads and runs `engineering-research`, which checks repository materials before the web. Do not copy POST. Do not write `dispatch_session.py`. Planning 决策 staffs only `planning implement` / `planning review`. Do not Task delivery / acceptance / arbitration / extract from planning. Ignore `dispatch` on employee cells; they remain delegate roles. No Task on the department bridge → fail; do not spawn an employee conversation. Do not GET child `/events/search`.
7. Employee kinds only from templates.md **职责表**: table "no" = must not staff; "yes" = must staff via that role as **delegate**. Only that department's **manage** staffs them. Manage is the window, not a Task.
8. One implement ticket = **exactly one** working-contains node. Multiple modules → stop, init must split. Do not open extra GitHub tickets for employees.
9. Ticket labels: `ready-for-human` only with `human`; `ready-for-agent` never `human`. Mismatch → stop.
10. Employee prompt contains only: ticket URL, **ticket-tree `cd` path first (prompt only, not Canvas `working_dir`)**, allowlist, constraints, done criteria, receipt shape, one line "follow repo `AGENTS.md` / `CONTEXT.md` / `docs/adr/` if present; do not ask semi-auto or full-auto; do not git push; do not `gh pr`". `planning` implement may read `PROCESS.md` and run `engineering-init` **patch**; must not write `mode` / main `template`. Other employees must not read or edit PROCESS.md. Add a HANDOFF path line only if `HANDOFF.md` exists. Opening a child conversation for an employee → **fail**.
11. `HANDOFF.md` default do not create. Allowed: crash and ticket still open; this **department** window hit **300** and ticket still open; hardware on-site. Employees do not use 300. Other department at 300 → write HANDOFF; next planning 推进 **分发** the same department on that ticket. Planning department at 300 during 决策 → write HANDOFF; next 推进 continues **决策**.
12. Human send-back: the **human** department (3a) reopens the previous implement ticket. Read `engineering-init` contract. Do not turn a gate ticket into `ready-for-agent`. Planning implement / patch must not reopen on human fail.
13. **One department window, one ticket.** Tree `issue:` is one number. Planning main `issue:` is `none`. Parallel line = another 分发 (another 推进 on planning) or another planning window. Do not write two issues on one tree `PROCESS.md`.
14. **Do not pull downstream while upstream is still blocking.** `blockedBy` still has open → do not 分发, do not work. User named it → still stop; report the blocking upstream. Unblock = those tickets are **closed**. Do not unblock with `remove-blocked-by`.
15. **PR only on a graph acceptance ticket.** Body contains `engineering:pr`. Not holding that ticket → no `gh pr`. Implement and gate tickets must not open/merge PRs. Do not switch the same ticket to acceptance.
16. **worktree.** Read and run [worktree.md](worktree.md). `planning` implement creates the tree before 分发. `acceptance` implement merges heads and removes trees after merge. Trees go under the Canvas container `worktree/`. Not wrapped → stop, init canvas.md. Do not POST sessions `worktree: true`. Do not POST a tree path as `working_dir`. Do not POST an **employee** conversation. Other department window = `spawn.py` dispatch. Manage must not run `git worktree`.
17. **`MODELS` latch.** Planning session start (Entry): print `docs/agents/MODELS.md` with the PROCESS fields; wait for confirm. Later turns: print the table; do not wait unless `confirmed:` is not `yes`. User confirms → `confirmed: yes`. User changes a cell → write and `confirmed: yes`. Follow the **targets**. Format is the n×m grid in models-stub (department × manage/implement/review/verify). Employee cells: use that cell's target; ignore a `dispatch` link. Planning manage cell: `stay`. Other department manage cells: `dispatch` + spawnable profile; 分发 uses that target. File has `supervisor` and no `planning` → treat that as planning manage `stay`. Missing other-department manage cell → 分发 uses this conversation's spawnable profile. Do not refill the table unless the user changes a cell. Other departments: do not ask; follow targets.
18. **Employees (forced).** Roles `planning implement` / `planning review` / `delivery implement` / `delivery review` / `delivery verify` / `acceptance implement` / `acceptance review` / `acceptance verify` / `arbitration implement` / `arbitration review` / `arbitration verify` / `datasheet extract` = **delegate**, and only from the matching **department manage**. MODELS says `dispatch` on those cells → ignore; still delegate. No Task → fail; do not spawn an employee conversation. Wait until each receipt is in this conversation. Background Task → **fail**. Receipt missing → **fail**; do not finish. Manage must not do that work in the window.

## Key points

Manage windows must not: edit product files, run patch, merge heads, open PDFs, paste datasheets / all three graphs / other modules' source, open an employee conversation window, `GET` child-session events, change contains/uses, clone the origin repo, `gh` the origin repo. Touching product paths in the editor / whole-repo format → **fail**.

Duties: [templates.md](templates.md) **职责表**. Staff employees only by reading and running `engineering-routing`; do not directly wire lower-level skills.

| Action | Who | Not who |
|---|---|---|
| 分发 a graph ticket | planning **manage** only | other departments; implement/review/verify |
| 决策 technical (patch: body, `blocked-by`, fix tickets, pause/resume, fill tests, apply verdict) | `planning` **implement** (`engineering-init` **patch**). From arbitration → apply the written verdict only | planning manage; other departments; do not judge the verdict |
| Write the arbitration verdict comment | `arbitration` **manage** (after employee receipts) | planning, delivery, human; implement writes the opinion only |
| Open / merge PR | `acceptance` **manage**, and current ticket body has `engineering:pr` | implement tickets, gates, planning; acceptance implement does git merge only |
| Close implement ticket | `delivery` **manage** after push | planning, implement/review/verify, gate/acceptance tickets |
| Close gate / sink | `human` **manage**: person said the phenomenon passed | do not reopen it as implement work |
| Talk to the user | planning **manage** (session-start confirm: PROCESS modes + MODELS; 推进 / mode / `until` / `merge`); human **manage** (how to test and accept, and help) | delivery, acceptance, arbitration; employees |
| Close acceptance | `acceptance` **manage** merged or the user said it merged | delivery, human, planning |
| `git commit` (product) | `delivery` implement only | review, verify, manage, planning implement, arbitration implement |
| `git push` | `delivery` **manage** only, and only after delivery verify passed | employees; planning; do not push the default branch |
| Pause downstream / register bugfix tickets / resume and notify pull | `planning` **implement** during 决策. Pause hangs on the **last acceptance** of the bugfix chain | planning manage; the delivery department that found the bug |
| Reproduce + arbitration opinion | `arbitration` implement; review reviews the opinion; `verify:` present → arbitration verify | debug, edit product code, open/merge PR |
| Create git worktree | `planning` implement before 分发, per worktree.md | manage; other departments; do not POST `worktree: true` |
| Merge heads / remove git worktree | `acceptance` implement, per worktree.md | manage; planning |

**Enter `arbitration` only on these three paths. No other receipt may 分发 arbitration.**

1. **Conflict:** implement `Result: pass` and review `Result: fail` (they disagree on the implementation).
2. **Employee challenge:** implement or review receipt `Challenge:` is not `none` (`upstream #<n>` or `contract`).
3. **User challenge:** the user challenges this ticket's implementation.

**Verify is not a trigger.** Delivery/acceptance verify has no `Challenge` field. `verify:`/`accept:` fail → send implement back or isolate; do not 分发 3b. Command green with extra notes → write a ticket comment; delivery may still pass. If verify writes `Challenge` anyway → treat it as `Notes`; do not enter 3b.

**Not arbitration:** verify=`fail` → send implement back. implement=`fail` and paths 2–3 did not fire → delivery failed.

**Reproduce ≠ debug.** Arbitration may only reproduce.

**Already judged:** delivery must not resubmit a rejected implementation unchanged. planning must not change the verdict.
