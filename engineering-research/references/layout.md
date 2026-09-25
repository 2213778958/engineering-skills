# Research layout

Two libraries sit beside `master/` and `worktree/` in the container folder, outside the code repo. Every checkout and worktree shares them.

```text
<container>/
  master/
  worktree/
  research/                    # research library: Markdown only
    Home.md                    # index: one row per research — date, topic, entry link
    resources.md               # resource manifest (see below)
    <YYYY-MM>-<slug>/
      <slug>.md                # entry: requirement, conclusion, face index, conflicts, not found
      <slug>--<face>.md        # one per face: question, answer, named sources
  resources/                   # raw materials, never in any git repo
    datasheets/
    assets/
    refs/
```

## Research library

- Markdown only. No PDFs, images, archives or downloaded pages under `research/`.
- File names are unique across the whole library (GitHub Wiki page names are global): entry `<slug>.md`, findings `<slug>--<face>.md`. Never a bare `README.md` or `<face>.md`.
- One directory per research topic. New directory: `<YYYY-MM>` = the current month, `<slug>` = the topic in kebab-case. Same topic again → keep the existing directory and names; add a dated section to its entry md.
- Index row: `| <YYYY-MM> | <topic> | [[<slug>]] | research:<YYYY-MM>-<slug>/<slug>.md |`. `[[<slug>]]` is the Wiki page link; agents follow the `research:` path. Create `Home.md` with a `| date | topic | page | path |` header if missing.
- Markdown refers to research files as `research:<path under research/>`, e.g. `research:2026-09-pixel-roguelike/pixel-roguelike.md`.

## Sync

- `research/` is a git repo → the synthesis subagent commits there and pushes it. That push is the only push a research employee makes; it never touches the code repo.
- Collaboration: clone the project's GitHub Wiki as `research/` (`git clone https://github.com/<owner>/<repo>.wiki.git research`; the Wiki needs one page created on the web first). Private project without a Wiki plan → a separate research repo cloned as `research/`.
- `research/` is a plain directory → write files only; sharing means packing it.

## Resource library

- Never `git add` a file under `resources/`. Sharing → pack it separately (archive / GitHub Release asset); the manifest is the contract.
- Candidate assets stay here. An asset adopted by the product is copied into the product's own asset directory by the implement ticket.
- Markdown refers to a raw file as `resources:<path under resources/>`, e.g. `resources:datasheets/w25q128jv.pdf`. Never a filesystem-relative path.

## Resolving the roots

`research:` and `resources:` resolve the same way (`<lib>` = `research` / `resources`, `<VAR>` = `ENGINEERING_RESEARCH` / `ENGINEERING_RESOURCES`), first hit wins:

1. Environment variable `<VAR>`.
2. From the current checkout, walk up the parents; the first directory that holds `<lib>/` and `master/` (or `root/`) → its `<lib>/`.
3. No `<lib>/` yet → the first parent directory that holds `master/` (or `root/`): create `<lib>/` there.
4. No such parent (a plain clone) and no environment variable → the whole research stops: `Result: fail` + `Missing: <VAR>` (for `resources`, only when a face must store or read a raw file).

## Manifest

`research:resources.md`, one row per raw file:

```markdown
| path | source URL | fetched | license | size | sha256 |
|---|---|---|---|---|---|
| resources:datasheets/w25q128jv.pdf | https://example.com/w25q128jv.pdf | 2026-09 | vendor, no redistribution | 2.1 MB | 3f5a… |
```

- Every `resources:` path used in any research md has a row.
- Only the synthesis subagent writes this file; face subagents return their rows in the receipt.
- Missing locally → fetch from the URL, check sha256; mismatch or unreachable → list under not found in the entry md.
- License unknown → write `unknown`; the synthesis step flags it.
