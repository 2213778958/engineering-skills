# Worktree

The **planning implement** employee attaches ticket branches as **git worktrees** under the Canvas container `worktree/` before handoff. Planning **manage** must not run `git worktree`. The other department `cd`s that tree. Implement / review / verify see the path in the Task prompt. Details live only here. Chain/stop points follow `supervise.md` "When to stop"; do not write a second copy here. Canvas hang shape: `engineering-init` canvas.md. Duties: templates.md **duty table**.

## Rules

1. Only `git worktree add` / `remove` / `prune`. Do not POST sessions `worktree: true`. Do not put a tree path in Canvas `workspace.working_dir`.
2. Trees live in the imported container's `worktree/` (sibling of `master/` or `root/`). Do not create them inside the git checkout. Do not create sibling `*-wt-*` next to a bare git root.
3. One **other** department window follows one tree `issue:` at a time. Planning department main `issue:` is `none`. Parallel leaves = another handoff (another advance on the planning department). Do not hand off two implement tickets in one planning turn.
4. **Implement tickets and acceptance tickets (heads≥2)** must have a tree. Gates / sinks do not get a tree.
5. **Acceptance with exactly 1 head** → open the PR from that existing `feat/`/`fix/` implement tree; do not create a `merge/<n>` tree.
6. Leave-one-out isolation uses one-shot isolation trees; delete immediately after the test; do not keep them until close.
7. Employee prompt uses that tree's absolute path; first line `cd`. Ticket `git` for this hop also runs in that tree. `planning` implement creates the tree; `delivery` manage pushes from it; `acceptance` implement merges heads and removes trees.
8. `PROCESS.md`: main checkout keeps `mode` / `contract` / `verify` / `accept` / `merge`. The ticket tree keeps the same latch plus this ticket's `template` / `issue`. When creating a tree, **copy latch fields** from main checkout; do not re-ask `mode`. Do not `git add` `PROCESS.md` / `HANDOFF.md`. `MODELS.md` follows the default branch; do not invent a copy on the tree.
9. **Drift audit before activating an existing tree.** Before handoff to a department on an EXISTING tree, `planning` implement runs the drift audit at handoff prep and includes it in the receipt: `git rev-list --count` both directions (branch vs `origin/<default>`) + `git cherry` to count true-unique commits. behind <= 5 → cheap fast-forward refresh (preserve the disk-only `PROCESS.md`). behind > 5 AND true-unique commits exist → do NOT bulk-merge: recreate the tree from `origin/<default>` and cherry-pick the carried commits one by one, resolving each as its own reviewable commit; carried arbitration receipts attach to the cherry-picked SHAs. behind > 5 AND no true-unique content → recreate the tree fresh; nothing to preserve. This policy does NOT override a standing arbitration preservation verdict by itself: where a verdict mandates preserving specific carried work, cherry-pick satisfies preservation; outright discard only applies when there is nothing unique to preserve.


## Key points

| Name | How to recognize | When it exists |
|---|---|---|
| **imported** | parent of main checkout; Canvas `working_dir` | always; sessions POST this |
| **main checkout** | `git worktree list` entry whose `.git` is a **directory** (not a `.git` file); folder name `master` or `root` | landing repo; always kept |
| **implement tree** | `<imported>/worktree/<n>-<slug>`, branch `feat/<n>-<slug>` or `fix/<n>-<slug>` | when planning hands off an implement ticket; remove after that branch merges to default |
| **acceptance tree** | `<imported>/worktree/pr-<n>`, branch `merge/<n>` | when planning hands off an acceptance ticket and heads≥2; remove after that acceptance merges to default |
| **isolation tree** | `<imported>/worktree/iso-<acceptance-n>-<tag>` | during leave-one-out; delete after the test |

`slug`: ticket title lowercased, keep `a-z0-9`, spaces to `-`, collapse `--`, max 30. Empty → `m`.

Default branch: `master` if the repo already uses it, else `main`. Start point: `origin/<default>` (else local default). Folder `master/` is not that branch name.

**Do not:** `--force` remove the main checkout; remove an implement tree not yet merged to default; treat an isolation tree as an implement tree.

## Steps: paths

Read and run `engineering-init` canvas.md **Detect**. Use those three paths. Do not set `imported = dirname(git rev-parse --show-toplevel)` from the Canvas cwd.

Not wrapped (Detect fails) → **stop**. Report wrap paths from init canvas.md. Do not add a sibling `*-wt-*`. Do not change Canvas `working_dir`. Do not glob for latch files.

Wrapped and `worktree/` missing → mkdir it. Do not git add it (it is outside the checkout).

`git worktree add` fails (nested, etc.) → stop; report the command and path. Do not change Canvas `working_dir`.

Every supervise start: print `imported`, `master`/`root`, `worktree`.

## Steps: create (`planning` implement, after pick-ticket, before handoff)

1. Already on the tree for the target branch → use it; do not add again.
2. Implement ticket: `git fetch` → `git worktree add -B feat/<n>-<slug> <implement-tree> origin/<default>` (bug tickets use `fix/`).
3. Acceptance heads≥2: `git worktree add -B merge/<n> <acceptance-tree> origin/<default>`.
4. Acceptance heads=1: `cd` to that head's implement tree. Missing → create it per step 2.
5. Gate / sink: no tree. `cd` main checkout.
6. Write main-checkout `PROCESS.md` latch fields into this tree's `docs/agents/PROCESS.md`; fill `issue:` / `template:` (department hop). Do not `git add` this file.
7. Tree missing `AGENTS.md` / `CONTEXT.md` / `docs/agents/MODELS.md` → copy them from main checkout (the implement **employee** may commit those; still do not commit `PROCESS.md`).

## Steps: remove (`acceptance` implement)

Isolation trees: `git worktree remove <isolation-tree>` after each leave-one-out tree is tested; then `git worktree prune`.

Implement / acceptance trees: only after **that acceptance closed per hops.md 3e** (`check_acceptance.py post` passed, or the squash confirmation):

1. cwd is the tree to delete → `cd` main checkout first.
2. Each merged `feat/`/`fix/` in heads → `git worktree remove <implement-tree>` (skip if missing).
3. If an acceptance tree was created → `git worktree remove <acceptance-tree>` (skip if missing).
4. `git worktree prune`.
