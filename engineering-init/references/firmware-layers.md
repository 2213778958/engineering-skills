# C/C++ layer templates

C and C++. Do not use for other languages. Layer names and prefixes already in the repo or named by the user → **follow the repo**. Directory names below are examples, not the only legal names.

## Rules (both templates)

- Template unconfirmed → invent no layers, open no tickets.
- Keep the three relationship graphs separate. Do not derive `#include` direction from functional layering. Do not derive include direction from runtime paths.
- Vendor (HAL, OS API, third-party, generated code) keeps original names. Do not open rename tickets.
- Layer directories and prefixes: ask first; if none given, use this file's examples and write them into `AGENTS.md` and the glossary. Do not treat examples as the only legal names.

## Key points: which template

| Template | When | DIP / Handle / PortOps / Bind |
|---|---|---|
| **no-layer** | No stable layers | skip |
| **simple-layers** | No fake backends, no swapping implementations | **skip** |
| **high-abstraction** | Swap backends / host-test components / multiple environments | **do** (high-abstraction section only) |

Hang the Vendor tree off the depended-on node. Do not treat it as a layer of this repo.

## Key points: simple-layers

Three roles: entry, middle, next-to-Vendor. Example dirs: `app` `drv` `bsp`. User may pick three other names.

uses (example names): entry uses middle; middle uses next-to-Vendor; entry does not use next-to-Vendor / Vendor (except ticket whitelist).

Public functions: prefix follows **this repo's layer names**. Examples: `App_*` `Drv_*` `Bsp_*`. Not fixed words.

Do not write PortOps, Bind, or a Handle ownership table. Do not invent a standalone `port/`.

## Key points: high-abstraction (DIP + injection)

Roles (example dirs, rename allowed). **Do not freeze five layers.** Entry and product-flow are small → same directory, same layer (grill). Still required: components, adapters, assembly (if no assembly layer, the entry group root also assembles).

| Role | Example dir | Does |
|---|---|---|
| entry | `APP` | boot, task entry. May merge with product-flow |
| product-flow | `Service` | cross-capability product flow. Does not assemble low-level Handles. May merge with entry |
| assembly | `Platform` | **upper**: long-lived Handle and Context; calls Bind |
| reusable component | `Components` | implements function only. Owns the PortOps **type**. Does not hold this-environment instances |
| adapter | `Adapters` | **lower**: PortOps **function implementations**. May include Vendor. Does not pick global instances itself |

Ownership example (replace names with this repo's layer names; merge entry+product-flow → one fewer cell):

```text
Vendor → adapter → component → assembly → product-flow → entry
```

### Who holds what (high-abstraction only)

| Thing | Who defines | Who holds the instance | Who provides the impl |
|---|---|---|---|
| Handle | component header | assembly layer (else entry group root) | component functions take `Handle *` |
| PortOps type | **owned by the component** | pointer in Handle | — |
| PortOps functions | — | — | adapter `.c` |
| Context | adapter header | assembler holds it; pointer in Handle | adapter uses it to call Vendor |

Assembly order: hold Handle + Context → Bind (Ops+Context into Handle) → component Init.

Forbidden (high-abstraction only):

- `static` this-environment instances inside a component
- component includes adapter / assembly / Vendor / product-flow / entry
- adapter picks a global instance itself
- standalone `port/` directory, or a read/write API parallel to PortOps on assembly / next-to-Vendor
- a second product layer for the OS; to add OS: component owns Os PortOps, adapter implements, Bind at assembly

`#include`: adapter `.c` includes the component header = implementing PortOps, not a cycle. Assembly `.c` includes component, adapter, and this-environment instance headers, only for Bind. Do not draw runtime paths on uses.

### Naming (high-abstraction only)

- Reusable components: follow domain/device/protocol names (e.g. `FT6X36_Init`). **Do not require** `Layer_Module_Action`; do not rename to `Comp_*`. Existing symbols: no rename tickets
- Assembly / product-flow / entry: default `Layer_Module_Action`; **layer segment is this repo's layer name** (not necessarily `Platform_`)
- Adapter: Bind name may follow the module file; do not change component symbols
- Vendor: original names

## Steps: grill (C/C++, before drawing uses)

1. Ask: no-layer / simple-layers / high-abstraction. Unconfirmed → stop.
2. If layered: ask this repo's top-level directory names. High-abstraction also ask: entry and product-flow separate or merged. No names given → use examples; at close-out write the `AGENTS.md` directory table and the `CONTEXT.md` layer group. Layer choice → ADR per repo-docs. User says merge or function is small → one layer does entry + product-flow.
3. Simple-layers: write only the three-layer uses and prefixes. Do not write a DIP ownership table.
4. High-abstraction: write role↔directory map, ownership table, legal includes. No standalone `port/`. Do not freeze five layers.
5. Existing component symbols → record "follow current names".
