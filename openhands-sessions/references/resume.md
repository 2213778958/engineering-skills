# Resume

Planning may continue an existing direct department child without replacing its conversation, history, or employee receipts:

```text
python <this-skill>/scripts/spawn.py --mode resume --target-id <child Canvas id> --prompt-file <txt>
```

Use only to recover a watch result of `terminal + missing-notify` or `terminal + finalization-failed`, or an explicitly paused/idle/awaiting-user department child. For a terminal target, the wrapper appends the message with `run: false` and then calls the run API (`message-then-run`). For a safe non-terminal target, it appends the message with `run: true` and does not issue a second run request (`message-with-run`).

Validation requires all of these:

- current conversation is planning and has no parent;
- target is its direct child and points back with the same `parent_conversation_id`;
- imported `working_dir` is identical;
- `clientsource=agentcanvas`, `layer=department`, non-planning department, dispatch id, and ticket tags are present;
- target state is `finished`, `stopped`, `error`, `paused`, `idle`, or `awaiting_user`.

Reject arbitrary ids, descendants, parents, siblings, unrelated workspaces, missing tags, employee-layer targets, planning children, `running`, and unknown transitional states. Do not use notify for planning-to-child messages. Do not repeat completed employees; prompt only the failed finalization tail.
