---
name: engineering-research
description: >-
  Researches one question and delivers one research document: repo
  sources first, then the web. Use when the user asks to 调研, 查资料,
  调研报告, research this, investigate, or compare options with
  sources. Do not use to advance tickets; that is engineering-process.
---

# Engineering research

| Mode | When | Done |
|---|---|---|
| **research** | A question needs sourced answers | One document written; every claim cites a source; repo searched before the web |

Deliver one document. Do not implement tickets (that is `engineering-process`), do not write product code, do not open PRs, do not register or enable skills (that is a patch ticket via `engineering-routing`).

Missing question or output path → read and run `grilling` (decision).

Search with the tools this session already has (file search, fetch, browser). Do not wire MCP servers or new services. Who should do the reading (stay / delegate) → read and run `engineering-routing`.

[references/sources.md](references/sources.md)
[references/report.md](references/report.md)

## research

1. Fix the question and the output path. Path: user-named this turn → repo docs conventions → `<topic>-research.md` beside the caller's docs.
2. Repo first: repo library, `AGENTS.md`, `CONTEXT.md`, `docs/`, then code. Collect file paths + line numbers.
3. Repo exhausted → web. Primary sources (official docs, standards, changelogs) before secondary. Record URL + access date.
4. Write the document per [references/report.md](references/report.md); citations per [references/sources.md](references/sources.md). A claim with no source → delete the claim or move it to Open questions.
5. Report: document path, source counts (repo / web), open questions.
