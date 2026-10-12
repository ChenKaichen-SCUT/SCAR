# chain_net：完整七配置

| 配置 | 成功 | 动作 | 新费用 |
| --- | --- | --- | --- |
| P0 | False | 40 | 0.023898 |
| P1 | False | 40 | 0.013030 |
| P2 | False | 40 | 0.025415 |
| P3 | True | 39 | 0.023964 |
| P4 | False | 40 | 0.041473 |
| P5 | False | 40 | 0.014531 |
| P6 | False | 40 | 0.022073 |

## P0

任务：`sequence-6c1d62349d18c4d3-P0-ef4303edb0db`；最终缺失必要配方：`[]`。

| 步 | 模型提案 | 当前公开状态旧S1动作 | P1动作 | 实际动作 | 原生结果 | 目标 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | enter courtyard | inspect chain_net | inspect chain_net | inspect chain_net | 合法；产量0；损血0 | False |
| 2 | enter courtyard | inspect salvage_cloth | inspect salvage_cloth | inspect salvage_cloth | 合法；产量0；损血0 | False |
| 3 | enter courtyard | store 1 salvage_cloth inventory | store 1 salvage_cloth inventory | store 1 salvage_cloth inventory | 合法；产量0；损血0 | False |
| 4 | enter courtyard | inspect crown_shard | inspect crown_shard | inspect crown_shard | 合法；产量0；损血0 | False |
| 5 | enter courtyard | craft 2 sinew_cord | craft 2 sinew_cord | craft 2 sinew_cord | 拒绝；产量0；损血0 | False |
| 6 | enter cellar | enter cellar | enter cellar | enter cellar | 合法；产量0；损血0 | False |
| 7 | enter courtyard | inspect scrap_iron | inspect scrap_iron | inspect scrap_iron | 合法；产量0；损血0 | False |
| 8 | enter courtyard | store 6 scrap_iron inventory | store 6 scrap_iron inventory | store 6 scrap_iron inventory | 合法；产量0；损血6 | False |
| 9 | enter courtyard | craft 2 iron_nugget | craft 2 iron_nugget | craft 2 iron_nugget | 拒绝；产量0；损血6 | False |
| 10 | enter courtyard | enter courtyard | enter courtyard | enter courtyard | 合法；产量0；损血6 | False |
| 11 | craft 1 chain_net | inspect crucible | inspect crucible | inspect crucible | 合法；产量0；损血6 | False |
| 12 | craft 1 chain_net | inspect war_bench | inspect war_bench | inspect war_bench | 合法；产量0；损血6 | False |
| 13 | craft 1 chain_net | craft 2 iron_nugget | craft 2 iron_nugget | craft 2 iron_nugget | 合法；产量2；损血2 | False |
| 14 | craft 1 chain_net | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血2 | False |
| 15 | craft 1 chain_net | inspect iron_nugget | inspect iron_nugget | inspect iron_nugget | 合法；产量0；损血2 | False |
| 16 | craft 1 chain_net | store 2 iron_nugget inventory | store 2 iron_nugget inventory | store 2 iron_nugget inventory | 合法；产量0；损血6 | False |
| 17 | craft 1 chain_net | craft 2 iron_bar | craft 2 iron_bar | craft 2 iron_bar | 合法；产量1；损血2 | False |
| 18 | craft 1 chain_net | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血2 | False |
| 19 | craft 1 chain_net | inspect iron_bar | inspect iron_bar | inspect iron_bar | 合法；产量0；损血2 | False |
| 20 | craft 1 sinew_cord | store 1 iron_bar inventory | store 1 iron_bar inventory | store 1 iron_bar inventory | 合法；产量0；损血4 | False |
| 21 | craft 1 sinew_cord | craft 2 sinew_cord | craft 2 sinew_cord | craft 2 sinew_cord | 合法；产量2；损血4 | False |
| 22 | pick up sinew_cord | pick up sinew_cord | pick up sinew_cord | pick up sinew_cord | 合法；产量0；损血4 | False |
| 23 | pick up sinew_cord | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血4 | False |
| 24 | pick up sinew_cord | craft 1 chain_net | craft 1 chain_net | craft 1 chain_net | 拒绝；产量0；损血4 | False |
| 25 | pick up sinew_cord | store 2 sinew_cord inventory | store 2 sinew_cord inventory | store 2 sinew_cord inventory | 合法；产量0；损血4 | False |
| 26 | inspect inventory | craft 2 iron_nugget | craft 2 iron_nugget | craft 2 iron_nugget | 合法；产量2；损血0 | False |
| 27 | pick up iron_nugget | pick up iron_nugget | pick up iron_nugget | pick up iron_nugget | 合法；产量0；损血2 | False |
| 28 | craft 2 iron_nugget | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血2 | False |
| 29 | craft 1 chain_net | store 1 iron_nugget inventory | store 1 iron_nugget inventory | store 1 iron_nugget inventory | 合法；产量0；损血2 | False |
| 30 | craft 1 chain_net | store 1 iron_nugget inventory | store 1 iron_nugget inventory | store 1 iron_nugget inventory | 合法；产量0；损血4 | False |
| 31 | craft 1 chain_net | craft 2 iron_bar | craft 2 iron_bar | craft 2 iron_bar | 合法；产量1；损血0 | False |
| 32 | pick up iron_bar | pick up iron_bar | pick up iron_bar | pick up iron_bar | 合法；产量0；损血2 | False |
| 33 | craft 1 chain_net | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血2 | False |
| 34 | craft 1 chain_net | craft 1 chain_net | craft 1 chain_net | craft 1 chain_net | 拒绝；产量0；损血2 | False |
| 35 | take out sinew_cord scout_satchel_0 | store 1 chain_net inventory | store 1 chain_net inventory | store 1 chain_net inventory | 合法；产量0；损血2 | False |
| 36 | scavenge | craft 2 iron_nugget | craft 2 iron_nugget | craft 2 iron_nugget | 合法；产量2；损血0 | False |
| 37 | pick up iron_nugget | pick up iron_nugget | pick up iron_nugget | pick up iron_nugget | 合法；产量0；损血0 | False |
| 38 | take out sinew_cord scout_satchel_0 | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血0 | False |
| 39 | take out sinew_cord scout_satchel_0 | store 1 iron_nugget inventory | store 1 iron_nugget inventory | store 1 iron_nugget inventory | 合法；产量0；损血0 | False |
| 40 | take out sinew_cord scout_satchel_0 | store 1 iron_nugget inventory | store 1 iron_nugget inventory | store 1 iron_nugget inventory | 合法；产量0；损血2 | False |

## P1

任务：`sequence-6c1d62349d18c4d3-P1-ef4303edb0db`；最终缺失必要配方：`[]`。

| 步 | 模型提案 | 当前公开状态旧S1动作 | P1动作 | 实际动作 | 原生结果 | 目标 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | enter courtyard | inspect chain_net | inspect chain_net | inspect chain_net | 合法；产量0；损血0 | False |
| 2 | enter courtyard | inspect salvage_cloth | inspect salvage_cloth | inspect salvage_cloth | 合法；产量0；损血0 | False |
| 3 | enter courtyard | store 1 salvage_cloth inventory | store 1 salvage_cloth inventory | store 1 salvage_cloth inventory | 合法；产量0；损血0 | False |
| 4 | enter courtyard | inspect crown_shard | inspect crown_shard | inspect crown_shard | 合法；产量0；损血0 | False |
| 5 | enter courtyard | craft 2 sinew_cord | craft 2 sinew_cord | craft 2 sinew_cord | 拒绝；产量0；损血0 | False |
| 6 | enter courtyard | enter cellar | enter cellar | enter cellar | 合法；产量0；损血0 | False |
| 7 | enter courtyard | inspect scrap_iron | inspect scrap_iron | inspect scrap_iron | 合法；产量0；损血0 | False |
| 8 | enter courtyard | store 6 scrap_iron inventory | store 6 scrap_iron inventory | store 6 scrap_iron inventory | 合法；产量0；损血6 | False |
| 9 | enter courtyard | craft 2 iron_nugget | craft 2 iron_nugget | craft 2 iron_nugget | 拒绝；产量0；损血6 | False |
| 10 | enter courtyard | enter courtyard | enter courtyard | enter courtyard | 合法；产量0；损血6 | False |
| 11 | craft 1 chain_net | inspect crucible | inspect crucible | inspect crucible | 合法；产量0；损血6 | False |
| 12 | craft 1 chain_net | inspect war_bench | inspect war_bench | inspect war_bench | 合法；产量0；损血6 | False |
| 13 | craft 1 chain_net | craft 2 iron_nugget | craft 2 iron_nugget | craft 2 iron_nugget | 合法；产量2；损血2 | False |
| 14 | talk to sarah_cole | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血2 | False |
| 15 | craft 1 chain_net | inspect iron_nugget | inspect iron_nugget | inspect iron_nugget | 合法；产量0；损血2 | False |
| 16 | talk to sarah_cole | store 2 iron_nugget inventory | store 2 iron_nugget inventory | store 2 iron_nugget inventory | 合法；产量0；损血6 | False |
| 17 | craft 1 chain_net | craft 2 iron_bar | craft 2 iron_bar | craft 2 iron_bar | 合法；产量1；损血2 | False |
| 18 | craft 1 chain_net | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血2 | False |
| 19 | craft 1 chain_net | inspect iron_bar | inspect iron_bar | inspect iron_bar | 合法；产量0；损血2 | False |
| 20 | craft 1 sinew_cord | store 1 iron_bar inventory | store 1 iron_bar inventory | store 1 iron_bar inventory | 合法；产量0；损血4 | False |
| 21 | craft 1 sinew_cord | craft 2 sinew_cord | craft 2 sinew_cord | craft 2 sinew_cord | 合法；产量2；损血4 | False |
| 22 | pick up sinew_cord | pick up sinew_cord | pick up sinew_cord | pick up sinew_cord | 合法；产量0；损血4 | False |
| 23 | pick up sinew_cord | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血4 | False |
| 24 | pick up sinew_cord | store 2 sinew_cord inventory | store 2 sinew_cord inventory | store 2 sinew_cord inventory | 合法；产量0；损血4 | False |
| 25 | craft 2 iron_nugget | craft 2 iron_nugget | craft 2 iron_nugget | craft 2 iron_nugget | 合法；产量2；损血0 | False |
| 26 | pick up iron_nugget | pick up iron_nugget | pick up iron_nugget | pick up iron_nugget | 合法；产量0；损血2 | False |
| 27 | craft 2 iron_nugget | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血2 | False |
| 28 | pick up iron_nugget | store 1 iron_nugget inventory | store 1 iron_nugget inventory | store 1 iron_nugget inventory | 合法；产量0；损血2 | False |
| 29 | craft 2 iron_nugget | store 1 iron_nugget inventory | store 1 iron_nugget inventory | store 1 iron_nugget inventory | 合法；产量0；损血4 | False |
| 30 | craft 2 iron_nugget | craft 2 iron_bar | craft 2 iron_bar | craft 2 iron_bar | 合法；产量1；损血0 | False |
| 31 | pick up iron_bar | pick up iron_bar | pick up iron_bar | pick up iron_bar | 合法；产量0；损血2 | False |
| 32 | craft 2 iron_nugget | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血2 | False |
| 33 | craft 2 iron_nugget | craft 2 iron_nugget | craft 2 iron_nugget | craft 2 iron_nugget | 合法；产量2；损血0 | False |
| 34 | pick up iron_nugget | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血0 | False |
| 35 | craft 1 iron_bar | store 2 iron_nugget inventory | store 2 iron_nugget inventory | store 2 iron_nugget inventory | 合法；产量0；损血2 | False |
| 36 | take out 2 iron_nugget inventory | craft 2 iron_bar | craft 2 iron_bar | craft 2 iron_bar | 合法；产量1；损血0 | False |
| 37 | pick up iron_bar | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血0 | False |
| 38 | pick up iron_bar | store 1 iron_bar inventory | store 1 iron_bar inventory | store 1 iron_bar inventory | 合法；产量0；损血0 | False |
| 39 | take out 2 iron_nugget scout_satchel_0 | store 1 iron_bar inventory | store 1 iron_bar inventory | store 1 iron_bar inventory | 合法；产量0；损血0 | False |
| 40 | pick up iron_bar | craft 1 chain_net | craft 1 chain_net | craft 1 chain_net | 合法；产量1；损血0 | False |

## P2

任务：`sequence-6c1d62349d18c4d3-P2-ef4303edb0db`；最终缺失必要配方：`[]`。

| 步 | 模型提案 | 当前公开状态旧S1动作 | P1动作 | 实际动作 | 原生结果 | 目标 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | enter courtyard | inspect chain_net | inspect chain_net | inspect chain_net | 合法；产量0；损血0 | False |
| 2 | enter courtyard | inspect salvage_cloth | inspect salvage_cloth | inspect salvage_cloth | 合法；产量0；损血0 | False |
| 3 | enter courtyard | store 1 salvage_cloth inventory | store 1 salvage_cloth inventory | store 1 salvage_cloth inventory | 合法；产量0；损血0 | False |
| 4 | enter courtyard | inspect crown_shard | inspect crown_shard | inspect crown_shard | 合法；产量0；损血0 | False |
| 5 | enter courtyard | craft 2 sinew_cord | craft 2 sinew_cord | craft 2 sinew_cord | 拒绝；产量0；损血0 | False |
| 6 | enter courtyard | enter cellar | enter cellar | enter cellar | 合法；产量0；损血0 | False |
| 7 | enter courtyard | inspect scrap_iron | inspect scrap_iron | inspect scrap_iron | 合法；产量0；损血0 | False |
| 8 | enter courtyard | store 6 scrap_iron inventory | store 6 scrap_iron inventory | store 6 scrap_iron inventory | 合法；产量0；损血6 | False |
| 9 | enter courtyard | craft 2 iron_nugget | craft 2 iron_nugget | craft 2 iron_nugget | 拒绝；产量0；损血6 | False |
| 10 | enter courtyard | enter courtyard | enter courtyard | enter courtyard | 合法；产量0；损血6 | False |
| 11 | craft 1 chain_net | inspect crucible | inspect crucible | inspect crucible | 合法；产量0；损血6 | False |
| 12 | craft 1 chain_net | inspect war_bench | inspect war_bench | inspect war_bench | 合法；产量0；损血6 | False |
| 13 | craft 1 chain_net | craft 2 iron_nugget | craft 2 iron_nugget | craft 2 iron_nugget | 合法；产量2；损血2 | False |
| 14 | craft 1 chain_net | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血2 | False |
| 15 | craft 1 chain_net | inspect iron_nugget | inspect iron_nugget | inspect iron_nugget | 合法；产量0；损血2 | False |
| 16 | pick up iron_nugget | store 2 iron_nugget inventory | store 2 iron_nugget inventory | store 2 iron_nugget inventory | 合法；产量0；损血6 | False |
| 17 | craft 1 chain_net | craft 2 iron_bar | craft 2 iron_bar | craft 2 iron_bar | 合法；产量1；损血2 | False |
| 18 | inspect iron_bar | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血2 | False |
| 19 | craft 1 chain_net | inspect iron_bar | inspect iron_bar | inspect iron_bar | 合法；产量0；损血2 | False |
| 20 | craft 1 sinew_cord | store 1 iron_bar inventory | store 1 iron_bar inventory | store 1 iron_bar inventory | 合法；产量0；损血4 | False |
| 21 | craft 4 iron_nugget | craft 2 sinew_cord | craft 2 sinew_cord | craft 2 sinew_cord | 合法；产量2；损血4 | False |
| 22 | pick up sinew_cord | pick up sinew_cord | pick up sinew_cord | pick up sinew_cord | 合法；产量0；损血4 | False |
| 23 | take out iron_bar inventory | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血4 | False |
| 24 | pick up iron_bar | store 1 chain_net inventory | store 1 chain_net inventory | store 1 chain_net inventory | 合法；产量0；损血4 | False |
| 25 | pick up sinew_cord | store 1 sinew_cord inventory | store 1 sinew_cord inventory | store 1 sinew_cord inventory | 合法；产量0；损血4 | False |
| 26 | craft 4 iron_nugget | store 1 sinew_cord inventory | store 1 sinew_cord inventory | store 1 sinew_cord inventory | 合法；产量0；损血4 | False |
| 27 | craft 4 iron_nugget | craft 2 iron_nugget | craft 2 iron_nugget | craft 2 iron_nugget | 合法；产量2；损血0 | False |
| 28 | pick up iron_nugget | pick up iron_nugget | pick up iron_nugget | pick up iron_nugget | 合法；产量0；损血2 | False |
| 29 | take out sinew_cord inventory | take out sinew_cord inventory | take out sinew_cord inventory | take out sinew_cord inventory | 合法；产量0；损血2 | False |
| 30 | pick up iron_nugget | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血2 | False |
| 31 | pick up iron_nugget | store 1 iron_nugget inventory | store 1 iron_nugget inventory | store 1 iron_nugget inventory | 合法；产量0；损血2 | False |
| 32 | craft 2 iron_nugget | store 1 iron_nugget inventory | store 1 iron_nugget inventory | store 1 iron_nugget inventory | 合法；产量0；损血4 | False |
| 33 | craft 2 iron_nugget | craft 2 iron_bar | craft 2 iron_bar | craft 2 iron_bar | 合法；产量1；损血0 | False |
| 34 | pick up iron_bar | pick up iron_bar | pick up iron_bar | pick up iron_bar | 合法；产量0；损血2 | False |
| 35 | take out iron_bar scout_satchel_0 | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血2 | False |
| 36 | take out iron_bar scout_satchel_0 | craft 2 iron_nugget | craft 2 iron_nugget | craft 2 iron_nugget | 合法；产量2；损血0 | False |
| 37 | pick up iron_nugget | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血0 | False |
| 38 | pick up iron_nugget | store 2 iron_nugget inventory | store 2 iron_nugget inventory | store 2 iron_nugget inventory | 合法；产量0；损血2 | False |
| 39 | craft 1 chain_net | craft 2 iron_bar | craft 2 iron_bar | craft 2 iron_bar | 合法；产量1；损血0 | False |
| 40 | pick up iron_bar | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血0 | False |

## P3

任务：`sequence-6c1d62349d18c4d3-P3-ef4303edb0db`；最终缺失必要配方：`[]`。

| 步 | 模型提案 | 当前公开状态旧S1动作 | P1动作 | 实际动作 | 原生结果 | 目标 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | enter courtyard | inspect chain_net | inspect chain_net | inspect chain_net | 合法；产量0；损血0 | False |
| 2 | enter courtyard | inspect salvage_cloth | inspect salvage_cloth | inspect salvage_cloth | 合法；产量0；损血0 | False |
| 3 | enter courtyard | store 1 salvage_cloth inventory | store 1 salvage_cloth inventory | store 1 salvage_cloth inventory | 合法；产量0；损血0 | False |
| 4 | enter courtyard | inspect crown_shard | inspect crown_shard | inspect crown_shard | 合法；产量0；损血0 | False |
| 5 | enter courtyard | craft 2 sinew_cord | craft 2 sinew_cord | craft 2 sinew_cord | 拒绝；产量0；损血0 | False |
| 6 | enter cellar | enter cellar | enter cellar | enter cellar | 合法；产量0；损血0 | False |
| 7 | enter courtyard | inspect scrap_iron | inspect scrap_iron | inspect scrap_iron | 合法；产量0；损血0 | False |
| 8 | enter courtyard | store 6 scrap_iron inventory | store 6 scrap_iron inventory | store 6 scrap_iron inventory | 合法；产量0；损血6 | False |
| 9 | enter courtyard | craft 2 iron_nugget | craft 2 iron_nugget | craft 2 iron_nugget | 拒绝；产量0；损血6 | False |
| 10 | enter courtyard | enter courtyard | enter courtyard | enter courtyard | 合法；产量0；损血6 | False |
| 11 | craft 1 chain_net | inspect crucible | inspect crucible | inspect crucible | 合法；产量0；损血6 | False |
| 12 | craft 1 chain_net | inspect war_bench | inspect war_bench | inspect war_bench | 合法；产量0；损血6 | False |
| 13 | craft 1 chain_net | craft 2 iron_nugget | craft 2 iron_nugget | craft 2 iron_nugget | 合法；产量2；损血2 | False |
| 14 | craft 1 chain_net | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血2 | False |
| 15 | craft 1 chain_net | inspect iron_nugget | inspect iron_nugget | inspect iron_nugget | 合法；产量0；损血2 | False |
| 16 | craft 1 chain_net | store 2 iron_nugget inventory | store 2 iron_nugget inventory | store 2 iron_nugget inventory | 合法；产量0；损血6 | False |
| 17 | craft 1 chain_net | craft 2 iron_bar | craft 2 iron_bar | craft 2 iron_bar | 合法；产量1；损血2 | False |
| 18 | talk to sarah_cole | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血2 | False |
| 19 | craft 1 chain_net | inspect iron_bar | inspect iron_bar | inspect iron_bar | 合法；产量0；损血2 | False |
| 20 | craft 1 sinew_cord | store 1 iron_bar inventory | store 1 iron_bar inventory | store 1 iron_bar inventory | 合法；产量0；损血4 | False |
| 21 | craft 2 sinew_cord | craft 2 sinew_cord | craft 2 sinew_cord | craft 2 sinew_cord | 合法；产量2；损血4 | False |
| 22 | craft 2 iron_nugget | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血4 | False |
| 23 | pick up sinew_cord | store 2 sinew_cord inventory | store 2 sinew_cord inventory | store 2 sinew_cord inventory | 合法；产量0；损血4 | False |
| 24 | craft 4 iron_nugget | craft 2 iron_nugget | craft 2 iron_nugget | craft 2 iron_nugget | 合法；产量2；损血0 | False |
| 25 | pick up iron_nugget | pick up iron_nugget | pick up iron_nugget | pick up iron_nugget | 合法；产量0；损血2 | False |
| 26 | craft 4 iron_nugget | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血2 | False |
| 27 | pick up iron_nugget | store 1 iron_nugget inventory | store 1 iron_nugget inventory | store 1 iron_nugget inventory | 合法；产量0；损血2 | False |
| 28 | pick up iron_nugget | store 1 iron_nugget inventory | store 1 iron_nugget inventory | store 1 iron_nugget inventory | 合法；产量0；损血4 | False |
| 29 | craft 1 iron_bar | craft 2 iron_bar | craft 2 iron_bar | craft 2 iron_bar | 合法；产量1；损血0 | False |
| 30 | pick up iron_bar | pick up iron_bar | pick up iron_bar | pick up iron_bar | 合法；产量0；损血2 | False |
| 31 | scavenge | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血2 | False |
| 32 | craft 1 iron_bar | craft 2 iron_nugget | craft 2 iron_nugget | craft 2 iron_nugget | 合法；产量2；损血0 | False |
| 33 | craft 1 chain_net | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血0 | False |
| 34 | pick up iron_nugget | store 2 iron_nugget inventory | store 2 iron_nugget inventory | store 2 iron_nugget inventory | 合法；产量0；损血2 | False |
| 35 | craft 1 iron_bar | craft 2 iron_bar | craft 2 iron_bar | craft 2 iron_bar | 合法；产量1；损血0 | False |
| 36 | pick up iron_bar | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血0 | False |
| 37 | pick up iron_bar | store 1 iron_bar inventory | store 1 iron_bar inventory | store 2 iron_bar inventory | 合法；产量0；损血0 | False |
| 38 | inspect inventory | craft 1 chain_net | craft 1 chain_net | craft 1 chain_net | 合法；产量1；损血0 | False |
| 39 | pick up chain_net | pick up chain_net | pick up chain_net | pick up chain_net | 合法；产量0；损血0 | True |

## P4

任务：`sequence-6c1d62349d18c4d3-P4-ef4303edb0db`；最终缺失必要配方：`[]`。

| 步 | 模型提案 | 当前公开状态旧S1动作 | P1动作 | 实际动作 | 原生结果 | 目标 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | enter cellar | inspect chain_net | inspect chain_net | inspect chain_net | 合法；产量0；损血0 | False |
| 2 | enter courtyard | inspect salvage_cloth | inspect salvage_cloth | inspect salvage_cloth | 合法；产量0；损血0 | False |
| 3 | enter courtyard | store 1 salvage_cloth inventory | store 1 salvage_cloth inventory | store 1 salvage_cloth inventory | 合法；产量0；损血0 | False |
| 4 | enter courtyard | inspect crown_shard | inspect crown_shard | inspect crown_shard | 合法；产量0；损血0 | False |
| 5 | enter cellar | craft 2 sinew_cord | craft 2 sinew_cord | craft 2 sinew_cord | 拒绝；产量0；损血0 | False |
| 6 | enter courtyard | enter cellar | enter cellar | enter cellar | 合法；产量0；损血0 | False |
| 7 | enter courtyard | inspect scrap_iron | inspect scrap_iron | inspect scrap_iron | 合法；产量0；损血0 | False |
| 8 | enter courtyard | store 6 scrap_iron inventory | store 6 scrap_iron inventory | store 6 scrap_iron inventory | 合法；产量0；损血6 | False |
| 9 | enter courtyard | craft 2 iron_nugget | craft 2 iron_nugget | craft 2 iron_nugget | 拒绝；产量0；损血6 | False |
| 10 | enter courtyard | enter courtyard | enter courtyard | enter courtyard | 合法；产量0；损血6 | False |
| 11 | craft 1 chain_net | inspect crucible | inspect crucible | inspect crucible | 合法；产量0；损血6 | False |
| 12 | craft 1 chain_net | inspect war_bench | inspect war_bench | inspect war_bench | 合法；产量0；损血6 | False |
| 13 | craft 1 chain_net | craft 2 iron_nugget | craft 2 iron_nugget | craft 2 iron_nugget | 合法；产量2；损血2 | False |
| 14 | talk to sarah_cole | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血2 | False |
| 15 | craft 1 chain_net | inspect iron_nugget | inspect iron_nugget | inspect iron_nugget | 合法；产量0；损血2 | False |
| 16 | craft 2 iron_nugget | store 2 iron_nugget inventory | store 2 iron_nugget inventory | store 2 iron_nugget inventory | 合法；产量0；损血6 | False |
| 17 | craft 1 chain_net | craft 2 iron_bar | craft 2 iron_bar | craft 2 iron_bar | 合法；产量1；损血2 | False |
| 18 | craft 1 chain_net | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血2 | False |
| 19 | craft 1 chain_net | inspect iron_bar | inspect iron_bar | inspect iron_bar | 合法；产量0；损血2 | False |
| 20 | craft 1 sinew_cord | store 1 iron_bar inventory | store 1 iron_bar inventory | store 1 iron_bar inventory | 合法；产量0；损血4 | False |
| 21 | craft 4 iron_nugget | craft 2 sinew_cord | craft 2 sinew_cord | craft 2 sinew_cord | 合法；产量2；损血4 | False |
| 22 | pick up sinew_cord | pick up sinew_cord | pick up sinew_cord | pick up sinew_cord | 合法；产量0；损血4 | False |
| 23 | pick up sinew_cord | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血4 | False |
| 24 | pick up sinew_cord | store 2 sinew_cord inventory | store 2 sinew_cord inventory | store 2 sinew_cord inventory | 合法；产量0；损血4 | False |
| 25 | take out scrap_iron scout_satchel_0 | craft 2 iron_nugget | craft 2 iron_nugget | craft 2 iron_nugget | 合法；产量2；损血0 | False |
| 26 | pick up iron_nugget | pick up iron_nugget | pick up iron_nugget | pick up iron_nugget | 合法；产量0；损血2 | False |
| 27 | pick up iron_nugget | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血2 | False |
| 28 | take out scrap_iron scout_satchel_0 | store 1 iron_nugget inventory | store 1 iron_nugget inventory | store 1 iron_nugget inventory | 合法；产量0；损血2 | False |
| 29 | craft 2 iron_nugget | store 1 iron_nugget inventory | store 1 iron_nugget inventory | store 1 iron_nugget inventory | 合法；产量0；损血4 | False |
| 30 | craft 1 chain_net | craft 2 iron_bar | craft 2 iron_bar | craft 2 iron_bar | 合法；产量1；损血0 | False |
| 31 | pick up iron_bar | pick up iron_bar | pick up iron_bar | pick up iron_bar | 合法；产量0；损血2 | False |
| 32 | craft 1 chain_net | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血2 | False |
| 33 | craft 1 iron_bar | craft 2 iron_nugget | craft 2 iron_nugget | craft 2 iron_nugget | 合法；产量2；损血0 | False |
| 34 | pick up iron_nugget | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血0 | False |
| 35 | pick up iron_nugget | store 2 iron_nugget inventory | store 2 iron_nugget inventory | store 2 iron_nugget inventory | 合法；产量0；损血2 | False |
| 36 | craft 1 iron_bar | craft 2 iron_bar | craft 2 iron_bar | craft 2 iron_bar | 合法；产量1；损血0 | False |
| 37 | pick up iron_bar | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血0 | False |
| 38 | pick up iron_bar | store 1 iron_bar inventory | store 1 iron_bar inventory | store 1 iron_bar inventory | 合法；产量0；损血0 | False |
| 39 | pick up iron_bar | store 1 iron_bar inventory | store 1 iron_bar inventory | store 1 iron_bar inventory | 合法；产量0；损血0 | False |
| 40 | craft 1 chain_net | craft 1 chain_net | craft 1 chain_net | craft 1 chain_net | 合法；产量1；损血0 | False |

## P5

任务：`sequence-6c1d62349d18c4d3-P5-ef4303edb0db`；最终缺失必要配方：`[]`。

| 步 | 模型提案 | 当前公开状态旧S1动作 | P1动作 | 实际动作 | 原生结果 | 目标 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | enter courtyard | inspect chain_net | inspect chain_net | inspect chain_net | 合法；产量0；损血0 | False |
| 2 | enter courtyard | inspect salvage_cloth | inspect salvage_cloth | inspect salvage_cloth | 合法；产量0；损血0 | False |
| 3 | enter courtyard | store 1 salvage_cloth inventory | store 1 salvage_cloth inventory | store 1 salvage_cloth inventory | 合法；产量0；损血0 | False |
| 4 | enter courtyard | inspect crown_shard | inspect crown_shard | inspect crown_shard | 合法；产量0；损血0 | False |
| 5 | enter courtyard | craft 2 sinew_cord | craft 2 sinew_cord | craft 2 sinew_cord | 拒绝；产量0；损血0 | False |
| 6 | enter courtyard | enter cellar | enter cellar | enter cellar | 合法；产量0；损血0 | False |
| 7 | enter courtyard | inspect scrap_iron | inspect scrap_iron | inspect scrap_iron | 合法；产量0；损血0 | False |
| 8 | enter courtyard | store 6 scrap_iron inventory | store 6 scrap_iron inventory | store 6 scrap_iron inventory | 合法；产量0；损血6 | False |
| 9 | enter courtyard | craft 2 iron_nugget | craft 2 iron_nugget | craft 2 iron_nugget | 拒绝；产量0；损血6 | False |
| 10 | enter courtyard | enter courtyard | enter courtyard | enter courtyard | 合法；产量0；损血6 | False |
| 11 | craft 1 chain_net | inspect crucible | inspect crucible | inspect crucible | 合法；产量0；损血6 | False |
| 12 | craft 1 chain_net | inspect war_bench | inspect war_bench | inspect war_bench | 合法；产量0；损血6 | False |
| 13 | craft 1 chain_net | craft 2 iron_nugget | craft 2 iron_nugget | craft 2 iron_nugget | 合法；产量2；损血2 | False |
| 14 | craft 1 chain_net | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血2 | False |
| 15 | craft 1 chain_net | inspect iron_nugget | inspect iron_nugget | inspect iron_nugget | 合法；产量0；损血2 | False |
| 16 | talk to sarah_cole | store 2 iron_nugget inventory | store 2 iron_nugget inventory | store 2 iron_nugget inventory | 合法；产量0；损血6 | False |
| 17 | craft 1 chain_net | craft 2 iron_bar | craft 2 iron_bar | craft 2 iron_bar | 合法；产量1；损血2 | False |
| 18 | talk to sarah_cole | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血2 | False |
| 19 | talk to sarah_cole | inspect iron_bar | inspect iron_bar | inspect iron_bar | 合法；产量0；损血2 | False |
| 20 | craft 1 chain_net | store 1 iron_bar inventory | store 1 iron_bar inventory | store 1 iron_bar inventory | 合法；产量0；损血4 | False |
| 21 | craft 2 sinew_cord | craft 2 sinew_cord | craft 2 sinew_cord | craft 2 sinew_cord | 合法；产量2；损血4 | False |
| 22 | pick up sinew_cord | pick up sinew_cord | pick up sinew_cord | pick up sinew_cord | 合法；产量0；损血4 | False |
| 23 | pick up sinew_cord | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血4 | False |
| 24 | pick up sinew_cord | store 2 sinew_cord inventory | store 2 sinew_cord inventory | store 2 sinew_cord inventory | 合法；产量0；损血4 | False |
| 25 | craft 1 chain_net | craft 2 iron_nugget | craft 2 iron_nugget | craft 2 iron_nugget | 合法；产量2；损血0 | False |
| 26 | pick up iron_nugget | pick up iron_nugget | pick up iron_nugget | pick up iron_nugget | 合法；产量0；损血2 | False |
| 27 | pick up iron_nugget | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血2 | False |
| 28 | craft 1 iron_nugget | store 1 iron_nugget inventory | store 1 iron_nugget inventory | store 1 iron_nugget inventory | 合法；产量0；损血2 | False |
| 29 | craft 2 iron_nugget | store 1 iron_nugget inventory | store 1 iron_nugget inventory | store 1 iron_nugget inventory | 合法；产量0；损血4 | False |
| 30 | inspect inventory | craft 2 iron_bar | craft 2 iron_bar | craft 2 iron_bar | 合法；产量1；损血0 | False |
| 31 | pick up iron_bar | pick up iron_bar | pick up iron_bar | pick up iron_bar | 合法；产量0；损血2 | False |
| 32 | craft 1 iron_nugget | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血2 | False |
| 33 | craft 2 iron_nugget | craft 2 iron_nugget | craft 2 iron_nugget | craft 2 iron_nugget | 合法；产量2；损血0 | False |
| 34 | pick up iron_nugget | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血0 | False |
| 35 | pick up iron_nugget | store 2 iron_nugget inventory | store 2 iron_nugget inventory | store 2 iron_nugget inventory | 合法；产量0；损血2 | False |
| 36 | craft 1 iron_bar | craft 2 iron_bar | craft 2 iron_bar | craft 2 iron_bar | 合法；产量1；损血0 | False |
| 37 | pick up iron_bar | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血0 | False |
| 38 | pick up iron_bar | store 1 iron_bar inventory | store 1 iron_bar inventory | store 1 iron_bar inventory | 合法；产量0；损血0 | False |
| 39 | pick up iron_bar | store 1 iron_bar inventory | store 1 iron_bar inventory | store 1 iron_bar inventory | 合法；产量0；损血0 | False |
| 40 | craft 1 chain_net | craft 1 chain_net | craft 1 chain_net | craft 1 chain_net | 合法；产量1；损血0 | False |

## P6

任务：`sequence-6c1d62349d18c4d3-P6-ef4303edb0db`；最终缺失必要配方：`[]`。

| 步 | 模型提案 | 当前公开状态旧S1动作 | P1动作 | 实际动作 | 原生结果 | 目标 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | enter courtyard | inspect chain_net | inspect chain_net | inspect chain_net | 合法；产量0；损血0 | False |
| 2 | enter courtyard | inspect salvage_cloth | inspect salvage_cloth | inspect salvage_cloth | 合法；产量0；损血0 | False |
| 3 | enter courtyard | store 1 salvage_cloth inventory | store 1 salvage_cloth inventory | store 1 salvage_cloth inventory | 合法；产量0；损血0 | False |
| 4 | enter courtyard | inspect crown_shard | inspect crown_shard | inspect crown_shard | 合法；产量0；损血0 | False |
| 5 | enter courtyard | craft 2 sinew_cord | craft 2 sinew_cord | craft 2 sinew_cord | 拒绝；产量0；损血0 | False |
| 6 | enter cellar | enter cellar | enter cellar | enter cellar | 合法；产量0；损血0 | False |
| 7 | enter courtyard | inspect scrap_iron | inspect scrap_iron | inspect scrap_iron | 合法；产量0；损血0 | False |
| 8 | enter courtyard | store 6 scrap_iron inventory | store 6 scrap_iron inventory | store 6 scrap_iron inventory | 合法；产量0；损血6 | False |
| 9 | enter courtyard | craft 2 iron_nugget | craft 2 iron_nugget | craft 2 iron_nugget | 拒绝；产量0；损血6 | False |
| 10 | enter courtyard | enter courtyard | enter courtyard | enter courtyard | 合法；产量0；损血6 | False |
| 11 | craft 1 chain_net | inspect crucible | inspect crucible | inspect crucible | 合法；产量0；损血6 | False |
| 12 | craft 1 chain_net | inspect war_bench | inspect war_bench | inspect war_bench | 合法；产量0；损血6 | False |
| 13 | craft 1 chain_net | craft 2 iron_nugget | craft 2 iron_nugget | craft 2 iron_nugget | 合法；产量2；损血2 | False |
| 14 | craft 1 chain_net | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血2 | False |
| 15 | craft 1 chain_net | inspect iron_nugget | inspect iron_nugget | inspect iron_nugget | 合法；产量0；损血2 | False |
| 16 | talk to sarah_cole | store 2 iron_nugget inventory | store 2 iron_nugget inventory | store 2 iron_nugget inventory | 合法；产量0；损血6 | False |
| 17 | craft 1 chain_net | craft 2 iron_bar | craft 2 iron_bar | craft 2 iron_bar | 合法；产量1；损血2 | False |
| 18 | craft 1 chain_net | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血2 | False |
| 19 | craft 1 chain_net | inspect iron_bar | inspect iron_bar | inspect iron_bar | 合法；产量0；损血2 | False |
| 20 | craft 1 sinew_cord | store 1 iron_bar inventory | store 1 iron_bar inventory | store 1 iron_bar inventory | 合法；产量0；损血4 | False |
| 21 | craft 2 sinew_cord | craft 2 sinew_cord | craft 2 sinew_cord | craft 2 sinew_cord | 合法；产量2；损血4 | False |
| 22 | pick up sinew_cord | pick up sinew_cord | pick up sinew_cord | pick up sinew_cord | 合法；产量0；损血4 | False |
| 23 | pick up sinew_cord | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血4 | False |
| 24 | pick up sinew_cord | store 2 sinew_cord inventory | store 2 sinew_cord inventory | store 2 sinew_cord inventory | 合法；产量0；损血4 | False |
| 25 | craft 2 iron_nugget | craft 2 iron_nugget | craft 2 iron_nugget | craft 2 iron_nugget | 合法；产量2；损血0 | False |
| 26 | pick up iron_nugget | pick up iron_nugget | pick up iron_nugget | pick up iron_nugget | 合法；产量0；损血2 | False |
| 27 | craft 2 iron_nugget | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血2 | False |
| 28 | craft 2 iron_nugget | store 1 iron_nugget inventory | store 1 iron_nugget inventory | store 1 iron_nugget inventory | 合法；产量0；损血2 | False |
| 29 | craft 2 iron_nugget | store 1 iron_nugget inventory | store 1 iron_nugget inventory | store 1 iron_nugget inventory | 合法；产量0；损血4 | False |
| 30 | craft 1 iron_bar | craft 2 iron_bar | craft 2 iron_bar | craft 2 iron_bar | 合法；产量1；损血0 | False |
| 31 | craft 1 chain_net | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血0 | False |
| 32 | craft 2 iron_nugget | store 1 iron_bar inventory | store 1 iron_bar inventory | store 1 iron_bar inventory | 合法；产量0；损血2 | False |
| 33 | craft 2 iron_nugget | craft 2 iron_nugget | craft 2 iron_nugget | craft 2 iron_nugget | 合法；产量2；损血0 | False |
| 34 | pick up iron_nugget | pick up iron_nugget | pick up iron_nugget | pick up iron_nugget | 合法；产量0；损血0 | False |
| 35 | craft 2 iron_bar | craft 3 iron_bar | craft 3 iron_bar | craft 3 iron_bar | 拒绝；产量0；损血0 | False |
| 36 | pick up iron_nugget | store 2 iron_nugget inventory | store 2 iron_nugget inventory | store 2 iron_nugget inventory | 合法；产量0；损血2 | False |
| 37 | craft 2 iron_nugget | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血2 | False |
| 38 | craft 1 iron_bar | craft 2 iron_bar | craft 2 iron_bar | craft 2 iron_bar | 合法；产量1；损血0 | False |
| 39 | pick up iron_bar | pick up iron_bar | pick up iron_bar | pick up iron_bar | 合法；产量0；损血0 | False |
| 40 | craft 1 iron_bar | inspect inventory | inspect inventory | inspect inventory | 合法；产量0；损血0 | False |
