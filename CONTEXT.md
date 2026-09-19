# engineering-skills

给智能体用的工程 skill 仓库。规划、拆票、分活跟具体工具无关；跟会话工具绑在一起的只有 sessions 和 watch。

## Language

### Product

**engineering-skills**:
一组开源的智能体工程 skill。第一版七个。个人机器上 Cursor 与 OpenHands 各装一份相同内容。
_Avoid_: skills-for-openhands-automation

**skill**:
一个可拷贝的目录，入口是 SKILL.md。

### Harness

**sessions**:
开会话、列 profile、派子会话的那一层。现在的实现是 openhands-sessions。
_Avoid_: 把整套工程 skill 写成某一个工具专用

**watch**:
看子会话是活着、卡住还是结束。现在的实现是 openhands-watch。

**harness adapter**:
sessions 加 watch。换 Codex 只换这一对。
