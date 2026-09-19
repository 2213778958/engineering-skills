# AGENTS.md

Process latch: `docs/agents/PROCESS.md`
Model table: `docs/agents/MODELS.md`
Glossary: `CONTEXT.md`
Decisions: `docs/adr/`

Coding and directory conventions. Do not put the current ticket number, mode, or template in this file.

## Git

- Default branch: `main`
- Branches: `feat/<issue>-<slug>` / `fix/<issue>-<slug>`
- Commit: `type(scope): subject`, scope = module name; body `Fixes #<n>` when needed
- type: `feat` `fix` `docs` `refactor` `test` `chore`
- Do not commit straight to the default branch; do not `--force` push shared branches; do not commit secrets or build products

## Directories

Shallow directories; paths follow contains nodes. Do not invent layer directories.
Each contains node is a top-level skill directory (`SKILL.md`, optional `references/`, optional `scripts/`). Python helpers and their tests live in that skill's `scripts/`.

## Style

**Python:** PEP 8, column 88, type annotations on public functions. Run Ruff if present.

**Markdown:** follow the language of the file being edited. Skill bodies stay operations, not rationale.

## Comments

Public APIs must have doc comments. Do not restate the next line. Do not write line numbers.

**Python:** Public modules/classes/functions: Google-style docstring (Args / Returns)

## Build

- Command: `python engineering-init/scripts/test_render_graph_refs.py && python openhands-watch/scripts/test_watch.py`
- Do not commit products
