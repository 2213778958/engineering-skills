# Classification

How `scripts/watch.py` maps native Canvas lifecycle states to the verdicts `alive` / `hung` / `terminal`.

**Hung** = `stuck` / `waiting_for_confirmation` / `paused` / `deleting` / stall / missing `tags.clientsource=agentcanvas` while not terminal / 404 / loop poll-timeout.

**Terminal** = `finished` / `error` / `stopped`. Finished with empty tags is still terminal.

**Alive** = non-terminal, tagged, heartbeat younger than `--stall-sec`.

Heartbeat = last `events/search` `timestamp`, else conversation `updated_at`.

Do not print event bodies. Terminal rows may include truncated `final_response`.

## Task facts (additive)

Each child row also carries `task`: `{ticket, department, request_id, dispatch_status, recorded_at, notify, reason}`, from the parent's dispatch ledger (read-only). Ledger parent = explicit `--parent-id`, else the children's single common `parent_conversation_id`; dispatch entry = the ledger entry whose `child_id` matches the child.

`notify` values:

| Value | Meaning |
|---|---|
| `n/a` | child not terminal yet |
| `notified` | terminal, and a parent-ledger `notify` entry carries the dispatch ticket |
| `missing-notify` | terminal, no such notify entry — the hop is not done |
| `finalization-failed` | ledger unreadable, or entries contradict (conflicting dispatch entries for the child; notify ticket matching no dispatch ticket) |
| `unknown` | no parent ledger identifiable (`--ids` only, no common parent) |

Ledger problems never change `verdict` or the process exit. Unavailable facts keep `null` fields plus `reason` (`ledger-unreadable`, `parent-ledger-unavailable`, `no-dispatch-entry`, `conflicting-dispatch-entries`).
