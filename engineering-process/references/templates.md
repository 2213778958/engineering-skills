# Templates

**Department** `template` on the ticket tree picks the hop. Duties: this **职责表** only. Five departments × four employee kinds. Datasheet extract is not a column (`datasheet-headers` from delivery only). Never a child conversation for an employee.

**manage** = this department window. Not a Task. **implement** / **review** / **verify** = **delegate**. Table "yes" = that manage must staff that role. Manage must not do implement / review / verify work.

## 职责表

| | manage | implement | review | verify |
|---|---|---|---|---|
| **planning** | yes | yes | yes | no |
| **delivery** | yes | yes | yes | yes |
| **acceptance** | yes | yes | yes | yes |
| **arbitration** | yes | yes | yes | if `verify:` set |
| **human** | yes | no | no | no |

| Department | manage | implement | review | verify |
|---|---|---|---|---|
| **planning** | talk to the user; this conversation has not confirmed yet (not 回传): write missing `until: none`, print `mode` / `until` / `merge` / `verify` / `accept` + MODELS, wait for confirm, then 推进; 分发 other departments; staff this department's employees; collect receipts; after 分发 stop; after 回传 / 决策 receipts follow **Stop** tables | 决策 technical: `engineering-init` **patch**, apply verdict, pause/resume, open bug tickets, comment pull again; create the ticket tree before 分发 | review the planning implement output | — |
| **delivery** | staff employees; after receipts `git push` and close this implement ticket; sessions **notify** | product code + `git commit` (no push) | review the implementation | run `verify:` |
| **acceptance** | staff employees; after receipts `gh pr` / honor `merge:`; close this acceptance; sessions **notify** | merge `engineering:heads`: create `merge/<n>` if needed, merge heads, worktree add/remove per worktree.md | review merge / PR scope | run `accept:` (`none` may still open a PR) |
| **arbitration** | staff employees; after receipts write the verdict comment; sessions **notify** (next hop is 决策) | reproduce + opinion; no product-code edits | review the opinion | run `verify:`; check whether reproduction holds |
| **human** | talk to the user: how to test and accept this gate, and help them do it; write comments; pass → close this gate/sink; fail → reopen implement; sessions **notify** | — | — | — |

## Rules

- Employee kinds follow this 职责表. Datasheet extract is not a column: when needed, run `datasheet-headers` on the **delivery** department's implement ticket; not under `human` / `arbitration` / `planning` / `acceptance`. Do not open a separate extract ticket.
- Before staffing, take the target from the `MODELS.md` employee cell (department × duty), then `engineering-routing`. Ignore a `dispatch` link on employee cells. Do not pick a subagent outside the catalog unless the user named one. Do not rewrite delegate to a child conversation. Wait until each employee receipt is in the department window. Background Task → **fail**. Launching Task is not hop finished.
- 决策 technical work only by `planning` **implement**. From arbitration, apply the verdict; do not change it. Planning **manage** staffs that implement + review; does not run patch. Open/merge PR only by `acceptance` **manage**, and only if the ticket body has `engineering:pr`. Product-code edits only by the `delivery` implement **employee**. Heads merge / worktree git only by `acceptance` implement.
- Arbitration: implement employee reproduces + opinion; review reviews the opinion; verify checks reproduction if a command exists. The verdict is written by the arbitration **department**. planning does not judge.
- Enter arbitration only on the paths in `SKILL.md` Key points and **Review disposition** below. Delivery department reports those paths; planning **分发** arbitration. Delivery verify is not a trigger and has no `Challenge` field.
- `git push` only the delivery **manage**, and only after delivery verify passed.
- Unblock = close upstream tickets. Do not unblock with `remove-blocked-by`.
- worktrees: `planning` implement creates them before 分发; `acceptance` implement removes after merge. Both semi-auto and full-auto. Under the Canvas container `worktree/`. See [worktree.md](worktree.md). Do not POST `worktree: true`. Do not POST a tree path as `working_dir`.
- After a 分发 → **stop**. Do not watch. After 回传 / 决策 receipts → **Stop** tables. After a **close**: first a ticket that close unblocked (`human` then acceptance); none → hop table. Same class → smallest issue number.
- Close or reopen actions write no graph. Ticket order comes from GitHub-native relationships only (`blockedBy` + open sub-issue parent blocks its children). Human review fail: only the **human** department reopens the implement ticket (3a).
- Parallel = another 分发 (another 推进 on the planning department) or another planning department window. Not two tickets in one tree `PROCESS.md`.
- Do not 分发 downstream while upstream still blocks. Named tickets neither.

## Review disposition

Delivery staffs implement, then review, and staffs verify only after review passes. Review pass with non-blocking notes remains a pass; copy the notes to the ticket comment, with no rework or arbitration. Blocking review failure skips verify.

A blocking review failure returns findings to the original implement employee. Each finding is one block with a stable ID that remains unchanged across rework and fresh review:

```
ID: <stable finding ID>
Category: <contract | correctness | test | quality | scope>
Evidence: <contract/code evidence>
Required behavior: <observable behavior required to pass>
```

The original implement employee returns exactly this disposition, with the accepted and disputed IDs partitioning every blocking finding ID:

```
Review disposition: accept | partial | dispute
Accepted findings: <stable finding IDs or none>
Disputed findings: <stable finding IDs or none>
Reason: <contract/code evidence>
Action: rework | arbitration
```

Follow this canonical transition table. Every transition preserves `prior-work`: existing commits, current context, valid receipts, and unrelated completed work.

| Current state | Event | Next state | Arbitration scope | Preserve |
| --- | --- | --- | --- | --- |
| `implementation` | `review-pass` | `verify` | `none` | `prior-work` |
| `implementation` | `blocking-review-fail` | `disposition` | `none` | `prior-work` |
| `implementation` | `review-contract-challenge` | `disposition` | `none` | `prior-work` |
| `implementation` | `review-upstream-challenge` | `disposition` | `none` | `prior-work` |
| `implementation` | `implement-contract-challenge` | `arbitration` | `challenged-only` | `prior-work+accepted-fixes` |
| `implementation` | `implement-upstream-challenge` | `arbitration` | `challenged-only` | `prior-work+accepted-fixes` |
| `implementation` | `user-challenge` | `arbitration` | `challenged-only` | `prior-work+accepted-fixes` |
| `disposition` | `accept-all` | `focused-rework` | `none` | `prior-work` |
| `disposition` | `partial` | `arbitration` | `disputed-only` | `prior-work+accepted-fixes` |
| `disposition` | `dispute-all` | `arbitration` | `disputed-only` | `prior-work` |
| `focused-rework` | `rework-complete` | `fresh-review` | `none` | `prior-work` |
| `fresh-review` | `review-pass` | `verify` | `none` | `prior-work` |
| `fresh-review` | `same-finding-blocking-fail` | `post-rework-disposition` | `none` | `prior-work+accepted-fixes` |
| `fresh-review` | `review-contract-challenge` | `post-rework-disposition` | `none` | `prior-work+accepted-fixes` |
| `fresh-review` | `review-upstream-challenge` | `post-rework-disposition` | `none` | `prior-work+accepted-fixes` |
| `post-rework-disposition` | `accept-repeated` | `send-back` | `none` | `prior-work+accepted-fixes` |
| `post-rework-disposition` | `partial` | `arbitration` | `repeated-disputed-only` | `prior-work+accepted-fixes` |
| `post-rework-disposition` | `dispute-repeated` | `arbitration` | `repeated-disputed-only` | `prior-work+accepted-fixes` |

`accept-all` requires `Review disposition: accept` and `Action: rework`; the same implement employee performs focused rework and receives a fresh review without arbitration. On a fresh blocking review of the same stable finding, the original implement employee returns a new disposition in `post-rework-disposition`. Accepting all repeated findings sends delivery back. A `partial` disposition sends only repeated disputed stable IDs to arbitration and preserves accepted fixes; `dispute-repeated` sends all repeated disputed stable IDs to arbitration. There is no transition from `post-rework-disposition` to `focused-rework`, so the same-finding loop is bounded.

`partial` requires both accepted and disputed IDs and `Action: arbitration`. `dispute-all` requires disputed IDs only and `Action: arbitration`. Accepted independent findings may be fixed without re-litigating them. A review-originated contract or upstream challenge is a blocking review result and must return to the original implement employee for disposition. Only an implement-originated contract or upstream challenge, or a user challenge, takes direct arbitration without a disposition. Blocking review failure has no transition to verify; review pass with non-blocking notes takes `review-pass`, remains a pass, and copies the notes to the ticket comment.

A malformed disposition or findings without all four fields are incomplete receipts. Do not staff verify, push, close, or notify until corrected. Arbitration receives only the finding blocks selected by the table's arbitration scope, the disposition when one exists, relevant implementation/review receipts, and preserved accepted fixes; it does not reconsider accepted independent findings.

## Key points: what each hop does

Follow the **职责表**. Hop `template` = that department's **manage** window.

| template | Must not |
|---|---|
| **planning** | product code; open/merge PR; full plan; 分发 before 决策 receipts; follow to fix upstream; staff delivery/acceptance/arbitration employees; manage running patch |
| **delivery** | open/merge PR; extra extract ticket; same-ticket switch to acceptance; 分发 another department; manage writing product code |
| **acceptance** | PR on an implement ticket; manage merging heads or worktrees; 分发 another department |
| **arbitration** | debug; edit product code; open/merge PR; nest arbitration; apply the verdict (planning implement); manage writing the opinion |
| **human** | change contract; edit code; open/merge PR; staff implement/review/verify; treat 推进 as entry; notify before pass/fail |

## Stop (these two tables are source of truth)

Hard stop. `until` must not skip a row.

| Condition | Stop at |
|---|---|
| human window waiting pass/fail | that human window |
| `merge: human` PR opened | `wait-merge` |
| change-contract, person must confirm | planning 决策; wait for the person |
| isolation unclear | this acceptance; give the table to the person |
| no pullable ticket | planning |

`mode` × `until`. Follow this table. A hard-stop row wins when both match.

`until` reached: `#n` → that ticket's department hop reported (`done` / `send-back` / `blocked` / `need-arbitration` / `wait-merge`); do not 分发 a later ticket; still blocked → do upstream first. Department name → the next hop of that department reported.

| mode | until | After 回传 | After 决策 receipts |
|---|---|---|---|
| **manual** | `none` | print; stop; no 分发 | print next; stop; no 分发 |
| **manual** | `#n` or department | until not reached and no hard stop → one 推进 | next hop is 分发 → 分发 once this turn; next hop is 决策 → this turn stop (print); chain not dead |
| **auto** | `none` | one 推进 until a hard stop | next hop is 分发 → 分发 once this turn; next hop is 决策 → this turn stop (print) |
| **auto** | `#n` or department | same as auto `none`, and stop when until reached | same, and stop when until reached |

Missing `until:` → write `until: none`. Planning **manage** writes `until` only when the user names a stop; writes `none` when the user clears it. Session start prints the current value; do not invent.

Do not switch delivery to acceptance on the same ticket. Do not skip `ready-for-human`. One 分发 = one department hop. Same class of pullable tickets → smallest issue number.

## Steps: hop from the ticket

Set this on the **ticket tree** when the planning department 分发, or run 决策 when the hop is `planning`. Not the conversation entry.

Tree already has `issue:` = this open ticket and `template:` is a department hop → use that hop. Do not recompute.

| See | Hop | Planning department does |
|---|---|---|
| tree hop already set (ticket still open) | that `template:` | **分发** that other department. `planning` leftover on a tree → **决策**, do not spawn |
| plan / split tickets / fill graphs / change contract / fill tests / resume pause / unapplied verdict | `planning` | **决策** (this department's hop). Do not spawn |
| implement ticket `ready-for-agent` (no `engineering:pr`) | `delivery` | **分发** delivery department |
| acceptance ticket `ready-for-agent` (has `engineering:pr`) and unblocked | `acceptance` | **分发** acceptance department |
| `ready-for-human` | `human` | **分发** human department |
| disputed review finding after disposition/rework, explicit contract/upstream challenge, or user challenge | `arbitration` | **分发** arbitration department |

## Test intensity

| Hop | Field | Run |
|---|---|---|
| delivery verify | `verify:` | host light. `none` may still pass. No `Challenge`. Fail → send implement back. Green + notes → ticket comment only |
| acceptance verify | `accept:` | full + hooks. `none` still may open a PR; receipt `Verify: none` |
| arbitration verify | `verify:` | check reproduction. If it does not hold, do not write a verdict |

## Nodes on the graph

- Source: `engineering:source`. Default close at plan close-out.
- Implement: close this after delivery passed. Extract headers on this ticket if needed.
- Gate: `blocked-by` implement. Person pass → close. Do not put a human on every acceptance.
- Acceptance: `engineering:pr`, heads direct children ≤4. Mid layer heads write `merge/<child-acceptance>` or `feat/…`. Blocked → no PR.
- Sink: open only if someone must see the merge phenomenon; `blocked-by` the final acceptance.

Default 1 source 1 sink; multiple only if the user says so.

## Upstream bug

1. The delivery department that found it only goes as far as reporting arbitration.
2. `planning` **implement** during 决策 pauses that downstream (body `engineering:paused-by #<bug-acceptance>`, `blocked-by` the last acceptance of the bugfix), opens bug implement+acceptance, notifies pull again. Planning manage then stops.
3. A later 分发 sends the bugfix to a delivery department (not the one that found it).
4. Bugfix acceptance closed: that acceptance department stops; report asking planning to 决策 resume.
5. `planning` implement during 决策 clears the pause, comments pull again. Planning manage does not 分发 the downstream in that 决策 turn.

## Acceptance-fail isolation (leave-one-out)

Only this **current acceptance ticket**'s `engineering:heads` (≤4). One-shot isolation trees per worktree.md; do not edit each `feat/`; do not push; delete after the test. Command = `accept:`.

1. `|heads|==1` → that one is the accused.
2. `engineering:isolate: no` or `accept: none` → no isolation; stop and report to the person / `none` may still open a PR.
3. Leave-one-out: for each h, merge "all except h" onto the default branch. Merge fails → h is accused. `accept:` turns green → dropping h fixes it; h is accused.
4. Accused still empty → merge one at a time. Single fail → accused. Every single passes, all together fail → **integration issue**: do not auto-reopen; stop; give the table to the person/planning.
5. Accused nonempty and not pure integration → reopen the accused. feat → reopen that implement (and that line's closed gates). `merge/<child-acceptance>` → **run this section on that child acceptance**; do not reopen every implement from the top.
6. Write the isolation table as a comment on the current acceptance. `issue: none`. Stop. Report to planning.
