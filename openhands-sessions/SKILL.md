---
name: openhands-sessions
description: Use whenever the user asks to spawn, dispatch, notify, list, resume, or delegate OpenHands/Agent Canvas sessions. Provides harness-specific conversation APIs; repository routing policy remains owned by engineering-routing.
---
# OpenHands Sessions
This skill is the Agent Canvas/OpenHands transport adapter. It does not decide process routing, department sequence, gates, or completion. Follow the repository's routing skill for those decisions.

All session adapters must satisfy the provider-neutral capability contract in [capabilities](references/capabilities.md). Open only that reference when implementing or validating a harness adapter. A native harness or CLI may expose its own internal delegation mechanism; this is conditional and must not be confused with department dispatch.

## Shared rules
1. Read [identity](references/identity.md) before any mode that reads or mutates a conversation or invokes GitHub.
2. Preserve the imported workspace, Canvas identity, parent direction, and receipts.
3. These modes are non-interactive. Never ask semi-auto or full-auto.
4. Never print credentials, use a credential alias, or discover credentials independently.
5. A launch receipt means launched, not accepted or complete. Only a validated correlated report can close a department dispatch.
6. Resolve scripts relative to this installed skill directory, not the repository checkout.
## Modes
| Mode | Use | Reference |
|---|---|---|
| `list` | Inspect live profiles and LLM catalog | [list](references/list.md) |
| `open` | New independent conversation on a named profile/model | [spawn](references/spawn.md) |
| `dispatch` | Planning department hands off to **another** department, or user opens a session | [spawn](references/spawn.md) |
| `notify` | Other department manage hop finished; report child-to-parent | [notify](references/notify.md) |
| `resume` | Continue a validated existing direct department child | [resume](references/resume.md) |
| `delegate` | Run a synchronous employee Task subagent | [delegate](references/delegate.md) |
Open only the selected one-level reference plus `identity.md`. Do not recursively search for more instructions.
## Mode selection
- A request to list available models or profiles selects `list`.
- A user-requested new independent conversation selects `open`.
- A routing decision already made by the routing skill to launch a department selects `dispatch`.
- A department child reporting to its parent selects `notify`.
- Planning continuing the same validated direct department child selects `resume`.
- Department-internal employee work selects `delegate`.
If the routing skill has not selected a process action, this skill must not invent one.
Task-type routing (who should work) is `engineering-routing`, which may dispatch only to rows whose state is `enabled` in `engineering-routing/references/routing-table.md`; a `registered` row is not routable. If the user asked to pick by task type and routing did not already call this skill → read and run `engineering-routing`. If routing already called this skill, or the user named a profile/model → only the named mode.

This copy runs on the **ACP bridge**. A **department** (including planning) may be a **model** on this bridge (e.g. grok). Do not call that window "ACP". **Employees** = **delegate**. Do not rewrite `delegate` to `dispatch`. No Task here → **fail** delegate; do not spawn a child instead. Do not hand off an employee.

## Rules

1. Live API only. Do not cache ids, profile names, or efforts across turns.
2. Never print the API key. Credential, host, and transport mechanics (key
   header, backend/UI hosts, PowerShell 5.1) → [identity](references/identity.md).
3. Do not copy this POST into other skills. Do not write a local
   `dispatch_session.py`. Hand-written `POST` / `GET` / `python -c` against
   `/api/conversations` → **fail**. Callers: read and run this skill. Open,
   dispatch, and notify only via `scripts/spawn.py`. Child GET `id` missing
   or tags missing `clientsource=agentcanvas` after spawn → **fail**.
4. Do not choose a profile by task type here. That is `engineering-routing`, which may dispatch only to rows whose state is `enabled` in `engineering-routing/references/routing-table.md`; a `registered` row is not routable.
5. Do not change the engineering contract (that is `engineering-init`). Do
   not advance tickets (that is `engineering-process`).
6. At most 3 concurrent dispatch children.

## Key points

**Agent profile** = spawnable runtime (`openhands` vs `cursor-acp`) + id. POST `agent_profile_id`. Mutually exclusive with `agent` / `agent_settings`.

**LLM profile** = `model` + `reasoning_effort` (detail endpoint; list omits effort). Same list `model` can be several efforts. Match **name / effort**, not list `model`. Grok effort is the `acp_model` suffix (`-high` / `-xhigh`).

**open** vs **dispatch:** open may be a greeting and polls only if asked. dispatch always has a task, always sets `parent_conversation_id` to this conversation (unless the user asked for an unrelated conversation). Process handoff: `--poll-sec 0`; planning **stops** (does not watch). User opens a session: poll only if asked.

Conversation identity, credential, host, transport, and workspace mechanics (GET `id` vs empty `conversation_id`, `CURSOR_CONVERSATION_ID` 404 semantics, spawn.py resolution walk-up, POST `worktree` semantics, sidebar grouping) → [identity](references/identity.md).

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

The adapter maps that registered source to consumer `GH_TOKEN` with an authenticated `LookupSecret`. Source `none`, unavailable source, authentication failure, or lookup/create rejection fails closed. Never alias the source variable in a prompt. Do not pass these options for employee Task/delegate work. GitHub finalization failure must still preserve completed receipts and run **notify**.

Omit `--this-id`. Script exit ≠ 0 → **stop**. Do not retry with a guessed id. Do not grep disk. Resolution walk, POST copy semantics, and the sanitized `githubbinding` tag → [identity](references/identity.md).

User named a subdir / ticket tree → prompt `cd` only. User asked to open in a **different imported project** → `--mode open` on a conversation whose `working_dir` is that project; no parent.

- `max_iterations` floors (one-shot 80 … large slices 500; user-named cap wins) → [spawn](references/spawn.md). Hitting the cap marks `error` (`MaxIterationsReached`, not retryable) and skips later steps such as `git commit`.
- Report the JSON `url`, `working_dir`, `tags`, `id`. `clientsource` missing or `id` missing → failure. Empty `conversation_id` is OK.

Prompt is self-contained: goal, paths, constraints, done criteria, report shape. Process handoff: tell the child it is that department **manage**; staff employees per process templates.md **duty table**; wait until each receipt is in that window; then sessions **notify**; stop. Human child: talk to the user — how to test and accept, and help; do not notify until pass or fail. Manage must not do implement/review/verify work. Do not finish after launching Task. Do not claim to be the planning department; do not hand off to another department. User opens a session: tell the child it is the **planning** manage window (talks to the user). Do not tell an employee prompt it is a department. Department windows may read the ticket-tree `PROCESS.md`. Employee prompts must not (`planning` implement may read `PROCESS.md` for patch).

Poll is `--poll-sec` on `spawn.py` only if the user asked to wait. Planning handoff uses `--poll-sec 0` and does not watch. Employees do not dispatch. Do not GET child `/events/search`.

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
suggested next: hand off <department> #<n> | decide | stop
```

Then extra lines as needed. This message is **not** "推进". Report the JSON `url` / `parent_id`.

Trust `launched_agent_profile` and create-time `agent.llm.reasoning_effort`. Ignore the child's self-identified name and the UI picker.

Cursor ACP may emit an early placeholder `LLMBadRequestError`. Finished ACP tools still count as success.

## Steps: delegate

Do not POST `/api/conversations`. Task a subagent this runtime exposes.

Wait until that Task ends and the receipt is in this conversation. `isBackground: true` / background / fire-and-forget → **fail**. Receipt missing → **fail**. Do not finish. Do not report the hop done.

`general-purpose` → Task `general-purpose`; if that name is missing, Task `generalPurpose`. `code-explorer` / `web-researcher` → those names. Name missing → **fail**. No Task tool → **fail**. Do not run `spawn.py`.

Prompt: goal, paths, constraints, done criteria, receipt shape. Do not tell the subagent it is planning or a department.
