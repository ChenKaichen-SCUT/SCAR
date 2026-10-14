# Stage18 与 LongContext 路径差异

这里比较的是 LongContext 完成第一章的路径，不是完整 mark 通关。跨方法只有一个随机模型样本，初始配方展示顺序未完全控制；路径比较为描述性证据。只有单独列出的同状态原生分支支持局部因果判断。

## 信息第一次出现

| 公开事实/事件首次出现 | Stage18 | STM | LongContext |
| --- | --- | --- | --- |
| 教程结束 | 31 | 28 | 28 |
| 向导主动提供任务提醒 | 32 | 31 | 31 |
| 制作 oak_rod 的主线指令 | 63 | 32 | 32 |
| oak_rod 由 oak_log 制作 | 21 | 18 | 18 |
| 精确配方 0.5 oak_log | 未出现 | 36 | 34 |
| 制作拒绝揭示缺少工作台 | 未出现 | 37 | 35 |
| library 地面可见 oak_log | 32 | 33 | 29 |
| hall 地面可见 workbench | 31 | 28 | 28 |
| 制作 copper_sword 的指令 | 未出现 | 41 | 39 |
| 前往图书管理员所在区域的指令 | 未出现 | 51 | 95 |
| 纸条需写 kindness | 未出现 | 52 | 96 |
| 前往 stalls 的指令 | 未出现 | 78 | 118 |
| 制作火把的指令 | 未出现 | 81 | 121 |
| 第一章完成事件 | 未出现 | 186 | 165 |
| 第二章介绍事件 | 未出现 | 186 | 165 |

教程已让 Stage18 在 a21 保存 oak_rod→oak_log 的配方名称关系，不能写成“oak_rod 配方完全不知道”。原公开名字关系没有精确数量，a63 NPC 所说需要 1 oak_log 也不能当作精确消耗 1。LongContext a34 拾取木材后得到 `oak_rod (0.5 oak_log)`；a35 制作失败公开缺少 workbench，再于 a36 回 hall、a37 制作、a38 拾取。Stage18 没有执行到这些经验。

## 关键分歧与反馈利用

| 阶段 | LongContext 实际行为 | Stage18 实际行为 | 证据范围 |
| --- | --- | --- | --- |
| 教程结束后找目标 | a31 获得向导提醒，a32 talk to remy | a32 获得提醒，a33/35 talk 提案被改回 hall；a63 才对话 | a33/35 同状态分支证实目标知识机会损失 |
| 切换到 oak_rod 制作 | a33 前往 library；a34 取材 | a64 library；a65/67 拾取受双手占用约束，实际回 hall | 模型原提案也不是当前可成功执行的拾取 |
| 发现工作台条件并恢复 | a35 制作被拒；a36 hall；a37 成功；a38 收取 | hall 工作台一直公开，但没有执行 oak_rod 制作 | a35→36 是首段明确反馈修正；不是首个全局错误消除证明 |
| 第一奖励后的新目标 | a39 NPC 提供 copper_sword 指令 | 没有第一奖励，未收到此下一阶段指令 | 不能把下游未披露当独立记忆丢失 |
| 容量/锁门绕过 | a52/53 重试锁门、a56 手满、a63–66 往返；a84 drop pen、a85 pick small_pouch_0，最后 a94 取得铜剑 | a40 起纸张与战利品占手；没有形成推进 oak_rod 的收纳/腾手路径 | LongContext 也有无效重复，不能只选其顺利片段 |
| 字词条件 | a96 得到 kindness，a104 写入 paper_0 | 从未收到该主线条件 | 属于下游信息未获得 |
| 第一章完成与剩余预算 | a165 累计 10 分；后续第二章仍未完成，a223–236 有拾取/丢弃循环 | a300 仍在最初阶段 | 不存在“长记忆解决全部长程任务”的证据 |

关键原文：[a32](关键证据原文.md#longcontextagent-a032), [a34](关键证据原文.md#longcontextagent-a034), [a35](关键证据原文.md#longcontextagent-a035), [a36](关键证据原文.md#longcontextagent-a036), [a37](关键证据原文.md#longcontextagent-a037), [a38](关键证据原文.md#longcontextagent-a038), [a39](关键证据原文.md#longcontextagent-a039), [a52](关键证据原文.md#longcontextagent-a052), [a53](关键证据原文.md#longcontextagent-a053), [a56](关键证据原文.md#longcontextagent-a056), [a84](关键证据原文.md#longcontextagent-a084), [a85](关键证据原文.md#longcontextagent-a085), [a94](关键证据原文.md#longcontextagent-a094), [a96](关键证据原文.md#longcontextagent-a096), [a104](关键证据原文.md#longcontextagent-a104), [a165](关键证据原文.md#longcontextagent-a165), [a223](关键证据原文.md#longcontextagent-a223), [a236](关键证据原文.md#longcontextagent-a236)。

“第一次调整目标”按可观察行为定义：a32 收到任务后，a33–38 转入相应取材、制作与收取；拿到第一奖励后 a39 寻求下一阶段。LongContext 没有单独 goal 字段，不能把行为判断冒充读到了内部目标变量。其全历史保存会让 a32 指令进入后续每次模型输入，但这不等同于模型每次都有效利用。

STM 提供重要对照：它也是 5 条短记忆，仍在 a35 drop pen 腾手，a37 得到工作台拒绝后 a38 回 hall，a40 取得 oak_rod；a44 收纳 paper_0、a45 拾 key、a46 解锁 armory，a50 获得铜剑。最终 a186 完成第一章。这反驳了“只要 STM5 就必然拿不到第一阶段奖励”的解释，尚不足以隔离控制器和额外提示的独立效应。

## 十次主线阶段奖励

| 累计主线奖励 | STM 动作/步骤 | LongContext 动作/步骤 |
| --- | --- | --- |
| 1 | a40 pick up oak_rod | a38 pick up oak_rod |
| 2 | a50 pick up copper_sword | a94 pick up copper_sword |
| 3 | a52 enter library | a96 enter library |
| 4 | a66 write kindness paper_0 | a104 write kindness paper_0 |
| 5 | a68 enter armory | a106 enter armory |
| 6 | a77 pick up key | a117 pick up key |
| 7 | a80 enter stalls | a120 enter stalls |
| 8 | a166 pick up torch | a131 pick up torch |
| 9 | a178 enter backstreets | a135 enter backstreets |
| 10 | a186 attack page_gnawer | a165 attack page_gnawer |

全部 20 次原始奖励事件连同完整反馈见 [quest_gain_events.json](../../results/stage22b/quest_gain_events.json)。Stage18 在 a1–300 无主线奖励事件；教程制作 key 的成功不计为这一主线目标进展。

## 保存、登记、进入模型是三件事

Stage18 第一次 oak_rod 指令在 a63 公开：a64 时它在当前 observation、表中 feedback 和后果暂存；a65–69 时在 STM5，a70 起这段原文在全部当时保存状态中找不到。a93 等后续对话再披露相同目标，但目标字段始终不变。a183 后原文进入持久 consequences 记录；例如 a200 的 `/controller/consequences/records/23/feedback` 仍含指令，却没有进入当次模型输入。

九次披露在 a63、93、123、153、183、211、243、270、277。a64–300 共 237 次后续决策中，明确原指令有 141 次仍在保存状态/当前观测，只有 54 次进入模型输入，87 次保存但未入上下文；另 96 次原文既不在保存状态也不在当前观测。结构化事实摘要中出现该明确指令为 0 次，当前目标登记 oak_rod 为 0 次。用原文路径匹配可重算这些计数；不把措辞改写或潜在语义当成可观察变量。

长期记忆并非唯一问题：公开配方名称关系持续登记，多个决策也确实看见任务指令，但控制器依然围绕 hall 仲裁。有效研究问题是“信息如何被登记成当前可执行目标，以及何时触发其使用”；本轮不实现新机制。
