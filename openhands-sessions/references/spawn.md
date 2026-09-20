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

Use a realistic `max_iterations`: 80 for a one-shot, 200 for a single-file fix, 400 for a page or a few files, and 500 for a feature slice or uncertainty. User-named caps win.
