# Research delivers one research directory; raw materials live outside git

## Status

Accepted, 2026-09-26. Supersedes the output part of ADR 0006 (datasheet extraction writing header files).

## Context

ADR 0006 folded `datasheet-headers` into `engineering-research` with two functions split by output type: a question produced one research document, a datasheet produced `.h` files. A real requirement usually spans several faces — a game needs prior approaches and reusable assets — and the faces constrain each other (engine, art style, license). Split by output type, the caller had to run each face separately and stitch the answers; nobody cross-checked them. Downloaded datasheets and assets had no home: inside a checkout they bloat git, raise redistribution questions, and must be copied into every worktree.

## Decision

1. Research always delivers one research directory, `docs/research/<YYYY-MM>-<slug>/`, entered through its `README.md`. Downstream agents enter from that md; headers, asset imports and code are their work.
2. `docs/research/README.md` indexes every research directory; research reads it first and extends an existing directory for the same topic. Research directories hold Markdown only.
3. Research splits the requirement into faces, records their dependencies, researches independent faces in parallel and dependent faces with the upstream conclusion as a constraint, then synthesizes: it cross-checks licenses, formats and conflicting recommendations and writes them into the entry md. Face and synthesis work run in delegated subagents; only the synthesis subagent writes the index and the manifest. The synthesis subagent commits `docs/research/` on the ticket's branch; `docs/research/` is outside every implement allowlist. Research is staffed by the delivery, acceptance or planning manage, never human or arbitration; planning-staffed research commits on the default branch in `master/` and planning implement pushes it.
4. Raw materials live in `resources/` beside `master/` and `worktree/` in the container folder, outside every git checkout, shared by all worktrees. Sharing them means packing them separately.
5. `docs/research/resources.md` is committed: one row per raw file with URL, fetch date, license, size and sha256. A missing file is fetched again and hash-checked; unreachable → listed as not found.
6. Markdown refers to raw files as `resources:<path>`. The root resolves from `ENGINEERING_RESOURCES`, else the first parent directory holding both `master/` and `resources/`, else `resources/` is created beside the first parent's `master/`. No `master/` parent and no variable while a face needs raw files → the whole research fails with `Missing: ENGINEERING_RESOURCES`.
7. Material not found is not a failure; the entry md lists it with where research looked. A chip-interface face with no datasheet PDF anywhere fails.
8. A datasheet is one face: the PDF goes to `resources:datasheets/`, registers and interfaces go to `findings/chip-<part>.md` with page references, and the delivery implement writes the header files from that md per `engineering-research/references/headers.md`. No agent downstream opens the PDF.

## Consequences

Every research call has the same done criterion, so callers and downstream agents learn one entry shape. Header mechanics stay in `engineering-research/references/headers.md` but their reader is the delivery implement. A fresh clone lacks `resources/`; the manifest is enough to rebuild it. The container folder, not the repo, becomes the unit that owns raw materials.

## Alternatives rejected

Keeping two functions split by output type was rejected because multi-face requirements could not be synthesized. Storing raw files in the repo (directly or through git LFS) was rejected because every worktree would copy large files and redistribution-restricted datasheets would enter git history. One shared research directory for all topics was rejected because conclusions would overwrite each other; a per-topic directory plus an index keeps history and a single entry point.
