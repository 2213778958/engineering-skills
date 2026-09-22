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

## Do not

Changing contains layer cuts, breaking a uses cycle, migrate, opening a ticket net from scratch → stop; use **plan** or **migrate**.

## Steps

1. Read `docs/agents/PROCESS.md`. `contract:` is not `ready` → stop.
2. Read spec and related tickets.
3. New need: edit User Stories on spec; if needed open an implement ticket aligned to **one existing** contains node; edges only official `blocked-by`. Need acceptance → extra `engineering:pr` ticket with `engineering:heads` (≤4). Parallel leaves still default `blocked-by` the same source. Hard-to-see gate → extra `ready-for-human`.
4. Send-back continue: only change the label to `ready-for-agent`; do not edit the body.
5. Arbitration verdict exists: only apply the verdict (edit body / send back / open / reopen). Scan `blocking` and `blocked-by`. Close obsolete tickets with `wontfix` or put blockers back. Do not change the verdict. Do not always terminate. Human review fail is the **human** department (process 3a), not this patch.
6. Verdict "upstream bug": pause the downstream that found it (body `engineering:paused-by #<bug-acceptance>`, `--add-blocked-by` the **last acceptance** of the bugfix chain). Open a `bug` implement ticket; if a PR is needed, open an acceptance (heads ≤4). Do not let the original delivery **department** keep fixing it.
7. Resume pause: bugfix acceptance closed → drop `paused-by` and the blocker, comment **pull again** `<ref>`, restore `ready-for-agent` as needed.
8. Any contract or upstream-code change: comment still-open downstream tickets "pull again `<ref>`".
9. Test commands updated → write `verify:` / `accept:`. Do not clear a legal `mode`.
10. Opened, reopened, closed, or `blocked-by` / `blocking` changed → update GitHub-native relationships only: official `blocked-by` edges, and an open parent sub-issue blocks its children. Do not change contains / uses.
11. Report: which tickets changed; new bug ticket URL if any; whether `verify` / `accept` updated; new issue numbers and their GitHub-native edges.
