# skill-maker privileges

Contract for skill-maker's authority, split in three (ADR 0006 Decision 3:
`docs/adr/0006-skill-registry-grouped-disclosure-and-maker-privilege.md`).
Enforcement is review plus the guard tests named below. Registration follows
`engineering-routing/references/routing-table.md` § Registration (#50
procedure) step-for-step.

## 1. Exclusive engineering-series modifier

Only skill-maker may edit or create engineering-series skills — directories
`engineering-*`, `*-sessions`, `*-watch`. Every such change goes through
skill-maker on a patch/acceptance ticket. Ad-hoc edits to those directories
fail.

- Guard test: `engineering-process/scripts/test_source_markers.py` (fail
  closed) keeps the floor: every engineering-series `SKILL.md` carries its
  source marker — the frontmatter `name:` equal to the directory name.
- The real enforcement is review.

## 2. Registrar

skill-maker is the registrar: it executes registration patch tickets per
`engineering-routing/references/routing-table.md` § Registration (#50):

1. Skill files land in the repo. `<name>/SKILL.md` present; frontmatter
   `name:` equals the directory name. Anyone may author; authorship is not
   gated.
2. Spec contains/uses entry added: a contains edge from the owning parent;
   every enabled craft skill adds one `uses -> engineering-routing` edge;
   craft skills never get `-> sessions` edges.
3. Exactly one routing-table row appended to
   `engineering-routing/references/routing-table.md`, with state
   `registered` (not `enabled`): empty `group`, empty `uses`, `entry` equal
   to the skill name with no path separators.
4. Never engine code: no edits to engineering-series `SKILL.md` or scripts.
   The table file itself is data, not engine code.
5. Registration never dispatches anything: the table is data; routing
   consumes it. `registered` is NOT routable. Enablement (`registered` ->
   `enabled`) is a separate patch ticket, not part of registration.

Validate a registration with `scripts/registrar_check.py` before executing
the patch; empty offender list = pass, fail closed on malformed input.

## 3. No ownership of product craft content

Anyone may author a product craft skill (pcb, ppt, ...); authorship is not
gated. skill-maker does not own, rewrite, or gate craft content — only
registration and routability pass through the registry.

## Table row

`skill-maker` itself stays `registered`: files in repo, spec entry, one
row, not routable. Enablement is a separate patch ticket, never part of
registration.
