# Canvas workspace

Hang the landing checkout and the ticket-tree parent in **one** Agent Canvas import. Do not ask how to open. Init does not POST a conversation, does not `git clone`, does not move the repo.

## Shape (locked)

```
<imported>/          ← Canvas working_dir; sessions POST this only
  master/            ← landing git checkout (`PROCESS.md`, `gh`, default branch)
  worktree/          ← empty at init; process adds ticket trees here
```

`root/` instead of `master/` is the same shape. Folder name `master` is not the git default branch.

Do not import the git root by itself. Do not import each ticket tree as its own Canvas project. Do not put `worktree/` inside the git checkout.

## Detect

Canvas `working_dir` / this cwd is usually **imported**, not the landing checkout. Do not use container `git rev-parse` as the landing repo. Do not glob for `PROCESS.md`.

A hit = a folder `master` or `root` whose `.git` is a **directory** (not a `.git` file). Look in this order, stop at the first hit:

1. this cwd
2. parent of cwd
3. parent of parent of cwd

Then: imported = that folder; checkout = `imported/master` or `imported/root`; trees = `imported/worktree`. Missing `worktree/` → mkdir. Process: sessions `spawn.py --mode this` **before** `cd` checkout. The script also matches cwd at `master/` / `root/` / `worktree/<tree>`. Then `cd` checkout for `PROCESS.md` / `gh` / landing `git`.

No hit → not wrapped. Do not treat imported itself as the landing repo even if it has a `.git`.

## Close-out

Already wrapped → create empty `worktree/` if missing; print the three paths; continue.

Not wrapped → **stop**. Do not POST. Print (user-named container path wins; else default):

```
Canvas import: <dirname(R)>/<basename(R)>-canvas
  master:   <that>/master     ← move R here
  worktree: <that>/worktree   ← mkdir
Import <that> in Agent Canvas. Reopen the **planning department** there. Rerun this close-out.
```

User already named an import path → use it as `<that>`. Do not offer a second shape.
