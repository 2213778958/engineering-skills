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
- Missing decision → `grilling`. Missing fact → look it up. Do not paste manuals into the entry skill.
- Repo already has engineering conventions → follow them. Else write defaults and mark them as defaults.
- Other skills' APIs → write "read and run `<skill>`". Do not copy them.
- Spawn / subagent **mechanism** → read and run `openhands-sessions`. Do not copy POST. Do not call Task directly. Delegate: wait until the receipt is in this conversation. Background Task → **fail**. Do not finish without the receipt. Department hop done → sessions **notify** (`engineering:report` to the parent). Planning must not notify.
- Stay / dispatch / delegate / model by task type → read and run `engineering-routing`. Do not copy the type table into a product skill.
- `engineering-init` only plans (including migrate graphs and tickets). No clone, no ticket advance. Do not copy planning steps into other skills.
- `engineering-process`: planning is a **department**. The window is **manage**. It **分发** other departments or runs **决策** (staff `planning implement` + review; manage does not run patch). Planning and human **manage** talk to the user. Human tells the user how to test and accept, and helps. 推进 only on planning. Planning conversation that has not confirmed yet (not 回传): write missing `until: none`; print PROCESS modes + MODELS; wait; then 推进. After 回传 / 决策 receipts: templates.md **Stop** tables only (`mode` × `until`; hard stop wins). Patch that changes the ticket net applies only GitHub-native changes (official `blocked-by` edges; an open parent sub-issue blocks its children). Duties: templates.md **职责表** only. Do not rewrite that table elsewhere.
- Do not write process / planning / department / entry rules into `AGENTS.md`. Coding conventions go in root `AGENTS.md`; glossary in `CONTEXT.md`; hard-to-reverse decisions in `docs/adr/`. Latch in `PROCESS.md`. Ask `mode` once and write it; `contract: ready` means initialized; if already set, follow the file; change `mode` only when the user explicitly asks. Model presets in `MODELS.md`: roles follow the `engineering-routing` table; targets resolve via this harness's `*-sessions` **list**; report the table at supervise start. Existing convention files → follow the repo; do not overwrite.
- `SKILL.md` < 500 lines. Paths use forward slashes (`scripts/foo.py`).

## Done

Write both copies. Report paths. Walk the list above, then stop.
