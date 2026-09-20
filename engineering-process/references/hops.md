# Department hops

Read and run [rules.md](rules.md), [supervise.md](supervise.md), and the applicable tables in [templates.md](templates.md). Staff every employee by reading and running `engineering-routing`.

## 3a. `human` (department)

Talk to the user. Tell them how to test and accept this gate (what to run or look at, what pass looks like). Help if they ask. Write comments as needed. Do not staff employees. Do not 分发. Do not notify until the person said pass or fail.

Person said fail → reopen the previous implement ticket and send it back to `ready-for-agent`. Do not turn the gate ticket into `ready-for-agent`. Tree `issue: none`. Run `python <engineering-init>/scripts/render_graph.py --issue <spec> --write` (spec = `Part of #<n>` on this ticket). Script fail → **fail**. Notify (`hop: send-back`, suggested next 分发 delivery). Person said the phenomenon passed → close **this** gate or sink, `issue: none`, run the same graph write, notify (`hop: done`).

## 3b. `arbitration` (department)

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

## 3c. `planning` (planning **manage** 决策)

`contract` is not `ready` → stop, go to plan. Already `ready`: staff `planning implement` then `planning review` (**delegate**). Prompt implement: ticket URLs, read and run `engineering-init` **patch**, receipt (include whether spec `engineering:graph` was written). Edges changed and graph not written → receipt incomplete; do not finish. Review checks the spec flow graph has the new nodes and edges. Do not run patch in this window. No open/merge PR. No product-code edits by manage. Do not staff delivery / acceptance / arbitration employees. Wait until both receipts are in this conversation; receipts missing → do not finish. No `spawn.py`. Changing layers / breaking a cycle / migrate → stop, go to plan or migrate.

Implement does the patch (verdict, new need, fill tests, pause/resume, rewrite spec `engineering:graph` when tickets or edges change). Review reviews that output and the spec graph. Manage does not edit issue bodies or `blocked-by`. Does not run `render_graph.py`.

After implement receipt:

- Verdict "send-back" → next hop is 分发 delivery on that ticket.
- Verdict "change-contract" (not upstream-bug) → hard stop (person must confirm).
- Verdict "upstream-bug" → planning implement opens the bug tickets; next hop is 分发 that bug implement (not the department that found the bug).
- Resume done → next hop is 分发 if any.

Then templates.md **Stop** tables (After 决策 receipts).

## 3d. `delivery` (department)

Current ticket body contains `engineering:pr` → stop; that is 3e.

Need research or datasheet work → staff `datasheet extract` by reading and running `engineering-routing` inside this implement ticket; that employee reads and runs `engineering-research`, which checks repository materials before the web. Do not open a separate extract ticket. Then staff implement + review + verify (**delegate**) (roles `delivery implement` / `delivery review` / `delivery verify`). Wait until implement, review, and verify receipts are in this conversation. Receipts missing → do not push, do not close, do not finish. implement may add+commit only; no push. verify runs `verify:`. Manage must not edit product files. No open/merge PR. Do not close gate or acceptance tickets. Do not resubmit a rejected implementation unchanged. Do not spawn a child conversation.

implement / review receipt:

```
Changed paths:
Verify:
Challenge: none | upstream #<n> | contract
Result: pass | fail
Failure:
```

verify receipt (no `Challenge`):

```
Verify: pass | fail | none
Notes: <none or observations>
Failure:
```

Command ran but did not cover this module, or assertions are vacuous → verify `fail` (send implement back). Command green; notes are about later tightness → `pass` plus `Notes`; department copies Notes to a ticket comment. Do not 分发 arbitration.

verify=`fail` (when a command exists), both implement and review `fail`, or implement=`fail` and paths 2–3 did not fire → do not push, do not close, send back to `ready-for-agent`. Tree `issue: none`. Notify (`hop: send-back`). Stop.

implement=`pass` and review=`pass` and (`verify: none` or pass) → **delivery manage** `git push -u origin HEAD` → **close this implement ticket**. Tree `issue: none`. Run `python <engineering-init>/scripts/render_graph.py --issue <spec> --write` (spec = `Part of #<n>` on this ticket). Script fail → **fail**. Notify (`hop: done`). Do not open a PR. Do not change gate-ticket edges. Stop.

Conflict / `Challenge` not `none` / user challenge → do not push; write tree `template: arbitration`; keep `issue:`; notify (`hop: need-arbitration`). Do not run 3b in this window. Next planning 推进 **分发** arbitration (tree hop already set).

## 3e. `acceptance` (department)

Current ticket body has no `engineering:pr` → stop; no PR.

Do not edit product code in this window. Staff implement + review + verify (**delegate**) (roles `acceptance implement` / `acceptance review` / `acceptance verify`). Wait until those receipts are in this conversation. Receipts missing → do not open/merge a PR, do not finish. implement merges `engineering:heads` and worktrees per worktree.md. `accept:` is `none` or empty → verify receipt `Verify: none`, issue comment "full suite unset", **still may open a PR**. Command present → acceptance verify runs `accept:`. Acceptance verify has no `Challenge`; do not enter 3b from this hop. Do not spawn a child conversation.

`accept:` failed → staff acceptance implement for leave-one-out isolation per templates.md (this ticket heads ≤4; if the accused is `merge/<child-acceptance>`, recurse that child). Then `issue: none`. Run `python <engineering-init>/scripts/render_graph.py --issue <spec> --write`. Do not edit product code on this ticket. Notify (`hop: blocked`). Stop.

User said it already merged → confirm the default branch contains the commits → close this acceptance.

Else passed → **acceptance manage** opens a PR from `engineering:heads` (one head: that branch after implement merged if needed; several: implement created `merge/<this-acceptance>` and merged the list). `Fixes #<n>` n=this acceptance. List empty → stop, fill heads. PR already open and not merged → do not open another; notify (`hop: wait-merge`); stop. `merge: auto` → manage merges the PR then close the acceptance. `merge: human` → open, keep this ticket open, notify (`hop: wait-merge`); stop.

If this acceptance is a bugfix: after close, list downstream with `paused-by` this acceptance; notify (`suggested next: 决策` resume). Do not 分发 those downstream tickets.

After closing acceptance: tree `issue: none`. Staff acceptance implement to remove merged implement trees and the acceptance tree per worktree.md. Run `python <engineering-init>/scripts/render_graph.py --issue <spec> --write` (spec = `Part of #<n>` on this ticket). Script fail → **fail**. Notify (`hop: done`). Stop.
