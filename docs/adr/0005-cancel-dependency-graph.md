# Cancel the dependency-graph rendering; GitHub-native ordering only

## Context

The engineering contract kept a flow-graph mechanism alongside the GitHub ticket
net: `engineering-init/scripts/render_graph.py` rendered the mermaid dependency
graph onto the spec, plan step 9 mandated a `--write` pass, the `graph` hop
refreshed it, and close/reopen/hop actions in `engineering-process` re-rendered
it with "script fail → fail" enforcement. The ticket net, meanwhile, was already
expressed natively: implement tickets carry official `blocked-by` edges, and
acceptance/gate tickets hang off them, so GitHub already holds the ordering
truth. Keeping a rendered copy of that same net meant two sources that could
disagree, plus render latency and failure modes on every hot action.

## Decision

The dependency-graph rendering mechanism is cancelled (#47, person-approved).
`render_graph.py` and its test are deleted, the `graph` hop and the flow-graph
plan step are removed, and no close/reopen/hop action renders anything.
GitHub-native relationships — sub-issue parent links plus `blockedBy` edges —
are the single source of ordering truth. Ticket pull/next logic must treat an
open parent sub-issue as blocking its children, matching GitHub sub-issue
`blocked` semantics, and otherwise follow `blockedBy`. This supersedes the
ADR 0003 sentence "Allowlist comparison, graph dependencies, ticket identity,
and isolated worktrees determine whether ticket lines are independent enough to
run in parallel.": independence is now determined by allowlist comparison,
GitHub-native ticket relationships, ticket identity, and isolated worktrees.
The contains/uses architecture graphs and their spec markers are not affected.

## Consequences

Verification no longer runs a render stage. `verify.py` stages are watch,
verify, and a guard (`test_no_render_mandates.py`) that keeps render mandates,
graph-test wiring, and hard imports from returning. Close/reopen/hop actions
lose their render failure mode, and ordering questions resolve by reading the
issue directly (`gh issue view` with dependencies/relations) instead of a
rendered file. Old spec files may still contain a rendered `engineering:graph`
block; it is inert history and must not be regenerated.

## Alternatives rejected

Keeping the renderer optional (render on demand, never mandated) was rejected
because the rendered graph would still drift from the GitHub net whenever
someone skipped it, preserving the two-sources problem. Replacing the renderer
with a new generator over the same spec markers was rejected for the same
reason. Moving ordering into a repository file checked by CI was rejected
because it duplicates GitHub sub-issue/blockedBy state outside GitHub and adds
merge conflicts on a shared file.
