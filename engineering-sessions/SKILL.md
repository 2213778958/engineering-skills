---
name: engineering-sessions
description: >-
  Selects the repository's sessions adapter from its sessions latch, then
  reads and runs that adapter. Use when another engineering skill needs to
  list session targets, open or dispatch a conversation, notify a parent, or
  delegate employee work.
---

# Engineering sessions

1. Read `sessions:` from `docs/agents/PROCESS.md`. If it is absent, read
   `sessions:` from `docs/agents/MODELS.md`.
2. Require exactly one adapter name: `openhands-sessions` or an installed
   future adapter such as `codex-sessions`. A missing, conflicting, or
   unavailable adapter is a failure; do not infer one from the current model,
   runtime, or ACP.
3. Read and run the named adapter for the caller's requested mode and inputs.
   Return its result unchanged.

Do not implement catalog, spawn, dispatch, notify, or delegate here. Do not
copy session API or POST logic into this skill.
