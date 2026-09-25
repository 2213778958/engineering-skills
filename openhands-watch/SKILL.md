---
name: openhands-watch
description: >-
  Watch dispatched Agent Canvas child conversations and report
  alive, hung, or terminal, plus per-child employee-task facts
  (ticket, department, request_id, notify classification) read
  from the sessions dispatch ledger. Use when the user asks to
  openhands-watch, 巡查, 挂掉, 派发会话是否挂掉, or when a **dispatch window** must be
  waited on. Do not use to open or dispatch a conversation;
  that is openhands-sessions. Engineering implement/review/verify
  are employees (subagents), not watch targets. The planning
  department 分发 does not watch.
---

# OpenHands watch

This skill owns child-session liveness. Spawn stays in `openhands-sessions`. Ticket advance stays in `engineering-process`.

The normalized watch and session semantics are defined in [the harness capability contract](../openhands-sessions/references/capabilities.md). Provider-specific lifecycle states must be mapped to that contract before they reach engineering skills. A native harness or CLI may delegate internally, but watch does not inspect or manage that internal delegation unless it exposes a separately correlated, watchable session.

| Mode | When | Done |
|---|---|---|
| **once** | Snapshot these child ids (default) | JSON `verdict` printed |
| **loop** | Wait until not `alive` | JSON `verdict` printed; process exit set |

## Rules

1. Live API only. Do not cache ids across turns.
2. Never print the API key. Credential, host, and transport mechanics (key header, backend/UI hosts, PowerShell 5.1) live in [../openhands-sessions/references/identity.md](../openhands-sessions/references/identity.md).
3. Call `scripts/watch.py`. Do not `curl` child `/events/search` from any department.
4. Do not POST `/api/conversations`. Do not write `dispatch_session.py`. Do not interrupt / pause / run the child unless the user said to.
5. Read-only: watch never dispatches, advances tickets, or changes the engineering contract. Reading the dispatch ledger JSON is its only filesystem access; never call sessions' `save_ledger` / `record_ledger`.
6. At most 3 child ids in one watch.

State classification (hung / terminal / alive mapping, heartbeat, output rules) → [classification](references/classification.md).

## Task facts

Terminal is not hop-done. Each child row in the verdict JSON carries an additive `task` object: `{ticket, department, request_id, dispatch_status, recorded_at, notify, reason}`, read read-only from the parent's ledger file (`~/.openhands/agent-canvas/dispatch-ledger/<parent_id>.json`; `OPENHANDS_DISPATCH_LEDGER_DIR` overrides the directory in tests). Ledger parent = explicit `--parent-id`, else the children's single common `parent_conversation_id`.

- Dispatch facts come from the ledger entry whose `child_id` matches the child.
- `notify`: `notified` / `missing-notify` once the child is terminal (a notify entry with that dispatch ticket exists in the parent ledger, or not); `finalization-failed` when the ledger is unreadable or its entries contradict (conflicting dispatch entries for the child, or a notify ticket matching no dispatch ticket); `n/a` while the child runs; `unknown` when no parent ledger can be identified (`--ids` only and no common parent).
- Ledger problems never change the liveness verdict or the process exit code. Unavailable facts keep `null` fields plus a short `reason` (`ledger-unreadable`, `parent-ledger-unavailable`, `no-dispatch-entry`, `conflicting-dispatch-entries`).

## Steps

Need ids from spawn JSON `id` / `conversation_id`, or this conversation's children:

```
python <this-skill>/scripts/watch.py --ids <uuid>[,<uuid>]
python <this-skill>/scripts/watch.py --ids <uuid> --loop --poll-sec 30 --stall-sec 600 --timeout-sec 5400
python <this-skill>/scripts/watch.py --parent-id <this conversation id> --loop
```

`--loop` omitted → one snapshot. `--stall-sec` default 600. `--timeout-sec` default 5400. `--poll-sec` default 30.

Planning 分发 does not watch (stop after spawn). Employees are Task subagents, not watch targets. `--loop` only if the user asked 巡查 on a dispatch **window**. Hung / error / timeout → fail that wait; do not dispatch again unless the user says so. Do not GET child events yourself.

Print the JSON. Follow the process exit:

| Exit | Meaning |
|---|---|
| 0 | all `finished` |
| 2 | any hung |
| 3 | terminal but not all `finished` |
| 1 | usage / API failure |
