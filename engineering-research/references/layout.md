# Research layout

## Research directory (in git)

```text
docs/research/
  README.md                  # index: one row per research — date, topic, entry link
  resources.md               # resource manifest (see below)
  <YYYY-MM>-<slug>/
    README.md                # entry: requirement, conclusion, face index, conflicts, not found
    findings/
      <face>.md              # one per face: question, answer, named sources
```

- Markdown only. No PDFs, images, archives or downloaded pages under `docs/research/`.
- One directory per research topic. New directory: `<YYYY-MM>` = the current month, `<slug>` = the topic in kebab-case. Same topic again → keep the existing directory name; add a dated section to its entry md.
- Index row: `| <YYYY-MM> | <topic> | [<slug>](<slug>/README.md) |`. Create `docs/research/README.md` with a `| date | topic | entry |` header if missing.

## Resource library (outside git)

`resources/` sits beside `master/` and `worktree/`, in the container folder, never inside a git checkout. Every checkout and worktree shares it.

```text
<container>/
  master/
  worktree/
  resources/
    datasheets/
    assets/
    refs/
```

- Never `git add` a file under `resources/`. Sharing → pack it separately (archive / release asset); the manifest is the contract.
- Candidate assets stay here. An asset adopted by the product is copied into the product's own asset directory by the implement ticket.

## `resources:` paths

Markdown refers to a raw file as `resources:<path under resources/>`, e.g. `resources:datasheets/w25q128jv.pdf`. Never a filesystem-relative path.

Resolve the root, first hit wins:

1. Environment variable `ENGINEERING_RESOURCES`.
2. From the current checkout, walk up the parents; the first directory that holds both `master/` and `resources/` → its `resources/`.
3. No `resources/` yet → the first parent directory that holds `master/`: create `resources/` there.
4. No such parent (a plain clone) and no environment variable → a face that must store or read a raw file stops the whole research: `Result: fail` + `Missing: ENGINEERING_RESOURCES`.

## Manifest

`docs/research/resources.md` is committed. One row per raw file:

```markdown
| path | source URL | fetched | license | size | sha256 |
|---|---|---|---|---|---|
| resources:datasheets/w25q128jv.pdf | https://example.com/w25q128jv.pdf | 2026-09 | vendor, no redistribution | 2.1 MB | 3f5a… |
```

- Every `resources:` path used in any research md has a row.
- Only the synthesis subagent writes this file; face subagents return their rows in the receipt.
- Missing locally → fetch from the URL, check sha256; mismatch or unreachable → list under not found in the entry md.
- License unknown → write `unknown`; the synthesis step flags it.
