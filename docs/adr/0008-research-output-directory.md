# Research delivers one research directory; research and raw materials live outside the code repo

## Status

Accepted, 2026-09-26. Revised before the v0.1 tag by #78 (research library moved out of the code repo; staffing narrowed). Supersedes the output part of ADR 0006 (datasheet extraction writing header files).

## Context

ADR 0006 folded `datasheet-headers` into `engineering-research` with two functions split by output type: a question produced one research document, a datasheet produced `.h` files. A real requirement usually spans several faces — a game needs prior approaches and reusable assets — and the faces constrain each other (engine, art style, license). Split by output type, the caller had to run each face separately and stitch the answers; nobody cross-checked them. Downloaded datasheets and assets had no home: inside a checkout they bloat git, raise redistribution questions, and must be copied into every worktree.

The first version of this decision (#75) kept research directories in the code repo under `docs/research/`. That forced every research result onto a ticket branch: research had to commit, implement allowlists and reviews had to carve out the research commit, and planning — which has no ticket branch — could not land research at all without pushing the default branch.

## Decision

1. Research always delivers one research directory, `research:<YYYY-MM>-<slug>/`, entered through `<slug>.md`. Downstream agents enter from that md; headers, asset imports and code are their work.
2. The research library `research/` sits beside `master/` and `worktree/` in the container folder, outside the code repo. `research:Home.md` indexes every directory; research reads it first and extends an existing directory for the same topic. The library holds Markdown only, with file names unique across the library.
3. Research splits the requirement into faces, records their dependencies, researches independent faces in parallel and dependent faces with the upstream conclusion as a constraint, then synthesizes: it cross-checks licenses, formats and conflicting recommendations and writes them into the entry md. Face and synthesis work run in delegated subagents; only the synthesis subagent writes the index and the manifest.
4. The code repo never receives research files. When `research/` is a git repo — the project's GitHub Wiki, or a separate research repo for private projects — the synthesis subagent commits and pushes it; that is the only push a research employee makes. Otherwise research only writes files.
5. Raw materials live in `resources/`, also beside `master/`, outside every git repo. Sharing them means packing them separately (archive or GitHub Release asset).
6. `research:resources.md` lists every raw file with URL, fetch date, license, size and sha256. A missing file is fetched again and hash-checked; unreachable → listed as not found.
7. Markdown refers to files as `research:<path>` and `resources:<path>`. Each root resolves from `ENGINEERING_RESEARCH` / `ENGINEERING_RESOURCES`, else the first parent directory holding both `master/` and the library, else the library is created beside the first parent's `master/`. No `master/` parent and no variable → the whole research fails with `Missing: <variable>`.
8. Material not found is not a failure; the entry md lists it with where research looked. A chip-interface face with no datasheet PDF anywhere fails.
9. A datasheet is one face: the PDF goes to `resources:datasheets/`, registers and interfaces go to `<slug>--chip-<part>.md` with page references, and the delivery implement writes the header files from that md per `engineering-research/references/headers.md`. No agent downstream opens the PDF.
10. Research is staffed by the delivery (default), acceptance or planning manage; never human or arbitration.

## Consequences

Every research call has the same done criterion, so callers and downstream agents learn one entry shape. Any staffing department can research without a ticket branch, and no rule has to carve out research commits from implement allowlists or reviews. Research results are versioned and shared only when `research/` is a git repo; a plain directory is local to one machine. A fresh clone of the code repo has neither library; cloning the Wiki restores research, and the manifest rebuilds `resources/`. The container folder, not the code repo, owns research and raw materials.

## Alternatives rejected

Keeping two functions split by output type was rejected because multi-face requirements could not be synthesized. Storing raw files in the repo (directly or through git LFS) was rejected because every worktree would copy large files and redistribution-restricted datasheets would enter git history. Keeping research directories in the code repo (`docs/research/`, the #75 version) was rejected because planning could not land them and every other department needed commit carve-outs. A planning-only exception to push the default branch was rejected because it bypasses review and contradicts the repo's no-direct-push rule. One shared research file for all topics was rejected because conclusions would overwrite each other; a per-topic directory plus an index keeps history and a single entry point.
