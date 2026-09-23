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
| `open` / `dispatch` | Create an independent or child conversation | [spawn](references/spawn.md) |
| `notify` | Report a department result child-to-parent | [notify](references/notify.md) |
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
