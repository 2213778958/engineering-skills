# Compress execution before adding parallelism

## Context

The next version may run multiple independent ticket lines concurrently, but parallel dispatch is safe only when modification boundaries are machine-checkable. The current workflow also repeatedly loads broad process guidance, scans unrelated code, and repeats completed work after tail failures. These behaviors increase model usage without improving engineering confidence.

This is a technical-efficiency problem, not a budgeting problem. Model choices remain explicit in `MODELS.md`; the process does not need monetary limits, token quotas, price-based routing, or automatic model downgrades.

## Decision

The next version starts by making ticket allowlists structured, machine-readable, and enforceable. Allowlist comparison, graph dependencies, ticket identity, and isolated worktrees determine whether ticket lines are independent enough to run in parallel. The same contract constrains employee reads and edits and detects out-of-scope changes.

After allowlists, introduce progressive disclosure. Entry skills stay small and load detailed references only when the current state requires them: parallel-selection rules when several tickets are pullable, recovery rules after a failure, arbitration rules after a challenge, and backend details only at an adapter boundary. Employee prompts contain the current role's contract, allowlist, relevant evidence, and receipt shape rather than the complete engineering process.

Compress execution by using deterministic scripts for mechanical checks, restricting repository reads to relevant paths, preserving valid commits and receipts, resuming existing conversations, and rerunning only work invalidated by a change. Push, graph, notify, Task-return, or receipt failures must not automatically repeat completed implementation and review.

Safe parallel dispatch follows these capabilities. Independent ticket lines may run concurrently only when dependencies are closed, worktrees and tickets differ, and structured allowlists do not conflict. Each ticket's internal department hops remain serial.

## Consequences

The implementation order is:

1. structured and enforced allowlists;
2. progressive disclosure and reduced repeated context, reads, and work;
3. safe parallel dispatch of independent ticket lines;
4. integration with the separately planned employee-monitoring chain.

The next version does not introduce monetary budgets, token quotas, price-aware scheduling, automatic model downgrades, or cost approval workflows. Efficiency is measured through less unnecessary context, fewer broad scans, fewer duplicate calls, and less repeated work.

## Alternatives

Adding parallel dispatch before machine-checkable allowlists was rejected because natural-language path boundaries cannot reliably prevent conflicting work. Adding a detailed cost-control system was rejected because the immediate need is to remove technical waste, while users can continue choosing models explicitly through `MODELS.md`. Loading all process and failure guidance into every agent prompt was rejected because most of that context is irrelevant on the normal path.
