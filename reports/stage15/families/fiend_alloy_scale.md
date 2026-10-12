# fiend_alloy_scale：完整七配置

| 配置 | 成功 | 动作 | 新费用 |
| --- | --- | --- | --- |
| P0 | True | 20 | 0.004030 |
| P1 | True | 20 | 0.004950 |
| P2 | True | 20 | 0.004620 |
| P3 | True | 20 | 0.004549 |
| P4 | True | 20 | 0.005116 |
| P5 | True | 20 | 0.017631 |
| P6 | True | 20 | 0.006762 |

## P0

任务：`sequence-583fbd031e489fe8-P0-ef4303edb0db`；最终缺失必要配方：`[]`。

| 步 | 模型提案 | 当前公开状态旧S1动作 | P1动作 | 实际动作 | 原生结果 | 目标 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | enter cellar | inspect fiend_alloy_scale | inspect fiend_alloy_scale | inspect fiend_alloy_scale | 合法；产量0；损血0 | False |
| 2 | enter courtyard | inspect brimite_ingot | inspect brimite_ingot | inspect brimite_ingot | 合法；产量0；损血0 | False |
| 3 | enter courtyard | store 2 brimite_ingot inventory | store 2 brimite_ingot inventory | store 2 brimite_ingot inventory | 合法；产量0；损血0 | False |
| 4 | enter courtyard | enter cellar | enter cellar | enter cellar | 合法；产量0；损血0 | False |
| 5 | enter courtyard | inspect hellcoal_concentrate | inspect hellcoal_concentrate | inspect hellcoal_concentrate | 合法；产量0；损血0 | False |
| 6 | enter courtyard | store 2 hellcoal_concentrate inventory | store 2 hellcoal_concentrate inventory | store 2 hellcoal_concentrate inventory | 合法；产量0；损血4 | False |
| 7 | enter courtyard | craft 2 fiend_alloy | craft 2 fiend_alloy | craft 2 fiend_alloy | 拒绝；产量0；损血4 | False |
| 8 | enter courtyard | enter courtyard | enter courtyard | enter courtyard | 合法；产量0；损血4 | False |
| 9 | craft 1 fiend_alloy_scale | inspect crucible | inspect crucible | inspect crucible | 合法；产量0；损血4 | False |
| 10 | craft 1 fiend_alloy_scale | inspect war_bench | inspect war_bench | inspect war_bench | 合法；产量0；损血4 | False |
| 11 | craft 1 fiend_alloy_scale | craft 2 fiend_alloy | craft 2 fiend_alloy | craft 2 fiend_alloy | 合法；产量2；损血0 | False |
| 12 | craft 1 fiend_alloy_scale | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血0 | False |
| 13 | craft 1 fiend_alloy_scale | inspect fiend_alloy | inspect fiend_alloy | inspect fiend_alloy | 合法；产量0；损血0 | False |
| 14 | craft 1 fiend_alloy_scale | store 2 fiend_alloy inventory | store 2 fiend_alloy inventory | store 2 fiend_alloy inventory | 合法；产量0；损血0 | False |
| 15 | craft 1 fiend_alloy_scale | craft 2 fiend_alloy_sheet | craft 2 fiend_alloy_sheet | craft 2 fiend_alloy_sheet | 合法；产量1；损血0 | False |
| 16 | inspect fiend_alloy_sheet | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血0 | False |
| 17 | craft 1 fiend_alloy_scale | inspect fiend_alloy_sheet | inspect fiend_alloy_sheet | inspect fiend_alloy_sheet | 合法；产量0；损血0 | False |
| 18 | pick up fiend_alloy_sheet | store 1 fiend_alloy_sheet inventory | store 1 fiend_alloy_sheet inventory | store 1 fiend_alloy_sheet inventory | 合法；产量0；损血0 | False |
| 19 | craft 1 fiend_alloy_scale | craft 1 fiend_alloy_scale | craft 1 fiend_alloy_scale | craft 1 fiend_alloy_scale | 合法；产量1；损血0 | False |
| 20 | pick up fiend_alloy_scale | pick up fiend_alloy_scale | pick up fiend_alloy_scale | pick up fiend_alloy_scale | 合法；产量0；损血0 | True |

## P1

任务：`sequence-583fbd031e489fe8-P1-ef4303edb0db`；最终缺失必要配方：`[]`。

| 步 | 模型提案 | 当前公开状态旧S1动作 | P1动作 | 实际动作 | 原生结果 | 目标 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | enter courtyard | inspect fiend_alloy_scale | inspect fiend_alloy_scale | inspect fiend_alloy_scale | 合法；产量0；损血0 | False |
| 2 | enter courtyard | inspect brimite_ingot | inspect brimite_ingot | inspect brimite_ingot | 合法；产量0；损血0 | False |
| 3 | enter courtyard | store 2 brimite_ingot inventory | store 2 brimite_ingot inventory | store 2 brimite_ingot inventory | 合法；产量0；损血0 | False |
| 4 | enter cellar | enter cellar | enter cellar | enter cellar | 合法；产量0；损血0 | False |
| 5 | enter courtyard | inspect hellcoal_concentrate | inspect hellcoal_concentrate | inspect hellcoal_concentrate | 合法；产量0；损血0 | False |
| 6 | enter courtyard | store 2 hellcoal_concentrate inventory | store 2 hellcoal_concentrate inventory | store 2 hellcoal_concentrate inventory | 合法；产量0；损血4 | False |
| 7 | enter courtyard | craft 2 fiend_alloy | craft 2 fiend_alloy | craft 2 fiend_alloy | 拒绝；产量0；损血4 | False |
| 8 | enter courtyard | enter courtyard | enter courtyard | enter courtyard | 合法；产量0；损血4 | False |
| 9 | craft 1 fiend_alloy_scale | inspect crucible | inspect crucible | inspect crucible | 合法；产量0；损血4 | False |
| 10 | craft 1 fiend_alloy_scale | inspect war_bench | inspect war_bench | inspect war_bench | 合法；产量0；损血4 | False |
| 11 | craft 1 fiend_alloy_scale | craft 2 fiend_alloy | craft 2 fiend_alloy | craft 2 fiend_alloy | 合法；产量2；损血0 | False |
| 12 | craft 1 fiend_alloy_scale | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血0 | False |
| 13 | craft 1 fiend_alloy_scale | inspect fiend_alloy | inspect fiend_alloy | inspect fiend_alloy | 合法；产量0；损血0 | False |
| 14 | inspect fiend_alloy_scale | store 2 fiend_alloy inventory | store 2 fiend_alloy inventory | store 2 fiend_alloy inventory | 合法；产量0；损血0 | False |
| 15 | craft 1 fiend_alloy_scale | craft 2 fiend_alloy_sheet | craft 2 fiend_alloy_sheet | craft 2 fiend_alloy_sheet | 合法；产量1；损血0 | False |
| 16 | craft 1 fiend_alloy_scale | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血0 | False |
| 17 | inspect fiend_alloy_scale | inspect fiend_alloy_sheet | inspect fiend_alloy_sheet | inspect fiend_alloy_sheet | 合法；产量0；损血0 | False |
| 18 | craft 1 fiend_alloy_scale | store 1 fiend_alloy_sheet inventory | store 1 fiend_alloy_sheet inventory | store 1 fiend_alloy_sheet inventory | 合法；产量0；损血0 | False |
| 19 | craft 1 fiend_alloy_scale | craft 1 fiend_alloy_scale | craft 1 fiend_alloy_scale | craft 1 fiend_alloy_scale | 合法；产量1；损血0 | False |
| 20 | pick up fiend_alloy_scale | pick up fiend_alloy_scale | pick up fiend_alloy_scale | pick up fiend_alloy_scale | 合法；产量0；损血0 | True |

## P2

任务：`sequence-583fbd031e489fe8-P2-ef4303edb0db`；最终缺失必要配方：`[]`。

| 步 | 模型提案 | 当前公开状态旧S1动作 | P1动作 | 实际动作 | 原生结果 | 目标 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | enter courtyard | inspect fiend_alloy_scale | inspect fiend_alloy_scale | inspect fiend_alloy_scale | 合法；产量0；损血0 | False |
| 2 | enter courtyard | inspect brimite_ingot | inspect brimite_ingot | inspect brimite_ingot | 合法；产量0；损血0 | False |
| 3 | enter courtyard | store 2 brimite_ingot inventory | store 2 brimite_ingot inventory | store 2 brimite_ingot inventory | 合法；产量0；损血0 | False |
| 4 | enter courtyard | enter cellar | enter cellar | enter cellar | 合法；产量0；损血0 | False |
| 5 | enter courtyard | inspect hellcoal_concentrate | inspect hellcoal_concentrate | inspect hellcoal_concentrate | 合法；产量0；损血0 | False |
| 6 | enter courtyard | store 2 hellcoal_concentrate inventory | store 2 hellcoal_concentrate inventory | store 2 hellcoal_concentrate inventory | 合法；产量0；损血4 | False |
| 7 | enter courtyard | craft 2 fiend_alloy | craft 2 fiend_alloy | craft 2 fiend_alloy | 拒绝；产量0；损血4 | False |
| 8 | enter courtyard | enter courtyard | enter courtyard | enter courtyard | 合法；产量0；损血4 | False |
| 9 | craft 1 fiend_alloy_scale | inspect crucible | inspect crucible | inspect crucible | 合法；产量0；损血4 | False |
| 10 | craft 1 fiend_alloy_scale | inspect war_bench | inspect war_bench | inspect war_bench | 合法；产量0；损血4 | False |
| 11 | craft 1 fiend_alloy_scale | craft 2 fiend_alloy | craft 2 fiend_alloy | craft 2 fiend_alloy | 合法；产量2；损血0 | False |
| 12 | craft 1 fiend_alloy_scale | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血0 | False |
| 13 | craft 1 fiend_alloy_scale | inspect fiend_alloy | inspect fiend_alloy | inspect fiend_alloy | 合法；产量0；损血0 | False |
| 14 | craft 1 fiend_alloy_scale | store 2 fiend_alloy inventory | store 2 fiend_alloy inventory | store 2 fiend_alloy inventory | 合法；产量0；损血0 | False |
| 15 | craft 1 fiend_alloy_scale | craft 2 fiend_alloy_sheet | craft 2 fiend_alloy_sheet | craft 2 fiend_alloy_sheet | 合法；产量1；损血0 | False |
| 16 | craft 1 fiend_alloy_scale | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血0 | False |
| 17 | enter cellar | inspect fiend_alloy_sheet | inspect fiend_alloy_sheet | inspect fiend_alloy_sheet | 合法；产量0；损血0 | False |
| 18 | pick up fiend_alloy_sheet | store 1 fiend_alloy_sheet inventory | store 1 fiend_alloy_sheet inventory | store 1 fiend_alloy_sheet inventory | 合法；产量0；损血0 | False |
| 19 | craft 1 fiend_alloy_scale | craft 1 fiend_alloy_scale | craft 1 fiend_alloy_scale | craft 1 fiend_alloy_scale | 合法；产量1；损血0 | False |
| 20 | pick up fiend_alloy_scale | pick up fiend_alloy_scale | pick up fiend_alloy_scale | pick up fiend_alloy_scale | 合法；产量0；损血0 | True |

## P3

任务：`sequence-583fbd031e489fe8-P3-ef4303edb0db`；最终缺失必要配方：`[]`。

| 步 | 模型提案 | 当前公开状态旧S1动作 | P1动作 | 实际动作 | 原生结果 | 目标 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | enter courtyard | inspect fiend_alloy_scale | inspect fiend_alloy_scale | inspect fiend_alloy_scale | 合法；产量0；损血0 | False |
| 2 | enter courtyard | inspect brimite_ingot | inspect brimite_ingot | inspect brimite_ingot | 合法；产量0；损血0 | False |
| 3 | enter courtyard | store 2 brimite_ingot inventory | store 2 brimite_ingot inventory | store 2 brimite_ingot inventory | 合法；产量0；损血0 | False |
| 4 | enter cellar | enter cellar | enter cellar | enter cellar | 合法；产量0；损血0 | False |
| 5 | enter courtyard | inspect hellcoal_concentrate | inspect hellcoal_concentrate | inspect hellcoal_concentrate | 合法；产量0；损血0 | False |
| 6 | enter courtyard | store 2 hellcoal_concentrate inventory | store 2 hellcoal_concentrate inventory | store 2 hellcoal_concentrate inventory | 合法；产量0；损血4 | False |
| 7 | enter courtyard | craft 2 fiend_alloy | craft 2 fiend_alloy | craft 2 fiend_alloy | 拒绝；产量0；损血4 | False |
| 8 | enter courtyard | enter courtyard | enter courtyard | enter courtyard | 合法；产量0；损血4 | False |
| 9 | craft 1 fiend_alloy_scale | inspect crucible | inspect crucible | inspect crucible | 合法；产量0；损血4 | False |
| 10 | craft 1 fiend_alloy_scale | inspect war_bench | inspect war_bench | inspect war_bench | 合法；产量0；损血4 | False |
| 11 | craft 1 fiend_alloy_scale | craft 2 fiend_alloy | craft 2 fiend_alloy | craft 2 fiend_alloy | 合法；产量2；损血0 | False |
| 12 | craft 1 fiend_alloy_scale | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血0 | False |
| 13 | craft 1 fiend_alloy_scale | inspect fiend_alloy | inspect fiend_alloy | inspect fiend_alloy | 合法；产量0；损血0 | False |
| 14 | craft 1 fiend_alloy_scale | store 2 fiend_alloy inventory | store 2 fiend_alloy inventory | store 2 fiend_alloy inventory | 合法；产量0；损血0 | False |
| 15 | craft 1 fiend_alloy_scale | craft 2 fiend_alloy_sheet | craft 2 fiend_alloy_sheet | craft 2 fiend_alloy_sheet | 合法；产量1；损血0 | False |
| 16 | craft 1 fiend_alloy_scale | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血0 | False |
| 17 | craft 1 fiend_alloy_scale | inspect fiend_alloy_sheet | inspect fiend_alloy_sheet | inspect fiend_alloy_sheet | 合法；产量0；损血0 | False |
| 18 | craft 1 fiend_alloy_scale | store 1 fiend_alloy_sheet inventory | store 1 fiend_alloy_sheet inventory | store 1 fiend_alloy_sheet inventory | 合法；产量0；损血0 | False |
| 19 | craft 1 fiend_alloy_scale | craft 1 fiend_alloy_scale | craft 1 fiend_alloy_scale | craft 1 fiend_alloy_scale | 合法；产量1；损血0 | False |
| 20 | pick up fiend_alloy_scale | pick up fiend_alloy_scale | pick up fiend_alloy_scale | pick up fiend_alloy_scale | 合法；产量0；损血0 | True |

## P4

任务：`sequence-583fbd031e489fe8-P4-ef4303edb0db`；最终缺失必要配方：`[]`。

| 步 | 模型提案 | 当前公开状态旧S1动作 | P1动作 | 实际动作 | 原生结果 | 目标 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | enter courtyard | inspect fiend_alloy_scale | inspect fiend_alloy_scale | inspect fiend_alloy_scale | 合法；产量0；损血0 | False |
| 2 | enter courtyard | inspect brimite_ingot | inspect brimite_ingot | inspect brimite_ingot | 合法；产量0；损血0 | False |
| 3 | enter courtyard | store 2 brimite_ingot inventory | store 2 brimite_ingot inventory | store 2 brimite_ingot inventory | 合法；产量0；损血0 | False |
| 4 | enter cellar | enter cellar | enter cellar | enter cellar | 合法；产量0；损血0 | False |
| 5 | enter courtyard | inspect hellcoal_concentrate | inspect hellcoal_concentrate | inspect hellcoal_concentrate | 合法；产量0；损血0 | False |
| 6 | enter courtyard | store 2 hellcoal_concentrate inventory | store 2 hellcoal_concentrate inventory | store 2 hellcoal_concentrate inventory | 合法；产量0；损血4 | False |
| 7 | enter courtyard | craft 2 fiend_alloy | craft 2 fiend_alloy | craft 2 fiend_alloy | 拒绝；产量0；损血4 | False |
| 8 | enter courtyard | enter courtyard | enter courtyard | enter courtyard | 合法；产量0；损血4 | False |
| 9 | craft 1 fiend_alloy_scale | inspect crucible | inspect crucible | inspect crucible | 合法；产量0；损血4 | False |
| 10 | craft 1 fiend_alloy_scale | inspect war_bench | inspect war_bench | inspect war_bench | 合法；产量0；损血4 | False |
| 11 | craft 1 fiend_alloy_scale | craft 2 fiend_alloy | craft 2 fiend_alloy | craft 2 fiend_alloy | 合法；产量2；损血0 | False |
| 12 | craft 1 fiend_alloy_scale | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血0 | False |
| 13 | craft 1 fiend_alloy_scale | inspect fiend_alloy | inspect fiend_alloy | inspect fiend_alloy | 合法；产量0；损血0 | False |
| 14 | pick up fiend_alloy | store 2 fiend_alloy inventory | store 2 fiend_alloy inventory | store 2 fiend_alloy inventory | 合法；产量0；损血0 | False |
| 15 | craft 1 fiend_alloy_scale | craft 2 fiend_alloy_sheet | craft 2 fiend_alloy_sheet | craft 2 fiend_alloy_sheet | 合法；产量1；损血0 | False |
| 16 | craft 1 fiend_alloy_scale | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血0 | False |
| 17 | craft 1 fiend_alloy_scale | inspect fiend_alloy_sheet | inspect fiend_alloy_sheet | inspect fiend_alloy_sheet | 合法；产量0；损血0 | False |
| 18 | craft 1 fiend_alloy_scale | store 1 fiend_alloy_sheet inventory | store 1 fiend_alloy_sheet inventory | store 1 fiend_alloy_sheet inventory | 合法；产量0；损血0 | False |
| 19 | craft 1 fiend_alloy_scale | craft 1 fiend_alloy_scale | craft 1 fiend_alloy_scale | craft 1 fiend_alloy_scale | 合法；产量1；损血0 | False |
| 20 | pick up fiend_alloy_scale | pick up fiend_alloy_scale | pick up fiend_alloy_scale | pick up fiend_alloy_scale | 合法；产量0；损血0 | True |

## P5

任务：`sequence-583fbd031e489fe8-P5-ef4303edb0db`；最终缺失必要配方：`[]`。

| 步 | 模型提案 | 当前公开状态旧S1动作 | P1动作 | 实际动作 | 原生结果 | 目标 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | enter courtyard | inspect fiend_alloy_scale | inspect fiend_alloy_scale | inspect fiend_alloy_scale | 合法；产量0；损血0 | False |
| 2 | enter courtyard | inspect brimite_ingot | inspect brimite_ingot | inspect brimite_ingot | 合法；产量0；损血0 | False |
| 3 | enter cellar | store 2 brimite_ingot inventory | store 2 brimite_ingot inventory | store 2 brimite_ingot inventory | 合法；产量0；损血0 | False |
| 4 | enter courtyard | enter cellar | enter cellar | enter cellar | 合法；产量0；损血0 | False |
| 5 | enter courtyard | inspect hellcoal_concentrate | inspect hellcoal_concentrate | inspect hellcoal_concentrate | 合法；产量0；损血0 | False |
| 6 | enter courtyard | store 2 hellcoal_concentrate inventory | store 2 hellcoal_concentrate inventory | store 2 hellcoal_concentrate inventory | 合法；产量0；损血4 | False |
| 7 | enter courtyard | craft 2 fiend_alloy | craft 2 fiend_alloy | craft 2 fiend_alloy | 拒绝；产量0；损血4 | False |
| 8 | enter courtyard | enter courtyard | enter courtyard | enter courtyard | 合法；产量0；损血4 | False |
| 9 | craft 1 fiend_alloy_scale | inspect crucible | inspect crucible | inspect crucible | 合法；产量0；损血4 | False |
| 10 | craft 1 fiend_alloy_scale | inspect war_bench | inspect war_bench | inspect war_bench | 合法；产量0；损血4 | False |
| 11 | craft 1 fiend_alloy_scale | craft 2 fiend_alloy | craft 2 fiend_alloy | craft 2 fiend_alloy | 合法；产量2；损血0 | False |
| 12 | craft 1 fiend_alloy_scale | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血0 | False |
| 13 | craft 1 fiend_alloy_scale | inspect fiend_alloy | inspect fiend_alloy | inspect fiend_alloy | 合法；产量0；损血0 | False |
| 14 | pick up fiend_alloy | store 2 fiend_alloy inventory | store 2 fiend_alloy inventory | store 2 fiend_alloy inventory | 合法；产量0；损血0 | False |
| 15 | craft 1 fiend_alloy_scale | craft 2 fiend_alloy_sheet | craft 2 fiend_alloy_sheet | craft 2 fiend_alloy_sheet | 合法；产量1；损血0 | False |
| 16 | craft 1 fiend_alloy_scale | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血0 | False |
| 17 | craft 1 fiend_alloy_scale | inspect fiend_alloy_sheet | inspect fiend_alloy_sheet | inspect fiend_alloy_sheet | 合法；产量0；损血0 | False |
| 18 | pick up fiend_alloy_sheet | store 1 fiend_alloy_sheet inventory | store 1 fiend_alloy_sheet inventory | store 1 fiend_alloy_sheet inventory | 合法；产量0；损血0 | False |
| 19 | craft 1 fiend_alloy_scale | craft 1 fiend_alloy_scale | craft 1 fiend_alloy_scale | craft 1 fiend_alloy_scale | 合法；产量1；损血0 | False |
| 20 | pick up fiend_alloy_scale | pick up fiend_alloy_scale | pick up fiend_alloy_scale | pick up fiend_alloy_scale | 合法；产量0；损血0 | True |

## P6

任务：`sequence-583fbd031e489fe8-P6-ef4303edb0db`；最终缺失必要配方：`[]`。

| 步 | 模型提案 | 当前公开状态旧S1动作 | P1动作 | 实际动作 | 原生结果 | 目标 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | enter courtyard | inspect fiend_alloy_scale | inspect fiend_alloy_scale | inspect fiend_alloy_scale | 合法；产量0；损血0 | False |
| 2 | enter courtyard | inspect brimite_ingot | inspect brimite_ingot | inspect brimite_ingot | 合法；产量0；损血0 | False |
| 3 | enter courtyard | store 2 brimite_ingot inventory | store 2 brimite_ingot inventory | store 2 brimite_ingot inventory | 合法；产量0；损血0 | False |
| 4 | enter cellar | enter cellar | enter cellar | enter cellar | 合法；产量0；损血0 | False |
| 5 | pick up hellcoal_concentrate | inspect hellcoal_concentrate | inspect hellcoal_concentrate | inspect hellcoal_concentrate | 合法；产量0；损血0 | False |
| 6 | pick up hellcoal_concentrate | store 2 hellcoal_concentrate inventory | store 2 hellcoal_concentrate inventory | store 2 hellcoal_concentrate inventory | 合法；产量0；损血4 | False |
| 7 | enter courtyard | craft 2 fiend_alloy | craft 2 fiend_alloy | craft 2 fiend_alloy | 拒绝；产量0；损血4 | False |
| 8 | enter courtyard | enter courtyard | enter courtyard | enter courtyard | 合法；产量0；损血4 | False |
| 9 | craft 1 fiend_alloy_scale | inspect crucible | inspect crucible | inspect crucible | 合法；产量0；损血4 | False |
| 10 | craft 1 fiend_alloy_scale | inspect war_bench | inspect war_bench | inspect war_bench | 合法；产量0；损血4 | False |
| 11 | talk to william_brooks | craft 2 fiend_alloy | craft 2 fiend_alloy | craft 2 fiend_alloy | 合法；产量2；损血0 | False |
| 12 | craft 1 fiend_alloy_scale | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血0 | False |
| 13 | craft 1 fiend_alloy_scale | inspect fiend_alloy | inspect fiend_alloy | inspect fiend_alloy | 合法；产量0；损血0 | False |
| 14 | craft 1 fiend_alloy_scale | store 2 fiend_alloy inventory | store 2 fiend_alloy inventory | store 2 fiend_alloy inventory | 合法；产量0；损血0 | False |
| 15 | craft 1 fiend_alloy_scale | craft 2 fiend_alloy_sheet | craft 2 fiend_alloy_sheet | craft 2 fiend_alloy_sheet | 合法；产量1；损血0 | False |
| 16 | inspect fiend_alloy_sheet | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血0 | False |
| 17 | craft 1 fiend_alloy_scale | inspect fiend_alloy_sheet | inspect fiend_alloy_sheet | inspect fiend_alloy_sheet | 合法；产量0；损血0 | False |
| 18 | craft 1 fiend_alloy_scale | store 1 fiend_alloy_sheet inventory | store 1 fiend_alloy_sheet inventory | store 1 fiend_alloy_sheet inventory | 合法；产量0；损血0 | False |
| 19 | craft 1 fiend_alloy_scale | craft 1 fiend_alloy_scale | craft 1 fiend_alloy_scale | craft 1 fiend_alloy_scale | 合法；产量1；损血0 | False |
| 20 | pick up fiend_alloy_scale | pick up fiend_alloy_scale | pick up fiend_alloy_scale | pick up fiend_alloy_scale | 合法；产量0；损血0 | True |
