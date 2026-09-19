---
name: engineering-routing
description: >-
  Routes a task to current session, a child conversation, or a subagent by
  task type, then runs openhands-sessions. Use when the user asks to
  按任务类型分发, 子智能体, session 还是 subagent, 派谁干, 选模型干活,
  or when another engineering skill needs to spawn work.
---

# Engineering routing

Pick link and target first, then read and run this harness's `*-sessions` (default `openhands-sessions`; use `codex-sessions` only if this session is Codex and that skill exists). Do not copy POST. Do not write `dispatch_session.py`. Do not call Task directly. Do not change the engineering contract (that is `engineering-init`).

| Mode | When | Done |
|---|---|---|
| **route** | Dispatch work / pick who by type | stay / dispatch / delegate chosen and sessions run; delegate receipt in this conversation |

Planning is a **department** (user entry). The department window is **manage**. Other departments this process 分发: delivery / acceptance / arbitration / human. Planning and human **manage** talk to the user. Human: how to test and accept, and help. **Employee** = implement / review / verify / extract (Task). Duties: `engineering-process` templates.md **职责表**. Do not skip department → employee.

- Planning **manage** **决策** → **stay** (staff `planning implement` + `planning review`; do not run patch here).
- Planning **manage** **分发** another department → **dispatch**.
- Department manage staffing an employee → **delegate**.
- User said "子会话" / 开会话 → **dispatch** another **planning** department window.
- User said "subagent / 子代理 / 子智能体" → **delegate**.
- Do not 分发 an employee. Do not Task a department. Do not rewrite employee delegate to dispatch.

User named a profile or model → follow the user for the **target**, then resolve via sessions. If the user did not name a target: repo `docs/agents/MODELS.md` has a row for this **role** → use that row's **target**. Planning department row: `stay`. Other department rows: `dispatch`. Employee rows: ignore a `dispatch` link; still **delegate**. Else use the table below. Only targets that appear in sessions **list** / subagent catalog. Missing row → read and run `grilling`. Do not pick `gpt-6-astra-*`.

## Table

| Task type | Link | Target |
|---|---|---|
| Extract registers from a PDF / datasheet; keep the body out of this session | delegate | subagent `general-purpose` |
| Mechanical edits: rename / format / small patch | delegate | subagent `general-purpose` |
| Read-only search / locate files and symbols | delegate | subagent `code-explorer` (`inherit`) |
| Search / fetch web sources | delegate | subagent `web-researcher` |
| General subtask that must run commands | delegate | subagent `general-purpose` |
| Architecture / hard problem / deep debug | delegate | subagent `general-purpose` |
| Long-running implementation that writes files | delegate | subagent `general-purpose` |
| Medium-complexity implementation | delegate | subagent `general-purpose` |
| Several parallel employees | delegate | subagent `general-purpose` ×N (concurrency ≤ 3) |
| Planning manage 决策 (staff only; no patch in this window) | stay | this conversation's model |
| Planning implement (patch; no product code) | delegate | subagent `general-purpose` |
| Planning department 分发 another department | dispatch | MODELS other-department row, else this conversation's spawnable profile |
| Other department manage hop already in this child window | stay | this conversation's model |
| Acceptance implement (merge heads / worktrees) | delegate | subagent `general-purpose` |

**ACP is the Cursor bridge, not a role.** A department may sit on that bridge (e.g. grok via ACP). Employees are Task subagents, not conversation windows. Do not call a department "ACP".

**Forced:**

- Planning **manage** 决策 = `stay`. Do not run patch in this conversation. Other department manage hop already spawned = `stay`. Do not fail because the bridge is ACP.
- Employee roles = **delegate**. MODELS `dispatch` on those rows → ignore; still delegate.
- `delegate` stays `delegate`. No Task on this bridge → **fail**. Do not spawn a child conversation instead. Wait until the receipt is in this conversation. Background Task → **fail**. Receipt missing → **fail**.
- 分发 another department = `dispatch` via sessions `scripts/spawn.py` (planning department 分发, or user 开会话). Hand-written `POST /api/conversations`, `curl`, or a local `dispatch_session.py` → **fail**.
- Do not POST `code-explorer` / `web-researcher` / `general-purpose` as `agent_profile`.
- `inherit` = this conversation's model

## route

1. Classify the task type (process: planning department 决策 / 分发 another department / other department hop / employee role from `MODELS.md`). Unsure → read and run `grilling` (decision) or scan the repo (fact).
2. **stay** → finish in this conversation. No POST, no Task. ACP bridge is allowed.
3. **dispatch** → planning **manage** 分发 **another** department, or user 开会话 (another **planning** department window). sessions `spawn.py` only. Omit `--this-id`. Do not pass `CURSOR_CONVERSATION_ID`. Process 分发 prompt: this child is that department **manage**; staff employees per 职责表; wait until each receipt is in that window; then sessions **notify**; stop. User 开会话 prompt: this child is the **planning** manage window.
4. **delegate** → sessions **delegate** only (Task). Same prompt rules. Wait until the receipt is in this conversation. Background Task / fire-and-forget → **fail**. Receipt missing → **fail**. No Task → fail; do not dispatch.
5. Report: link, target, subagent receipt or (dispatch only) sessions id/URL.
