# Precondition Understanding Replay

所有 336 次真实公开拒绝都进入测试，未依据回答删样本。

| 类别 | 数量 | 比例 |
|---|---|---|
| Correct grounding | 319 | 94.94% |
| Partial grounding | 17 | 5.06% |
| Wrong grounding | 0 | 0.00% |
| No grounding | 0 | 0.00% |


| 公开失败类型 | 样本 | Correct | Partial | Wrong | No |
|---|---|---|---|---|---|
| locked_exit | 26 | 23 | 3 | 0 | 0 |
| missing_lockpick_tool | 5 | 3 | 2 | 0 | 0 |
| object_not_held_or_visible | 12 | 12 | 0 | 0 | 0 |
| hand_capacity | 114 | 112 | 2 | 0 | 0 |
| missing_workbench | 8 | 8 | 0 | 0 | 0 |
| combat_blocks_exit | 32 | 30 | 2 | 0 | 0 |
| not_equippable | 20 | 20 | 0 | 0 | 0 |
| missing_writing_tool | 19 | 14 | 5 | 0 | 0 |
| insufficient_ingredients | 30 | 30 | 0 | 0 | 0 |
| container_capacity | 15 | 15 | 0 | 0 | 0 |
| target_not_held | 10 | 10 | 0 | 0 | 0 |
| no_path | 5 | 4 | 1 | 0 | 0 |
| container_nesting | 9 | 9 | 0 | 0 | 0 |
| equipment_slot_occupied | 4 | 4 | 0 | 0 | 0 |
| not_writable | 7 | 5 | 2 | 0 | 0 |
| unknown_object | 3 | 3 | 0 | 0 | 0 |
| unspecified_rejection | 1 | 1 | 0 | 0 | 0 |
| missing_furnace | 1 | 1 | 0 | 0 | 0 |
| object_unavailable | 10 | 10 | 0 | 0 | 0 |
| not_craftable | 4 | 4 | 0 | 0 | 0 |
| not_edible | 1 | 1 | 0 | 0 | 0 |


## 核验方法

`scar_stage27/grade.py` 按公开失败类别核验原因、缺失条件和恢复优先项；`understanding_judgments.json` 保存逐条标签、命中规则与证据复核说明，单独的 `understanding_adjudications.json` 保存可复用的语义裁决输入。66 条经过本助手进一步公开证据语义复核（包括母轨迹全部 34 条）；剩余为规则评价，不能称全部经独立人工评审。复核未盲化，没有独立评审者一致性统计。所有解析失败同样进入分母。

核心因果识别与完整恢复建议分开存储。典型 Partial 包括：把写字所需手持工具放宽成装备工具，把地面钥匙说成已持有，把门锁与黑暗的共现误当共同拒绝原因，以及死亡复活后未一致更新位置。词法漏掉同义表达的案例通过保存证据复核纠正；不调用模型裁判。

本结果表明显式拒绝通常可以被解释。它不保证模型行动前能检查全部前置条件，也不证明 workflow 是唯一责任方。模型经提示能解释与在原始行动提示下稳定利用，是两项不同能力。

完整数据库：`results/stage27/failure_database.jsonl.gz`；原始回答、来源和标签：`understanding_answers.jsonl.gz`。每个样本都有 step/goal/observation/inventory/location/previous_actions/candidate_action/environment_response/failure_reason，及原轨迹行号。
