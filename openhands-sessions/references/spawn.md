# Spawn

Write a self-contained prompt to a temporary text file. Open and generic child compatibility commands remain:

```text
python <this-skill>/scripts/spawn.py --mode open --profile-id <uuid> --prompt-file <txt> --max-iterations <n>
python <this-skill>/scripts/spawn.py --mode dispatch --profile-id <uuid> --prompt-file <txt> --max-iterations <n> --poll-sec 0
```

A process department dispatch must include correlation metadata:

```text
python <this-skill>/scripts/spawn.py --mode dispatch --profile-id <uuid> --prompt-file <txt> --department <delivery|acceptance|arbitration|human> --ticket #<n> --poll-sec 0
```

The script creates a stable dispatch UUID and returns `dispatch_id`, `child_conversation_id`, `department`, and `ticket`, both directly and in child tags for watch consumers. Preserve that receipt for exact report correlation.

The script copies imported `working_dir` and tags, forces `clientsource=agentcanvas`, and uses `worktree: false`. Planning process dispatch stops after launch and does not watch. Generic legacy dispatch without department metadata remains supported for user-requested child planning windows; it is not a process department dispatch.

## max_iterations floors

`max_iterations` is estimated, never a fixed 100. Count likely tool-calls (read, install, each edit, build, browser, commit), **×2 at least**, then use a floor:

| Child work | Floor |
|---|---|
| one-shot question only | 80 |
| single-file fix | 200 |
| a page / a few files + test | 400 |
| feature slice: install, multi-file, verify, commit | 500 |
| open with no task yet / unsure | 500 |

Prefer the next floor up when unsure. Large slices start at **500**. User-named cap wins. Report the number with the UI link.

Hitting the cap marks `error` (`MaxIterationsReached`, not retryable) and skips later steps such as `git commit`.
