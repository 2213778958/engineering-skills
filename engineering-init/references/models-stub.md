# MODELS.md

Landing repo `docs/agents/MODELS.md`. Do not write the origin repo. Do not put this table in `AGENTS.md`. After write, commit + push the default branch with the convention files. Do not put `PROCESS.md` in git.

## Rules

- Target names must resolve via this harness's `*-sessions` **list** (Cursor / OpenHands: `openhands-sessions`. Use `codex-sessions` only if this session is Codex and that skill exists). Do not copy POST. Do not invent catalog ids.
- Role → task type only from the `engineering-routing` table. Do not invent a third task-type table here.
- Write the routing **link as the table says**. Planning department row is `stay`. Other department rows are `dispatch`. Employee roles are `delegate`. Do not rewrite `delegate` to `dispatch`. Do not write `delegate` on a department row.
- Planning is a **department**. Conversation windows. Planning department `stay`. 分发 another department (`delivery` / `acceptance` / `arbitration` / `human`) `dispatch`. Target for stay = **this conversation's model** (ACP is the Cursor bridge, not the role; grok via ACP is allowed). Target for dispatch = a spawnable profile from sessions **list** (same family/effort as this conversation when possible).
- **Employee** rows: `delegate` + a subagent name (`general-purpose` / `code-explorer` / `web-researcher`). Those are not conversation windows. Department rows are the **manage** seat. MODELS must not write `dispatch` on implement / review / verify / datasheet extract. Duties: process templates.md **职责表**.
- User named a model / profile → follow the user for stay/dispatch windows only. Employee staffing still delegate.
- `confirmed: no`: written, reported, user has not said to use this table. `yes`: user said use it or leave it.
- process does not refill the whole table unless the user changes a row. Existing file has `supervisor` and no `planning` → process treats that row as planning `stay`. Missing other-department rows → process 分发 uses this conversation's spawnable profile.

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
| datasheet extract | employee | Extract registers from a PDF / datasheet; keep the body out of this session |

## Steps: fill at plan close-out

1. Read and run this harness's sessions **list** (no POST).
2. For each row: write the routing link and a resolvable target. Planning department: `stay` + this conversation's model (ACP bridge allowed). Other department rows: `dispatch` + spawnable profile. Employee rows: `delegate` + subagent name (`general-purpose` / `code-explorer` / `web-researcher`). Do not write `dispatch` on employee rows. Cannot resolve a name → `grilling` that row; do not invent a name.
3. Write this file. `confirmed: no`.
4. Print the whole table; ask if the user wants changes. User says use it / no change → `confirmed: yes`. User changes a row → write then `yes`.

## Steps: file contents

```
confirmed: no | yes
updated: <ISO-8601>

role | task type | link | target
planning | Planning manage 决策 (staff only; no patch in this window) | stay | <this conversation's model>
delivery | Planning department 分发 another department | dispatch | <spawnable profile>
acceptance | Planning department 分发 another department | dispatch | <spawnable profile>
arbitration | Planning department 分发 another department | dispatch | <spawnable profile>
human | Planning department 分发 another department | dispatch | <spawnable profile>
planning implement | Planning implement (patch; no product code) | delegate | general-purpose
planning review | Read-only search / locate files and symbols | delegate | code-explorer
delivery implement | Long-running implementation that writes files | delegate | general-purpose
delivery review | Medium-complexity implementation | delegate | general-purpose
delivery verify | General subtask that must run commands | delegate | general-purpose
acceptance implement | Acceptance implement (merge heads / worktrees) | delegate | general-purpose
acceptance review | Medium-complexity implementation | delegate | general-purpose
acceptance verify | General subtask that must run commands | delegate | general-purpose
arbitration implement | Architecture / hard problem / deep debug | delegate | general-purpose
arbitration review | Medium-complexity implementation | delegate | general-purpose
arbitration verify | General subtask that must run commands | delegate | general-purpose
datasheet extract | Extract registers from a PDF / datasheet; keep the body out of this session | delegate | general-purpose
```
