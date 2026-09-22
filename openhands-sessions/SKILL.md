---
name: openhands-sessions
description: >-
  List Agent Canvas agent/LLM catalogs and open or dispatch a conversation
  on a specified profile or model. Spawned sessions default to this project's
  working_dir. Use when the user asks to 看profile, 列模型, 开会话, 指定模型,
  DeepSeek/GPT/Cursor/Grok, thinking depth, or to 派发/开子会话 a child
  conversation. Do not use to 按任务类型分发; that is engineering-routing.
---

# OpenHands sessions

This skill owns catalog + spawn. Encrypted `agent_settings` / tool merge stay in `agent-canvas-environment`.

Pick one mode from the request. Do not treat every call as dispatch.

| Mode | When | Done |
|---|---|---|
| **list** | Show profiles / which can spawn | Catalog JSON printed. No POST |
| **open** | New conversation on a named profile/model | Created in the imported workspace. UI link reported. That window is the **planning** department |
| **dispatch** | Planning department 分发 **another** department, or user 开会话 | Child in the same imported workspace with `parent_conversation_id`. Process 分发 → other department. User 开会话 → another planning department |
| **notify** | Other department **manage** hop finished | Report posted to the parent planning conversation and `run`. Planning window URL printed. No parent → **fail** |
| **delegate** | **Employee** work (implement / review / verify / extract / planning review) | Task ended in this conversation; receipt returned. Background Task → **fail**. No Task → **fail**; do not spawn a child instead |

Task-type routing (who should work) is `engineering-routing`. If the user asked to pick by task type and routing did not already call this skill → read and run `engineering-routing`. If routing already called this skill, or the user named a profile/model → only the named mode.

This copy runs on the **ACP bridge**. A **department** (including planning) may be a **model** on this bridge (e.g. grok). Do not call that window "ACP". **Employees** = **delegate**. Do not rewrite `delegate` to `dispatch`. No Task here → **fail** delegate; do not spawn a child instead. Do not 分发 an employee.

## Rules

1. Live API only. Do not cache ids, profile names, or efforts across turns.
2. Never print the API key. Header `X-Session-API-Key` from `~/.openhands/agent-canvas/api-key.txt`.
3. Hosts: backend `http://localhost:8000`, UI `http://localhost:3001`.
4. Windows: PowerShell 5.1. Write `.py` files for HTTP. Do not rely on `curl.exe` flags.
5. Do not copy this POST into other skills. Do not write a local `dispatch_session.py`. Hand-written `POST` / `GET` / `python -c` against `/api/conversations` → **fail**. Callers: read and run this skill. Open, dispatch, and notify only via `scripts/spawn.py`. Child GET `id` missing or tags missing `clientsource=agentcanvas` after spawn → **fail**. GET `conversation_id` empty is not a failure (Canvas stores the uuid in `id`).
6. Do not choose a profile by task type here. That is `engineering-routing`.
7. Do not change the engineering contract (that is `engineering-init`). Do not advance tickets (that is `engineering-process`).
8. At most 3 concurrent dispatch children.

## Key points

**This conversation** = the Canvas conversation running this skill now. Identity is GET `/api/conversations/{id}` field **`id`**. `CURSOR_CONVERSATION_ID` is the ACP session id; it 404s on that GET. Do not pass it as `--this-id`. Do not grep `dev_conversations`. Do not `python -c` GET.

**Imported workspace** = absolute `workspace.working_dir` of this conversation (the folder imported into Agent Canvas). Copy it. Do not invent a checkout path.

**Git worktree path** (`master\`, `root\`, `worktree\wave-a`, …) = prompt-only (`cd` / `git worktree add`). Never put it in `workspace.working_dir`.

**POST `worktree`** = server clone switch. Default `false`. `true` only if the user asked to leave this project for a new clone (often under `conversation_worktree_root`).

Canvas sidebar groups by imported `working_dir` **and** `tags.clientsource=agentcanvas`. API POST without that tag lands under 无工作区 even when `working_dir` matches. `spawn.py` copies this conversation's tags and sets `clientsource`. Child identity is GET `id`. Do not treat empty `conversation_id` as failure.

A worktree/checkout path is a different workspace: the child lands outside this project, and `parent_conversation_id` returns 422.

If the imported workspace itself is a git working tree, git refuses nested worktrees under it. Engineering hang: import the **container** (`master\` or `root\` plus `worktree\`), not the git root and not a ticket tree.

**Agent profile** = spawnable runtime (`openhands` vs `cursor-acp`) + id. POST `agent_profile_id`. Mutually exclusive with `agent` / `agent_settings`.

**LLM profile** = `model` + `reasoning_effort` (detail endpoint; list omits effort). Same list `model` can be several efforts. Match **name / effort**, not list `model`. Grok effort is the `acp_model` suffix (`-high` / `-xhigh`).

**open** vs **dispatch:** open may be a greeting and polls only if asked. dispatch always has a task, always sets `parent_conversation_id` to this conversation (unless the user asked for an unrelated conversation). Process 分发: `--poll-sec 0`; planning **stops** (does not watch). User 开会话: poll only if asked.

## Steps: list

```
python <this-skill>/scripts/list_catalog.py
```

| Catalog key | Meaning |
|---|---|
| `spawnable_agent_profiles` | POST with `agent_profile_id` works |
| `llm_profiles_without_agent` | LLM exists; `agent_profile_id` will not hit that effort |

List stops here.

## Steps: resolve target

User-named or routing-named profile/model wins.

1. Exact `agent_profile_name`
2. Exact spawnable `llm_profile`
3. Family + effort (e.g. "deepseek max", "grok xhigh")
4. Only if they asked this skill to **choose** (and routing did not): runtime → family → effort (Cursor ACP vs OpenHands tools; DeepSeek cheap/fast vs GPT-6 heavier vs named GPT 5.6; mechanical `high`/`medium`, default `max`, hard `xhigh`)

Named an LLM in `llm_profiles_without_agent` → say so. Then either encrypted `agent_settings` + that LLM (`agent-canvas-environment`), or the nearest **higher** spawnable effort in the same family, named explicitly. Do not silently downgrade.

## Steps: open / dispatch

Write the prompt to a temp `.txt`. Then:

```
python <this-skill>/scripts/spawn.py --mode this
python <this-skill>/scripts/spawn.py --mode open --profile-id <uuid> --prompt-file <txt> --max-iterations <n>
python <this-skill>/scripts/spawn.py --mode dispatch --profile-id <uuid> --prompt-file <txt> --max-iterations <n> --poll-sec 0
```

For every open or dispatch command, set the terminal timeout to at least 200 seconds. A terminal soft timeout (`exit=-1`) is not a dispatch failure: first read the remaining output, and treat a receipt JSON containing `conversation_id` or `id` as success. If the result is uncertain, GET the child status before retrying. Re-dispatch only after confirming the original child is absent or in `error`; never retry an active or unknown child. Dispatch refuses an active same-parent, same-department child; use `--force` only when the duplicate is intentional.

A department manage window that requires GitHub also passes both:
```
--department <delivery|acceptance|arbitration|human> --github-token-secret <PROCESS.github-token-secret>
```

The adapter maps that registered source to consumer `GH_TOKEN` with an authenticated `LookupSecret`. Source `none`, unavailable source, authentication failure, or lookup/create rejection fails closed. Never alias the source variable in a prompt. The script adds a sanitized `githubbinding` tag and `github_binding` result only; it never stores the source identity or value there. Do not pass these options for employee Task/delegate work. Regular OpenHands preflight explicitly references `GH_TOKEN`; ACP receives it in subprocess env. GitHub finalization failure must still preserve completed receipts and run **notify**.
Omit `--this-id`. `spawn.py` resolves the Canvas `id` (cwd + running + `clientsource=agentcanvas`, **including** a department child with `parent_conversation_id`). cwd may be the imported container, or that container's `master/` / `root/` / `worktree/<tree>` — the script walks up to the imported `working_dir`. Env `OPENHANDS_CONVERSATION_ID` / `CONVERSATION_ID` wins. Several matches → the most recently updated. Passing `CURSOR_CONVERSATION_ID` 404s; do not grep after a 404. `--this-id` only if it is already a Canvas `id`.

`spawn.py` GETs this conversation, copies `working_dir` and tags, sets `tags.clientsource=agentcanvas`, keeps `worktree: false`. Dispatch also sets `parent_conversation_id`. Do not pass a ticket-tree path. Do not hand-write POST or GET. Script exit ≠ 0 → **stop**. Do not retry with a guessed id. Do not grep disk.

User named a subdir / ticket tree → prompt `cd` only. User asked to open in a **different imported project** → `--mode open` on a conversation whose `working_dir` is that project; no parent.

- `max_iterations`: 500 unless they named a cap or it is clearly a one-shot question (80).
- Report the JSON `url`, `working_dir`, `tags`, `id`. `clientsource` missing or `id` missing → failure. Empty `conversation_id` is OK.

Prompt is self-contained: goal, paths, constraints, done criteria, report shape. Do not paste PDF body. Process 分发: tell the child it is that department **manage**; staff employees per process templates.md **职责表**; wait until each receipt is in that window; then sessions **notify**; stop. Human child: talk to the user — how to test and accept, and help; do not notify until pass or fail. Manage must not do implement/review/verify work. Do not finish after launching Task. Do not claim to be the planning department; do not 分发 another department. User 开会话: tell the child it is the **planning** manage window (talks to the user). Do not tell an employee prompt it is a department. Department windows may read the ticket-tree `PROCESS.md`. Employee prompts must not (`planning` implement may read `PROCESS.md` for patch).

**`max_iterations` is estimated, never a fixed 100.** Hitting the cap marks `error` (`MaxIterationsReached`, not retryable) and skips later steps such as `git commit`. Count likely tool-calls (read, install, each edit, build, browser, commit), **×2 at least**, then use a floor:

| Child work | Floor |
|---|---|
| one-shot question only | 80 |
| single-file fix | 200 |
| a page / a few files + test | 400 |
| feature slice: install, multi-file, verify, commit | 500 |
| open with no task yet / unsure | 500 |

Prefer the next floor up when unsure. Large slices start at **500**. User-named cap wins. Report the number with the UI link.

Poll is `--poll-sec` on `spawn.py` only if the user asked to wait. Planning 分发 uses `--poll-sec 0` and does not watch. Employees do not dispatch. Do not GET child `/events/search`.

## Steps: notify

Other department **manage** only. Planning must not notify.

Write the report to a temp `.txt`. First line must be `engineering:report`. Then:

```
python <this-skill>/scripts/spawn.py --mode notify --prompt-file <txt>
```

Omit `--this-id`. Script resolves this window, POSTs to `parent_conversation_id` with `run: true`. Parent missing or GET fail → **fail**. Script exit ≠ 0 → **fail**. Do not finish the hop as reported. Do not GET parent `/events/search`. Do not watch.

```
engineering:report
department: delivery | acceptance | arbitration | human
ticket: #<n>
hop: done | send-back | need-arbitration | need-human | blocked | wait-merge
receipts: <role=pass|fail|none; …>
suggested next: 分发 <department> #<n> | 决策 | stop
```

Then extra lines as needed. This message is **not** 推进. Report the JSON `url` / `parent_id`.

Trust `launched_agent_profile` and create-time `agent.llm.reasoning_effort`. Ignore the child's self-identified name and the UI picker.

Cursor ACP may emit an early placeholder `LLMBadRequestError`. Finished ACP tools still count as success.

## Steps: delegate

Do not POST `/api/conversations`. Task a subagent this runtime exposes.

Wait until that Task ends and the receipt is in this conversation. `isBackground: true` / background / fire-and-forget → **fail**. Receipt missing → **fail**. Do not finish. Do not report the hop done.

`general-purpose` → Task `general-purpose`; if that name is missing, Task `generalPurpose`. `code-explorer` / `web-researcher` → those names. Name missing → **fail**. No Task tool → **fail**. Do not run `spawn.py`.

Prompt: goal, paths, constraints, done criteria, receipt. Do not paste PDF body. Do not tell the subagent it is planning or a department.
