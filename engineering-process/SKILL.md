---
name: engineering-process
description: >-
  Advances an initialized repo from the planning department.
  Planning is a department: it 分发 tickets to other departments or
  runs 决策. Manage staffs implement/review/verify per the 职责表.
  Use when the user asks to 推进, 领票,
  下一张票, 主管, process, planning, delivery, acceptance, arbitration, or
  继续工程. 推进 / 领票 / 下一张票 / 主管 / 继续工程 default to planning. Do not use to
  规划, 初始化, or 迁移.
---

# Engineering process

| Call | When | Done |
|---|---|---|
| **next** | Only asking for the next ticket | Print one pullable ticket URL |
| **supervise** | Advance / pull a ticket (default) | Planning: after 分发 stop; after 回传 / 决策 receipts follow **Stop** tables. Other department: employee receipts in hand, hop actions done, then stop |

Break a rule → **stop or fail**. Detail tables: [references/templates.md](references/templates.md)

## Layers

Two layers: **department** and **employee**. Do not skip. Do not call a department an employee. Do not call an employee a department.

Planning is a **department**, not a layer above departments. Other departments this process 分发: `delivery` / `acceptance` / `arbitration` / `human`.

| Layer | Who | Window | Does | Must not |
|---|---|---|---|---|
| **department (manage)** | planning | user entry: `parent_conversation_id` empty | talk to the user; **分发** one graph ticket to **another** department, then stop; or **决策**: staff `planning` implement + review, wait receipts, then stop | run delivery/acceptance/arbitration/human hops; run the phenomenon test; run patch; watch the other department; 分发 to itself; staff other departments' employees |
| **department (manage)** | delivery / acceptance / arbitration | `spawn.py --mode dispatch` child | one tree `issue:`; staff **employees** per 职责表; wait for each receipt; finish that hop; sessions **notify**; stop | 分发 another department; reset to planning; treat user 推进 as entry; finish after launching Task; do implement/review/verify work |
| **department (manage)** | human | `spawn.py --mode dispatch` child | one tree `issue:` (or main checkout if no tree); talk to the user: how to test and accept, and help; wait for pass/fail; sessions **notify** | staff implement/review/verify; 分发; treat user 推进 as entry |
| **employee** | implement / review / verify / datasheet extract | Task subagent only | the receipt | a conversation window; `spawn.py`; `git push`; `gh pr` |

**分发** = already-created graph ticket (init to-tickets) → write hop + `issue:` on the **ticket tree** → `planning` implement creates the tree if needed → `spawn.py --mode dispatch` that **other** department → report URL → **stop**. Do not watch.

**决策** = planning **manage** own hop. Stay. Staff `planning` implement (`engineering-init` **patch`) + `planning` review. Wait receipts. Do not run patch in this window. Do not spawn. After receipts: templates.md **Stop** tables (may 分发 once this turn).

## Entry

- User commands 推进 / 领票 / 下一张票 / 主管 / 继续工程 only on the **planning department**. Main checkout `template:` stays `planning`. Main `issue:` stays `none`.
- **Talk to the user:** planning **manage** and human **manage** only. Delivery / acceptance / arbitration do not. Planning: 推进, mode, `until`, `merge`, MODELS, next hop. Human: how to test and accept this gate, and help. Phenomenon replies belong on the **human** window; they are not 推进.
- **Planning session start.** This planning conversation has not confirmed yet, and the user text is not `engineering:report`: if `until:` is missing, write `until: none`. Print main `PROCESS.md` fields `mode` / `until` / `merge` / `verify` / `accept` and `MODELS.md`. Ask whether to use them. **Wait.** Do not 分发, do not 决策, do not treat 推进 / 领票 / 下一张票 / 主管 / 继续工程 as start. User confirms → later turns in this conversation may 推进. User changes a field → write it, then later turns may 推进. Later turns after confirm, and 回传, do not ask again. Other departments do not ask.
- `spawn.py --mode this` `parent_conversation_id` empty → planning department. Parent set and tree hop set → that **other** department (3a/3b/3d/3e only; skip 3c). Parent set and tree hop empty → **stop**.
- User typed 推进 on another department window → **stop**; say: command 推进 on the planning department. On **human**, keep helping with the test after that line.
- Other department window: one tree `issue:` only. After the hop (required receipts in this window and hop actions done), sessions `spawn.py --mode notify`, then **stop** (unless 返工 on that same department ticket). Notify fail → **fail**; do not finish as reported. Receipts missing → do not notify, do not finish.
- This turn's user text starts with `engineering:report` → **回传**, not 推进. Planning **manage** only. Latch still. Follow templates.md **Stop** tables (`mode` × `until`; hard stop wins). `hop: wait-merge` is a hard stop. Do not GET the child.
- After implement `#n` closed: first 分发 the unblocked `ready-for-human` blocked by `#n`, else the unblocked acceptance blocked by `#n`. Do not skip those for a sibling implement. None → hop table. Same class → smallest issue number. 返工 → 分发 delivery again on that implement ticket.

## Rules

1. Current repo = landing checkout (`master/` or `root/` under the imported container). Canvas cwd is imported. Detect per `engineering-init` canvas.md. Sessions `spawn.py --mode this` **before** `cd` checkout. Then `cd` that checkout before `PROCESS.md` / `gh` / landing `git`. Do not read `<imported>/docs/agents/`. `PROCESS.md` `contract:` is not `ready` → stop, go to `engineering-init` **plan** (or normalize migrate). Do not write the origin repo. Do not write process / current ticket / `mode` into `AGENTS.md`.
2. Layers as the table. Planning is a department. A department hop does not become another department in the same window. An employee is not 分发'd.
3. On the main checkout, read `docs/agents/PROCESS.md` first. Missing there → create per `engineering-init` process-stub, `contract: none`, then stop for init. Do not glob. `contract: ready` but no `docs/agents/MODELS.md` on that checkout → stop, init must fill the model table.
4. **`mode` / `until` latch.** File values stay. Missing `until:` → write `until: none`. Empty `mode` and `contract: ready` → the session-start confirm asks (semi-auto=`manual`, full-auto=`auto`) and writes. Planning session start (Entry) confirms `mode` / `until` / `merge` / `verify` / `accept` plus MODELS before any 推进 when this conversation has not confirmed yet. Later turns: change `mode` / `until` / `merge` only when the user explicitly asks. User names a stop → write `until:`. User clears it → `none`. Do not invent. Create/remove trees: rule 16. After a 分发, stop (do not watch). After 决策 receipts and after 回传: templates.md **Stop** tables only. Hard stop wins. Same class of pullable tickets → smallest issue number. After a **close**: first what that close unblocked (`human` then acceptance); none → hop table.
5. **`template`.** Main checkout: always `planning`. Empty → write `planning`. User named `delivery` / `acceptance` as the **entry** → still `planning`. Hop names live only on the **ticket tree**. Occupied tree `issue:` on another department window → do not reset that tree to planning.
6. Planning **manage** **分发** via sessions `spawn.py --mode dispatch` (**other** department). Then stop. Do not `openhands-watch`. That department's manage staffs employees via `engineering-routing` **delegate**; wait until each receipt is in that window. Datasheet extract only via `datasheet-headers` inside delivery. Do not copy POST. Do not write `dispatch_session.py`. Planning 决策 staffs only `planning implement` / `planning review`. Do not Task delivery / acceptance / arbitration / extract from planning. MODELS `dispatch` on employee rows → ignore; still delegate. No Task on the department bridge → fail; do not spawn an employee conversation. Do not GET child `/events/search`.
7. Employee kinds only from templates.md **职责表**: table "no" = must not staff; "yes" = must staff via that role as **delegate**. Only that department's **manage** staffs them. Manage is the window, not a Task.
8. One implement ticket = **exactly one** working-contains node. Multiple modules → stop, init must split. Do not open extra GitHub tickets for employees.
9. Ticket labels: `ready-for-human` only with `human`; `ready-for-agent` never `human`. Mismatch → stop.
10. Employee prompt contains only: ticket URL, **ticket-tree `cd` path first (prompt only, not Canvas `working_dir`)**, allowlist, constraints, done criteria, receipt shape, one line "follow repo `AGENTS.md` / `CONTEXT.md` / `docs/adr/` if present; do not ask semi-auto or full-auto; do not git push; do not `gh pr`". `planning` implement may read `PROCESS.md` and run `engineering-init` **patch**; must not write `mode` / main `template`. Other employees must not read or edit PROCESS.md. Add a HANDOFF path line only if `HANDOFF.md` exists. Opening a child conversation for an employee → **fail**.
11. `HANDOFF.md` default do not create. Allowed: crash and ticket still open; this **department** window hit **300** and ticket still open; hardware on-site. Employees do not use 300. Other department at 300 → write HANDOFF; next planning 推进 **分发** the same department on that ticket. Planning department at 300 during 决策 → write HANDOFF; next 推进 continues **决策**.
12. Human send-back: the **human** department (3a) reopens the previous implement ticket. Read `engineering-init` contract. Do not turn a gate ticket into `ready-for-agent`. Planning implement / patch must not reopen on human fail.
13. **One department window, one ticket.** Tree `issue:` is one number. Planning main `issue:` is `none`. Parallel line = another 分发 (another 推进 on planning) or another planning window. Do not write two issues on one tree `PROCESS.md`.
14. **Do not pull downstream while upstream is still blocking.** `blockedBy` still has open → do not 分发, do not work. User named it → still stop; report the blocking upstream. Unblock = those tickets are **closed**. Do not unblock with `remove-blocked-by`.
15. **PR only on a graph acceptance ticket.** Body contains `engineering:pr`. Not holding that ticket → no `gh pr`. Implement and gate tickets must not open/merge PRs. Do not switch the same ticket to acceptance.
16. **worktree.** Read and run [references/worktree.md](references/worktree.md). `planning` implement creates the tree before 分发. `acceptance` implement merges heads and removes trees after merge. Trees go under the Canvas container `worktree/`. Not wrapped → stop, init canvas.md. Do not POST sessions `worktree: true`. Do not POST a tree path as `working_dir`. Do not POST an **employee** conversation. Other department window = `spawn.py` dispatch. Manage must not run `git worktree`.
17. **`MODELS` latch.** Planning session start (Entry): print `docs/agents/MODELS.md` with the PROCESS fields; wait for confirm. Later turns: print the table; do not wait unless `confirmed:` is not `yes`. User confirms → `confirmed: yes`. User changes a cell → write and `confirmed: yes`. Follow the **targets**. Format is the n×m grid in models-stub (department × manage/implement/review/verify). Employee cells: use that cell's target; ignore a `dispatch` link. Planning manage cell: `stay`. Other department manage cells: `dispatch` + spawnable profile; 分发 uses that target. File has `supervisor` and no `planning` → treat that as planning manage `stay`. Missing other-department manage cell → 分发 uses this conversation's spawnable profile. Do not refill the table unless the user changes a cell. Other departments: do not ask; follow targets.
18. **Employees (forced).** Roles `planning implement` / `planning review` / `delivery implement` / `delivery review` / `delivery verify` / `acceptance implement` / `acceptance review` / `acceptance verify` / `arbitration implement` / `arbitration review` / `arbitration verify` / `datasheet extract` = **delegate**, and only from the matching **department manage**. MODELS says `dispatch` on those cells → ignore; still delegate. No Task → fail; do not spawn an employee conversation. Wait until each receipt is in this conversation. Background Task → **fail**. Receipt missing → **fail**; do not finish. Manage must not do that work in the window.

## Key points

Manage windows must not: edit product files, run patch, merge heads, open PDFs, paste datasheets / all three graphs / other modules' source, open an employee conversation window, `GET` child-session events, change contains/uses, clone the origin repo, `gh` the origin repo. Touching product paths in the editor / whole-repo format → **fail**.

Duties: templates.md **职责表**.

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

1. **Disputed review finding:** `partial` / `dispute` under templates.md **Review disposition**, or `dispute-repeated` from its `post-rework-disposition` state. Arbitrate only the disputed finding IDs selected by that flow.
2. **Employee challenge:** implement or review explicitly challenges the contract or upstream (`Challenge: upstream #<n>` or `contract`).
3. **User challenge:** the user challenges this ticket's implementation.

An ordinary implement `Result: pass` plus blocking review `Result: fail` is not arbitration; follow templates.md **Review disposition** first. Direct arbitration is only paths 2–3. **Verify is not a trigger.** Delivery/acceptance verify has no `Challenge` field. `verify:`/`accept:` fail → send implement back or isolate; do not 分发 3b. Command green with extra notes → write a ticket comment; delivery may still pass. If verify writes `Challenge` anyway → treat it as `Notes`; do not enter 3b.

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

Path: `docs/agents/MODELS.md` (follows the default branch; do not invent a copy on the ticket tree). Format: `engineering-init` models-stub n×m grid. Missing → stop, init must fill. Planning session start prints the table with PROCESS fields and waits (rule 17 / Entry). Later turns print; wait only if `confirmed:` is not `yes`. Planning **manage** 决策 uses the planning manage cell (`stay`) then staffs the planning implement / review cells. 分发 uses the **other** department manage cell then sessions **dispatch**. Employee staffing uses that department's implement / review / verify cell then sessions **delegate**.

### When to stop

Planning session start before the user confirms PROCESS modes + MODELS → **stop** (wait). Continue or stop after 回传 / 决策 receipts: templates.md **Stop** tables only. Hard stop wins.

- Planning department after 分发: report the other department URL, **stop**. Do not watch. Do not run 3a–3e.
- Other department hop finished: required employee receipts are in this window and hop actions are done. Then sessions **notify**. Then **stop**. Notify fail → **fail**. Receipts missing → do not notify, do not finish. Launching Task is not hop finished.
- `human` department: tell the user how to test and accept; help; wait for pass/fail. Then notify. Do not notify after the first help turn.
- `merge: human` PR opened → notify `hop: wait-merge`; keep the acceptance ticket open. Planning 回传 of `wait-merge` is a hard stop.
- Upstream-bug verdict: planning implement opens the bug tickets; if the next hop is 分发, the **Stop** tables may 分发 this turn (not the delivery department that found the bug).

One 分发 = one department hop. Do not switch hop in that window. Delivery must not switch the same ticket to acceptance.

## Steps: next

`issue:` already set on **this department tree**, ticket still open, not paused → print that one; do not list another.

Else (planning): scan

- after implement `#n` closed: tickets `#n` blocked (`ready-for-human` first, else `engineering:pr`); none → unblocked `ready-for-human` first; else unblocked `ready-for-agent`
- else: unblocked `ready-for-human` first; else unblocked `ready-for-agent`
- same class → smallest issue number

```
gh issue list --label <label> --state open --limit 50 --json number,title,url,blockedBy
```

Keep only unblocked: `blockedBy` empty, or every item closed. Open upstream → drop it. No ticket → stop; report still-open sinks (may be more than one).

## Steps: supervise

1. **Latch.** Detect per canvas.md. Print imported / `master` or `root` / `worktree`. Not wrapped → stop, init canvas.md. Run sessions `spawn.py --mode this` **before** `cd` checkout (cwd may be imported or `master/` / `root/`; the script matches both). Parent empty → planning department (main `template: planning`, `issue: none`). Parent set → read the ticket-tree `PROCESS.md`; hop empty → stop; hop is `planning` → **stop** (planning department is not a child); hop is delivery/acceptance/arbitration/human → that department, skip to step 3. Then `cd` main checkout. Then read main `PROCESS.md` / `MODELS.md` (rules 1, 3–4, 17). Missing MODELS → stop, init must fill. Planning and this turn is not `engineering:report` and this conversation has not confirmed yet → Entry **Planning session start** (print PROCESS fields + MODELS; **wait**; do not go to step 2). User typed 推进 on another department window → **stop**, Entry. This turn starts with `engineering:report` → Entry 回传 (templates.md **Stop** tables).
2. **Planning department: 决策 or 分发.** Main `issue:` stays `none`. Run next (one ticket). If that ticket's tree already has `issue:` = this number, ticket still open, and `template:` is a department hop → use that hop (do not recompute). Else hop from templates.md "hop from the ticket":
   - hop `planning` → **决策** (this department's hop): run 3c. Do not write a tree hop. Do not spawn. Then "When to stop".
   - else → **分发** to **another** department: write hop + `issue:` on that **ticket tree**. Just closed implement `#n` → prefer a ticket `#n` blocked (human then acceptance). None → hop table. Named sibling implement while a `#n`-blocked human/acceptance is still open → **stop**. `blockedBy` still open → stop. Paused → stop. Implement or acceptance tree missing → staff `planning implement` to create it per worktree.md; wait that receipt; manage must not run `git worktree`. `spawn.py --mode dispatch` that department (prompt: this child is that department **manage**; staff employees per 职责表; wait until each receipt is in that window; then sessions **notify**; stop). Report URL. **Stop.** Do not watch. Do not Task delivery implement.
3. **Other department hop** (3a / 3b / 3d / 3e from the **tree** `template` only; never 3c). Staff employees **delegate** (read and run `engineering-routing`). Wait until each receipt is in this conversation before the next employee or hop action. Background Task → **fail**. Receipts missing → do not update hop-done fields, do not notify, do not finish. After receipts and hop actions: update that tree `PROCESS.md` (disk only; **do not git add**). Write `engineering:report` and run sessions `spawn.py --mode notify`. Notify fail → **fail**. Then "When to stop".

### 3a. `human` (department)

Talk to the user. Tell them how to test and accept this gate (what to run or look at, what pass looks like). Help if they ask. Write comments as needed. Do not staff employees. Do not 分发. Do not notify until the person said pass or fail.

Person said fail → reopen the previous implement ticket and send it back to `ready-for-agent`. Do not turn the gate ticket into `ready-for-agent`. Tree `issue: none`. Run `python <engineering-init>/scripts/render_graph.py --issue <spec> --write` (spec = `Part of #<n>` on this ticket). Script fail → **fail**. Notify (`hop: send-back`, suggested next 分发 delivery). Person said the phenomenon passed → close **this** gate or sink, `issue: none`, run the same graph write, notify (`hop: done`).

### 3b. `arbitration` (department)

Staff implement + review via MODELS (**delegate**). If `verify:` is not `none`, staff verify via MODELS (**delegate**). Roles: `arbitration implement` / `arbitration review` / `arbitration verify`. Wait until each staffed receipt is in this conversation. Receipts missing → do not write a verdict, do not finish. Manage writes the verdict comment only after receipts. No product-code edits, no commit/push, no open/merge PR. No datasheet extract. Do not spawn a child conversation.

implement: reproduce, give an arbitration opinion, do not fix. review: review that opinion only. verify: run `verify:`; check whether reproduction holds. `none` → `Verify: none`.

implement receipt:

```
Reproduction:
Evidence path:
Opinion: send-back | change-contract | upstream-bug | review-wrong
Suggested edits: <ticket list or none>
Challenge target: <this ticket | upstream #<n> | contract>
Result: pass | fail
Failure:
```

review receipt: `Review: agree | reject`, `Result: pass | fail`. verify receipt: `Verify: holds | does-not-hold | none`.

- Reproduction does not hold → do not write a verdict; stop and report to the person.
- review rejects → same-ticket implement submits the opinion once more. Second reject → stop and report to the person. Do not nest arbitration.
- review agrees and reproduction holds or `none` → **arbitration manage** writes the verdict as an issue comment:

```
Reproduction:
Evidence path:
Verdict: send-back | change-contract | upstream-bug | review-wrong
Suggested edits: <ticket list or none>
Hand to: planning
```

`Verdict: review-wrong` and the implement ticket still open → write tree `template: delivery` and `issue:` that implement (suggested next 分发 delivery). Other verdicts → write tree `issue: none` (suggested next 决策). Notify. Stop.

### 3c. `planning` (planning **manage** 决策)

`contract` is not `ready` → stop, go to plan. Already `ready`: staff `planning implement` then `planning review` (**delegate**). Prompt implement: ticket URLs, read and run `engineering-init` **patch**, receipt (include whether spec `engineering:graph` was written). Edges changed and graph not written → receipt incomplete; do not finish. Review checks the spec flow graph has the new nodes and edges. Do not run patch in this window. No open/merge PR. No product-code edits by manage. Do not staff delivery / acceptance / arbitration employees. Wait until both receipts are in this conversation; receipts missing → do not finish. No `spawn.py`. Changing layers / breaking a cycle / migrate → stop, go to plan or migrate.

Implement does the patch (verdict, new need, fill tests, pause/resume, rewrite spec `engineering:graph` when tickets or edges change). Review reviews that output and the spec graph. Manage does not edit issue bodies or `blocked-by`. Does not run `render_graph.py`.

After implement receipt:

- Verdict "send-back" → next hop is 分发 delivery on that ticket.
- Verdict "change-contract" (not upstream-bug) → hard stop (person must confirm).
- Verdict "upstream-bug" → planning implement opens the bug tickets; next hop is 分发 that bug implement (not the department that found the bug).
- Resume done → next hop is 分发 if any.

Then templates.md **Stop** tables (After 决策 receipts).

### 3d. `delivery` (department)

Current ticket body contains `engineering:pr` → stop; that is 3e.

Need headers → `datasheet-headers` (inside this implement ticket; no separate extract ticket; role `datasheet extract`), then staff implement and review (**delegate**) (roles `delivery implement` / `delivery review`). Wait for each receipt before the next step. Staff `delivery verify` only after review passes. Receipts required by the chosen path must be in this conversation before push, close, or notify. implement may add+commit only; no push. verify runs `verify:`. Manage must not edit product files. No open/merge PR. Do not close gate or acceptance tickets. Do not resubmit a rejected implementation unchanged. Do not spawn a child conversation.

implement receipt:

```
Changed paths:
Verify:
Challenge: none | upstream #<n> | contract
Result: pass | fail
Failure:
```

review pass receipt uses the same shape. A blocking review fail instead returns structured findings from templates.md **Review disposition**. Follow that flow in this delivery window with the original implement employee; do not notify between disposition, focused rework, and fresh review.

verify receipt (no `Challenge`):

```
Verify: pass | fail | none
Notes: <none or observations>
Failure:
```

Review pass with non-blocking notes remains pass; copy Notes to a ticket comment. Blocking review failure skips verify. After review passes, staff verify. Command ran but did not cover this module, or assertions are vacuous → verify `fail` (send implement back). Command green; notes are about later tightness → `pass` plus `Notes`; department copies Notes to a ticket comment. Do not 分发 arbitration.

verify=`fail` (when a command exists), implement=`fail` and paths 2–3 did not fire, or a blocking finding accepted on fresh review still fails → do not push, do not close, send back to `ready-for-agent`. Tree `issue: none`. Notify (`hop: send-back`). Stop.

implement=`pass` and review=`pass` and (`verify: none` or pass) → **delivery manage** `git push -u origin HEAD` → **close this implement ticket**. Tree `issue: none`. Run `python <engineering-init>/scripts/render_graph.py --issue <spec> --write` (spec = `Part of #<n>` on this ticket). Script fail → **fail**. Notify (`hop: done`). Do not open a PR. Do not change gate-ticket edges. Stop.

A disposition with `Action: arbitration`, the same finding disputed after focused rework, an explicit contract/upstream challenge, or a user challenge → do not push; write tree `template: arbitration`; keep `issue:`; notify (`hop: need-arbitration`). Include only disputed finding IDs and preserve accepted fixes and prior valid receipts. Do not run 3b in this window. Next planning 推进 **分发** arbitration (tree hop already set).

### 3e. `acceptance` (department)

Current ticket body has no `engineering:pr` → stop; no PR.

Do not edit product code in this window. Staff implement + review + verify (**delegate**) (roles `acceptance implement` / `acceptance review` / `acceptance verify`). Wait until those receipts are in this conversation. Receipts missing → do not open/merge a PR, do not finish. implement merges `engineering:heads` and worktrees per worktree.md. `accept:` is `none` or empty → verify receipt `Verify: none`, issue comment "full suite unset", **still may open a PR**. Command present → acceptance verify runs `accept:`. Acceptance verify has no `Challenge`; do not enter 3b from this hop. Do not spawn a child conversation.

`accept:` failed → staff acceptance implement for leave-one-out isolation per templates.md (this ticket heads ≤4; if the accused is `merge/<child-acceptance>`, recurse that child). Then `issue: none`. Run `python <engineering-init>/scripts/render_graph.py --issue <spec> --write`. Do not edit product code on this ticket. Notify (`hop: blocked`). Stop.

User said it already merged → confirm the default branch contains the commits → close this acceptance.

Else passed → **acceptance manage** opens a PR from `engineering:heads` (one head: that branch after implement merged if needed; several: implement created `merge/<this-acceptance>` and merged the list). `Fixes #<n>` n=this acceptance. List empty → stop, fill heads. PR already open and not merged → do not open another; notify (`hop: wait-merge`); stop. `merge: auto` → manage merges the PR then close the acceptance. `merge: human` → open, keep this ticket open, notify (`hop: wait-merge`); stop.

If this acceptance is a bugfix: after close, list downstream with `paused-by` this acceptance; notify (`suggested next: 决策` resume). Do not 分发 those downstream tickets.

After closing acceptance: tree `issue: none`. Staff acceptance implement to remove merged implement trees and the acceptance tree per worktree.md. Run `python <engineering-init>/scripts/render_graph.py --issue <spec> --write` (spec = `Part of #<n>` on this ticket). Script fail → **fail**. Notify (`hop: done`). Stop.
