---
name: engineering-research
description: >-
  Runs a research employee that answers one technical question and delivers one
  research document. The repo's own library comes first (docs/, docs/adr/,
  AGENTS.md, CONTEXT.md, the module tree); the internet is only the fallback.
  Datasheet extraction — mining a datasheet PDF into hardware header files
  (regs.h, cfg.h, address.h, config.h) — is one function of this employee.
  Use when the user asks to 调研, 技术选型,
  资料, 数据手册, 寄存器, 技术文档 PDF, regs.h, cfg.h, address.h, config.h, or to
  extract hardware interfaces from a datasheet.
---

# Engineering research

One **research** employee: it answers one technical question or delivers one research document. Internally it splits by function; datasheet extraction (a datasheet PDF mined into hardware header files) is one function among several:

- **question research** — repo facts, technical options, or a topic. Done: one research document written into the repo; source list shows repo hits and, only for the gaps, web sources.
- **datasheet extraction** — registers / interfaces from a datasheet PDF. Done: Headers written; reader subagent finished; this conversation only checked `.h` files; PDF was not opened here.

This is an **employee** (Task), not a department. Do not write drivers, do not open issues, do not paste PDF body into this conversation. Do not open a child conversation. Any department's **manage** may staff this role; the default home is the **delivery** implement ticket.

Delegate: read and run `engineering-routing` (role `research`). Repo `MODELS.md` target wins if present; ignore a `dispatch` link. Do not read `openhands-sessions`, do not copy POST, do not call Task directly.

Question research missing the question, or datasheet extraction missing `<module>` / PDF path → `grilling` (decision); datasheet extraction also finds `.pdf` files in the repo. Do not ask the user to list registers.

Source order — the same for every function, repo first:

1. This repo's library: `docs/`, `docs/adr/`, `AGENTS.md`, `CONTEXT.md`, then the module tree (code, comments, existing conventions). A repo hit answers before the internet is opened.
2. The internet: only the parts the repo library does not answer. Name each source.

[references/headers.md](references/headers.md)

## Function: question research

1. Fix the question, the scope, and the deliverable path. Deliverable: one research document (repo library hits first, then web sources, each named; conclusion + what was not found).
2. Read and run `engineering-routing`. Prompt contains only: question, scope, deliverable path, done criteria. Do not paste long source text into the prompt.
3. Wait until the subagent ends and the receipt is in this conversation. Background Task → **fail**. No `spawn.py`.
4. Check the document answers the question from named sources; repo-library-first is visible in the source list. Web-only answers with a repo hit available → fail, then run research again.
5. Report: document path + subagent name.

## Function: datasheet extraction

1. Fix `<module>` and absolute PDF paths (may be several). Resolve output paths with [references/headers.md](references/headers.md).
2. Read and run `engineering-routing`. Prompt contains only: goal, PDF paths, output paths, header constraints, done criteria. Do not paste PDF body.
3. Wait until the subagent ends and the receipt is in this conversation. Background Task → **fail**. No `spawn.py`.
4. This conversation only reads the generated `.h` files (names, include guards, page comments). Opening the PDF or pasting datasheet paragraphs into a later implement prompt → fail, then run datasheet extraction again.
5. Report: header paths + subagent name.
