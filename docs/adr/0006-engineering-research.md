# Datasheet extract is a research type; research checks the repo library first

## Status

Accepted, 2026-09-25. Output part superseded by ADR 0008 (research delivers one research directory; headers are written downstream).

## Context

The v0.1 skill set carried a dedicated `datasheet-headers` skill. It existed
only for one narrow case — mining a datasheet PDF into `<module>_regs.h` /
`<module>_cfg.h` / `<module>_address.h` / `<module>_config.h` header files —
while a general research capability (answering technical questions, comparing
options, delivering a research document) was planned but never landed. Routing
held a separate datasheet extract row, `engineering-process` named a dedicated
`datasheet extract` employee role, and callers had to know the skill by name.
Because the research capability was missing, tickets were accepted
(#21) with a FAIL on its absence; #55 asks to fold the two together.

This is a capability-modeling problem, not a header-format problem: the header
mechanics were sound, but modeling extraction as its own employee role forced
callers to dispatch differently for research versus datasheet work.

## Decision

`datasheet-headers` is merged into a new `engineering-research` skill. The
skill performs general research — it delivers one research document — and
datasheet extraction becomes one mode of it, still writing the same hardware
header files under `engineering-research/references/`. The `datasheet-headers`
directory is deleted. Employee role names in `engineering-process` and the
职责表 change from `datasheet extract` to `research`, and `engineering-routing`
routes both research and datasheet tasks to `engineering-research`.

Source order is fixed for every mode: the repo's own library first — `docs/`,
`docs/adr/`, `AGENTS.md`, `CONTEXT.md`, then the module tree — and the internet
only for the parts the repo library does not answer. A research document's
source list must show repo hits before any web source.

Callers only read and run `engineering-routing`; they do not name
`engineering-research` and do not name a person (Matt). Any department's
manage may staff the `research` employee; the default home is the delivery
implement ticket.

The decision record is numbered 0006, not 0005, because main's `docs/adr/`
already holds `0005-cancel-dependency-graph.md`. An early draft of this
decision circulated as a `0005-engineering-research.md` note on the branch
`feat/adr-skill-layers`; that draft was a short Chinese memo, not an ADR, and
its number was already taken on main. `0004` is reserved by an untracked
`0004-*.md` file in the main checkout and is deliberately left unused here.

## Consequences

The skill count stays at seven and v0.1 needs no eighth skill. Routing loses
the datasheet extract row and the trigger words; callers need one entry for
"answer a question or extract a datasheet". Employee kind lists gain `research`
and lose `datasheet extract`; a MODELS row named `datasheet` now means the
`research` employee. Datasheet extraction inherits the repo-library-first
order, so a datasheet task still consults repo conventions for output paths
and symbols before opening the PDF. Documents that mentioned the standalone
`datasheet-headers` skill describe history only; the name survives solely in
this record.

## Alternatives rejected

Keeping `datasheet-headers` as a separate skill was rejected because it
duplicates the research entry — both answer "find out and report" — and forces
callers to choose between two dispatch paths. Renaming the old skill to
`engineering-research` without merging the mechanics into a reference file was
rejected because the general research behavior and the header mechanics would
compete for the same SKILL.md body, and the header rules are reader-level
detail that belongs behind a reference link. Numbering this record 0005 was
rejected because main already committed `0005-cancel-dependency-graph.md`.
