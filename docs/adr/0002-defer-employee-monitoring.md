# Defer employee monitoring to the next version

## Context

The current version must make the department dispatch, notify, and resume chain work end to end. The existing `openhands-watch` parent-conversation inactivity heuristic can report a false hang while a department manage conversation is synchronously waiting for a healthy long-running Task employee: during #24, the department was marked hung after more than 600 seconds without parent activity, but implement later returned pass with commit `27565d8` and passing tests.

## Decision

Current-version acceptance is not blocked by Task- or employee-aware monitoring. In particular, #23 retains its department-conversation monitoring contract and does not expand to employee Task monitoring.

Employee monitoring is a secondary, next-version capability. It must distinguish department scope from employee scope: a department waiting on an active employee is alive (`waiting-for-employee`), not hung. The backend watch adapter owns raw Task/subagent facts; `engineering-watch` owns their engineering meaning. Employee status requires Task Action-to-Observation matching, task/subagent identity, subagent heartbeat or state, and receipt presence and validity. Recovery must preserve completed-work receipts so a lost return or receipt does not repeat completed work.

## Consequences

The next-version work is scheduled after the current-version sink #21 and may not enter #21 acceptance. Separate changes may be required in `openhands-watch` and `engineering-watch`, followed by one acceptance ticket.

## Alternatives

Expanding #23 now was rejected because it would delay the current department-level delivery and conflate two monitoring scopes. Treating parent inactivity alone as a hang was rejected because #24 demonstrates that it can misclassify healthy delegated work.
