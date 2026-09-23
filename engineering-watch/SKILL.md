---
name: engineering-watch
description: >-
  Inspect dispatched department child conversations on demand and report
  alive, hung, terminal+notified, terminal+missing-notify, or
  terminal+finalization-failed. Use when the user asks to engineering-watch,
  巡查回传, 报告到了吗, check-dispatch, or when planning must confirm whether a
  department child's engineering:report landed. Do not use to dispatch,
  resume, or notify; that is openhands-sessions. Do not use for raw child
  liveness only; that is openhands-watch. Employee Task monitoring is out of
  scope (ADR 0002).
---

# Engineering watch

This skill owns the engineering meaning of a dispatch: report arrival correlated to the request identity. Raw liveness stays in `openhands-watch`. Spawn / resume / notify stay in `openhands-sessions`. Ticket advance stays in `engineering-process`.

| Mode | When | Done |
|---|---|---|
| **once** | One snapshot of these child ids (default) | JSON verdict printed |
| **parent** | Discover this conversation's children via `--parent-id` | JSON verdict printed |

## Rules

1. Read-only. Never POST / PATCH / DELETE / run. Never resume, reply to, or mutate a child conversation or the dispatch ledger.
2. Explicit inspection only, run on demand by planning after a dispatch. Never an automatic loop, never unattended, never on a timer. After 分发, planning still stops; this tool runs only when the user asks 巡查.
3. Never print the API key. Header `X-Session-API-Key` from `~/.openhands/agent-canvas/api-key.txt`.
4. Latch is not overridden: a `hung` or gap verdict never resumes the child and never dispatches again. Report and wait for the user.
5. `terminal` alone never counts as `notified`. `notified` requires the correlated `engineering:report` in the parent conversation's events; an unrelated conversation's report does not count.
6. Do not dump event bodies. Terminal rows echo at most a truncated `final_response`.
7. Import `openhands-watch/scripts/watch.py` primitives; do not reimplement the probe, do not edit it, do not copy it.
8. Never invent conversation ids. Use spawn JSON ids or `--parent-id` discovery. Do not GET child `/events/search` yourself; the probe owns event reads.

## Statuses

| Status | Meaning | Evidence |
|---|---|---|
| **alive** | child running, heartbeat fresh | non-terminal status, `clientsource=agentcanvas`, age < `--stall-sec` |
| **hung** | openhands-watch stall semantics | `stuck` / `waiting_for_confirmation` / `paused` / `deleting` / stall / not-found while not terminal. A healthy child waiting on in-flight delegated work is alive, not hung, without further evidence |
| **terminal + notified** | child terminal and report arrived | correlated `engineering:report` found in the parent events: `request:` line equals `dispatch:{parent_id}:{department}:{ticket}:{request_id}` parts |
| **terminal + missing-notify** | child terminal, no correlated report | terminal verdict from the probe, correlated report absent in the parent events |
| **terminal + finalization-failed** | child finished but 收尾 failed | child `final_response` marks push / graph / PROCESS / notify failure (e.g. `notify fail`, `finalization failed`, `收尾失败`); correlated report absent → not success |

`missing-notify` and `finalization-failed` are recoverable-gap states: surface them to planning as gaps. Do not silently treat them as success; do not auto-recover.

## Key points

Report correlation is by dispatch identity, built like `spawn.py` `request_identity()`: `dispatch:{parent_id}:{department}:{ticket}:{request_id}`. The child's report text carries a `request: <request-id>` line; the parent-side search also matches `department:` and `ticket:` lines. The first line must be `engineering:report`. Any `engineering:report` with a different `request:` / department / ticket is not correlated.

Resume stays in `openhands-sessions`: a terminal child stays resumable there. This skill reports the state and stops.

## Steps

Planning holds the dispatch JSON (`id` / `conversation_id`, `request_id`, `department`, `ticket`, `parent_id` / `this_id`):

```
python <this-skill>/scripts/watch_engineering.py --ids <uuid> --parent-id <parent conversation id> --request-id <id> --department <name> --ticket #<n>
python <this-skill>/scripts/watch_engineering.py --parent-id <parent conversation id> --ticket #<n> --department <name> --request-id <id>
```

`--ids` plus `--parent-id` needs both: `--parent-id` names the parent whose events are searched and whose children are discovered when `--ids` is omitted. Omitted `--department` / `--ticket` / `--request-id` weaken the correlation to the lines present.

Print the JSON. Follow the process exit:

| Exit | Meaning |
|---|---|
| 0 | all children `terminal + notified` |
| 2 | any child alive or hung |
| 3 | terminal reached but any gap (`missing-notify` / `finalization-failed`) |
| 1 | usage / API failure |

Act on gaps per `engineering-process` 回传 rules only, with the user; this skill itself stops at the report.
