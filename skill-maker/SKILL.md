---
name: skill-maker
description: >-
  Author or edit personal Agent Skills as operations-only documents. Use when
  the user asks to 制作 skill, 写 skill, 改 skill, skill-maker, or to add a
  SKILL.md. Writes commands, not reasons. Skills are written in English.
---

# skill-maker

Read this when creating or editing a skill. Write operations, not reasons.

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
- Missing decision → read and run `engineering-routing` for the decision. Missing fact → look it up. Do not paste manuals into the entry skill.
- Repo already has engineering conventions → follow them. Else write defaults and mark them as defaults.
- Process / planning behavior (planning is a **department**; **hand off** / **decide** / **report back**; duties **duty table**) → read and run `engineering-process`. Do not copy that behavior into a product skill.
- Convention-file and latch behavior (`AGENTS.md` / `CONTEXT.md` / `docs/adr/` / `PROCESS.md` / `MODELS.md`; ask `mode` once) → read and run `engineering-init`. Do not copy that behavior into a product skill.
- `SKILL.md` < 500 lines. Paths use forward slashes (`scripts/foo.py`).

## Privileges

Authority is split in three; detail and the registration/enablement flow: read `references/privileges.md`.

1. **Exclusive engineering-series modifier** — only skill-maker edits or creates engineering-series skills (`engineering-*`, `*-sessions`, `*-watch`); every such change goes through a patch/acceptance ticket. Ad-hoc edits → **fail**.
2. **Registrar** — execute registration patch tickets per `references/privileges.md`: the routing table `engineering-routing/references/routing-table.md` is data, routing consumes it; `registered` is NOT routable; enablement is a separate patch ticket; registration never dispatches; never engine code; validate with `scripts/registrar_check.py` first and fail closed on malformed input.
3. **No ownership of product craft content** — anyone may author a craft skill; skill-maker does not own, rewrite, or gate craft content.

## Done

Write both copies. Report paths. Walk the list above, then stop.
