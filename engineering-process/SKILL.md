---
name: engineering-process
description: >-
  Advances an initialized repo from the planning department.
  Planning is a department: it 分发 tickets to other departments or
  runs 决策. Manage staffs implement/review/verify per the 职责表.
  Use when the user asks to 推进, 领票,
  下一张票, 主管, process, planning, delivery, acceptance, arbitration, or
  继续工程. 推进 / 领票 / 下一张票 / 主管 / 继续工程 default to planning. Do not use to
  规划, 初始化, or 迁移.
---

# Engineering process

| Call | When | Done |
|---|---|---|
| **next** | Only asking for the next ticket | Print one pullable ticket URL |
| **supervise** | Advance / pull a ticket (default) | Planning: after 分发 stop; after 回传 / 决策 receipts follow **Stop** tables. Other department: employee receipts in hand, hop actions done, then stop |

Break a rule → **stop or fail**.

## Read and run

1. Always read and run [references/rules.md](references/rules.md).
2. For **next** or **supervise**, read and run [references/supervise.md](references/supervise.md).
3. When supervise selects a department hop (3a / 3b / 3c / 3d / 3e), read and run [references/hops.md](references/hops.md).
4. Use [references/templates.md](references/templates.md) for duties, stop tables, hop selection, review disposition, department resume, and isolation.
5. When creating, merging, or removing ticket trees, read and run [references/worktree.md](references/worktree.md).

Whenever a department staffs an employee, read and run `engineering-routing`; do not directly wire or invoke lower-level skills. Research / datasheet reading → role `research` (`engineering-research`), staffable by any department's manage (rules.md 6, 18).
