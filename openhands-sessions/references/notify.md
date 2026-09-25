# Notify

Notify remains child to parent only. Write the report to a temporary file and run:

```text
python <this-skill>/scripts/spawn.py --mode notify --prompt-file <txt>
```

The exact envelope is:

```text
engineering:report
dispatch-id: <dispatch UUID>
child-conversation-id: <Canvas child id>
department: delivery | acceptance | arbitration | human
ticket: #<n>
hop: done | send-back | need-arbitration | need-human | blocked | wait-merge
receipts: <role=pass|fail|none; ...>
suggested next: hand off <department> #<n> | decide | stop
```

The script requires non-empty identity, `hop`, `receipts`, and `suggested next`, and rejects missing, partial, stale, or mismatched correlation identity before posting. Reports from children created before correlation metadata may use `--allow-legacy-report` only when no identity fields are present and the operational envelope is complete; this produces `correlation: legacy-unverified` and `completion_eligible: false`, never completion. Never use compatibility for partial identity or a mismatch.

Only another department manage window notifies. Parent missing, API failure, or validation failure means the hop was not reported.
