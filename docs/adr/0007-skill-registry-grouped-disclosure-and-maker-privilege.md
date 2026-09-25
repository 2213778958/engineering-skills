# 0007 — Skill registry, grouped disclosure, and skill-maker privilege

Date: 2026-09-23
Status: Accepted (person decision, recorded in planning conversation 2f26c192)

## Context

Spec #1 fixes the layering: product skills only `read and run engineering-routing`; craft lives only in the routing table; process / init / skill-maker / research never touch the sessions adapter ("不对接 Matt"). Three pressures now converge: (a) more interface-layer skills are coming (pcb, ppt, …) and each must onboard without editing engine code; (b) the routing table currently lives inside `engineering-routing/SKILL.md`, coupling the registry to engine code; (c) skill-maker's authority is undefined — today it is a generic authoring skill, while the engineering family needs a controlled writer.

## Decisions

1. **Registry is data.** The routing table moves out of `engineering-routing/SKILL.md` into a reference file (references/routing-table.md) read at runtime. Registering a skill = spec contains/uses entry + one routing-table row + skill files. No engine logic edits. Registration is executed as a planning patch ticket.
2. **Two disclosure states.** A skill is `registered` (files in repo, spec entry exists, NOT routable) or `enabled` (has a routing-table row under a task-type group). Progressive disclosure is a routing-time decision: groups are cut by task type (office / hardware / research / …); install-time visibility does not imply routability. Enablement = patch ticket.
3. **skill-maker privilege, split in three.** (a) It holds the exclusive right to modify engineering-series skills (engineering-*, *-sessions adapters) — every such change goes through skill-maker plus a patch/acceptance ticket, never ad-hoc edits. (b) It is the registrar that executes registrations per Decision 1. (c) It does not own product craft content — anyone may author a pcb/ppt skill; authorship is not gated, routability is. A guard test asserts engineering-series SKILL.md files carry their source marker; the real enforcement is review.
4. **Dependency semantics.** Every enabled craft skill adds one `uses → engineering-routing` edge. Craft skills never get `→ sessions` edges. skill-maker's relation to the family is `maintains`, recorded in prose (and optionally an annotated graph edge later), not merged into the `uses` semantics.

## Consequences

- #16 (implement the routing skill table) implements the data table, groups, and the two states per this ADR; it is blocked by the registry-contract ticket.
- #17 (skill-maker goes through routing) wires skill-maker in under the three-way privilege split; blocked by the registry-contract ticket.
- #14 (init goes through routing) and #19 (merge the routing callers) keep their scope; the registry contract defines their calling convention.
- Future registrations are routine patch tickets; the engine never forks per skill.
- Spec #1 body is rewritten only when this line executes (first patch), not now.
