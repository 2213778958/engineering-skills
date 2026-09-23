# engineering-skills

一组给智能体用的工程 skill。

规划、拆票、分活这几件，跟你用 Cursor、OpenHands 还是 Codex 无关。会碰到具体工具的只有两个：`openhands-sessions`、`openhands-watch`。以后要 Codex 版，按这两个的职责再写一对就行，前面那些不用动。

现在仓库里是 OpenHands 这一对。第一版，八个 skill。

## Skills

**engineering-init**
工程还没开始、或要把已有项目接进这套合同，用这个。它定目录嵌套、依赖、票怎么串，也管后来改合同。它不写产品代码。

**engineering-process**
合同立完了，用这个往下推。规划部门分票；交付、验收、仲裁、人工各干各的。不要拿它初始化。

**engineering-research**
各类调研：先查仓库资料，没有再上网；交付一份调研文档。

**engineering-routing**
先问这活留在当前会话、开一个子会话，还是交给 subagent。选好了再去调 sessions。不要让它改合同，也不要让它自己 POST。

**openhands-sessions**
跟 Agent Canvas 打交道：有哪些 profile、开会话、派子会话。规划分发、开会话都走它。换 Codex 的时候，换的就是这一层。

**openhands-watch**
看派出去的子会话是还在跑、挂了、还是结束了。规划分发本身不巡查。换 Codex 的时候，连这一层一起换。

**datasheet-headers**
从芯片数据手册里抽出寄存器头文件。不在当前会话打开 PDF，也不写驱动。

**skill-maker**
写 skill 或改 skill。只写步骤，不写理由。Cursor 和 OpenHands 目录各落一份相同的。

---

# engineering-skills

Agent skills for running an engineering job.

Planning, tickets, and routing do not care whether the agent is Cursor, OpenHands, or Codex. The only harness-specific pieces are `openhands-sessions` and `openhands-watch`. A Codex port is another pair with the same jobs; the rest stays.

This repo has the OpenHands pair. Eight skills, first version.

## Skills

**engineering-init**
Use this when the repo has no contract yet, or an existing project needs one. It sets the contains/uses graphs and the ticket net, and it patches that contract later. It does not implement product code.

**engineering-process**
Use this after init, to move tickets. Planning hands work to delivery, acceptance, arbitration, or a human. Do not use it to plan a new repo.

**engineering-research**
Researches a topic: repo sources first, then the web; delivers one research document.

**engineering-routing**
Decides stay / child conversation / subagent, then calls sessions. It does not change the contract and does not POST on its own.

**openhands-sessions**
Talks to Agent Canvas: list profiles, open a conversation, dispatch a child. Replace this file for Codex.

**openhands-watch**
Checks whether a dispatched child is alive, hung, or done. Planning does not watch after dispatch. Replace this file for Codex.

**datasheet-headers**
Turns a datasheet PDF into register headers. It does not open the PDF in this session and does not write drivers.

**skill-maker**
Writes or edits a skill. Commands only, no rationale. Same files under the Cursor skills dir and the OpenHands skills dir.
