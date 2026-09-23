# Routing table

Contract for `references/routing-table.md` (this file). #16 implements the data table into this file's format; #17 wires skill-maker. The table lives here as data read at runtime, never engine code (ADR 0006 Decision 1: `docs/adr/0006-skill-registry-grouped-disclosure-and-maker-privilege.md`).

## Format

One Markdown table. One row per registered skill. Columns, in order:

| skill | state | group | entry | uses |
|---|---|---|---|---|
| | | | | |

- `skill`: the skill's declared `name:` in its SKILL.md frontmatter (the source marker). Must equal the directory name.
- `state`: `registered` or `enabled`.
- `group`: one of the task-type groups below.
- `entry`: the spec contains-node path of the skill.
- `uses`: default `engineering-routing`.

#16 fills rows. Do not invent rows here.

## States

- `registered`: skill files exist in the repo + a spec contains entry exists + a routing-table row exists with state `registered`. NOT routable; routing must skip it.
- `enabled`: additionally listed under exactly one task-type group. Routable.

Enablement and registration are both patch-ticket actions, never ad-hoc edits. `registered` → `enabled` transition = patch ticket only.

## Groups

Fixed group vocabulary: `office` / `hardware` / `research` / `process`.

A group is a routing-time grouping for progressive disclosure. The group cut is a routing-time decision: install-time visibility does not imply routability (ADR 0006 Decision 2).

## Registration

A planning patch ticket registers a future skill as exactly three steps:

1. Skill files land in the repo. Anyone may author; authorship is not gated (ADR 0006 Decision 3).
2. Spec contains/uses entry added: a contains edge from the owning parent; every enabled craft skill adds one `uses → engineering-routing` edge; craft skills never get `→ sessions` edges.
3. One routing-table row appended to this file.

Never engine code edits: no SKILL.md engine changes, no scripts in `engineering-*/` or `*-sessions/`. skill-maker is the registrar that executes the patch per its privilege split (ADR 0006 Decision 1 + Decision 3). Registration never dispatches anything by itself: the table is data; routing consumes it.

## Source marker

Every engineering-series skill — directories `engineering-*`, `*-sessions`, `*-watch` — must carry its source marker: the SKILL.md frontmatter `name:` field matching its directory name. Enforcement: guard test `engineering-process/scripts/test_source_markers.py` (fail closed); review is the real enforcement (ADR 0006 Decision 3).

## Consumers

- #16 implements the table rows, groups, and states per this format.
- #17 wires skill-maker as registrar.
- #14 / #19 take their calling convention from this contract.
