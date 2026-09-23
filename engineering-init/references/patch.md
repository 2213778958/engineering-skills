# Patch

Change the ticket contract after init. Do not redo plan.

## Rules

- Landing repo only. No clone. No implement. No 分发. No PR. Do not write process into `AGENTS.md`. Do not rewrite `AGENTS.md` / `CONTEXT.md` / `docs/adr/` / formatters unless the user explicitly changes conventions, glossary, or a decision.
- `PROCESS.md` `contract:` must be `ready`. Else stop, go to **plan**.
- Do not ask `mode`. Do not change `mode`. Do not change `contract:`. Do not refill `MODELS.md` unless the user explicitly changes a model row.
- Do not re-grill the layer template unless the user explicitly changes layers.
- Do not rename Vendor / Components public names to `Layer_Module_Action`.
- No `triage`. No separate datasheet ticket.
- New acceptance tickets: `engineering:heads` direct children ≤4. Over that, split a mid acceptance first.
- Default 1 source 1 sink; multiple only if the user says so.

## When

- process `planning` **implement** during **决策**: land an unapplied arbitration verdict; or new need / edit body / edit `blocked-by` / open a fix ticket. Planning **manage** must not run these steps.
- Fill `verify:` / `accept:` commands
- Resume a paused ticket
- Same-ticket department continuation after arbitration sends the ticket back, or unpause resume: resume the original **department manage** session per **Department resume** below. Never a new dispatch / new window, and never the implement employee / subagent.

## Do not

Changing contains layer cuts, breaking a uses cycle, migrate, opening a ticket net from scratch → stop; use **plan** or **migrate**.

## Steps

1. Read `docs/agents/PROCESS.md`. `contract:` is not `ready` → stop.
2. Read spec and related tickets.
3. New need: edit User Stories on spec; if needed open an implement ticket aligned to **one existing** contains node; edges only official `blocked-by`. Need acceptance → extra `engineering:pr` ticket with `engineering:heads` (≤4). Parallel leaves still default `blocked-by` the same source. Hard-to-see gate → extra `ready-for-human`.
4. Send-back continue: only change the label to `ready-for-agent`; do not edit the body.
5. Arbitration verdict exists: only apply the verdict (edit body / send back / open / reopen). Scan `blocking` and `blocked-by`. Close obsolete tickets with `wontfix` or put blockers back. Do not change the verdict. Do not always terminate. Human review fail is the **human** department (process 3a), not this patch.
6. Verdict "upstream bug": pause the downstream that found it (body `engineering:paused-by #<bug-acceptance>`, `--add-blocked-by` the **last acceptance** of the bugfix chain). Open a `bug` implement ticket; if a PR is needed, open an acceptance (heads ≤4). Do not let the original delivery **department** keep fixing it.
7. Resume pause: bugfix acceptance closed → drop `paused-by` and that blocker, comment **pull again** `<ref>`, restore `ready-for-agent` as needed — then resume the original **department manage** session per **Department resume** below. Never resume or reuse the implement employee / subagent for the pull. Other blockers stay: a ticket still `blocked-by` an open ticket is not pulled, and no `paused-by` cause is removed but this bug's.
8. Any contract or upstream-code change: comment still-open downstream tickets "pull again `<ref>`". Ticket still blocked (open `blocked-by`) → not pulled; fixing this bug does not bypass another blocker.
9. Test commands updated → write `verify:` / `accept:`. Do not clear a legal `mode`.
10. Opened, reopened, closed, or `blocked-by` / `blocking` changed → update GitHub-native relationships only: official `blocked-by` edges, and an open parent sub-issue blocks its children. Do not change contains / uses.
11. Report: which tickets changed; new bug ticket URL if any; whether `verify` / `accept` updated; new issue numbers and their GitHub-native edges.

## Department resume (same-ticket continuation)

Same-ticket department continuation: after arbitration sends the ticket back, or on unpause resume, planning resumes the **original department manage session** — sessions `spawn.py --mode resume --target-id <child id recorded at 分发> --ticket <n> --request-id <stable request id>`. Never `--mode dispatch` / `--mode open` a new window for that ticket + department. The resume target is the department **manage** window (the dispatch child carrying that department tag), never the implement employee / subagent conversation. Report unknown evidence upward (see below).

Old child ID is not delivery acceptance. Do not treat an old conversation / child id found elsewhere as evidence the department finished the work. Evidence classes:

- `accepted` — verified delivery state (accepted fix, valid receipt, closed per the ticket's own `verify:` / `accept:`). Preserve its commits, fixes and receipts; do not re-run the accepted scope.
- `unknown` — receipt state unproven (timeout, lost response, ambiguous comment). Reconcile without blind retry: do not automatically re-run the work; verify actual state (ticket comments, receipts, commits) and follow the review disposition / send-back flow; report the unknown upward.
- `rejected` — delivery or receipt explicitly rejected. Stop with the receipt evidence; no automatic replacement dispatch.

Notify stays child → parent: the resumed department manage session still notifies the planning parent via sessions notify. No raw POST, no notify overload — do not POST to the parent directly to skip the child.

## Walkthroughs

1. **Arbitration continuation.** Arbitration sends the ticket back to the same department: patch step 5 applies only the verdict (send-back → label `ready-for-agent`, per step 4). Planning then resumes the original department manage session with `spawn.py --mode resume --target-id <child id recorded at 分发> --ticket <n> --request-id <same stable request id>`. No new dispatch / new window for that ticket + department; never the implement employee / subagent. Documented in **Department resume** above and steps 4–5.
2. **Unknown receipt.** The resume receipt state is unknown (timeout / lost response): do not blind retry and do not re-run the work automatically. Verify actual state — ticket comments, receipts, commits — then follow the disposition / send-back flow and report the unknown upward. Documented in **Department resume** (`unknown` evidence class).
3. **Final acceptance unpause.** Bugfix acceptance closes: drop `paused-by` and that blocker from the downstream ticket, comment **pull again** `<ref>`, restore `ready-for-agent` as needed — then resume the original department manage session per **Department resume**, never the employee / subagent. Documented in step 7 + **Department resume**.
4. **Remaining blocker.** This bug's pause removed must not bypass another blocker: the ticket still `blocked-by` an open ticket stays un-pulled; other blockers and other `paused-by` causes are not removed. Step 8 pull-again comments go only to tickets whose blockers are all resolved. Documented in steps 7–8.
