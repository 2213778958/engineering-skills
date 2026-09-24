# Classification

How `scripts/watch.py` maps native Canvas lifecycle states to the verdicts `alive` / `hung` / `terminal`.

**Hung** = `stuck` / `waiting_for_confirmation` / `paused` / `deleting` / stall / missing `tags.clientsource=agentcanvas` while not terminal / 404 / loop poll-timeout.

**Terminal** = `finished` / `error` / `stopped`. Finished with empty tags is still terminal.

**Alive** = non-terminal, tagged, heartbeat younger than `--stall-sec`.

Heartbeat = last `events/search` `timestamp`, else conversation `updated_at`.

Do not print event bodies. Terminal rows may include truncated `final_response`.
