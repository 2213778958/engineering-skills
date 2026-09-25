---
name: engineering-research
description: >-
  Runs a research employee that turns one requirement into one research
  directory under docs/research/, entered through its README.md. It splits the
  requirement into research faces (prior approaches, assets, technical options,
  chip interfaces from a datasheet, repo facts), researches them, and
  synthesizes one cross-checked answer. For datasheets it produces the chip
  findings that header files are written from; it does not write headers.
  The repo's own library comes first; the internet is only the fallback.
  Raw materials (datasheet PDFs, assets) live in the resources/ library
  beside master/ and worktree/, outside git.
  Use when the user asks to 调研, 技术选型, 方案, 素材, 资料, 数据手册, 寄存器,
  技术文档 PDF, regs.h, cfg.h, address.h, config.h, or to extract hardware
  interfaces from a datasheet.
---

# Engineering research

One **research** employee: one requirement in, one **research directory** out. The manage that staffs research runs these steps; every file under `docs/research/` is written by a delegated subagent, never by the manage window. Every call delivers the same shape — `docs/research/<YYYY-MM>-<slug>/`, entered through its `README.md`. Downstream agents enter from that md; header files, asset imports and code are their work, not research's.

Research is an employee role, not a department: its workers (face and synthesis subagents) are employees (Task); the steps run in the staffing manage's window. Do not write drivers or headers, do not open issues, do not paste PDF body into this conversation. Do not open a child conversation. Any department's **manage** may staff this role; the default home is the **delivery** implement ticket.

Delegate: read and run `engineering-routing` (role `research`). Before delegating, check `../engineering-routing/references/routing-table.md`: only an `enabled` row is routable; a `registered` row stops at the gate (enablement is a patch ticket). Repo `MODELS.md` target wins if present; ignore a `dispatch` link. Do not read `openhands-sessions`, do not copy POST, do not call Task directly.

Directory layout, naming, resource manifest and `resources:` paths: [references/layout.md](references/layout.md).

Commit: the synthesis subagent `git add`s only `docs/research/` and commits on the ticket's branch; no push, no other path. `docs/research/` is outside every implement allowlist; implement and review only read it.

## Inputs

| Caller gives | Research finds |
|---|---|
| requirement (what must be known, and why); scope; return format (what the entry md must answer); hints if known (chip part, PDF path, engine) | faces and their order; sources: repo library first, then `resources/`, then the web |

Requirement missing → stop; `Result: fail` + `Missing: <fields>`. Do not guess, do not ask. Do not ask the user to list registers.

No resources root (layout.md resolution step 4) while a face must store or read a raw file → the whole research stops; `Result: fail` + `Missing: ENGINEERING_RESOURCES`.

Material not found → not an input failure: finish with what was found; list what was not found and where it looked. Exception: a chip-interface face with no datasheet PDF found anywhere cannot produce findings → `Result: fail` + where it looked.

## Sources

Source order — the same for every face:

1. This repo's library: `docs/research/README.md` (already researched → reuse and extend that directory), `docs/`, `docs/adr/`, `AGENTS.md`, `CONTEXT.md`, then the module tree (code, comments, existing conventions).
2. The `resources/` library through `docs/research/resources.md`: a listed resource missing locally → fetch it again from its URL and check the hash.
3. The internet: only the parts 1–2 do not answer. Name each source. A downloaded raw file goes into `resources/`; its manifest row goes into the face receipt.

## Faces

A face is one question the requirement depends on. Typical faces: `approach` (prior solutions), `assets` (reusable materials, license, format), `options` (technical selection), `chip-<part>` (registers / interfaces from a datasheet), `facts` (repo facts). Name others freely; one findings file per face.

A face depends on another when its search needs that face's conclusion (e.g. `assets` needs the engine and art style from `approach`). Write the dependencies before delegating.

## Steps

1. Check Inputs. Read `docs/research/README.md`; reuse an existing directory for the same topic, else name a new one per layout.md.
2. Split the requirement into faces: each face's question, its dependencies, its findings path. Keep this plan in this conversation; it goes into every face prompt and into the synthesis prompt.
3. Read and run `engineering-routing` once per face. Faces with no open dependency may run in parallel (≤3); a dependent face starts after its upstream finishes, and its prompt carries the upstream conclusion as a constraint. Prompt: the employee prompt fields of `engineering-process` rules.md 10 (ticket-tree `cd` path first, ticket URL, allowlist = the findings file only, the fixed repo-docs / no-push line), then face question, constraints, scope, done criteria (findings file written, not committed; downloaded raw files placed under `resources/`; their manifest rows returned in the receipt, not written to `resources.md`). Do not paste long source text or PDF body.
4. Wait until each subagent ends and its receipt is in this conversation. Background Task → **fail**. No `spawn.py`.
5. **Synthesize.** Read and run `engineering-routing` once more for a synthesis subagent. Prompt: the rules.md 10 fields (ticket-tree `cd` path first, ticket URL, allowlist = this research directory + `docs/research/README.md` + `docs/research/resources.md`), then the plan, the findings paths, the manifest rows from the face receipts. It cross-checks the findings against each other (license compatibility, format fits the chosen stack, conflicting recommendations, missing constraints), then writes the entry `README.md` (requirement, conclusion, per-face index, conflicts, not-found list), appends the manifest rows to `docs/research/resources.md`, and adds the directory's row to `docs/research/README.md`; it commits per Commit above and returns the commit SHA. Wait for its receipt.
6. Check: every claim cites a named source; repo-library-first is visible; every `resources:` path has a manifest row. Web-only answer with a repo hit available → fail, then run the face again.
7. Report: entry md path + faces + subagent names.

## Chip-interface face

The datasheet PDF goes to `resources:datasheets/`; find it by the caller's hint first, then the repo's `.pdf` files, then the web. A PDF found in the repo is copied into `resources:datasheets/`; its manifest row goes into the face receipt; it is not removed from git here. The reader subagent writes `findings/chip-<part>.md`: base addresses, register offsets, bitfields, timing and pin constants the requirement needs — each with PDF file name + page or section. This conversation only reads the findings md; it never opens the PDF.

Header files are written downstream by the delivery implement from that findings md, per [references/headers.md](references/headers.md).
