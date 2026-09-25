# Make delivery notify explicit, idempotent, and fast

## Context

Delivery completion is mechanically finished before the planning notification is sent. A notify attempt can nevertheless appear hung even after the report has been accepted: Windows PowerShell may write a UTF-8 BOM that fails the report-prefix check, automatic conversation discovery may scan historical conversations, and post-success cleanup can keep the command running after the API has already acknowledged the event. Retrying in that state risks posting duplicate completion reports.

## Decision

The notify path will be treated as a short, idempotent acknowledgement step rather than another delivery operation.

- Invoke notify with an explicit current conversation ID; do not resolve the sender by scanning conversations when the ID is available.
- Write report files as UTF-8 without a BOM, or provide an equivalent encoding-safe input path.
- Use a short notify request timeout. Once the events endpoint returns success, print the receipt and exit without additional blocking cleanup or parent reruns.
- Include a stable delivery receipt key, such as ticket number plus commit, and make retries safe by recognizing an already-posted receipt.
- If the outer terminal soft-times out after a successful receipt, treat the notify as successful and inspect the parent before retrying.

## Consequences

Delivery verification, commit, push, and issue closure remain separate from notification. Notify failures preserve the completed receipts and do not repeat implementation or review. The workflow becomes easier to observe: success is the events API acknowledgement, while parent execution status is checked independently.

The existing #39 implementation is accepted and installed; this ADR records the follow-up design rather than reopening that ticket.

## Alternatives

Keeping automatic conversation discovery was rejected because it is slower and can select the wrong historical conversation. Waiting for parent cleanup after a successful POST was rejected because it makes a successful notification look hung. Blindly retrying after a terminal soft timeout was rejected because it can duplicate the planning report.
