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

| Mode | When | Done |
|---|---|---|
| **once** | Snapshot these child ids (default) | JSON `verdict` printed |
| **loop** | Wait until not `alive` | JSON `verdict` printed; process exit set |

## Rules

1. Live API only. Do not cache ids across turns.
2. Never print the API key. Header `X-Session-API-Key` from `~/.openhands/agent-canvas/api-key.txt`.
3. Hosts: backend `http://localhost:8000`, UI `http://localhost:3001`.
4. Windows: PowerShell 5.1. Call `scripts/watch.py`. Do not `curl` child `/events/search` from any department.
5. Do not POST `/api/conversations`. Do not write `dispatch_session.py`. Do not interrupt / pause / run the child unless the user said to.
6. Do not change the engineering contract. Do not advance tickets.
7. At most 3 child ids in one watch.

## Key points

**Hung** = `stuck` / `waiting_for_confirmation` / `paused` / `deleting` / stall / missing `tags.clientsource=agentcanvas` while not terminal / 404 / loop poll-timeout.

**Terminal** = `finished` / `error` / `stopped`. Finished with empty tags is still terminal.

**Alive** = non-terminal, tagged, heartbeat younger than `--stall-sec`.

Heartbeat = last `events/search` `timestamp`, else conversation `updated_at`.

Do not print event bodies. Terminal rows may include truncated `final_response`.

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
