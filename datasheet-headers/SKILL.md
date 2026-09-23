---
name: datasheet-headers
description: >-
  Delegates a reader subagent to mine datasheet PDFs into hardware header
  files. Use when the user asks to 数据手册, 寄存器, 技术文档 PDF, regs.h, cfg.h,
  address.h, config.h, or to extract hardware interfaces from a datasheet.
---

# Datasheet headers

| Mode | When | Done |
|---|---|---|
| **extract** | Need registers / interfaces from a PDF | Headers written; reader subagent finished; this conversation only checked `.h` files; PDF was not opened here |

Do not write drivers, do not open issues, do not paste PDF body into this conversation. Do not open a child conversation. Call only from the **delivery department**. This is an **employee** (Task), not a department.

Delegate: read and run `engineering-routing` (role `datasheet extract`). Check `../engineering-routing/references/routing-table.md` first: only an `enabled` row is routable; a `registered` row is not routable, stop at the gate (enablement is a patch ticket). Repo `MODELS.md` target wins if present; ignore a `dispatch` link. Do not read `openhands-sessions`, do not copy POST, do not call Task directly.

Missing `<module>` or PDF path → `grilling` (decision) + find `.pdf` files in the repo. Do not ask the user to list registers.

[references/headers.md](references/headers.md)

## extract

1. Fix `<module>` and absolute PDF paths (may be several). Resolve output paths with [references/headers.md](references/headers.md).
2. Read and run `engineering-routing`. Prompt contains only: goal, PDF paths, output paths, header constraints, done criteria. Do not paste PDF body.
3. Wait until the subagent ends and the receipt is in this conversation. Background Task → **fail**. No `spawn.py`.
4. This conversation only reads the generated `.h` files (names, include guards, page comments). Opening the PDF or pasting datasheet paragraphs into a later implement prompt → fail, then run extract again.
5. Report: header paths + subagent name.
