# Supervise

## Layers

Two layers: **department** and **employee**. Do not skip. Do not call a department an employee. Do not call an employee a department.

Planning is a **department**, not a layer above departments. Other departments this process hands off to: `delivery` / `acceptance` / `arbitration` / `human`.

| Layer | Who | Window | Does | Must not |
|---|---|---|---|---|
| **department (manage)** | planning | user entry: `parent_conversation_id` empty | talk to the user; **hand off** one ticket to **another** department, then stop; or **decide**: staff `planning` implement + review, wait receipts, then stop | run delivery/acceptance/arbitration/human hops; run the phenomenon test; run patch; watch the other department; hand off to itself; staff other departments' employees |
| **department (manage)** | delivery / acceptance / arbitration | `spawn.py --mode dispatch` child | one tree `issue:`; staff **employees** per duty table; wait for each receipt; finish that hop; sessions **notify**; stop | hand off to another department; reset to planning; treat an advance request as entry; finish after launching Task; do implement/review/verify work |
| **department (manage)** | human | `spawn.py --mode dispatch` child | one tree `issue:` (or main checkout if no tree); talk to the user: how to test and accept, and help; wait for pass/fail; sessions **notify** | staff implement/review/verify; hand off; treat an advance request as entry |
| **employee** | implement / review / verify / research | Task subagent only | the receipt | a conversation window; `spawn.py`; `git push` (except research synthesis → external `research/` repo); `gh pr` |

**hand off** = already-created ticket (init to-tickets) → write hop + `issue:` on the **ticket tree** → `planning` implement creates the tree if needed → `spawn.py --mode dispatch` that **other** department → report URL → **stop**. Do not watch.

**decide** = planning **manage** own hop. Stay. Staff `planning` implement (`engineering-init` **patch`) + `planning` review. Wait receipts. Do not run patch in this window. Do not spawn. After receipts: templates.md **Stop** tables (may hand off once this turn).

## Entry

- **Advance request** = the user asks to move the project forward: continue, take or pull the next ticket, supervise (e.g. "推进", "领票", "下一张票", "主管", "继续工程", "advance", "next ticket", "keep going"). Judge by intent, not wording; unclear → planning / human manage ask the user; other departments stop. Advance requests act only on the **planning department**. Main checkout `template:` stays `planning`. Main `issue:` stays `none`.
- **Talk to the user:** planning **manage** and human **manage** only. Delivery / acceptance / arbitration do not. Planning: advance, mode, `until`, `merge`, MODELS, next hop. Human: how to test and accept this gate, and help. Phenomenon replies belong on the **human** window; they are not an advance request.
- **Planning session start.** This planning conversation has not confirmed yet, and the user text is not `engineering:report`: if `until:` is missing, write `until: none`. Print main `PROCESS.md` fields `mode` / `until` / `merge` / `verify` / `accept` and `MODELS.md`. Ask whether to use them. **Wait.** Do not hand off, do not decide, do not treat an advance request as start. User confirms → later turns in this conversation may advance. User changes a field → write it, then later turns may advance. Later turns after confirm, and report back, do not ask again. Other departments do not ask.
- `spawn.py --mode this` `parent_conversation_id` empty → planning department. Parent set and tree hop set → that **other** department (3a/3b/3d/3e only; skip 3c). Parent set and tree hop empty → **stop**.
- An advance request on another department window → **stop**; say: ask to advance on the planning department. On **human**, keep helping with the test after that line.
- Other department window: one tree `issue:` only. After the hop (required receipts in this window and hop actions done), sessions `spawn.py --mode notify`, then **stop** (unless rework on that same department ticket). Notify fail → **fail**; do not finish as reported. Receipts missing → do not notify, do not finish.
- This turn's user text starts with `engineering:report` → **report back**, not an advance request. Planning **manage** only. Latch still. Follow templates.md **Stop** tables (`mode` × `until`; hard stop wins). `hop: wait-merge` is a hard stop. Do not GET the child.
- After implement `#n` closed: first hand off the unblocked `ready-for-human` blocked by `#n`, else the unblocked acceptance blocked by `#n`. Do not skip those for a sibling implement. None → hop table. Same class → smallest issue number. Rework → hand off to delivery again on that implement ticket.

## When to stop

Planning session start before the user confirms PROCESS modes + MODELS → **stop** (wait). Continue or stop after report back / decide receipts: templates.md **Stop** tables only. Hard stop wins.

- Planning department after handoff: report the other department URL, **stop**. Do not watch. Do not run 3a–3e.
- Other department hop finished: required employee receipts are in this window and hop actions are done. Then sessions **notify**. Then **stop**. Notify fail → **fail**. Receipts missing → do not notify, do not finish. Launching Task is not hop finished.
- `human` department: tell the user how to test and accept; help; wait for pass/fail. Then notify. Do not notify after the first help turn.
- `merge: human` PR opened → notify `hop: wait-merge`; keep the acceptance ticket open. Planning report back of `wait-merge` is a hard stop.
- Upstream-bug verdict: planning implement opens the bug tickets; if the next hop is hand off, the **Stop** tables may hand off this turn (not the delivery department that found the bug).

One handoff = one department hop. Do not switch hop in that window. Delivery must not switch the same ticket to acceptance.

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

1. **Latch.** Detect per canvas.md. Print imported / `master` or `root` / `worktree`. Not wrapped → stop, init canvas.md. Run sessions `spawn.py --mode this` **before** `cd` checkout (cwd may be imported or `master/` / `root/`; the script matches both). Parent empty → planning department (main `template: planning`, `issue: none`). Parent set → read the ticket-tree `PROCESS.md`; hop empty → stop; hop is `planning` → **stop** (planning department is not a child); hop is delivery/acceptance/arbitration/human → that department, skip to step 3. Then `cd` main checkout. Then read main `PROCESS.md` / `MODELS.md` (rules 1, 3–4, 17). Missing MODELS → stop, init must fill. Planning and this turn is not `engineering:report` and this conversation has not confirmed yet → Entry **Planning session start** (print PROCESS fields + MODELS; **wait**; do not go to step 2). An advance request on another department window → **stop**, Entry. This turn starts with `engineering:report` → Entry report back (templates.md **Stop** tables).
2. **Planning department: decide or hand off.** Main `issue:` stays `none`. Run next (one ticket). If that ticket's tree already has `issue:` = this number, ticket still open, and `template:` is a department hop → use that hop (do not recompute). Else hop from templates.md "hop from the ticket":
   - hop `planning` → **decide** (this department's hop): run 3c. Do not write a tree hop. Do not spawn. Then "When to stop" above.
   - else → **hand off** to **another** department: write hop + `issue:` on that **ticket tree**. Just closed implement `#n` → prefer a ticket `#n` blocked (human then acceptance). None → hop table. Named sibling implement while a `#n`-blocked human/acceptance is still open → **stop**. `blockedBy` still open → stop. Paused → stop. Implement or acceptance tree missing → staff `planning implement` to create it per worktree.md; wait that receipt; manage must not run `git worktree`. `spawn.py --mode dispatch` that department (prompt: this child is that department **manage**; staff employees per duty table; wait until each receipt is in that window; then sessions **notify**; stop). Report URL. **Stop.** Do not watch. Do not Task delivery implement.
3. **Other department hop** (3a / 3b / 3d / 3e from the **tree** `template` only; never 3c). Staff employees **delegate** (read and run `engineering-routing`). Wait until each receipt is in this conversation before the next employee or hop action. Background Task → **fail**. Receipts missing → do not update hop-done fields, do not notify, do not finish. After receipts and hop actions: update that tree `PROCESS.md` (disk only; **do not git add**). Write `engineering:report` and run sessions `spawn.py --mode notify`. Notify fail → **fail**. Then "When to stop" above.
