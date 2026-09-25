# Repo convention files

How engineering conventions land in the landing repo. Do not write the origin repo. Writing must use this file's skeleton; do not invent headings or reorder them.

Same-named file already exists → **follow the repo; do not overwrite the whole file**. Fill only missing files. `patch` does not change these files by default; the user must explicitly change conventions / glossary / a decision.

Not-normalized migrate: do not inject. Normalized landing repo: this file.

## Rules

- Fix languages and project type first, then write files. Language unconfirmed → stop; do not write style.
- Only write language sections this repo uses. Do not put C Doxygen / header rules in a Python-only repo.
- Repo text must not contain skill paths, `firmware-layers.md`, `conventions.md`, or the phrase "example directory". Layer names are **this repo's confirmed names**.
- User-named convention text goes in verbatim. Do not rewrite it.
- Do not put `mode` / `issue` / `template` / dispatch table / planning or department steps in `AGENTS.md`, `CONTEXT.md`, or ADRs.
- UTF-8. Windows: `Path.write_text(..., encoding="utf-8")`.
- `docs/agents/PROCESS.md` and `docs/agents/HANDOFF.md` **are not in git** (add to `.gitignore`). Employee `git add -A` must not pick them up.
- Injecting convention files is not implementation.

## Key points: files

| Path | If missing | If present |
|---|---|---|
| `AGENTS.md` | create from the skeleton below | leave |
| `CONTEXT.md` | create only if this turn has confirmed terms | append new terms only |
| `CONTEXT-MAP.md` | create only if the user confirmed multiple bounded contexts | do not change map structure; only edit pointed-to booklets |
| `docs/adr/NNNN-slug.md` | create dir and file only if a qualifying decision exists | next number for a new decision |
| `.editorconfig` | create | leave |
| `.clang-format` | this repo has C/C++ and the file is missing | leave |
| `.prettierrc` | this repo has TS/JS and no Prettier | leave |
| `pyproject.toml` `[tool.ruff]` | this repo has Python and no Ruff/Black | existing toml: add the missing table only, do not split the original |
| `.gitignore` | create | append missing lines only; do not delete |

## Key points: project type → slices

Detect type (may be several; mixed repo: section by file language):

| Type | How |
|---|---|
| empty repo | no product source → grill primary language(s) |
| C/C++ embedded | user said MCU / HAL / STM32 / on-target, or HAL already in the tree |
| C/C++ host | has C/C++ but is not embedded |
| Python / TS / JS / Go / Rust / C# | extension or user-named |

`AGENTS.md` sections (write only those that apply; delete unused headings entirely):

| Section | When |
|---|---|
| Opening pointers | always |
| Git | always |
| Directories | always |
| Style | always (this repo's languages only) |
| Comments | always (this repo's languages only) |
| Headers | C/C++ |
| Cross-layer | C/C++ and **layered** confirmed (simple-layers or high-abstraction) |
| Errors / logs / hardware | C/C++ **embedded** |
| Build | always |

C/C++ no-layer → include Headers, omit Cross-layer. Non-C/C++ → omit both.

## Steps: sequence

plan / normalize-migrate close-out: `PROCESS.md` written (local) → this file injects → `MODELS.md` written → **one** commit + push default branch.

1. List this repo's languages, embedded or not, C/C++ layer template and layer dir names (unconfirmed → stop).
2. List files to create/fill this turn (see "Key points: files").
3. Write `AGENTS.md` (or skip if present).
4. Write `CONTEXT.md` (skip if no terms).
5. Write ADRs (skip if no qualifying decision).
6. Write formatters / `.gitignore` (gitignore must include `docs/agents/PROCESS.md` and `docs/agents/HANDOFF.md`).
7. Stop. Do not commit here. Return to plan: after `MODELS.md` is written, follow "Steps: commit".

## Steps: AGENTS.md

File exists → end this step. Missing → **write the skeleton below; heading order is fixed**. Delete inapplicable sections; do not leave empty headings.

```
# AGENTS.md

Process latch: `docs/agents/PROCESS.md`
Model table: `docs/agents/MODELS.md`
Glossary: `CONTEXT.md`
Decisions: `docs/adr/`

Coding and directory conventions. Do not put the current ticket number, mode, or template in this file.

## Git

- Default branch: `<main, or master if the repo already uses it>`
- Branches: `feat/<issue>-<slug>` / `fix/<issue>-<slug>`
- Commit: `type(scope): subject`, scope = module name; body `Fixes #<n>` when needed
- type: `feat` `fix` `docs` `refactor` `test` `chore`
- Do not commit straight to the default branch; do not `--force` push shared branches; do not commit secrets or build products

## Directories

<fill: Directories>

## Style

<one block per language, headings **C:** **Python:** etc.>

## Comments

Public APIs must have doc comments. Do not restate the next line. Do not write line numbers.

<only this repo's languages, copied from the conventions comments table>

## Headers

<C/C++ only; fill: Headers>

## Cross-layer

<C/C++ layered only; fill: Cross-layer>

## Errors / logs / hardware

<embedded only; copy the four conventions bullets; USART name follows the repo if it has one>

## Build

- Command: `<grilled build/test command; unconfirmed → "unset; see PROCESS.md verify/accept">`
- Do not commit products
```

### Fill: Directories

No layers: write "Shallow directories; paths follow contains nodes. Do not invent layer directories." Then one ecosystem line for the primary language:

| Language | Write |
|---|---|
| Python | package dir follows the module name; tests in `tests/` |
| TS / JS | one `src/` tree |
| Go | `cmd/` + `internal/` |
| Rust | crate root; `src/bin/` only if the user named it |
| C# | `.csproj` at repo root or `src/<name>/` (follow the user if named) |
| C/C++ no-layer | source and header in the same module dir; do not split `src/` / `Inc/` unless the user named it |

Layered (C/C++): write the template name (simple-layers / high-abstraction), then the table:

```
| Role | This repo dir | Prefix |
|---|---|---|
| <role> | `<confirmed dir>` | `<confirmed prefix_>` |
```

simple-layers: three fixed rows: entry, middle, next-to-Vendor. high-abstraction: confirmed roles (merged entry+product-flow → one fewer row). Then: modules under their layer (snake_case); public header next to `.c`. Vendor keeps original names.

### Fill: Style

Copy only this repo's languages. Turn the conventions style section into statements. C/C++ function naming: do not write "see section X"; write:

- no-layer: `snake_case`
- simple-layers: cross-layer public functions `<prefix>_*` using the table above
- high-abstraction: components follow device/protocol names; assembly/product/entry `Layer_Module_Action` (layer segment = this repo's layer name)

Mixed repo: add "follow the language of the file being edited".

### Fill: Headers

Use these bullets as-is; keep `<module>`:

- `<module>_regs.h`: base, offsets, bitfields
- `<module>_cfg.h`: this-board clock/pin/timing
- Repo already uses a single `<module>_hw.h` → follow the repo
- `#pragma once`; `#include <stdint.h>`; prefix `MODULE_REG_*` / `MODULE_CFG_*`
- Constant comments: datasheet + page/section. No source → delete or extract again
- Location: that module's contains directory

Repo already puts headers in `Inc/` → last bullet becomes "headers live in `Inc/`".

May add **one** C comment example. Prefix in the example must be this repo's prefix; do not write `Drv_` unless that is this repo's name.

### Fill: Cross-layer

First sentence: the confirmed template. Then:

- Include only the other side's public header. Do not include someone else's `.c`
- `_regs.h` only from that module's `.c`. Same layer must not include the other's `_regs.h`
- Shared types in a named public header. No cyclic includes
- ISR: set a flag / enqueue only; heavy work in a thread or the main loop

simple-layers: also write uses direction (entry → middle → next-to-Vendor; entry does not depend directly on next-to-Vendor / Vendor except ticket whitelist). Do not write PortOps / Bind / Handle.

high-abstraction: also write the role duty table (dirs = this repo's names), ownership table, assembly order `Handle+Context → Bind → Init`, forbidden list (static this-environment instance in a component; component includes adapter/assembly/Vendor; standalone `port/`). Do not freeze five layers.

## Steps: CONTEXT.md

Glossary. Not spec, not tickets, not style.

### Skeleton (single context, default)

```
# <product or repo name>

<one or two sentences: what this is>

## Language

### <group name>

**<chosen term>**:
<one or two sentences what it IS, not how it is implemented>
_Avoid_: <unused synonyms; omit this line if none>
```

Group order is fixed: `Product` → `Layers` (only if layered) → other domain clusters (device / protocol / gameplay / role…, create a group only if it has terms). Order inside a group may follow grill order; alphabetical not required.

### Which terms

Write: product name, confirmed layer names, **domain words** on the module list (device, protocol, gameplay, role, peripheral).

Do not write: `src` `utils` `test` `app` as ordinary modules (except as a layer name), ticket numbers, file names, general programming words (timeout, buffer, error).

One word, two meanings, unconfirmed → read and run `engineering-routing` for the decision; do not guess. Synonyms: pick one; the rest go under `_Avoid_`.

### File already exists

Append new terms under the matching group. Do not clear. Do not change old definitions unless the user edits the glossary.

### Multiple contexts

Only if the user confirmed multiple bounded contexts: root `CONTEXT-MAP.md`, each context its own `CONTEXT.md`. Map skeleton:

```
# Context Map

## Contexts

- [<name>](./<relative>/CONTEXT.md): <one sentence>

## Relationships

- **A → B**: <one sentence who emits what, who consumes>
```

Multiple contexts unconfirmed → root `CONTEXT.md` only. No terms this turn → do not create an empty glossary.

## Steps: ADR

Write only when all three hold: hard to reverse; a later reader of the code will ask why; there was a real trade-off.

| Write | Do not write |
|---|---|
| Which C/C++ layer template was chosen | default 1 source 1 sink |
| high-abstraction entry vs product-flow merged or split | default `merge: human` |
| User explicitly chose multi source / sink | default `verify: none` / `accept: none` |
| User changed default-branch policy, or deliberately skipped an ORM/framework | indent width (that is AGENTS.md) |
| How bounded contexts are cut, ownership | the module list itself (that is CONTEXT / spec) |

### File

Path: `docs/adr/NNNN-slug.md`. `NNNN` = highest existing + 1 (else `0001`). `slug` = title lowercased, `a-z0-9` only, spaces to `-`, max 40.

Dir missing and this turn has a qualifying decision → create it. No qualifying decision → do not create empty `docs/adr/`.

### Skeleton

```
# <short title>

<1–3 sentences: context, decision, why>
```

Do not add Status / Options / Consequences unless the user asks. Do not copy the ticket net.

Layer ADR title: `C/C++ uses <no-layer|simple-layers|high-abstraction>`. Body must include this repo's layer directory names.

## Steps: formatter

Matching file exists → skip that file. Missing → **write the full text below**; do not rename keys.

### `.editorconfig` (any language, only if missing)

Keep `[*]` plus sections this repo's languages will hit. No Go → no `[*.go]`.

```
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true
```

Append by language:

```
[*.{c,h,cpp,hpp}]
indent_style = space
indent_size = 4

[*.py]
indent_style = space
indent_size = 4

[*.{js,ts,tsx,jsx,json,yml,yaml}]
indent_style = space
indent_size = 2

[*.cs]
indent_style = space
indent_size = 4

[*.go]
indent_style = tab

[Makefile]
indent_style = tab
```

### `.clang-format` (C/C++, only if missing)

```
BasedOnStyle: LLVM
IndentWidth: 4
ColumnLimit: 100
BreakBeforeBraces: Attach
AllowShortIfStatementsOnASingleLine: false
SortIncludes: true
```

### `.prettierrc` (TS/JS, only if the repo has no Prettier)

```
{
  "tabWidth": 2,
  "singleQuote": true,
  "semi": true
}
```

### Ruff (Python, only if the repo has no Ruff/Black)

No `pyproject.toml` → create with only:

```
[tool.ruff]
line-length = 88
```

`pyproject.toml` exists without `[tool.ruff]` → append that table at the end. Ruff/Black already present → do not add a second set.

Go / Rust: do not write another formatter.

## Steps: .gitignore

File missing → create. Present → append lines below that are not already there.

Required:

```
build/
*.o
*.elf
.env
node_modules/
__pycache__/
docs/agents/PROCESS.md
docs/agents/HANDOFF.md
```

Append missing by language:

| Language | Append |
|---|---|
| Python | `*.pyc` `.venv/` `dist/` `*.egg-info/` |
| TS / JS | `dist/` `coverage/` |
| C / C++ | `*.a` `*.so` `*.exe` `*.hex` `*.map` |
| Rust | `/target/` |
| Go | `vendor/` only if the user does not vendor; default omit |
| C# | `bin/` `obj/` |

## Steps: commit

After `MODELS.md` is written. One commit.

```
git add AGENTS.md CONTEXT.md CONTEXT-MAP.md docs/adr .editorconfig .clang-format .prettierrc pyproject.toml .gitignore docs/agents/MODELS.md
```

Only add paths that exist and changed this turn. **Do not** `git add` `docs/agents/PROCESS.md` or `HANDOFF.md`.

Already on the default branch (`main`, or `master` if the repo uses it):

```
git commit
git push -u origin HEAD
```

Not on the default branch → stop; report the branch name. Do not leave convention files only on a feat branch.

This init close-out may push the default branch. The `AGENTS.md` line "do not commit straight to the default branch" constrains later employees.

Report: what was created, what was skipped as follow-the-repo, glossary term count, ADR filenames, whether origin has these files.
