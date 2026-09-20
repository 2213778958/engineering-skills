# Identity and credentials

## Conversation identity

- This conversation is GET `/api/conversations/{id}` field `id`; never use `CURSOR_CONVERSATION_ID`.
- Omit `--this-id` so `spawn.py` resolves the current Canvas conversation from the explicit OpenHands id or imported workspace. Do not grep local state.
- The imported workspace is `workspace.working_dir`; ticket worktree paths are prompt-only.
- Canvas conversations must carry `tags.clientsource=agentcanvas`.

## GitHub credential latch

Consume the exact `github-token-secret` configured in the repository PROCESS latch. Sessions does not discover names, choose aliases, or ask the user to align credentials.

- `none` means GitHub-dependent work is unavailable; report that before beginning it.
- Explicitly command-reference the configured registered key so on-demand injection occurs.
- Pipe only that reference to the wrapper; it maps the value to `GH_TOKEN` for the `gh` subprocess and never prints it.
- Do not assume `GITHUB_PERSONAL_ACCESS_TOKEN`, `GITHUB_TOKEN`, and `GH_TOKEN` are aliases.

PowerShell command shape, where `<KEY>` is the exact configured name:

```powershell
$env:<KEY> | python <this-skill>/scripts/github_command.py --key-name <KEY> -- gh <args>
```

The wrapper first runs `gh auth status`. Missing, expired, and `none` fail early with the configured key name and failure class; values are redacted. Do not assign the value to a persistent shell variable, echo it, or put it in command arguments.
