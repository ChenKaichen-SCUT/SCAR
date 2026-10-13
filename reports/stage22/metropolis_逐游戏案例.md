# metropolis：逐方法失败与进度证据

只分析该组合唯一一次真实轨迹。以下动作编号从 1 起；模型与环境随机分叉不是模块因果实验。

五局主线地点参数不完全配对，以下只作描述性比较。Stage18 在 a31 到达 7 分后停止新增奖励；LongContext 在 a167 到达 8 分后也停滞。NoMemory a300 制作 iron_bar 被原生拒绝，明确缺少当前位置的 statute_forge；STM a300 仍在处理背包物品；Voyager a300 的主线提示仍要求把 evidence dossier 送到 evidence_room，说明其 4 分不代表完成第一章全部交付。阶段分数、配方发现、实际取物和目标提交必须分开。SCAR a91 公开门锁变化未更新的局部问题另见控制器诊断。

SCAR 的同状态证据及明确的归因边界见 [控制器贡献与失败诊断](控制器贡献与失败诊断.md)。

## Stage18-Fixed

主线 7；辅助 4；动作 300；终止 `step_limit`；最后主线奖励在动作 31；其后 269 步未新增主线奖励。

制作动作 2，带成功制作反馈 1，材料拒绝 0；公开配方名称发现 25 类；控制器覆盖 220 次。发现数量不等于发现目标必要配方，不能仅由最终分数归因知识缺失。

主线奖励动作：

| 动作 | 执行 | 本步奖励 | 累计 |
| --- | --- | --- | --- |
| 2 | pick up evidence_dossier_0 | 1 | 1 |
| 4 | enter evidence_room | 1 | 2 |
| 27 | enter clerks_office | 2 | 4 |
| 31 | talk to archivist_lune | 3 | 7 |

最后十步：

| 动作 | 执行 | 累计主线 | 官方无效 |
| --- | --- | --- | --- |
| 291 | wait | 7 | False |
| 292 | enter lobby | 7 | False |
| 293 | wait | 7 | False |
| 294 | wait | 7 | False |
| 295 | wait | 7 | False |
| 296 | wait | 7 | False |
| 297 | wait | 7 | False |
| 298 | wait | 7 | False |
| 299 | wait | 7 | False |
| 300 | wait | 7 | False |

最后一步原始公开反馈（完整观测在轨迹中）：

```text
I waited for a while.

⚖️ SEVERE CONTEMPT OF COURT! The weight of the law bears down on me. My maximum health is reduced by 5 (total reduction: 10).
```

完整轨迹：`results/stage22/runs/metropolis__Stage18-Fixed/trajectory.jsonl.gz`；逐任务证据索引：`results/stage22/evidence.jsonl.gz`。

## NoMemoryAgent

主线 4；辅助 7；动作 300；终止 `step_limit`；最后主线奖励在动作 13；其后 287 步未新增主线奖励。

制作动作 5，带成功制作反馈 0，材料拒绝 0；公开配方名称发现 15 类；控制器覆盖 0 次。发现数量不等于发现目标必要配方，不能仅由最终分数归因知识缺失。

主线奖励动作：

| 动作 | 执行 | 本步奖励 | 累计 |
| --- | --- | --- | --- |
| 2 | pick up evidence_dossier_0 | 1 | 1 |
| 4 | enter clerks_office | 1 | 2 |
| 13 | talk to archivist_lune | 2 | 4 |

最后十步：

| 动作 | 执行 | 累计主线 | 官方无效 |
| --- | --- | --- | --- |
| 291 | pick up bailiff_eye | 4 | False |
| 292 | drop midnight_cipher_fragment | 4 | False |
| 293 | inspect midnight_cipher_fragment | 4 | False |
| 294 | enter lobby | 4 | False |
| 295 | talk to alex_smith | 4 | False |
| 296 | enter evidence_room | 4 | False |
| 297 | pick up midnight_cipher_fragment | 4 | False |
| 298 | inspect midnight_cipher_fragment | 4 | False |
| 299 | inspect iron_filings | 4 | False |
| 300 | craft 1 iron_bar | 4 | False |

最后一步原始公开反馈（完整观测在轨迹中）：

```text
Cannot craft iron_bar. Missing necessary statute_forge in the current area.
```

完整轨迹：`results/stage22/runs/metropolis__NoMemoryAgent/trajectory.jsonl.gz`；逐任务证据索引：`results/stage22/evidence.jsonl.gz`。

## ShortTermMemoryAgent

主线 4；辅助 10；动作 300；终止 `step_limit`；最后主线奖励在动作 7；其后 293 步未新增主线奖励。

制作动作 6，带成功制作反馈 0，材料拒绝 1；公开配方名称发现 30 类；控制器覆盖 0 次。发现数量不等于发现目标必要配方，不能仅由最终分数归因知识缺失。

主线奖励动作：

| 动作 | 执行 | 本步奖励 | 累计 |
| --- | --- | --- | --- |
| 2 | pick up evidence_dossier_0 | 1 | 1 |
| 4 | enter evidence_room | 1 | 2 |
| 7 | talk to archivist_lune | 2 | 4 |

最后十步：

| 动作 | 执行 | 累计主线 | 官方无效 |
| --- | --- | --- | --- |
| 291 | talk to clerk_aldiss | 4 | False |
| 292 | inspect docket_satchel_0 | 4 | False |
| 293 | store 5 writ_token docket_satchel_0 | 4 | False |
| 294 | wait | 4 | False |
| 295 | inspect docket_satchel_0 | 4 | False |
| 296 | talk to archivist_lune | 4 | False |
| 297 | store 1 statute_shard docket_satchel_0 | 4 | False |
| 298 | discard 1 gavel_timber | 4 | True |
| 299 | store 1 gavel_timber docket_satchel_0 | 4 | False |
| 300 | discard 1 gavel_timber docket_satchel_0 | 4 | False |

最后一步原始公开反馈（完整观测在轨迹中）：

```text
I discarded 1 gavel_timber from docket_satchel_0.
```

完整轨迹：`results/stage22/runs/metropolis__ShortTermMemoryAgent/trajectory.jsonl.gz`；逐任务证据索引：`results/stage22/evidence.jsonl.gz`。

## LongContextAgent

主线 8；辅助 11；动作 300；终止 `step_limit`；最后主线奖励在动作 167；其后 133 步未新增主线奖励。

制作动作 3，带成功制作反馈 0，材料拒绝 0；公开配方名称发现 16 类；控制器覆盖 0 次。发现数量不等于发现目标必要配方，不能仅由最终分数归因知识缺失。

主线奖励动作：

| 动作 | 执行 | 本步奖励 | 累计 |
| --- | --- | --- | --- |
| 2 | enter clerks_office | 1 | 1 |
| 3 | talk to archivist_lune | 2 | 3 |
| 5 | pick up evidence_dossier_0 | 1 | 4 |
| 166 | drop evidence_dossier_0 | 3 | 7 |
| 167 | talk to alex_smith | 1 | 8 |

最后十步：

| 动作 | 执行 | 累计主线 | 官方无效 |
| --- | --- | --- | --- |
| 291 | drop gavel_timber | 8 | False |
| 292 | pick up gavel_timber | 8 | False |
| 293 | drop gavel_timber | 8 | False |
| 294 | pick up gavel_timber | 8 | False |
| 295 | drop gavel_timber | 8 | False |
| 296 | pick up gavel_timber | 8 | False |
| 297 | drop gavel_timber | 8 | False |
| 298 | enter evidence_room | 8 | False |
| 299 | enter lobby | 8 | False |
| 300 | store 1 legal_brief_3 docket_satchel_0 | 8 | False |

最后一步原始公开反馈（完整观测在轨迹中）：

```text
I stored 1 legal_brief_3 in docket_satchel_0.
```

完整轨迹：`results/stage22/runs/metropolis__LongContextAgent/trajectory.jsonl.gz`；逐任务证据索引：`results/stage22/evidence.jsonl.gz`。

## VoyagerAgent

主线 4；辅助 4；动作 300；终止 `step_limit`；最后主线奖励在动作 48；其后 252 步未新增主线奖励。

制作动作 1，带成功制作反馈 0，材料拒绝 0；公开配方名称发现 4 类；控制器覆盖 0 次。发现数量不等于发现目标必要配方，不能仅由最终分数归因知识缺失。

主线奖励动作：

| 动作 | 执行 | 本步奖励 | 累计 |
| --- | --- | --- | --- |
| 2 | pick up evidence_dossier_0 | 1 | 1 |
| 4 | enter evidence_room | 1 | 2 |
| 48 | talk to archivist_lune | 2 | 4 |

最后十步：

| 动作 | 执行 | 累计主线 | 官方无效 |
| --- | --- | --- | --- |
| 291 | enter lobby | 4 | False |
| 292 | talk to alex_smith | 4 | False |
| 293 | pick up evidence_dossier | 4 | False |
| 294 | talk to alex_smith | 4 | False |
| 295 | pick up evidence dossier | 4 | True |
| 296 | pick up evidence_dossier | 4 | False |
| 297 | talk to alex_smith | 4 | False |
| 298 | talk to alex_smith | 4 | False |
| 299 | talk to alex_smith | 4 | False |
| 300 | talk to alex_smith | 4 | False |

最后一步原始公开反馈（完整观测在轨迹中）：

```text
I talked to alex_smith.
alex_smith says: Main goal: Uncover the first evidence of legal tampering in the Central Courthouse.

Current tasks:
[1] Bring the evidence dossier to the evidence room to begin cataloguing proof.
```

完整轨迹：`results/stage22/runs/metropolis__VoyagerAgent/trajectory.jsonl.gz`；逐任务证据索引：`results/stage22/evidence.jsonl.gz`。
