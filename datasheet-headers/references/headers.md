# Headers

Resolve output path; stop at the first hit:

1. Path the user named this turn
2. Repo `docs/agents/`, `AGENTS.md`, `CONTEXT.md`, existing module header naming
3. Defaults:

| File | Write | Do not write |
|---|---|---|
| `<module>_regs.h` | base, offsets, bitfields | init sequences, drivers |
| `<module>_cfg.h` | this-board clock/pin/timing constants, small enums | runtime code, HAL |

Directory: user path → repo conventions → contains node for that module (C: same directory as `.c`). Do not default to `include/` / `Inc/`. Repo already uses `Inc/` → follow the repo.

Repo convention is already a single file (e.g. `<module>_hw.h`) → follow it. Symbols not in the datasheet → omit or grill again; do not invent typical values.

`#pragma once` or a standalone include guard. `#include <stdint.h>`. Prefix follows the repo; else `MODULE_REG_*` / `MODULE_CFG_*`.

Every constant comment: datasheet file name + page or section (`// RM0008 p.142 §12.3.1`). A number with no comment → delete it or extract again. Do not invent registers. Only symbols this module ticket needs.

```c
#pragma once
#include <stdint.h>

#define UART1_BASE        0x40013800u  /* RM0008 p.51 */
#define UART1_SR_OFFSET   0x00u        /* RM0008 §27.6.1 */
#define UART1_SR_RXNE     (1u << 5)
```

Driver agents: read only these `.h` files and source. Do not open the PDF. Do not paste datasheet pages into context.
