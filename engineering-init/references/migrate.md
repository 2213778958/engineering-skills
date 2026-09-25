# Migrate

Attach an existing project to the contract. Conventions, contains, uses, ticket rules still live in the other three references. This file is only the delta vs **plan**.

## Rules

- No implement, no clone, no hand off, no Task, no PR.
- Origin repo: no `git commit`, no `gh`, no labels. Writes only on the landing-repo GitHub.
- Do not write process into `AGENTS.md`. Normalize landing repo: inject convention files per [repo-docs.md](repo-docs.md); existing files follow the repo. Not-normalized: do not inject to-be conventions.
- Do not rename vendor/generated symbols or Components device names to `Layer_Module_Action`
- No `triage`. Do not hand off onto `ready-for-human` (normalize still creates gate tickets).
- This skill does not `git clone` or create a GitHub repo.

## Key points

- Default **not normalized**: as-is graphs only; no tickets; do not ask semi/full auto.
- **Normalize** only then writes to-be graphs and the ticket net, asks `mode` once, writes `contract: ready`.
- Default landing path: sibling container `<origin-dirname>-mirror-canvas/` with `master/` (landing git) and `worktree/` (empty). `master/` must have **its own** GitHub remote (`nameWithOwner` ≠ origin).
- clone / `gh repo create` / wrapping into that container is the user or `engineering-automation`. If not built yet, tell the user to finish that, then rerun migrate writes. Canvas hang: [canvas.md](canvas.md).

## Steps

1. **Fix the origin project.** Absolute path. Scan only: dirs, includes/links, `docs/agents/`, `AGENTS.md`, `CONTEXT.md`, formatters, components (`HAL_*` `MX_*` vendor trees, generated areas).
2. **Normalize?** Unconfirmed → read and run `engineering-routing` for the decision. Unconfirmed → **not normalized**.
3. **Landing.** Path or remote unconfirmed → grill. Landing = container `master/` (canvas.md). Landing dir missing, not wrapped, or remote still the origin → **stop**. Report origin path, planned container (`master/` + `worktree/`), clone and swap origin. Do not ask a second open style.
4. **Before writes.** Current `gh` must hit the landing repo. Do not `gh issue create` inside the origin directory.
5. **Conventions (into landing spec, not origin files).** Current layout/names → record "follow origin". Gaps only cite [conventions.md](conventions.md) / [firmware-layers.md](firmware-layers.md) defaults. Vendor and Components public names stay.
6. **Module list.** Scan the origin tree. Gaps → grill. Node names = current names.
7. **Not normalized → close-out.** Landing must already exist and be wrapped (canvas.md). May create `PROCESS.md` per [process-stub.md](process-stub.md), `mode:` empty, `contract: none`. Do not ask semi/full auto. Do not open implement tickets. Do not change to-be markers. Report: landing spec URL, as-is block locations, Canvas paths.
8. **Normalize only then continue.**
   - Write to-be contains / uses as `engineering:contains` / `engineering:uses`. Keep as-is markers.
   - Normalize means changing boundaries/API/layers/headers, not only file/dir names. Do not open rename tickets for Vendor or reusable-component public names. C/C++ to-be layers follow firmware-layers confirmed template and **this repo's layer names**.
   - Scope: acceptance + sink title (user names it; not `Finish` / `master`). Default 1 source 1 sink; multiple only if the user says so.
   - to-be uses has a cycle and must be broken → break it before tickets; user wants to keep the cycle → no tickets.
   - labels + to-tickets on the landing repo. Implement tickets align to **to-be** contains nodes. Grill the source title (may say "create mirror"; clone already done → close; else close-out default close the source). Parallel leaves default `blocked-by` the same source. No separate datasheet ticket. Hard-to-see gate: extra `ready-for-human`, `blocked-by` that implement. Acceptance tickets exist from the start, body `engineering:pr` + `engineering:heads` (direct children ≤4); over that, split mid acceptance. Sink only if someone must look, `ready-for-human`, `blocked-by` the final acceptance. Default 1 source 1 sink.
   - `PROCESS.md`: existing `manual`/`auto` → do not ask. Else ask once semi-auto or full-auto; write `mode:`. Write `contract: ready`. Grill light `verify:`, full+hooks `accept:`; unconfirmed → `none`.
   - Repo conventions: inject per [repo-docs.md](repo-docs.md). Do not overwrite existing files.
   - `MODELS.md`: fill per [models-stub.md](models-stub.md). Route through the registry: `engineering-routing/references/routing-table.md` (a `registered` row is not routable), then run `engineering-sessions` **list**. Print the table; ask if the user wants changes.
9. **Report.** Origin unchanged; landing spec URL; normalized or not; as-is / to-be locations; if tickets, source/sink counts; if normalized, `mode`, `contract`, model table, which convention files were injected; Canvas paths per canvas.md. Not wrapped → stop; do not say to advance.
