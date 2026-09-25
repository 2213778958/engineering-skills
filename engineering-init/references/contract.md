# Contract (flow tickets)

`gh` is the only client. publish → `gh issue create`. fetch → `gh issue view <n> --comments`. migrate: run these only in the landing repo, never the origin repo.

Conventions, contains, uses are not in this file.

```
gh issue create --title "..." --body-file <utf8-file> --label enhancement --label ready-for-agent --blocked-by 11,12
gh issue edit <n> --add-blocked-by 11 --remove-blocked-by 12
gh issue view <n> --json number,title,state,url,blockedBy,blocking
gh issue reopen <n>
```

## Flow DAG

- Source: no `blocked-by`. Body line `engineering:source`
- Sink: no longer blocking anyone; title = grilled name; not `Finish` / `master`
- Graph `A --> B`: `B` blocked-by `A`
- Unblock = upstream tickets closed. `blockedBy` still has open → do not pull the downstream. Do not unblock by deleting `blocked-by` edges
- **Default 1 source 1 sink.** Multiple only if the user says so. Do not use `--strict-one-one` to block `--write` for the default
- PR nodes are pinned on the graph from the start. Not unblocked to an acceptance ticket → no PR
- Do not open a separate datasheet ticket. Need headers → research the chip interface inside that implement ticket's delivery; delivery implement writes the headers from the research findings
- Spec issue is not a node by default. User Stories stay off this graph
- Do not write extra `Depends on:` body edges
- A second flow graph → only if the user says so

## Acceptance fan-in (fixed when splitting tickets)

Each acceptance ticket's direct children (implement branches or mid `merge/<acceptance>`) **≤4** (default 4; user-named 2 or 3 → follow the user). A 5th to merge → split a mid acceptance first, then block it with the parent acceptance. Already ≤4 → do not split for splitting's sake.

Acceptance body must contain:

```
engineering:pr
engineering:heads:
- feat/<implement-n>-<slug>
engineering:isolate: yes
```

Mid-acceptance heads list direct children: `merge/<child-acceptance>` or `feat/<n>-…`. Do not flatten grandchild feats onto the parent. On-target isolation impossible → `engineering:isolate: no`.

## Labels

One category + one state per ticket. Do not run `triage`.

```
gh label create bug --color d73a4a --force
gh label create enhancement --color a2eeef --force
gh label create needs-triage --color e4e669 --force
gh label create needs-info --color fbca04 --force
gh label create ready-for-agent --color 0e8a16 --force
gh label create ready-for-human --color 1d76db --force
gh label create wontfix --color ffffff --force
```

| Ticket | state | Body |
|---|---|---|
| source | default: close at plan close-out. User wants to confirm the start themselves (e.g. "confirm start") → `ready-for-human` | `engineering:source` |
| implement | `ready-for-agent` | no `engineering:pr` |
| hard-to-see gate | `ready-for-human` | `blocked-by` that implement ticket |
| acceptance / PR (including mid) | `ready-for-agent` | `engineering:pr` + `engineering:heads` (≤4) |
| sink (merge phenomenon; open only if someone must look) | `ready-for-human` | `blocked-by` the final acceptance |

Pause: downstream body `engineering:paused-by #<acceptance>`; `blocked-by` the **last acceptance** of the bugfix chain.

Do not turn the same ticket into a gate. Do not open a PR on the same ticket. Human review fail: the **human** department reopens the previous implement ticket and sends it back to `ready-for-agent`. Do not turn a gate ticket into `ready-for-agent`.
