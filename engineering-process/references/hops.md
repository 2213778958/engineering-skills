# Department hops

Supervise step 2 (3c) or step 3 (3a / 3b / 3d / 3e) in [supervise.md](supervise.md) picks the section. Rules: [rules.md](rules.md). Tables: [templates.md](templates.md).

## 3a. `human` (department)

Talk to the user. Tell them how to test and accept this gate (what to run or look at, what pass looks like). Help if they ask. Write comments as needed. Do not staff employees. Do not hand off. Do not notify until the person said pass or fail.

Person said fail → reopen the previous implement ticket and send it back to `ready-for-agent`. Do not turn the gate ticket into `ready-for-agent`. Tree `issue: none`. Notify (`hop: send-back`, `suggested next: hand off delivery #<n>`). Person said the phenomenon passed → close **this** gate or sink, `issue: none`, notify (`hop: done`).

## 3b. `arbitration` (department)

Staff implement + review via MODELS (**delegate**). If `verify:` is not `none`, staff verify via MODELS (**delegate**). Roles: `arbitration implement` / `arbitration review` / `arbitration verify`. Wait until each staffed receipt is in this conversation. Receipts missing → do not write a verdict, do not finish. Manage writes the verdict comment only after receipts. No product-code edits, no commit/push, no open/merge PR. No datasheet reading, no research staffing. Do not spawn a child conversation.

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

`Verdict: review-wrong` and the implement ticket still open → write tree `template: delivery` and `issue:` that implement (`suggested next: hand off delivery #<n>`; same ticket and that department already dispatched → resume per rule 19 / templates.md **Department resume**, not a new dispatch). Other verdicts → write tree `issue: none` (`suggested next: decide`). Notify. Stop.

## 3c. `planning` (planning **manage** decide)

`contract` is not `ready` → stop, go to plan. Already `ready`: staff `planning implement` then `planning review` (**delegate**). Prompt implement: ticket URLs, read and run `engineering-init` **patch**, receipt. Review reviews that receipt. Do not run patch in this window. No open/merge PR. No product-code edits by manage. Planning needs research input (e.g. prior approaches before cutting tickets) → first staff `research` per `engineering-research` (tree `cd` = `master/`; ticket URL = the ticket being decided, else `none`); the planning implement prompt names its `research:` entry path as read-only input. Do not staff delivery / acceptance / arbitration employees. Wait until every staffed receipt is in this conversation; receipts missing → do not finish. No `spawn.py`. Changing layers / breaking a cycle / migrate → stop, go to plan or migrate.

Implement does the patch (verdict, new need, fill tests, pause/resume). Review reviews that output. Manage does not edit issue bodies or `blocked-by`.

After implement receipt:

- Verdict "send-back" → next hop is hand off to delivery on that ticket.
- Verdict "change-contract" (not upstream-bug) → hard stop (person must confirm).
- Verdict "upstream-bug" → planning implement opens the bug tickets; next hop is a handoff of that bug implement ticket to a delivery department (not the one that found the bug).
- Resume done → next hop is a handoff, if any.

Then templates.md **Stop** tables (After decide receipts).

## 3d. `delivery` (department)

Current ticket body contains `engineering:pr` → stop; that is 3e.

Need headers or research → `engineering-research` (role `research`; inside this implement ticket; no separate extract ticket); it delivers a research directory in the external `research/` library (never in this tree), and the implement prompt names its `research:` entry path as read-only input (headers are written by delivery implement from the findings), then staff implement and review (**delegate**) (roles `delivery implement` / `delivery review`). Wait for each receipt before the next step. Staff `delivery verify` only after review passes. Receipts required by the chosen path must be in this conversation before push, close, or notify. implement may add+commit only; no push. verify runs `verify:`. Manage must not edit product files. No open/merge PR. Do not close gate or acceptance tickets. Do not resubmit a rejected implementation unchanged. Do not spawn a child conversation.

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

Review pass with non-blocking notes remains pass; copy Notes to a ticket comment. Blocking review failure skips verify. After review passes, staff verify. Command ran but did not cover this module, or assertions are vacuous → verify `fail` (send implement back). Command green; notes are about later tightness → `pass` plus `Notes`; department copies Notes to a ticket comment. Do not hand off to arbitration.

verify=`fail` (when a command exists), implement=`fail` and paths 2–3 did not fire, or a blocking finding accepted on fresh review still fails → do not push, do not close, send back to `ready-for-agent`. Tree `issue: none`. Notify (`hop: send-back`). Stop.

implement=`pass` and review=`pass` and (`verify: none` or pass) → **delivery manage** `git push -u origin HEAD` → **close this implement ticket**. Tree `issue: none`. Notify (`hop: done`). Do not open a PR. Stop.

A disposition with `Action: arbitration`, the same finding disputed after focused rework, an implement-originated explicit contract/upstream challenge, or a user challenge → do not push; write tree `template: arbitration`; keep `issue:`; notify (`hop: need-arbitration`). Include only disputed finding IDs and preserve accepted fixes and prior valid receipts. A review-originated contract/upstream challenge follows the blocking-review disposition flow first. Do not run 3b in this window. The next planning advance **hands off** to arbitration (tree hop already set).

## 3e. `acceptance` (department)

Current ticket body has no `engineering:pr` → stop; no PR.

This acceptance's PR is already merged (`gh pr view` state `MERGED`; e.g. the planning resume says the user merged it) → skip merge heads, `pre` and `accept:`; go to **Post-merge**.

Do not edit product code in this window. Staff implement + review + verify (**delegate**) (roles `acceptance implement` / `acceptance review` / `acceptance verify`). Wait until those receipts are in this conversation. Receipts missing → do not open/merge a PR, do not finish. implement merges `engineering:heads` and worktrees per worktree.md. **Scope** = every implement ticket (body without `engineering:pr`, open or closed) reachable from this acceptance by following `blocked-by` edges through implement tickets, gates and open acceptances; stop at closed acceptances and at the source ticket. After merging heads, implement runs `git fetch` then `engineering-process` `scripts/check_acceptance.py pre --head <merge head> --tickets <scope>` in the tree and pastes the output (ticket tips and head SHA) and exit code in its receipt. Review checks the scope list against the `blocked-by` graph and inspects every `REVIEW merge` line with `git show --cc`. `pre` non-zero → do not staff verify and skip isolation. `accept:` is `none` or empty → verify receipt `Verify: none`, issue comment "full suite unset", **still may open a PR**. Command present → acceptance verify runs `accept:`. Acceptance verify has no `Challenge`; do not enter 3b from this hop. Do not spawn a child conversation.

`accept:` failed → staff acceptance implement for leave-one-out isolation per templates.md (this ticket heads ≤4; if the accused is `merge/<child-acceptance>`, recurse that child). Then `issue: none`. Do not edit product code on this ticket. Notify (`hop: blocked`). Stop.

`check_acceptance.py pre` non-zero → do not open a PR. `issue: none`. Notify (`hop: blocked`, `suggested next: decide`: planning patch fixes heads or tickets). Stop.

Else passed → **acceptance manage** opens a PR from `engineering:heads` (one head: that branch as delivery pushed it; implement does not commit on it; it conflicts with the default branch → send back to delivery (`hop: send-back`); several: implement created `merge/<this-acceptance>` and merged the list; manage pushes `merge/<this-acceptance>` first, force if `pre` noted it stale). The PR head commit must equal the head SHA `pre` printed; else rerun implement + `pre`. `Fixes #<n>` n=this acceptance. List empty → stop, fill heads. PR already open and not merged → do not open another; notify (`hop: wait-merge`); stop. `merge: auto` → manage merges the PR with a merge commit (no squash, no rebase), then **Post-merge**. `merge: human` → open, tell the person to merge with a merge commit (no squash, no rebase), keep this ticket open, notify (`hop: wait-merge`); stop.

**Post-merge:** staff acceptance implement: `git fetch`, then `engineering-process` `scripts/check_acceptance.py post --tickets <scope>` (a ticket whose branch was deleted after merge: `<n>=<tip SHA from pre>`); paste the output and exit code. Exit 0 → close the acceptance. Non-zero → keep it open; `issue: none`; notify (`hop: blocked`, `suggested next: decide`); stop. `post` non-zero while `gh pr view` is `MERGED` (squash / rebase) → implement also pastes `git cherry -v origin/<default> <tip>` per ticket; the person decides on the planning window (templates.md **Stop** hard stop); confirmed → planning implement comments that confirmation on this acceptance (`engineering-init` patch), the ticket stays open, and the next advance resumes this acceptance department. `post` non-zero, PR `MERGED`, and that confirmation comment present → close the acceptance.

If this acceptance is a bugfix: after close, list downstream with `paused-by` this acceptance; notify (`suggested next: decide` resume). Do not hand off those downstream tickets.

After closing acceptance: tree `issue: none`. Staff acceptance implement (may be the Post-merge task) to remove merged implement trees and the acceptance tree per worktree.md. Notify (`hop: done`). Stop.
