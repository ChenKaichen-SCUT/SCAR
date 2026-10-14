# State Sufficiency Test

| 范围 | 配对数 | A 接受 | B 接受 | B−A（百分点） | 双方接受 / 仅 A / 仅 B / 均不接受 |
|---|---|---|---|---|---|
| all | 334 | 281 | 275 | -1.80 | 245 / 36 / 30 / 23 |
| parent | 34 | 31 | 27 | -11.76 | 26 / 5 / 1 / 2 |
| branches | 300 | 250 | 248 | -0.67 | 219 / 31 / 29 / 21 |


## 首步原生反馈

| 首步指标 | A | B |
|---|---|---|
| syntax_valid | 330 | 327 |
| accepted | 281 | 275 |
| native_rejection | 49 | 52 |
| trigger_repeat_rejected | 0 | 0 |
| past_failed_action_rejected | 11 | 4 |
| new_public_state | 123 | 125 |
| new_information | 237 | 252 |
| new_area | 1 | 1 |
| accepted_held_gain | 32 | 27 |
| accepted_noncombat_information | 130 | 135 |
| progress_proxy | 155 | 157 |
| main_reward | 0 | 0 |
| death | 6 | 3 |


`accepted` 的分母包含不可解析/非法提案；`past_failed_action_rejected` 只数重复历史失败动作且本次仍被拒绝，不把条件改变后的成功重试误判成错误。`new_public_state` 使用既有公开状态签名（最多记 256 个）；新状态不等于主线推进。`accepted_held_gain` 只数手持净增加，不包括容器内不可见增加；`progress_proxy` 是接受且手持增加/新区域/新的非战斗反馈之一，仍可能只是局部操作。

| 失败类型 | n | A 接受 | B 接受 | B−A pp |
|---|---|---|---|---|
| combat_blocks_exit | 31 | 30 | 29 | -3.23 |
| container_capacity | 15 | 12 | 13 | +6.67 |
| container_nesting | 9 | 8 | 8 | +0.00 |
| equipment_slot_occupied | 4 | 3 | 2 | -25.00 |
| hand_capacity | 114 | 98 | 94 | -3.51 |
| insufficient_ingredients | 30 | 22 | 20 | -6.67 |
| locked_exit | 26 | 23 | 22 | -3.85 |
| missing_furnace | 1 | 1 | 0 | -100.00 |
| missing_lockpick_tool | 5 | 4 | 4 | +0.00 |
| missing_workbench | 7 | 6 | 7 | +14.29 |
| missing_writing_tool | 19 | 13 | 13 | +0.00 |
| no_path | 5 | 5 | 5 | +0.00 |
| not_craftable | 4 | 4 | 4 | +0.00 |
| not_edible | 1 | 1 | 0 | -100.00 |
| not_equippable | 20 | 17 | 16 | -5.00 |
| not_writable | 7 | 5 | 6 | +14.29 |
| object_not_held_or_visible | 12 | 10 | 11 | +8.33 |
| object_unavailable | 10 | 9 | 9 | +0.00 |
| target_not_held | 10 | 7 | 9 | +20.00 |
| unknown_object | 3 | 2 | 2 | +0.00 |
| unspecified_rejection | 1 | 1 | 1 | +0.00 |


## 三步恢复

| 母轨迹三步指标 | A | B |
|---|---|---|
| n | 34 | 34 |
| turns | 102 | 102 |
| executed | 101 | 101 |
| accepted | 89 | 78 |
| rejections | 12 | 23 |
| invalid | 1 | 1 |
| all_three_accepted | 23 | 17 |
| any_main | 2 | 2 |
| main_reward | 2 | 2 |
| original_action_retry_success | 7 | 5 |


短链只针对原定母轨迹 34 个检查点；没有根据首步结果挑选继续。失败/非法回答不重采样。A 与 B 的差异有正有负，完整 334 对表在 `results/stage27/paired_comparison.csv`，完整动作、理由、状态和奖励在各 `probes/*/[AB]/result.json`。

## 目标一致性

全部 668 个首步输出的原目标、新目标、理由与证据可核验性保存于 `action_quality.csv`。引文命中只能证明引用来自公开文本，不能自动证明目标合理。

母轨迹 68 个首步目标另外做语义复核，结果：

| 目标判断 | A | B |
|---|---|---|
| maintained_supported_goal | 32 | 30 |
| supported_adjustment | 1 | 3 |
| uncertain_or_partly_satisfied | 1 | 1 |


临时从采集转为存活/战斗有现实攻击支持；目标保持合理仍可伴随动作错误。a260 健康已为 100，继续恢复健康的必要性不足，但耐力信息不充分，保留“部分已满足/不确定”，不武断判整体目标失效。其余分支目标提供逐条输出与引文核验，不冒充全部完成独立语义标注。

## 解释边界

这是 1 条母轨迹及其 10 条相关分支的条件化诊断，不是 336 个独立任务。无显著性或跨游戏优劣结论。

实验一提供显式失败反馈并要求解释；它测可被提示激发的解释能力，不等于行动前预测能力。规则评分核验直接原因和恢复条件，不证明自由文本每句推理都正确；没有独立人类评审者一致性统计。

B 的静态补充有明确限度：`known_requirements` 主要整理公开拒绝，未穷举所有成功拾取时公开的制作配方；`known_tools` 是含 tool/workbench/furnace 的原始引文集合，不是已验证工具本体。它保留历史事实并警示可能过期，没有实现状态失效更新。它还增加历史覆盖和输入长度。因此结论限于这份预登记的补充，不能据此排除更完整状态表示的价值，更不能把负结果解释为 State Grounding 在任何实现上无用。

A 首次请求与保存请求逐字一致；三步短链的后续请求追加自身真实反馈，已不是历史原请求。两组均用原始提案直接原生验证，未运行 AGC 仲裁，因此这不是 AGC-v2 新版本成绩。当前目标以原 schema 的 goal_description 与理由记录。

相同初始状态和环境 RNG 可以核验局部可行性；供应商模型采样没有可控配对 seed，不能把每次分叉归因于结构字段。新信息可能只是战斗、失败或物品变化，接受动作也可能无效循环。三步不足以判长期可完成性。

