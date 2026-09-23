# Harness capability contract

This contract defines the provider-neutral capabilities that a sessions or watch adapter must expose. A harness may use native APIs, a CLI, ACP, or another transport internally; callers depend on these semantics, not provider-specific fields.

## Sessions capabilities

Required capabilities:

| Capability | Contract |
|---|---|
| `discover` | Return available profiles, runtimes, and declared capabilities. |
| `open` | Create an independent session and return its persisted identity. |
| `dispatch` | Create a child session with parent, department, ticket, and dispatch correlation. |
| `notify` | Submit a structured child-to-parent report. |
| `resume` | Continue a validated direct department child. |
| `get_status` | Return lifecycle state, relationship, correlation, and timestamps. |
| `get_receipt` | Return the final outcome and completion eligibility. |
| `correlate` | Validate parent, child, dispatch, department, and ticket identity. |

`dispatch` must verify the metadata persisted by the provider before returning a launch receipt. A launch receipt means only that the session was launched; it is not an acceptance or completion receipt.

`notify` must reject missing, partial, stale, or mismatched identity. Legacy reports may be accepted only as explicitly unverified and must never be completion-eligible. `resume` must validate direct parentage, workspace, department layer, target identity, and resumable state before mutation.

### Conditional delegation

`delegate` is not universally required. A native harness or CLI may provide its own internal delegation, employee, task, or sub-agent mechanism. An adapter may expose `delegate` when that mechanism is synchronous or otherwise has a defined receipt and lifecycle contract.

Internal delegation must remain distinct from `dispatch`: delegation is harness-internal work, while dispatch creates a department-level child session with correlation and parent notification. If `delegate` is exposed, it must declare whether it is synchronous, whether it returns a receipt, and whether it is watchable. It must not be silently substituted for `dispatch`.

Optional session capabilities may include `delegate`, `send_input`, `pause`, `continue`, `cancel`, and `stream_events`.

## Watch capabilities

Required capabilities:

| Capability | Contract |
|---|---|
| `snapshot` | Classify one or more target sessions without mutating them. |
| `await_terminal` | Wait until targets are no longer alive, subject to polling and timeout. |
| `classify` | Map provider states to `alive`, `hung`, or `terminal`. |
| `heartbeat` | Report the last activity time and stall age. |
| `rollup` | Produce a deterministic verdict for multiple targets. |
| `correlate_targets` | Verify targets belong to the requested parent or dispatch. |
| `exit_status` | Return stable machine-readable result and process status. |

The normalized verdicts are exactly:

```text
alive
hung
terminal
```

At minimum, adapters should normalize these reasons:

- terminal: `finished`, `error`, `stopped`, `cancelled`, `timeout`
- hung: `stall`, `waiting_for_confirmation`, `paused`, `missing-heartbeat`, `missing-correlation`, `not-found`, `provider-error`

Terminal state takes precedence over missing tags or heartbeat. A non-terminal session without valid correlation or a fresh heartbeat is `hung`, not `alive`. A loop timeout is a `hung` result with reason `timeout`, not an API failure.

For multiple targets, rollup is fixed: any `hung` yields `hung`; otherwise any `alive` yields `alive`; only all-terminal targets yield `terminal`.

Watch is read-only by default. It must not spawn, resume, pause, cancel, interrupt, or redispatch a target unless a separate operation explicitly requests that mutation.

## Common objects

Adapters should expose the smallest provider-neutral form of these objects:

```text
HarnessSession
- id
- provider
- parent_id
- workspace
- execution_state
- correlation
- created_at
- updated_at
- heartbeat_at
- capabilities

Correlation
- dispatch_id
- parent_session_id
- child_session_id
- department
- ticket
- layer

SessionReceipt
- session_id
- provider
- outcome
- correlation
- completion_eligible
- summary
- artifacts
- errors
```

Provider-specific fields are extensions and must not replace these core semantics.

## Capability discovery and conformance

Capability discovery should return a provider name, adapter version, and boolean support map. Missing required capabilities make an adapter non-conformant; missing optional capabilities must be visible to routing and must not be invoked.

Every adapter must have conformance coverage for dispatch correlation, resume validation, receipt eligibility, watch classification, heartbeat and stall detection, multi-target rollup, and stable failure behavior. Credentials, raw provider responses, and event bodies must not appear in ordinary receipts or watch output.
