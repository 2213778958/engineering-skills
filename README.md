# engineering-skills

一组给智能体用的工程 skill。

规划、拆票、分活这几件，跟你用 Cursor、OpenHands 还是 Codex 无关。会碰到具体工具的只有两个：`openhands-sessions`、`openhands-watch`。以后要 Codex 版，按这两个的职责再写一对就行，前面那些不用动。

现在仓库里是 OpenHands 这一对。第一版，九个 skill。判断用户要什么看意图，不看原话；原话只当例子。

## Skills

**engineering-init**
工程还没开始、或要把已有项目接进这套合同，用这个。它定目录嵌套、依赖、票怎么串，也管后来改合同。它不写产品代码。

**engineering-process**
合同立完了，用这个往下推。规划部门分票；交付、验收、仲裁、人工各干各的。验收合并前后都跑 `check_acceptance.py`（`pre` 查分支是否齐全、有没有范围外提交，`post` 查是否都进了默认分支），只用 merge commit 合并。不要拿它初始化。

**engineering-routing**
先问这活留在当前会话、开一个子会话，还是交给 subagent。选好了再去调 sessions。不要让它改合同，也不要让它自己 POST。

**engineering-sessions**
按仓库的 sessions 锁存选出会话适配器，再去读它、跑它。其他工程 skill 要开会话、派子会话、通知父会话、派员工时都经过它。

**engineering-watch**
按需查看派出去的部门子会话：活着、卡住、结束且已通知、结束但没通知、收尾失败。只在有人要看时跑，不自动循环。

**openhands-sessions**
跟 Agent Canvas 打交道：有哪些 profile、开会话、派子会话。规划分发、开会话都走它。换 Codex 的时候，换的就是这一层。

**openhands-watch**
看派出去的子会话是还在跑、挂了、还是结束了。规划分发本身不巡查。换 Codex 的时候，连这一层一起换。

**engineering-research**
调研员工：把一个需求变成外置调研库 `research/` 下的一个调研目录，从其中的 `<slug>.md` 进入。它把需求拆成若干调研面（先行方案、素材、技术选型、数据手册芯片接口），先查仓库自己的资料、再上网补缺，最后合成一份交叉核对过的结论。`research/` 与原始资料库 `resources/` 都放在与 `master/`、`worktree/` 同层，不进代码仓库；`research/` 可以 clone 成项目的 GitHub Wiki 用于协同，清单在 `research:resources.md`。不在当前会话打开 PDF，不写头文件，也不写驱动。

**skill-maker**
写 skill 或改 skill。只写步骤，不写理由。Cursor 和 OpenHands 目录各落一份相同的。

---

# engineering-skills

Agent skills for running an engineering job.

Planning, tickets, and routing do not care whether the agent is Cursor, OpenHands, or Codex. The only harness-specific pieces are `openhands-sessions` and `openhands-watch`. A Codex port is another pair with the same jobs; the rest stays.

This repo has the OpenHands pair. Nine skills, first version. What the user wants is judged by intent, not wording; phrases are only examples.

## Skills

**engineering-init**
Use this when the repo has no contract yet, or an existing project needs one. It sets the contains/uses graphs and the ticket net, and it patches that contract later. It does not implement product code.

**engineering-process**
Use this after init, to move tickets. Planning hands work to delivery, acceptance, arbitration, or a human. Acceptance runs `check_acceptance.py` before the PR (`pre`: every ticket branch is in, nothing out of scope) and after the merge (`post`: every branch reached the default branch), and merges with a merge commit only. Do not use it to plan a new repo.

**engineering-routing**
Decides stay / child conversation / subagent, then calls sessions. It does not change the contract and does not POST on its own.

**engineering-sessions**
Picks the repo's sessions adapter from its sessions latch, then reads and runs it. Other engineering skills go through it to open or dispatch a conversation, notify a parent, or delegate an employee.

**engineering-watch**
Inspects dispatched department children on demand: alive, hung, terminal and notified, terminal without notify, or finalization failed. Runs only when someone asks; never a loop.

**openhands-sessions**
Talks to Agent Canvas: list profiles, open a conversation, dispatch a child. Replace this file for Codex.

**openhands-watch**
Checks whether a dispatched child is alive, hung, or done. Planning does not watch after a handoff. Replace this file for Codex.

**engineering-research**
A research employee: turns one requirement into one research directory in the external `research/` library, entered through its `<slug>.md`. It splits the requirement into faces (approaches, assets, options, datasheet chip interfaces), researches them repo library first and the web only for gaps, and synthesizes one cross-checked answer. Both `research/` and the raw-material library `resources/` sit beside `master/` and `worktree/`, outside the code repo; `research/` may be a clone of the project's GitHub Wiki for collaboration; raw files are listed in `research:resources.md`. It does not open PDFs in this session and does not write headers or drivers.

**skill-maker**
Writes or edits a skill. Commands only, no rationale. Same files under the Cursor skills dir and the OpenHands skills dir.
