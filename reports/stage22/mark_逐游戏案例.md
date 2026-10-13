# mark：逐方法失败与进度证据

只分析该组合唯一一次真实轨迹。以下动作编号从 1 起；模型与环境随机分叉不是模块因果实验。

Stage18 与 NoMemory 主线均为 0，STM/LongContext 为 10，Voyager 为 3；这些都是阶段奖励，均未完成整个主线。Stage18 的教程数量覆盖与目标滞留具有逐步证据。STM/LongContext 的最后主线奖励在 a186/a165，随后也没有终局完成；a271–300 中 LongContext 反复 take out/store fiber_bundle，Voyager 11 次 equip copper_sword、8 次 talk to librarian_rowan，a300 仍收到人物自我介绍。不能把它们的高于 SCAR 得分夸大为游戏成功或普遍避免重复。

SCAR 的同状态证据及明确的归因边界见 [控制器贡献与失败诊断](控制器贡献与失败诊断.md)。

## Stage18-Fixed

主线 0；辅助 3；动作 300；终止 `step_limit`；最后主线奖励在动作 None；其后 300 步未新增主线奖励。

制作动作 1，带成功制作反馈 1，材料拒绝 0；公开配方名称发现 11 类；控制器覆盖 214 次。发现数量不等于发现目标必要配方，不能仅由最终分数归因知识缺失。

最后十步：

| 动作 | 执行 | 累计主线 | 官方无效 |
| --- | --- | --- | --- |
| 291 | wait | 0 | False |
| 292 | wait | 0 | False |
| 293 | wait | 0 | False |
| 294 | wait | 0 | False |
| 295 | wait | 0 | False |
| 296 | wait | 0 | False |
| 297 | wait | 0 | False |
| 298 | wait | 0 | False |
| 299 | wait | 0 | False |
| 300 | wait | 0 | False |

最后一步原始公开反馈（完整观测在轨迹中）：

```text
I waited for a while.
```

完整轨迹：`results/stage22/runs/mark__Stage18-Fixed/trajectory.jsonl.gz`；逐任务证据索引：`results/stage22/evidence.jsonl.gz`。

## NoMemoryAgent

主线 0；辅助 9；动作 300；终止 `step_limit`；最后主线奖励在动作 None；其后 300 步未新增主线奖励。

制作动作 14，带成功制作反馈 1，材料拒绝 2；公开配方名称发现 13 类；控制器覆盖 0 次。发现数量不等于发现目标必要配方，不能仅由最终分数归因知识缺失。

最后十步：

| 动作 | 执行 | 累计主线 | 官方无效 |
| --- | --- | --- | --- |
| 291 | talk to librarian_rowan | 0 | False |
| 292 | eat bread | 0 | False |
| 293 | pick up oak_log | 0 | False |
| 294 | craft 1 oak_rod | 0 | False |
| 295 | talk to librarian_rowan | 0 | False |
| 296 | talk to lydia_rowe | 0 | False |
| 297 | pick up oak_log | 0 | False |
| 298 | talk to librarian_rowan | 0 | False |
| 299 | pick up oak_log | 0 | False |
| 300 | drop oak_log | 0 | False |

最后一步原始公开反馈（完整观测在轨迹中）：

```text
I dropped oak_log.
```

完整轨迹：`results/stage22/runs/mark__NoMemoryAgent/trajectory.jsonl.gz`；逐任务证据索引：`results/stage22/evidence.jsonl.gz`。

## ShortTermMemoryAgent

主线 10；辅助 21；动作 300；终止 `step_limit`；最后主线奖励在动作 186；其后 114 步未新增主线奖励。

制作动作 15，带成功制作反馈 6，材料拒绝 0；公开配方名称发现 21 类；控制器覆盖 0 次。发现数量不等于发现目标必要配方，不能仅由最终分数归因知识缺失。

主线奖励动作：

| 动作 | 执行 | 本步奖励 | 累计 |
| --- | --- | --- | --- |
| 40 | pick up oak_rod | 1 | 1 |
| 50 | pick up copper_sword | 1 | 2 |
| 52 | enter library | 1 | 3 |
| 66 | write kindness paper_0 | 1 | 4 |
| 68 | enter armory | 1 | 5 |
| 77 | pick up key | 1 | 6 |
| 80 | enter stalls | 1 | 7 |
| 166 | pick up torch | 1 | 8 |
| 178 | enter backstreets | 1 | 9 |
| 186 | attack page_gnawer | 1 | 10 |

最后十步：

| 动作 | 执行 | 累计主线 | 官方无效 |
| --- | --- | --- | --- |
| 291 | pick up copper_bar | 10 | False |
| 292 | pick up coal_chunk | 10 | False |
| 293 | enter hall | 10 | False |
| 294 | attack scrap_goblin_8 | 10 | False |
| 295 | attack scrap_goblin_19 | 10 | False |
| 296 | enter library | 10 | False |
| 297 | attack scrap_goblin_27 | 10 | False |
| 298 | attack scrap_goblin_17 | 10 | False |
| 299 | attack scrap_goblin_30 | 10 | False |
| 300 | talk to librarian_rowan | 10 | False |

最后一步原始公开反馈（完整观测在轨迹中）：

```text
I talked to librarian_rowan.
librarian_rowan says: I'm A quiet librarian who watches hands more than faces.
```

完整轨迹：`results/stage22/runs/mark__ShortTermMemoryAgent/trajectory.jsonl.gz`；逐任务证据索引：`results/stage22/evidence.jsonl.gz`。

## LongContextAgent

主线 10；辅助 14；动作 300；终止 `step_limit`；最后主线奖励在动作 165；其后 135 步未新增主线奖励。

制作动作 13，带成功制作反馈 8，材料拒绝 4；公开配方名称发现 18 类；控制器覆盖 0 次。发现数量不等于发现目标必要配方，不能仅由最终分数归因知识缺失。

主线奖励动作：

| 动作 | 执行 | 本步奖励 | 累计 |
| --- | --- | --- | --- |
| 38 | pick up oak_rod | 1 | 1 |
| 94 | pick up copper_sword | 1 | 2 |
| 96 | enter library | 1 | 3 |
| 104 | write kindness paper_0 | 1 | 4 |
| 106 | enter armory | 1 | 5 |
| 117 | pick up key | 1 | 6 |
| 120 | enter stalls | 1 | 7 |
| 131 | pick up torch | 1 | 8 |
| 135 | enter backstreets | 1 | 9 |
| 165 | attack page_gnawer | 1 | 10 |

最后十步：

| 动作 | 执行 | 累计主线 | 官方无效 |
| --- | --- | --- | --- |
| 291 | take out fiber_bundle inventory | 10 | False |
| 292 | drop copper_sword | 10 | False |
| 293 | take out fiber_bundle inventory | 10 | False |
| 294 | pick up copper_sword | 10 | False |
| 295 | attack cave_chitter_3 | 10 | False |
| 296 | enter hall | 10 | False |
| 297 | pick up fiber_bundle | 10 | False |
| 298 | drop copper_sword | 10 | False |
| 299 | pick up fiber_bundle | 10 | False |
| 300 | drop fiber_bundle | 10 | False |

最后一步原始公开反馈（完整观测在轨迹中）：

```text
I dropped fiber_bundle.
```

完整轨迹：`results/stage22/runs/mark__LongContextAgent/trajectory.jsonl.gz`；逐任务证据索引：`results/stage22/evidence.jsonl.gz`。

## VoyagerAgent

主线 3；辅助 7；动作 300；终止 `step_limit`；最后主线奖励在动作 109；其后 191 步未新增主线奖励。

制作动作 13，带成功制作反馈 3，材料拒绝 9；公开配方名称发现 13 类；控制器覆盖 0 次。发现数量不等于发现目标必要配方，不能仅由最终分数归因知识缺失。

主线奖励动作：

| 动作 | 执行 | 本步奖励 | 累计 |
| --- | --- | --- | --- |
| 40 | pick up oak_rod | 1 | 1 |
| 95 | pick up copper_sword | 1 | 2 |
| 109 | enter library | 1 | 3 |

最后十步：

| 动作 | 执行 | 累计主线 | 官方无效 |
| --- | --- | --- | --- |
| 291 | equip copper_sword | 3 | False |
| 292 | defend | 3 | False |
| 293 | equip copper_sword | 3 | False |
| 294 | talk to librarian_rowan | 3 | False |
| 295 | equip copper_sword | 3 | False |
| 296 | talk to librarian_rowan | 3 | False |
| 297 | equip copper_sword | 3 | False |
| 298 | inspect copper_sword | 3 | False |
| 299 | equip copper_sword | 3 | False |
| 300 | talk to librarian_rowan | 3 | False |

最后一步原始公开反馈（完整观测在轨迹中）：

```text
I talked to librarian_rowan.
librarian_rowan says: I'm A quiet librarian who watches hands more than faces.
```

完整轨迹：`results/stage22/runs/mark__VoyagerAgent/trajectory.jsonl.gz`；逐任务证据索引：`results/stage22/evidence.jsonl.gz`。
