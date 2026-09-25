# skill-maker privileges

Contract for skill-maker's authority, split in three. Enforcement is review.

## 1. Exclusive engineering-series modifier

Only skill-maker may edit or create engineering-series skills — directories
`engineering-*`, `*-sessions`, `*-watch`. Every such change goes through
skill-maker on a patch/acceptance ticket. Ad-hoc edits to those directories
fail.

Every engineering-series `SKILL.md` carries its source marker: the
frontmatter `name:` equals the directory name.

## 2. Registrar

skill-maker is the registrar: it executes registration patch tickets against
the routing table in `engineering-routing`.

1. Skill files land in the repo. `<name>/SKILL.md` present; frontmatter
   `name:` equals the directory name. Anyone may author; authorship is not
   gated.
2. Spec contains/uses entry added: a contains edge from the owning parent;
   every enabled craft skill adds one `uses -> engineering-routing` edge;
   craft skills never get `-> sessions` edges.
3. Exactly one routing-table row appended to the routing table in
   `engineering-routing`, with state `registered` (not `enabled`): empty
   `group`, empty `uses`, `entry` equal to the skill name with no path
   separators.
4. Never engine code: no edits to engineering-series `SKILL.md` or scripts.
   The table file itself is data, not engine code.
5. Registration never dispatches anything: the table is data; routing
   consumes it. `registered` is NOT routable. Enablement (`registered` ->
   `enabled`) is a separate patch ticket, not part of registration.

Validate the patch against the current table before executing it: the skill
name, the spec entry, and the new row must all match the format above.
Malformed input → fail closed; never guess.

## 3. No ownership of product craft content

Anyone may author a product craft skill (pcb, ppt, ...); authorship is not
gated. skill-maker does not own, rewrite, or gate craft content — only
registration and routability pass through the registry.

## skill-maker's own row

`skill-maker` itself stays `registered`: files in repo, spec entry, one row,
not routable. Enablement is a separate patch ticket, never part of
registration.
