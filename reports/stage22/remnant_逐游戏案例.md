# remnant：逐方法失败与进度证据

只分析该组合唯一一次真实轨迹。以下动作编号从 1 起；模型与环境随机分叉不是模块因果实验。

五方法均只有 1 个主线奖励，说明本游戏对本批所有方法都形成瓶颈。Stage18 的旧目标和 wait 问题见控制器诊断。对照的末期证据也不能忽略：NoMemory a300 使用带数量的 pick up，原生报格式错误；STM a300 战斗死亡并丢失物品；LongContext a300 进入黑暗的 armory；Voyager a300 检查空纸且处于黑暗。a271–300 内 Voyager 13 次 talk to chronicler_lyra，LongContext 13 次 defend，说明它们同样没有继续兑现主线。不能仅由黑暗或死亡断言某一记忆模块是根因。

SCAR 的同状态证据及明确的归因边界见 [控制器贡献与失败诊断](控制器贡献与失败诊断.md)。

## Stage18-Fixed

主线 1；辅助 5；动作 300；终止 `step_limit`；最后主线奖励在动作 36；其后 264 步未新增主线奖励。

制作动作 1，带成功制作反馈 1，材料拒绝 0；公开配方名称发现 16 类；控制器覆盖 179 次。发现数量不等于发现目标必要配方，不能仅由最终分数归因知识缺失。

主线奖励动作：

| 动作 | 执行 | 本步奖励 | 累计 |
| --- | --- | --- | --- |
| 36 | enter library | 1 | 1 |

最后十步：

| 动作 | 执行 | 累计主线 | 官方无效 |
| --- | --- | --- | --- |
| 291 | wait | 1 | False |
| 292 | wait | 1 | False |
| 293 | wait | 1 | False |
| 294 | enter library | 1 | False |
| 295 | enter hall | 1 | False |
| 296 | wait | 1 | False |
| 297 | wait | 1 | False |
| 298 | wait | 1 | False |
| 299 | wait | 1 | False |
| 300 | wait | 1 | False |

最后一步原始公开反馈（完整观测在轨迹中）：

```text
I waited for a while.
I was attacked by goblin_warrior_18 and lost 1 HP.
```

完整轨迹：`results/stage22/runs/remnant__Stage18-Fixed/trajectory.jsonl.gz`；逐任务证据索引：`results/stage22/evidence.jsonl.gz`。

## NoMemoryAgent

主线 1；辅助 8；动作 300；终止 `step_limit`；最后主线奖励在动作 32；其后 268 步未新增主线奖励。

制作动作 5，带成功制作反馈 1，材料拒绝 3；公开配方名称发现 12 类；控制器覆盖 0 次。发现数量不等于发现目标必要配方，不能仅由最终分数归因知识缺失。

主线奖励动作：

| 动作 | 执行 | 本步奖励 | 累计 |
| --- | --- | --- | --- |
| 32 | enter library | 1 | 1 |

最后十步：

| 动作 | 执行 | 累计主线 | 官方无效 |
| --- | --- | --- | --- |
| 291 | attack goblin_warrior_30 | 1 | False |
| 292 | pick up 10 coin | 1 | True |
| 293 | attack goblin_warrior_33 | 1 | False |
| 294 | attack goblin_warrior_33 | 1 | False |
| 295 | pick up 10 coin | 1 | True |
| 296 | write quiet paper_7 | 1 | False |
| 297 | pick up pen | 1 | False |
| 298 | craft 1 paper_7 | 1 | False |
| 299 | attack goblin_warrior_34 | 1 | False |
| 300 | pick up 10 coin | 1 | True |

最后一步原始公开反馈（完整观测在轨迹中）：

```text
Invalid action. Action 'pick up' requires the format 'pick up <object_name>', but got 2 parameter(s).
Default to wait.
```

完整轨迹：`results/stage22/runs/remnant__NoMemoryAgent/trajectory.jsonl.gz`；逐任务证据索引：`results/stage22/evidence.jsonl.gz`。

## ShortTermMemoryAgent

主线 1；辅助 4；动作 300；终止 `step_limit`；最后主线奖励在动作 32；其后 268 步未新增主线奖励。

制作动作 8，带成功制作反馈 2，材料拒绝 2；公开配方名称发现 25 类；控制器覆盖 0 次。发现数量不等于发现目标必要配方，不能仅由最终分数归因知识缺失。

主线奖励动作：

| 动作 | 执行 | 本步奖励 | 累计 |
| --- | --- | --- | --- |
| 32 | enter library | 1 | 1 |

最后十步：

| 动作 | 执行 | 累计主线 | 官方无效 |
| --- | --- | --- | --- |
| 291 | enter hall | 1 | False |
| 292 | enter armory | 1 | False |
| 293 | enter plain | 1 | False |
| 294 | enter hall | 1 | False |
| 295 | talk to daniel_cross | 1 | False |
| 296 | enter library | 1 | False |
| 297 | enter hall | 1 | False |
| 298 | talk to daniel_cross | 1 | False |
| 299 | craft 1 lockpick | 1 | False |
| 300 | attack goblin_warrior_1 | 1 | False |

最后一步原始公开反馈（完整观测在轨迹中）：

```text
I attacked goblin_warrior_1 for 10 damage. goblin_warrior_1 has 1 HP remaining.
goblin_warrior_1 has engaged in combat.
goblin_warrior_1 is attacking.
I was attacked by goblin_warrior_1 and lost 22 HP.
I have been defeated by goblin_warrior_1!
I have died.
I revived at the starting point with full health but lost all items in hand, equipped items, and inventory items at the place I died.
```

完整轨迹：`results/stage22/runs/remnant__ShortTermMemoryAgent/trajectory.jsonl.gz`；逐任务证据索引：`results/stage22/evidence.jsonl.gz`。

## LongContextAgent

主线 1；辅助 3；动作 300；终止 `step_limit`；最后主线奖励在动作 33；其后 267 步未新增主线奖励。

制作动作 1，带成功制作反馈 1，材料拒绝 0；公开配方名称发现 18 类；控制器覆盖 0 次。发现数量不等于发现目标必要配方，不能仅由最终分数归因知识缺失。

主线奖励动作：

| 动作 | 执行 | 本步奖励 | 累计 |
| --- | --- | --- | --- |
| 33 | enter library | 1 | 1 |

最后十步：

| 动作 | 执行 | 累计主线 | 官方无效 |
| --- | --- | --- | --- |
| 291 | enter hall | 1 | False |
| 292 | store 2 coin small_satchel_0 | 1 | False |
| 293 | defend | 1 | False |
| 294 | defend | 1 | False |
| 295 | take out cloth small_satchel_0 | 1 | False |
| 296 | defend | 1 | False |
| 297 | enter armory | 1 | False |
| 298 | enter hall | 1 | False |
| 299 | defend | 1 | False |
| 300 | enter armory | 1 | False |

最后一步原始公开反馈（完整观测在轨迹中）：

```text
I entered armory.
It is too dark to see anything here.
```

完整轨迹：`results/stage22/runs/remnant__LongContextAgent/trajectory.jsonl.gz`；逐任务证据索引：`results/stage22/evidence.jsonl.gz`。

## VoyagerAgent

主线 1；辅助 6；动作 300；终止 `step_limit`；最后主线奖励在动作 63；其后 237 步未新增主线奖励。

制作动作 7，带成功制作反馈 1，材料拒绝 0；公开配方名称发现 7 类；控制器覆盖 0 次。发现数量不等于发现目标必要配方，不能仅由最终分数归因知识缺失。

主线奖励动作：

| 动作 | 执行 | 本步奖励 | 累计 |
| --- | --- | --- | --- |
| 63 | enter library | 1 | 1 |

最后十步：

| 动作 | 执行 | 累计主线 | 官方无效 |
| --- | --- | --- | --- |
| 291 | enter library | 1 | False |
| 292 | enter hall | 1 | False |
| 293 | enter library | 1 | False |
| 294 | enter hall | 1 | False |
| 295 | enter library | 1 | False |
| 296 | enter hall | 1 | False |
| 297 | pick up paper_7 | 1 | False |
| 298 | inspect paper_7 | 1 | False |
| 299 | enter library | 1 | False |
| 300 | inspect paper_7 | 1 | False |

最后一步原始公开反馈（完整观测在轨迹中）：

```text
I inspected paper_7: A clean sheet meant to hold short messages.
It can be used to craft: None.
It has nothing written on it.
It is too dark to see anything here.
```

完整轨迹：`results/stage22/runs/remnant__VoyagerAgent/trajectory.jsonl.gz`；逐任务证据索引：`results/stage22/evidence.jsonl.gz`。
