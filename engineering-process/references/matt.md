# Matt skill calls

This series owns the ticket flow. Matt skills are primitives. `read and run` the named skill. Do not copy its body.

## Do not run

`setup-matt-pocock-skills` `to-spec` `to-tickets` `triage` `wayfinder` `grill-me` `grill-with-docs` `ask-matt` `improve-codebase-architecture`

## Run

| Caller | Skill | When |
|---|---|---|
| `engineering-init` | `grilling` | Decision unconfirmed |
| `engineering-init` | `domain-modeling` | Writing `CONTEXT.md` / ADR |
| `engineering-init` | `writing-for-agents` | Injecting `AGENTS.md` |
| `engineering-init` | `codebase-design` | Contains cuts, layers, or seams |
| `engineering-routing` | `grilling` | Task type or MODELS row unclear |
| planning 决策 | `grilling` | Patch still needs a human decision |
| planning 决策 | `domain-modeling` | Glossary or ADR changes |
| planning 决策 | `prototype` | Cannot settle on paper; throwaway only, not the product branch |
| planning 决策 | `research` | Need primary-source facts; do not paste manuals here |
| delivery implement | `tdd` | Writing product code. Required. `verify:` is not a substitute |
| delivery implement | `codebase-design` | Interface, depth, or seam still open |
| delivery implement | `domain-modeling` | A new term or hard decision appears |
| delivery review | `code-review` | Standards (`AGENTS.md`) + spec (the implement ticket) |
| delivery verify | `diagnosing-bugs` | `verify:` is red; tighten the loop, then send implement back |
| acceptance implement | `resolving-merge-conflicts` | Heads conflict. Resolve by intent. Do not `--abort` |
| arbitration implement | `diagnosing-bugs` | Reproduce + opinion. Need a loop that is already red |
| arbitration implement | `codebase-design` | The fight is the seam or module shape |
| `datasheet-headers` | `grilling` | `<module>` or PDF path missing |
| `skill-maker` | `grilling` | Decision missing |
| `skill-maker` | `writing-for-agents` | Writing a skill or `AGENTS.md` |
| human manage | `wizard` | Only a human can click (secrets, vendor dashboards, cutover) |

`openhands-sessions` and `openhands-watch` do not call Matt skills.
