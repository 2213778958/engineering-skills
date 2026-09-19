---
name: engineering-init
description: >-
  Plans engineering contracts on GitHub: conventions, contains/uses graphs,
  and a ticket DAG (default one-source one-sink). Migrates an existing
  project by scanning it read-only and writing the spec onto a sibling
  mirror repo.
  Use when the user asks to 初始化工程, 规范化工程, 规划, 工程规范,
  架构图, 嵌套, uses, grill, to-spec, to-tickets, 迁移已有工程, 画依赖图,
  补票, 改合同, or patch. Do not use to 推进, 领票, clone mirror, or 实现.
---

# Engineering init

| Call | When | Done |
|---|---|---|
| **plan** | New-repo planning / init | Conventions decided and injected; three graphs on spec; tickets labeled (default 1 source 1 sink); `PROCESS.md` has `mode` and `contract: ready`; `MODELS.md` reported; Canvas folder is the `master/`+`worktree/` container |
| **migrate** | Attach an existing project to the contract | Origin repo not written; planning on the landing-repo GitHub; default as-is only; normalize only then to-be, ticket net, convention files, plus `mode` / `contract: ready` / `MODELS.md` reported; landing is container `master/` |
| **patch** | After init, change ticket contract / add test commands | Tickets and spec aligned to existing contains; spec `engineering:graph` matches the ticket net when edges changed; `mode` / `contract` unchanged |
| **graph** | Refresh the flow graph only | `render_graph.py` ran on the landing-repo spec |

## Rules

- Do not implement, do not call Task, do not `git clone`, do not 分发 departments, do not staff employees, do not open PRs. Injecting `AGENTS.md` / `CONTEXT.md` / ADRs / formatters is not implementation. Plan close-out may run sessions **list** to fill `MODELS.md`; do not POST a conversation.
- `gh` / `git commit` only on the **landing repo**, never the origin repo.
- Do not write process / planning / department / current ticket into `AGENTS.md`. Coding conventions, glossary, ADRs: [repo-docs.md](references/repo-docs.md). Existing files → follow the repo; do not overwrite.
- Unconfirmed decisions → `grilling`. Unconfirmed → no issues, no graphs, no code.
- Windows: `Path.write_text(..., encoding="utf-8")` → `gh … --body-file`. CJK only in files. Do not print tokens.
- Spec markers: `engineering:contains` `engineering:uses` `engineering:graph` (working / to-be). As-is: `engineering:contains-asis` `engineering:uses-asis` `engineering:graph-asis`. Seeing `github-engineering:*` → replace with the new markers.

## Key points

- Conventions: [references/conventions.md](references/conventions.md)
- Inject into repo: [references/repo-docs.md](references/repo-docs.md)
- C/C++ layers (DIP + injection): [references/firmware-layers.md](references/firmware-layers.md)
- Two architecture graphs: [references/architecture.md](references/architecture.md)
- Flow tickets: [references/contract.md](references/contract.md)
- Flow-graph script: [references/graph.md](references/graph.md)
- Migrate delta: [references/migrate.md](references/migrate.md)
- Latch file: [references/process-stub.md](references/process-stub.md)
- Model presets: [references/models-stub.md](references/models-stub.md)
- Canvas hang: [references/canvas.md](references/canvas.md). One imported folder with `master/` (landing) and `worktree/` (ticket trees). Do not ask how to open. Init does not POST, does not move the repo. Latch files go in the checkout, not `<imported>/docs/agents/`.
- Ask `mode` once; write `docs/agents/PROCESS.md`. Legal `mode` already set → do not ask, do not overwrite. Later runs follow the file; change only when the user explicitly asks.
- Write the model table to `docs/agents/MODELS.md` per models-stub. Planning department row is **manage** `stay` = this conversation's model (ACP bridge allowed). Other department rows `dispatch`. Employee rows `delegate` including `planning implement` and `acceptance implement`. Do not rewrite delegate to dispatch. At plan close-out, print the table; change a row only if the user asks. Duties: process templates.md **职责表**.
- If missing, inject `AGENTS.md` / `CONTEXT.md` / `docs/adr/` / formatters using the [repo-docs.md](references/repo-docs.md) skeleton. Do not invent heading order. Existing files follow the repo. Do not put process in `AGENTS.md`.
- After init, change the contract via [references/patch.md](references/patch.md)
- `contract: ready` is written by **plan** / **normalize migrate**. Process seeing `ready` plus a new need → **patch**, not a full plan.
- Human review fail: the **human** department reopens the previous implement ticket and sends it back to `ready-for-agent`. Do not turn a gate ticket into `ready-for-agent`. Do not do this in patch.

## Steps: plan

This repo must already have a GitHub remote.

1. **Conventions.** Repo already has `docs/agents/`, `AGENTS.md`, `CONTEXT.md`, `docs/adr/`, formatters → follow the repo. Else use [references/conventions.md](references/conventions.md) as defaults; inject at close-out per [repo-docs.md](references/repo-docs.md). C/C++: grill no-layer / simple-layers / high-abstraction per [firmware-layers.md](references/firmware-layers.md) and confirm layer directory names (if none given, use the examples). Other languages: grill cross-layer rules if unconfirmed. Directories follow contains: invent no layers if the tree has none. Grill tests: host light command → `verify:`; full + hooks / on-target scripts → `accept:`. Unconfirmed → `none`. Adding host tests later → **patch** those two fields.
2. **Scope.** Acceptance + sink title (user names it; not `Finish` / `master`). Default 1 source 1 sink; multiple only if the user says so.
3. **Module list.** Same names as the three graph nodes later.
4. **contains tree.** Write spec per [references/architecture.md](references/architecture.md).
5. **uses DAG.** Draw only after exposure rules are confirmed. Cycle → stop, return to 3–4, do not open tickets.
6. **to-spec.** User Stories only in spec prose. Write contains / uses mermaid under the markers. Each block has a graph title (architecture.md).
7. **labels.** If missing, create the seven labels in [references/contract.md](references/contract.md) with `gh label create --force`.
8. **to-tickets.** Edges only official `blocked-by`. One implement ticket per contains node. Parallel only when uses has no edge and paths do not overlap. Do not open a separate datasheet ticket. Implement tickets: `ready-for-agent` (body must not contain `engineering:pr`). Hard-to-see gates: extra `ready-for-human`, `blocked-by` that implement ticket. Acceptance/PR tickets exist from the start: `ready-for-agent`, body `engineering:pr` + `engineering:heads` (direct children ≤4, default 4); no visual gate → acceptance `blocked-by` the implement ticket; with a gate → `blocked-by` the gate. More than 4 to merge → split a mid acceptance; parent heads write `merge/<child-acceptance>`. Do not put a human on every acceptance; a single-line phenomenon hangs on the gate after implement; merge phenomenon hangs only on the final sink (open only if someone must look). Source ticket body `engineering:source`; parallel leaves default `blocked-by` the same source (multi-source: user names them); plan close-out default **close the source ticket**; if the user must confirm start, leave source `ready-for-human` and do not close. Default 1 source 1 sink. No `triage`, no implement, no PR, **do not 分发** `ready-for-human` here (gate tickets are created; this step does not staff departments).
9. **Flow graph.** `python <this-skill>/scripts/render_graph.py --issue <spec> --write`. Multi source/sink allowed by default. Check 1-source-1-sink only with `--strict-one-one` (exit 2 → fix edges and rerun). A second flow graph needs `--force`.
10. **PROCESS.md.** Write `docs/agents/PROCESS.md` per [process-stub.md](references/process-stub.md). Existing `manual`/`auto` → do not ask. Else ask once semi-auto or full-auto; write `mode:`. Write `contract: ready`. `verify:` / `accept:` from step 1. Leave `template:` empty. `merge: human`. `until: none`. Do not put these fields in `AGENTS.md`. **Do not git add this file.**
11. **Repo conventions.** Inject per [repo-docs.md](references/repo-docs.md) **sequence** (no commit in this step). Do not change skeleton heading order. Do not overwrite existing files. No terms → no empty `CONTEXT.md`. No qualifying decision → no empty `docs/adr/`.
12. **MODELS.md.** Fill `docs/agents/MODELS.md` per [models-stub.md](references/models-stub.md). Read the routing table + this harness's sessions **list**. Print the table; ask if the user wants changes.
13. **Commit.** Per repo-docs "Steps: commit": one commit of convention files + `MODELS.md` and push the default branch. Do not put `PROCESS.md` in git.
14. **Report.** Spec URL, sink title, where the three graphs live, source/sink counts, `mode`, `contract`, model table, which convention files were injected, origin pushed. Canvas hang per [canvas.md](references/canvas.md): print imported / `master/` / `worktree/`, or the wrap paths. Not wrapped → **stop**; do not say to advance. Wrapped → next sentence may say to advance.

## Steps: patch

Already initialized. Steps in [references/patch.md](references/patch.md). `contract` is not `ready` → stop, go to plan.

## Steps: migrate

Existing project. Steps in [references/migrate.md](references/migrate.md). Origin repo read-only. Default not normalized: as-is graphs only.

## Steps: graph

Refresh the **flow** graph only (`engineering:graph`). Do not change contains / uses. Do not grill. Run in the **landing repo**.

```
python <this-skill>/scripts/render_graph.py --issue <spec>
python <this-skill>/scripts/render_graph.py --issue <spec> --write
python <this-skill>/scripts/render_graph.py --issue <spec> --write --force
```
