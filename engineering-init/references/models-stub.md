# MODELS.md

Landing repo `docs/agents/MODELS.md`. Do not write the origin repo. Do not put this table in `AGENTS.md`. After write, commit + push the default branch with the convention files. Do not put `PROCESS.md` in git.

## Rules

- Target names must resolve via this harness's `*-sessions` **list** (Cursor / OpenHands: `openhands-sessions`. Use `codex-sessions` only if this session is Codex and that skill exists). Do not copy POST. Do not invent catalog ids.
- Role → task type only from the `engineering-routing` table. Do not invent a third task-type table here.
- Write the routing **link as the table says**. Planning manage cell is `stay`. Other department manage cells are `dispatch`. Employee cells are `delegate`. Do not rewrite `delegate` to `dispatch`. Do not write `delegate` on a manage cell.
- Planning is a **department**. Conversation windows. Planning department `stay`. 分发 another department (`delivery` / `acceptance` / `arbitration` / `human`) `dispatch`. Target for stay = **this conversation's model** (ACP is the Cursor bridge, not the role; grok via ACP is allowed). Target for dispatch = a spawnable profile from sessions **list** (same family/effort as this conversation when possible).
- **Employee** cells: `delegate` + a resolvable target. Those are not conversation windows. Department **manage** cells are the seat. MODELS must not write `dispatch` on implement / review / verify / research. Duties: process templates.md **职责表**.
- User named a model / profile → follow the user for stay/dispatch windows only. Employee staffing still delegate.
- `confirmed: no`: written, reported, user has not said to use this table. `yes`: user said use it or leave it.
- process does not refill the whole table unless the user changes a cell. Existing file has `supervisor` and no `planning` → process treats that as planning manage `stay`. Missing other-department manage cell → process 分发 uses this conversation's spawnable profile.

## Key points: role → routing task type

| Role | Layer | routing task type |
|---|---|---|
| planning | department (manage) | Planning manage 决策 (staff only; no patch in this window) |
| delivery | department (manage) | Planning department 分发 another department |
| acceptance | department (manage) | Planning department 分发 another department |
| arbitration | department (manage) | Planning department 分发 another department |
| human | department (manage) | Planning department 分发 another department |
| planning implement | employee | Planning implement (patch; no product code) |
| planning review | employee | Read-only search / locate files and symbols |
| delivery implement | employee | Long-running implementation that writes files |
| delivery review | employee | Medium-complexity implementation |
| delivery verify | employee | General subtask that must run commands |
| acceptance implement | employee | Acceptance implement (merge heads / worktrees) |
| acceptance review | employee | Medium-complexity implementation |
| acceptance verify | employee | General subtask that must run commands |
| arbitration implement | employee | Architecture / hard problem / deep debug |
| arbitration review | employee | Medium-complexity implementation |
| arbitration verify | employee | General subtask that must run commands |
| research | employee | Answer a technical question or write a research document, datasheet headers included; keep sources and PDF body out of this session |

## Steps: fill at plan close-out

1. Read and run this harness's sessions **list** (no POST).
2. For each cell: write a resolvable target. Planning manage: this conversation's model (ACP bridge allowed). Other manage cells: spawnable profile. Employee cells: catalog target. `—` = 职责表 no. Do not write `dispatch` on employee cells. Cannot resolve a name → `grilling` that cell; do not invent a name.
3. Write this file. `confirmed: no`.
4. Print the whole table; ask if the user wants changes. User says use it / no change → `confirmed: yes`. User changes a cell → write then `yes`.

## Steps: file contents

`MODELS.md` is one n×m grid: rows = departments, columns = `manage` / `implement` / `review` / `verify`. Same axes as the 职责表. Cell = target. `—` = 职责表 no. Research is not a department column; keep a 1×1 sidecar.

```
confirmed: no | yes
updated: <ISO-8601>

link: planning manage = stay; other manage = dispatch; implement / review / verify / research = delegate

| | manage | implement | review | verify |
|---|---|---|---|---|
| planning | <this conversation's model> | general-purpose | code-explorer | — |
| delivery | <spawnable profile> | general-purpose | general-purpose | general-purpose |
| acceptance | <spawnable profile> | general-purpose | general-purpose | general-purpose |
| arbitration | <spawnable profile> | general-purpose | general-purpose | general-purpose |
| human | <spawnable profile> | — | — | — |

| | research |
|---|---|
| research | general-purpose |
```

Role name for routing = manage cell → `<department>`; other cells → `<department> <duty>`; research sidecar → `research`.
