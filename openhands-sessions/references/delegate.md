# Delegate

Delegation is conditional. A native harness or CLI may provide its own internal employee, task, or sub-agent mechanism. Use that mechanism only when it exposes a defined receipt and lifecycle contract. Internal delegation is not department dispatch and must not be substituted for a correlated child conversation.

For the OpenHands runtime, delegate employee work only through a synchronous Task subagent. Do not call `spawn.py` or POST conversations.

Wait until Task ends and its receipt is in this conversation. Background, fire-and-forget, missing Task, missing named agent, or missing receipt fails. Do not substitute a child conversation.

Use `general-purpose` (or `generalPurpose` only when that is the exposed name), `code-explorer`, or `web-researcher`. Prompt only the goal, paths, constraints, done criteria, and receipt shape. Employees are not departments and must not be told otherwise.
