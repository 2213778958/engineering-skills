# Architecture

Two graphs, separate from the flow graph. Node names = module list. Do not draw tickets / human gates / sinks here.

C/C++: no-layer or simple-layers → uses follows the confirmed three-layer edges. High-abstraction → three relationships (functional ownership, compile-time `#include`, runtime); legal edges in [firmware-layers.md](firmware-layers.md). Adapter `.c` including a component header = implementing PortOps, not a cycle. Handle is not a uses node. Layer directory names follow this repo; node names below are examples.

Write into the matching spec markers; replace the whole block if a marker already exists. Every graph must have a **title** as a markdown heading inside the marker. mermaid starts with `flowchart TD`. Do not write mermaid `---` / `title:` frontmatter (GitHub treats `---` as a link).

| Marker | Title (write these strings) |
|---|---|
| `engineering:contains` | Contains（嵌套） |
| `engineering:uses` | Uses（编译依赖） |
| `engineering:graph` | Graph（流程） |
| `engineering:contains-asis` | Contains（现有嵌套） |
| `engineering:uses-asis` | Uses（现有依赖） |
| `engineering:graph-asis` | Graph（现有依赖序） |

Block shape (outer four-backtick fence is this doc only; write three-backtick mermaid into spec):

````
<!-- engineering:contains -->

### Contains（嵌套）

```mermaid
flowchart TD
…
```

<!-- /engineering:contains -->
````

**plan / normalize to-be (tickets follow this set):** `engineering:contains` `engineering:uses`

**migrate as-is (snapshot of the origin tree; tickets do not follow this set):** `engineering:contains-asis` `engineering:uses-asis`

Seeing `github-engineering:*` → replace with the matching new marker.

## contains (tree)

Edge: `parent contains child`. At most one parent per node. Paths, public headers, ticket allowlists come from the **working** contains. Layered → top-level nodes = layers; no layers → invent no layer nodes. Directory rules: [conventions.md](conventions.md).

Marker: `<!-- engineering:contains -->` … `<!-- /engineering:contains -->`. Write with title Contains（嵌套）.

As-is: `<!-- engineering:contains-asis -->` … `<!-- /engineering:contains-asis -->`

Layered node examples (names may change): simple-layers `bsp --> uart1`; high-abstraction `components --> ft6x36`.

## uses (DAG)

Edge: `A uses B` = A may `#include` / link B. Arrow points at the depended-on side. Legal edges: [conventions.md](conventions.md) "Cross-layer / same-layer exposure". This graph only draws edges that exist in this revision. A component may be a depended-on node; do not rename its symbols.

Marker: `<!-- engineering:uses -->` … `<!-- /engineering:uses -->`. Write with title Uses（编译依赖）.

As-is: `<!-- engineering:uses-asis -->` … `<!-- /engineering:uses-asis -->`

Edge examples (names may change): simple-layers `app -->|uses| uart1`; high-abstraction `adapters_ft6x36 -->|uses| components_ft6x36`.

Working uses has a cycle → do not open tickets. Change the module list or contains, then redraw. As-is has a cycle → record it; not-normalized migrate may still extract graphs only.

## Tickets

- One implement ticket = one node on **working** contains (and its private headers). allowlist = that node's path (inside the landing repo; after normalize, relative to the mirror)
- Two implement tickets in parallel → no working-uses edge, and contains paths do not overlap
- Datasheet output lands on that module node; extract inside that implement ticket's delivery; do not open a separate extract ticket
- As-is graphs do not open tickets
