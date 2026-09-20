**Department** `template` on the ticket tree picks the hop. Duties: this **职责表** only. Five departments × four employee kinds. Datasheet extract is not a column (`datasheet-headers` from delivery only). Never a child conversation for an employee.
| **planning** | talk to the user; this conversation has not confirmed yet (not 回传): write missing `until: none`, print `mode` / `until` / `merge` / `verify` / `accept` + MODELS, wait for confirm, then 推进; 分发 other departments; staff this department's employees; collect receipts; after 分发 stop; after 回传 / 决策 receipts follow **Stop** tables | 决策 technical: `engineering-init` **patch**, apply verdict, pause/resume, open bug tickets, comment pull again; create the ticket tree before 分发 | review the planning implement output | — |
- Employee kinds follow this 职责表. Datasheet extract is not a column: when needed, run `datasheet-headers` on the **delivery** department's implement ticket; not under `human` / `arbitration` / `planning` / `acceptance`. Do not open a separate extract ticket.
- Before staffing, take the target from the `MODELS.md` employee cell (department × duty), then `engineering-routing`. Ignore a `dispatch` link on employee cells. Do not pick a subagent outside the catalog unless the user named one. Do not rewrite delegate to a child conversation. Wait until each employee receipt is in the department window. Background Task → **fail**. Launching Task is not hop finished.
- 决策 technical work only by `planning` **implement**. From arbitration, apply the verdict; do not change it. Planning **manage** staffs that implement + review; does not run patch. Open/merge PR only by `acceptance` **manage**, and only if the ticket body has `engineering:pr`. Product-code edits only by the `delivery` implement **employee**. Heads merge / worktree git only by `acceptance` implement.
- Arbitration: implement employee reproduces + opinion; review reviews the opinion; verify checks reproduction if a command exists. The verdict is written by the arbitration **department**. planning does not judge.
- Enter arbitration only on the paths in `SKILL.md` Key points and **Review disposition** below. Delivery department reports those paths; planning **分发** arbitration. Delivery verify is not a trigger and has no `Challenge` field.
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

## Department resume (same-ticket continuation)

Same-ticket continuation = the next hop is a department that already has a dispatch child for this ticket (typical after arbitration sends the ticket back, or after a human send-back reopens the implement ticket). That continuation **resumes the original department manage conversation**. It is not a new 分发 and does not create a window.

Planning manage resumes via sessions only:

```
python <sessions-skill>/scripts/spawn.py --mode resume --target-id <uuid> --ticket #<n> --request-id <id>
```

- `--target-id` is the exact conversation id recorded at 分发 (dispatch report `id` / `url`). Never infer the continuation target from an old conversation id found elsewhere. `--ticket` + `--request-id` carry the stable request identity; when reconciling one intentional continuation, reuse the same `--request-id`.
- Do not `--mode dispatch` and do not `--mode open` the same department on the same ticket again; redispatch or a new department window → **fail**. The resume target is the department **manage** window (the dispatch child carrying that department tag), never an implement / review / verify subagent. Employees are Task delegate and have no conversation window to resume; resuming or reusing an employee conversation for department continuation → **fail**.
- Receipts: `accepted` = the continuation operation was accepted only, not department work completion; do not finish the hop, do not watch. `unknown` = unproven (timeout or lost response): reconcile with the same `--ticket` + `--request-id`; a timeout or lost response is unknown-until-reconciled, not a retry trigger — no blind retry, no redispatch on timeout. `rejected` = stop with the receipt evidence; no automatic replacement dispatch and no force bypass.
- Preserve commits, accepted fixes, existing history, and valid receipts across the resume. Rerun only the hops the arbitration verdict invalidated (the disputed scope); do not re-run accepted independent findings or already verified hops.
- Reporting stays child → parent: the resumed department manage still finishes the hop with sessions `spawn.py --mode notify`. Callers use spawn.py only; never copied raw HTTP calls.
- Receiver-side dedup: planning dedups incoming reports by the report's `request:` line, so a re-sent notify whose earlier post actually landed is duplicate-safe by design; keep the `request:` line intact in every report.
- This resume does not implement the **Review disposition** flow above. Disposition keeps returning review findings to the original implement employee inside that delivery window; resume only continues the department window. Keep both intact; do not conflate them.
| disputed review finding after disposition/rework, explicit contract/upstream challenge, or user challenge | `arbitration` | **分发** arbitration department |

Same ticket and the target department already has a dispatch child → that is a continuation, not a new 分发: **Department resume** above.
6. Write the isolation table as a comment on the current acceptance. `issue: none`. Stop. Report to planning.
