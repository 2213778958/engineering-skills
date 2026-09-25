---
name: openhands-watch
description: >-
  Watch dispatched Agent Canvas child conversations and report
  alive, hung, or terminal. Use when the user asks to openhands-watch,
  巡查, 挂掉, 派发会话是否挂掉, or when a **dispatch window** must be
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
5. Read-only: watch never dispatches, advances tickets, or changes the engineering contract.
6. At most 3 child ids in one watch.

State classification (hung / terminal / alive mapping, heartbeat, output rules) → [classification](references/classification.md).

## Steps

Need ids from spawn JSON `id` / `conversation_id`, or this conversation's children:

```
python <this-skill>/scripts/watch.py --ids <uuid>[,<uuid>]
python <this-skill>/scripts/watch.py --ids <uuid> --loop --poll-sec 30 --stall-sec 600 --timeout-sec 5400
python <this-skill>/scripts/watch.py --parent-id <this conversation id> --loop
```

`--loop` omitted → one snapshot. `--stall-sec` default 600. `--timeout-sec` default 5400. `--poll-sec` default 30.

Planning handoff does not watch (stop after spawn). Employees are Task subagents, not watch targets. `--loop` only if the user asks to keep watching a dispatch **window** (e.g. "巡查", "keep an eye on it"). Hung / error / timeout → fail that wait; do not dispatch again unless the user says so. Do not GET child events yourself.

Print the JSON. Follow the process exit:

| Exit | Meaning |
|---|---|
| 0 | all `finished` |
| 2 | any hung |
| 3 | terminal but not all `finished` |
| 1 | usage / API failure |
