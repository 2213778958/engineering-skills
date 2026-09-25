# Supervise

## Layers

Two layers: **department** and **employee**. Do not skip. Do not call a department an employee. Do not call an employee a department.

Planning is a **department**, not a layer above departments. Other departments this process 分发: `delivery` / `acceptance` / `arbitration` / `human`.

| Layer | Who | Window | Does | Must not |
|---|---|---|---|---|
| **department (manage)** | planning | user entry: `parent_conversation_id` empty | talk to the user; **分发** one ticket to **another** department, then stop; or **决策**: staff `planning` implement + review, wait receipts, then stop | run delivery/acceptance/arbitration/human hops; run the phenomenon test; run patch; watch the other department; 分发 to itself; staff other departments' employees |
| **department (manage)** | delivery / acceptance / arbitration | `spawn.py --mode dispatch` child | one tree `issue:`; staff **employees** per 职责表; wait for each receipt; finish that hop; sessions **notify**; stop | 分发 another department; reset to planning; treat user 推进 as entry; finish after launching Task; do implement/review/verify work |
| **department (manage)** | human | `spawn.py --mode dispatch` child | one tree `issue:` (or main checkout if no tree); talk to the user: how to test and accept, and help; wait for pass/fail; sessions **notify** | staff implement/review/verify; 分发; treat user 推进 as entry |
| **employee** | implement / review / verify / research | Task subagent only | the receipt | a conversation window; `spawn.py`; `git push`; `gh pr` |

**分发** = already-created ticket (init to-tickets) → write hop + `issue:` on the **ticket tree** → `planning` implement creates the tree if needed → `spawn.py --mode dispatch` that **other** department → report URL → **stop**. Do not watch.

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

## When to stop

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
gh issue view <n> --json blockedBy,subIssues
```

GitHub-native ordering only. Keep only unblocked: `blockedBy` empty or every item closed, and no open sub-issue parent above (an open parent sub-issue blocks its children, matching GitHub sub-issue `blocked` semantics). Open upstream → drop it. No ticket → stop; report still-open sinks (may be more than one).

## Steps: supervise

1. **Latch.** Detect per canvas.md. Print imported / `master` or `root` / `worktree`. Not wrapped → stop, init canvas.md. Run sessions `spawn.py --mode this` **before** `cd` checkout (cwd may be imported or `master/` / `root/`; the script matches both). Parent empty → planning department (main `template: planning`, `issue: none`). Parent set → read the ticket-tree `PROCESS.md`; hop empty → stop; hop is `planning` → **stop** (planning department is not a child); hop is delivery/acceptance/arbitration/human → that department, skip to step 3. Then `cd` main checkout. Then read main `PROCESS.md` / `MODELS.md` (rules 1, 3–4, 17). Missing MODELS → stop, init must fill. Planning and this turn is not `engineering:report` and this conversation has not confirmed yet → Entry **Planning session start** (print PROCESS fields + MODELS; **wait**; do not go to step 2). User typed 推进 on another department window → **stop**, Entry. This turn starts with `engineering:report` → Entry 回传 (templates.md **Stop** tables).
2. **Planning department: 决策 or 分发.** Main `issue:` stays `none`. Run next (one ticket). If that ticket's tree already has `issue:` = this number, ticket still open, and `template:` is a department hop → use that hop (do not recompute). Else hop from templates.md "hop from the ticket":
   - hop `planning` → **决策** (this department's hop): run 3c. Do not write a tree hop. Do not spawn. Then "When to stop" above.
   - else → **分发** to **another** department: write hop + `issue:` on that **ticket tree**. Just closed implement `#n` → prefer a ticket `#n` blocked (human then acceptance). None → hop table. Named sibling implement while a `#n`-blocked human/acceptance is still open → **stop**. `blockedBy` still open → stop. Paused → stop. Implement or acceptance tree missing → staff `planning implement` to create it per worktree.md; wait that receipt; manage must not run `git worktree`. `spawn.py --mode dispatch` that department (prompt: this child is that department **manage**; staff employees per 职责表; wait until each receipt is in that window; then sessions **notify**; stop). Report URL. **Stop.** Do not watch. Do not Task delivery implement.
3. **Other department hop** (3a / 3b / 3d / 3e from the **tree** `template` only; never 3c). Staff employees **delegate** (read and run `engineering-routing`). Wait until each receipt is in this conversation before the next employee or hop action. Background Task → **fail**. Receipts missing → do not update hop-done fields, do not notify, do not finish. After receipts and hop actions: update that tree `PROCESS.md` (disk only; **do not git add**). Write `engineering:report` and run sessions `spawn.py --mode notify`. Notify fail → **fail**. Then "When to stop" above.
