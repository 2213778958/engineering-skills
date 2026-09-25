# Conventions (defaults)

Repo already has `docs/agents/`, `AGENTS.md`, `CONTEXT.md`, editorconfig / clang-format / prettier / ruff → **follow the repo**; do not overlay these defaults.

Else use this file. Confirm cross-layer / same-layer exposure before drawing uses. Commit format does not block nested graphs.

## Git

- Default branch: `main` (repo already `master` → follow the repo)
- Branches: `feat/<issue>-<slug>` / `fix/<issue>-<slug>`
- Commit: `type(scope): subject`, scope = module name; body `Fixes #<n>` when needed
- type: `feat` `fix` `docs` `refactor` `test` `chore`
- Do not commit straight to the default branch; do not `--force` push shared branches; do not commit secrets or build products
- `.gitignore`: `build/` `*.o` `*.elf` `.env` `node_modules/` `__pycache__/` `docs/agents/PROCESS.md` `docs/agents/HANDOFF.md`

## PR

- Body: Summary, Test plan, `Fixes #<n>` (n = this acceptance ticket)
- Open a PR only while holding an acceptance ticket whose body contains `engineering:pr` (`engineering-process` `acceptance`). `merge: human` (default) → open then stop; `merge: auto` → merge. No acceptance ticket → no `gh pr`
- Human gates check behavior only; format via tools

## Directories

Path = contains node. Repo already has a layout or the user named one → follow the repo.

- Tree has no layers → shallow dirs. Do not invent `hal/` `drivers/` `app/`; do not split `src/` / `Inc/`
- **C/C++** and contains already has layers → one top-level dir per layer, **names from the grilled layer names** (examples in [firmware-layers.md](firmware-layers.md), not fixed words). Modules under their layer (snake_case); public header next to `.c` in that module dir
- **C/C++ installable library** (public shipped headers) only then `include/` + `src/`
- **Other languages** → that ecosystem's usual layout (Python package, TS one `src/`, Go `cmd/`+`internal/`, Rust crate). Do not graft HAL/driver/app dirs; do not invent `Inc/`
- Keep generated trees apart from hand-written; do not edit generated areas unless the ticket says so

## Headers (C/C++, when the repo has no rule)

- `<module>_regs.h`: base, offsets, bitfields
- `<module>_cfg.h`: this-board clock/pin/timing
- Repo already uses a single `<module>_hw.h` → follow the repo
- `#pragma once`; `#include <stdint.h>`; prefix `MODULE_REG_*` / `MODULE_CFG_*`
- Constant comments: datasheet + page/section. No source → delete or research again
- Only symbols this module ticket needs; do not invent registers or typical values
- Location: that module's contains directory. Repo already puts headers in `Inc/` → follow the repo

## Cross-layer / same-layer exposure (before drawing uses)

Non-C/C++: do not use this layer-name set; draw uses from real deps.

**C/C++:** grill no-layer / simple-layers / high-abstraction per [firmware-layers.md](firmware-layers.md) and confirm layer directory names. Unconfirmed → invent no layers, open no tickets. Repo already has names or the user named them → follow the repo.

Include only the other side's **public header**. Do not include someone else's `.c`. `_regs.h` only from that module's `.c`. Same layer must not include the other's `_regs.h`; collaborate via public API or the layer above. Shared types in a named public header. No cyclic includes. ISR: set a flag / enqueue only; heavy work in a thread or the main loop.

### Naming

- Same layer and inside a module (including `static`): `snake_case`
- **Vendor:** keep original names
- Repo already has a prefix table → follow the repo
- **simple-layers:** cross-layer prefix follows this repo's three layer names. Examples `App_` `Drv_` `Bsp_`, not fixed words. Do not write PortOps/Bind
- **high-abstraction:** reusable-component public symbols follow domain/device/protocol names; **do not require** `Layer_Module_Action`. Handle held by the upper assembler; PortOps impl held by the lower adapter. Assembly/product/entry default `Layer_Module_Action` (layer segment = this repo's layer name). Examples only: `FT6X36_Init`, `Platform_Touch_Init`

## Comments

Public APIs must have doc comments. Do not restate the next line. Do not write line numbers.

| Language | Do |
|---|---|
| **C / C++** | **Doxygen**. Public functions, types, macros in headers: `/** @brief … @param[in] x … @return … */`. File header: `@file` `@brief`. `static` in `.c` has no Doxygen unless exported via a header |
| Python | Public modules/classes/functions: Google-style docstring (Args / Returns) |
| TypeScript / JavaScript | Exports: **JSDoc** (`@param` `@returns`) |
| Go | Exports: godoc full sentence starting with the name |
| Rust | `pub`: `///`; crate: `//!` |
| C# | Public API: `/// <summary>` XML |

C example:

```c
/**
 * @file uart1.h
 * @brief USART1 driver public API.
 */

/**
 * @brief Initialize USART1 from _cfg.
 * @retval 0 success
 * @retval nonzero failure
 */
int Drv_Uart1_Init(void);
```

## Style (by file language; if the repo already has a formatter, run only that)

**C:** 4 spaces, column 100, K&R braces. Function names: "Cross-layer / same-layer exposure". Macros ALL_CAPS, `static` default internal, MMIO via `_regs.h` or HAL. No VLA, no recursion. No `malloc` unless the ticket says so. `stdint.h`. Warnings as errors (`-Wall -Wextra -Werror` if it can be turned on).

**C++:** same as C. Do not write C++ in `.c` files.

**Python:** run Ruff/Black if present; else PEP 8, column 88, type annotations on public functions.

**TypeScript / JavaScript:** run Prettier if present; else 2 spaces, strict equality, named export functions.

**Go:** only `gofmt` / `go vet`.

**Rust:** only `rustfmt`.

Mixed repo: follow the language of the file being edited. Do not apply C Doxygen to Python.

## Errors / logs / hardware (embedded default; skip if not embedded)

- Return 0 success, nonzero failure, or follow the HAL status type (repo already has one → follow it)
- Logs on the named USART; no `printf` in ISR
- Feed the watchdog only in the main loop
- `HAL_Delay`: do not use in ISR unless the ticket says so

## Build

- Commands follow the repo (`make` / `cmake` / `npm test`). None → grill one "how to build green"
- Do not commit products

## Tests and hooks

Grill at project start and write `docs/agents/PROCESS.md`. Later only **patch** may fill these; process must not invent commands.

| Field | When | Write |
|---|---|---|
| `verify:` | delivery light | host-runnable tests. None → `none`. After adding host tests, change this line |
| `accept:` | acceptance full | full tests + this repo's hooks (pre-push / CI / on-target scripts). None → `none` |

Arbitration runs `verify:` only to check whether reproduction holds. Failure is not "upstream bug". Enter arbitration only on the three paths in `engineering-process` Key points. Delivery verify is not a party and has no `Challenge` field.

## Agent

- allowlist = that contains node's path
- On own branch only `git add` (allowlist) + `git commit`; no `checkout`/`merge`/`push`. `git push` (code repo) only the delivery **manage**, and only after delivery verify passed; do not push the code repo's default branch. Only other push: the research synthesis subagent pushes the external `research/` repo. Heads merge / worktree git: `acceptance` implement.
- Open a PR only on an acceptance ticket (body `engineering:pr`)
- git worktrees: `engineering-process` creates/removes under the Canvas container `worktree/` (see canvas.md). Do not put a tree path in Canvas `working_dir`
- Implement must not open datasheet PDFs
- Pulling tickets and human review: [contract.md](contract.md)
- AI advance: `engineering-process`. Latch only in `docs/agents/PROCESS.md` (local, not in git): ask `mode` once; `contract: ready` means initialized; later starts follow the file; change `mode` only when the user explicitly asks. Model presets in `docs/agents/MODELS.md` (tracked).
- Do not write process / planning / department / entry rules into `AGENTS.md`. Coding conventions in root `AGENTS.md`; glossary `CONTEXT.md`; hard-to-reverse decisions `docs/adr/`. Existing convention files → follow the repo; do not overwrite.
- `docs/agents/HANDOFF.md` **default do not create**. Write only when the same ticket must cross conversations (crash, **department** 300 turns and ticket still open, hardware on-site). Fold into the close-ticket comment at merge; do not pile onto the default branch
- Department handoff by turn count: OpenHands this `run()` one `agent.step` = one turn; at **300** with ticket still open write HANDOFF; next planning 推进 分发 the same department. `max_iterations` is a cap, not the current turn. ACP: visible assistant turns, also 300. Employee Tasks do not use this cap.
