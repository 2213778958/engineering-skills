---
name: engineering-routing
description: >-
  Routes a task to current session, a child conversation, or a subagent by
  task type, then runs engineering-sessions. Use when the user asks to
  按任务类型分发, 子智能体, session 还是 subagent, 派谁干, 选模型干活,
  or when another engineering skill needs to spawn work.
---

# Engineering routing

Pick link and target first, then read and run `engineering-sessions` (it reads the `sessions:` latch and runs that adapter; default `openhands-sessions`). Do not copy POST. Do not write `dispatch_session.py`. Do not call Task directly. Do not change the engineering contract (that is `engineering-init`).

| Mode | When | Done |
|---|---|---|
| **research** | Need a requirement researched — prior approaches, assets, technical options, repo facts, or chip interfaces from a datasheet PDF — keeping sources and PDF body out of this session | `engineering-research` delegated; its research directory entry md and receipt in this conversation |
| **route** | Dispatch work / pick who by type | stay / dispatch / delegate chosen and sessions run; delegate receipt in this conversation |

Planning is a **department** (user entry). The department window is **manage**. Other departments this process hands off to: delivery / acceptance / arbitration / human. Planning and human **manage** talk to the user. Human: how to test and accept, and help. **Employee** = implement / review / verify / research (Task). Duties: `engineering-process` templates.md **duty table**. Do not skip department → employee.

- Planning **manage** **decide** → **stay** (staff `planning implement` + `planning review`, and `research` when planning needs research input; do not run patch here).
- Planning **manage** **hands off** to another department → **dispatch**.
- Department manage staffing an employee → **delegate**.
- The user asks for a separate conversation window (e.g. "子会话", "开会话", "new session") → **dispatch** another **planning** department window.
- The user asks for a subagent to do a task inside this conversation (e.g. "subagent", "子代理", "子智能体") → **delegate**.
- Judge these by intent, not wording. Unclear → the unconfirmed-decision row (planning / human manage ask; other callers report `Missing: decision`).
- Do not hand off an employee. Do not Task a department. Do not rewrite employee delegate to dispatch.

User named a profile or model → follow the user for the **target**, then resolve via sessions. If the user did not name a target: repo `docs/agents/MODELS.md` has a row for this **role** → use that row's **target**. Planning department row: `stay`. Other department rows: `dispatch`. Employee rows: ignore a `dispatch` link; still **delegate**. Else use the dispatch table below. Only targets that appear in sessions **list** / subagent catalog. Missing row → the dispatch table's unconfirmed-decision row. Do not pick `gpt-6-astra-*`.

The dispatch table (task type → link) is not the routing table: the routing table `references/routing-table.md` lists which skills are routable.

## Terms

| 中文 | English |
|---|---|
| 分发 | hand off |
| 决策 | decide |
| 推进 | advance |
| 职责表 | duty table |
| 回传 | report back |
| 开会话 | open a session |

## Dispatch table

| Task type | Link | Target |
|---|---|---|
| Research a requirement (approaches / assets / options / datasheet registers) into a research directory; keep the sources and body out of this session (`engineering-research`) | delegate | subagent `general-purpose` |
| Mechanical edits: rename / format / small patch | delegate | subagent `general-purpose` |
| Read-only search / locate files and symbols | delegate | subagent `code-explorer` (`inherit`) |
| Search / fetch web sources | delegate | subagent `web-researcher` |
| General subtask that must run commands | delegate | subagent `general-purpose` |
| Architecture / hard problem / deep debug | delegate | subagent `general-purpose` |
| Long-running implementation that writes files | delegate | subagent `general-purpose` |
| Medium-complexity implementation | delegate | subagent `general-purpose` |
| Several parallel employees | delegate | subagent `general-purpose` ×N (concurrency ≤ 3) |
| Unconfirmed decision (a caller read and ran routing for the decision) | stay | this conversation's model; planning / human manage: run `grilling` until the user confirms; any other caller: stop, report `Missing: decision` upward |
| Planning manage decide (staff only; no patch in this window) | stay | this conversation's model |
| Planning implement (patch; no product code) | delegate | subagent `general-purpose` |
| Planning department hands off to another department | dispatch | MODELS other-department row, else this conversation's spawnable profile |
| Other department manage hop already in this child window | stay | this conversation's model |
| Acceptance implement (merge heads / worktrees) | delegate | subagent `general-purpose` |

**ACP is the Cursor bridge, not a role.** A department may sit on that bridge (e.g. grok via ACP). Employees are Task subagents, not conversation windows. Do not call a department "ACP".

**Forced:**

- Planning **manage** decide = `stay`. Do not run patch in this conversation. Other department manage hop already spawned = `stay`. Do not fail because the bridge is ACP.
- Employee roles = **delegate**. MODELS `dispatch` on those rows → ignore; still delegate.
- `delegate` stays `delegate`. No Task on this bridge → **fail**. Do not spawn a child conversation instead. Wait until the receipt is in this conversation. Background Task → **fail**. Receipt missing → **fail**.
- Hand off to another department = `dispatch` via sessions `scripts/spawn.py` (planning department hands off, or user opens a session). Hand-written `POST /api/conversations`, `curl`, or a local `dispatch_session.py` → **fail**.
- Do not POST `code-explorer` / `web-researcher` / `general-purpose` as `agent_profile`.
- `inherit` = this conversation's model
- Unconfirmed decision = `stay`; never delegate or dispatch it. Only a manage that may talk to the user (planning, human) asks.

## route

1. Classify the task type (process: research / planning department decide / hand off to another department / other department hop / employee role from `MODELS.md`). Unsure → the unconfirmed-decision row (decision) or scan the repo (fact).
2. **stay** → finish in this conversation. No POST, no Task. ACP bridge is allowed.
3. **dispatch** → planning **manage** hands off to **another** department, or user opens a session (another **planning** department window). sessions `spawn.py` only. Omit `--this-id`. Do not pass `CURSOR_CONVERSATION_ID`. Process handoff prompt: this child is that department **manage**; staff employees per duty table; wait until each receipt is in that window; then sessions **notify**; stop. User open-a-session prompt: this child is the **planning** manage window.
4. **delegate** → sessions **delegate** only (Task). Same prompt rules. Wait until the receipt is in this conversation. Background Task / fire-and-forget → **fail**. Receipt missing → **fail**. No Task → fail; do not dispatch.
5. Report: link, target, subagent receipt or (dispatch only) sessions id/URL.
