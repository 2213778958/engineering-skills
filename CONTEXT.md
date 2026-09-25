# engineering-skills

给智能体用的工程 skill 仓库。规划、拆票、分活跟具体工具无关；跟会话工具绑在一起的只有 sessions 和 watch。

## Language

### Product

**engineering-skills**:
一组开源的智能体工程 skill。第一版九个。个人机器上 Cursor 与 OpenHands 各装一份相同内容。
_Avoid_: skills-for-openhands-automation

**skill**:
一个可拷贝的目录，入口是 SKILL.md。

### Process terms

skill 正文全英文；三个入口 skill（engineering-process、engineering-routing、engineering-init）各有一张 `## Terms` 表，中文只留在 frontmatter 触发词和引用的用户原话里。

**分发** = hand off（规划部门把一张票交给另一个部门；名词 handoff）。
**决策** = decide（规划部门自己的 hop）。
**推进** = advance。
**职责表** = duty table。
**回传** = report back。
**开会话** = open a session。
_Avoid_: 把分发译成 dispatch（dispatch 是路由的派发方式，不是流程术语）

**用户意图**:
判定条件是用户想做什么，不是用户的原话。正文用英文写意图，原话只放在 `(e.g. …)` 里当例子，可中英混。意图不明 → 能跟用户对话的一方追问，其他人上报 `Missing: decision`。

**验收守卫**:
`engineering-process/scripts/check_acceptance.py`。`pre` 在开 PR 前查范围内每张实现票的分支都在合并头里、没有范围外提交；`post` 在合并后、关票前查这些分支都已进入默认分支。只用 merge commit 合并。

### Harness

**sessions**:
开会话、列 profile、派子会话的那一层。现在的实现是 openhands-sessions。
_Avoid_: 把整套工程 skill 写成某一个工具专用

**watch**:
看子会话是活着、卡住还是结束。现在的实现是 openhands-watch。

**harness adapter**:
sessions 加 watch。换 Codex 只换这一对。

**engineering-research** (调研入口):
员工角色 `research` 的技能。每次交付一个调研目录 `research:<YYYY-MM>-<slug>/`，从其 `<slug>.md` 进入；调研库 `research/` 与原始资料库 `resources/` 都在 `master/` 同层、代码仓库之外（`research/` 可以是 GitHub Wiki 仓库）。先查本仓库资料库（`docs/`、`docs/adr/`、模块代码），再查 `research/` 与 `resources/`，没有的再查互联网；数据手册是其中一种调研面，头文件由下游 delivery implement 按调研结论写。
