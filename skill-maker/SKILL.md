---
name: skill-maker
description: >-
  Author or edit personal Agent Skills as operations-only documents. Use when
  the user asks to 制作 skill, 写 skill, 改 skill, skill-maker, or to add a
  SKILL.md. Writes commands, not reasons. Skills are written in English.
---

# skill-maker

Read this when creating or editing a skill. Write operations, not reasons.

## Registrar

Registering a skill = execute a registration patch ticket. Registration never dispatches anything: the table is data, routing consumes it; `registered` is NOT routable. Follow `engineering-routing/references/routing-table.md` § Registration step-for-step. Privileges and enforcement: read `references/privileges.md`.

1. Skill files land in the repo: `<name>/SKILL.md` present, frontmatter `name:` equal to the directory name. Anyone may author; authorship is not gated.
2. Spec contains/uses entry added: a contains edge from the owning parent; every enabled craft skill adds one `uses -> engineering-routing` edge; craft skills never get `-> sessions` edges.
3. Exactly one routing-table row appended to `engineering-routing/references/routing-table.md`: state `registered` (not `enabled`), empty `group`, empty `uses`, `entry` = the skill name with no path separators.
4. Never engine code: no edits to engineering-series `SKILL.md` or scripts. The table file itself is data, not engine code.
5. Registration never dispatches anything. Enablement (`registered` -> `enabled`) is a separate patch ticket, not part of registration.

Validate before executing the patch: `python skill-maker/scripts/registrar_check.py --name <name> --table engineering-routing/references/routing-table.md`. Empty output = pass. Fail closed on malformed input; never guess.

## Disk

1. Directories: `~/.cursor/skills/<name>/` and `~/.openhands/skills/<name>/`, identical copies.
2. Do not write `~/.cursor/skills-cursor/`.
3. Required: `SKILL.md`. Details in `references/`. Fragile steps in `scripts/`. One-level references only.
4. `name`: lowercase letters, digits, hyphens, ≤64.
5. `description`: what it does + when to use (trigger phrases), third person. Do not write why.

## Language

- Skill body, headings, tables, and receipts: **English only**.
- YAML `description`: English prose, plus the user's trigger phrases **verbatim** (any language). Do not translate those phrases.
- Talk to the user in the user's language. That is not the skill body.
- Keep API field names, file names, labels, and `engineering:*` markers as-is.

## Body

- Write: do X; if Y → do Z; done criteria.
- Do not write: reasons, root causes, why, background, comparisons, history, bug stories.
- Callers are **this conversation**. Keep API field names unchanged (e.g. `parent_conversation_id`).
- User-supplied sentences go in verbatim. Do not rewrite them.
- Missing decision → `grilling`. Missing fact → look it up. Do not paste manuals into the entry skill.
- Repo already has engineering conventions → follow them. Else write defaults and mark them as defaults.
- Process / planning behavior (planning is a **department**; **分发** / **决策** / **回传**; duties **职责表**) → read and run `engineering-process`. Do not copy that behavior into a product skill.
- Convention-file and latch behavior (`AGENTS.md` / `CONTEXT.md` / `docs/adr/` / `PROCESS.md` / `MODELS.md`; ask `mode` once) → read and run `engineering-init`. Do not copy that behavior into a product skill.
- `SKILL.md` < 500 lines. Paths use forward slashes (`scripts/foo.py`).

## Privileges

Authority is split in three; detail and the registration/enablement flow: read `references/privileges.md`.

1. **Exclusive engineering-series modifier** — only skill-maker edits or creates engineering-series skills (`engineering-*`, `*-sessions`, `*-watch`); every such change goes through a patch/acceptance ticket. Ad-hoc edits → **fail**.
2. **Registrar** — execute registration patch tickets per `references/privileges.md`: the routing table in `engineering-routing` is data, routing consumes it; `registered` is NOT routable; enablement is a separate patch ticket; registration never dispatches; never engine code; fail closed on malformed input.
3. **No ownership of product craft content** — anyone may author a craft skill; skill-maker does not own, rewrite, or gate craft content.

## Done

Write both copies. Report paths. Walk the list above, then stop.
