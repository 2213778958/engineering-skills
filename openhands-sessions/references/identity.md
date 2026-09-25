# Identity and credentials

## Conversation identity

**This conversation** = the Canvas conversation running this skill now. Identity is GET `/api/conversations/{id}` field **`id`**. `CURSOR_CONVERSATION_ID` is the ACP session id; it 404s on that GET. Do not pass it as `--this-id`. Do not grep `dev_conversations`. Do not `python -c` GET.

A receipt JSON containing `conversation_id` or `id` is success; do not re-POST. GET `conversation_id` empty is not a failure (Canvas stores the uuid in `id`).

**Imported workspace** = absolute `workspace.working_dir` of this conversation (the folder imported into Agent Canvas). Copy it. Do not invent a checkout path.

**Git worktree path** (`master\`, `root\`, `worktree\wave-a`, …) = prompt-only (`cd` / `git worktree add`). Never put it in `workspace.working_dir`.

**POST `worktree`** = server clone switch. Default `false`. `true` only if the user asked to leave this project for a new clone (often under `conversation_worktree_root`).

Canvas sidebar groups by imported `working_dir` **and** `tags.clientsource=agentcanvas`. API POST without that tag lands under 无工作区 even when `working_dir` matches. `spawn.py` copies this conversation's tags and sets `clientsource`. Child identity is GET `id`.

A worktree/checkout path is a different workspace: the child lands outside this project, and `parent_conversation_id` returns 422.

If the imported workspace itself is a git working tree, git refuses nested worktrees under it. Engineering hang: import the **container** (`master\` or `root\` plus `worktree\`), not the git root and not a ticket tree.

## Credentials, hosts, transport

Never print the API key, use a credential alias, or discover credentials independently. Header `X-Session-API-Key` from `~/.openhands/agent-canvas/api-key.txt`.

Hosts: backend `http://localhost:8000`, UI `http://localhost:3001`.

Windows: PowerShell 5.1. Write `.py` files for HTTP. Do not rely on `curl.exe` flags. Do not `python -c` GET.

## spawn.py resolution walk

Omit `--this-id`. `spawn.py` resolves the Canvas `id` (cwd + running + `clientsource=agentcanvas`, **including** a department child with `parent_conversation_id`). cwd may be the imported container, or that container's `master/` / `root/` / `worktree/<tree>` — the script walks up to the imported `working_dir`. Env `OPENHANDS_CONVERSATION_ID` / `CONVERSATION_ID` wins. Several matches → the most recently updated. Passing `CURSOR_CONVERSATION_ID` 404s; do not grep after a 404. `--this-id` only if it is already a Canvas `id`. Do not grep local state.

## spawn.py POST semantics

`spawn.py` GETs this conversation, copies `working_dir` and tags, sets `tags.clientsource=agentcanvas`, keeps `worktree: false`. Dispatch also sets `parent_conversation_id`. Do not pass a ticket-tree path. Do not hand-write POST or GET.

A `worktree/` checkout is a different workspace. POSTing `worktree` with that path opens a child whose workspace is outside the project and `parent_conversation_id` 422s. POST `worktree: false` and run from the imported container or `master/` root. To add a new ticket tree under `worktree/` first, run the POST inside the `worktree/` folder. Child workspace uses its own naming convention.

Nested worktree refusal → import the whole container (`master/` + `worktree/<tree>`), never a checkout. Container child workspace uses its own naming convention.

## Dispatch GitHub binding

The adapter maps that registered source to consumer `GH_TOKEN` with an authenticated `LookupSecret`. The script adds a sanitized `githubbinding` tag and `github_binding` result only; it never stores the source identity or value there. Regular OpenHands preflight explicitly references `GH_TOKEN`; ACP receives it in subprocess env.

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
