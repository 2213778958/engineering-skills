---
name: engineering-research
description: >-
  Runs a research employee that turns one requirement into one research
  directory in the external research/ library beside master/ and worktree/,
  entered through its <slug>.md. It splits the requirement into research faces
  (prior approaches, assets, technical options, chip interfaces from a
  datasheet, repo facts), researches them, and synthesizes one cross-checked
  answer. For datasheets it produces the chip findings that header files are
  written from; it does not write headers. The repo's own library comes first;
  the internet is only the fallback. Raw materials (datasheet PDFs, assets)
  live in the resources/ library, also outside the code repo.
  Use when the user asks to 调研, 技术选型, 方案, 素材, 资料, 数据手册, 寄存器,
  技术文档 PDF, regs.h, cfg.h, address.h, config.h, or to extract hardware
  interfaces from a datasheet.
---

# Engineering research

One **research** employee: one requirement in, one **research directory** out. Every call delivers the same shape — `research:<YYYY-MM>-<slug>/<slug>.md` in the external `research/` library, never inside the code repo. Downstream agents enter from that md; header files, asset imports and code are their work, not research's. The manage that staffs research runs these steps; every file under `research/` is written by a delegated subagent, never by the manage window.

Research is an employee role, not a department: its workers (face and synthesis subagents) are employees (Task); the steps run in the staffing manage's window. Do not write drivers or headers, do not open issues, do not paste PDF body into this conversation. Do not open a child conversation. Staffed by the **delivery** (default: its implement ticket), **acceptance** or **planning** manage (planning: during 决策, as input to planning). **human** and **arbitration** do not staff research.

Delegate: read and run `engineering-routing` (role `research`). Before delegating, check `../engineering-routing/references/routing-table.md`: only an `enabled` row is routable; a `registered` row stops at the gate (enablement is a patch ticket). Repo `MODELS.md` target wins if present; ignore a `dispatch` link. Do not read `openhands-sessions`, do not copy POST, do not call Task directly.

Libraries, naming, manifest, `research:` / `resources:` paths and sync: [references/layout.md](references/layout.md).

Sync: the code repo never receives research files. `research/` is a git repo (the project's GitHub Wiki, or a separate research repo) → the synthesis subagent commits and pushes that repo only. Otherwise it only writes files.

## Inputs

| Caller gives | Research finds |
|---|---|
| requirement (what must be known, and why); scope; return format (what the entry md must answer); hints if known (chip part, PDF path, engine) | faces and their order; sources: repo library first, then `research/` and `resources/`, then the web |

Requirement missing → stop; `Result: fail` + `Missing: <fields>`. Do not guess, do not ask. Do not ask the user to list registers.

No research root (layout.md) → the whole research stops; `Result: fail` + `Missing: ENGINEERING_RESEARCH`. No resources root while a face must store or read a raw file → the whole research stops; `Result: fail` + `Missing: ENGINEERING_RESOURCES`.

Material not found → not an input failure: finish with what was found; list what was not found and where it looked. Exception: a face whose type needs a primary document (Faces table) and none is found anywhere cannot produce findings → `Result: fail` + where it looked.

## Sources

Source order — the same for every face:

1. This repo's library: `docs/`, `docs/adr/`, `AGENTS.md`, `CONTEXT.md`, then the module tree (code, comments, existing conventions).
2. The research library: `research:Home.md` (already researched → reuse and extend that directory); the `resources/` library through `research:resources.md` (a listed resource missing locally → fetch it again from its URL and check the hash).
3. The internet: only the parts 1–2 do not answer. Name each source.

A raw file found in the repo or downloaded (PDF, spec, asset) is copied into `resources/` (not removed from git) and its manifest row goes into the face receipt. The manage window never opens a raw file; it reads findings md only.

## Faces

A face is one question the requirement depends on; one findings file per face (`<slug>--<face>.md`). Common types — pick the ones the requirement needs, name others freely:

| Type | Finds | Typical sources | Findings list | Primary document |
|---|---|---|---|---|
| `approach` | how others solved it | open-source projects, papers, talks, write-ups | approaches, trade-offs, links | no |
| `options` | technical selection | official docs, benchmarks | comparison table, criteria, recommendation | no |
| `library` | reusable code / dependencies | package registries, GitHub | name, version, license, maintenance, API fit | no |
| `assets` | reusable art / audio / models / fonts | asset sites, GitHub | name, license, format, `resources:` path | no |
| `api` | third-party API / SDK behavior | vendor docs, SDK source | calls, parameters, limits, auth, doc links | vendor docs |
| `standard` | protocol / specification requirements | specs, RFCs | clauses, each with section reference | the spec |
| `chip` | registers / interfaces of a part | datasheet, reference manual, app notes | addresses, offsets, bitfields, timing, pins, each with file + page | the datasheet |
| `facts` | what this repo already does | this repo | facts, each with `file:line` | no |

Raw documents go to `resources/` (`datasheets/`, `refs/`, `assets/`). A findings file that feeds a downstream format says so; `chip` findings are the input of [references/headers.md](references/headers.md).

A face depends on another when its search needs that face's conclusion (e.g. `assets` needs the engine and art style from `approach`). Write the dependencies before delegating.

## Steps

Every subagent prompt starts with the employee prompt fields of `engineering-process` rules.md 10: ticket-tree `cd` path first (planning-staffed: `master/`), ticket URL (planning-staffed: the ticket under 决策, else `none`), allowlist, the fixed repo-docs line.

1. Check Inputs. Resolve the research root. Read `research:Home.md`; reuse an existing directory for the same topic, else name a new one per layout.md.
2. Split the requirement into faces: each face's question, its dependencies, its findings path. Keep this plan in this conversation; it goes into every face prompt and into the synthesis prompt.
3. Read and run `engineering-routing` once per face. Faces with no open dependency may run in parallel (≤3); a dependent face starts after its upstream finishes, and its prompt carries the upstream conclusion as a constraint. Prompt: the fields above (allowlist = the findings file only; no commit, no push), then face question, constraints, scope, done criteria (findings file written; downloaded raw files placed under `resources/`; their manifest rows returned in the receipt, not written to `resources.md`). Do not paste long source text or PDF body.
4. Wait until each subagent ends and its receipt is in this conversation. Background Task → **fail**. No `spawn.py`.
5. **Synthesize.** Read and run `engineering-routing` once more for a synthesis subagent. Prompt: the fields above (allowlist = this research directory + `research:Home.md` + `research:resources.md`), then the plan, the findings paths, the manifest rows from the face receipts. It cross-checks the findings against each other (license compatibility, format fits the chosen stack, conflicting recommendations, missing constraints), then writes the entry `<slug>.md` (requirement, conclusion, per-face index, conflicts, not-found list), appends the manifest rows to `research:resources.md`, adds the directory's row to `research:Home.md`, and syncs per Sync above (returns the research-repo commit SHA, or `not a git repo`). In this prompt the fixed line reads "do not git push the code repo; push only the `research/` repo". Wait for its receipt.
6. Check: every claim cites a named source; repo-library-first is visible; every `resources:` path has a manifest row. Web-only answer with a repo hit available → fail, then run the face again and rerun synthesis.
7. Report: entry `research:` path + faces + sync result + subagent names.

Downstream implement prompts name the `research:` entry path as read-only input.
