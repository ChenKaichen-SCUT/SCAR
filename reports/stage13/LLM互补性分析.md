# LLM 互补性分析

**当前没有证据支持在 S1 上增加 LLM 语义探索决策。** J3 的原始四步指标仍为新增 4、丢失 8、净 −4；4 个正例分布于 4 个 family，但合并同 family 的负例后只有 1 个 family 净正。预冻结的单一公开互补条件 L 未触发，结果等于 S1。这个结论针对本轮条件，不能证明所有可能的简单条件都不存在。

## 全部 12 个差异状态


|状态|family|正/负|S1 路径及必要配方|J3 路径及必要配方|不同 Top3 是否含有效|下位有效候选|
|---|---|---|---|---|---|---|
|[d12_2bd7c9c561fcf61b](states/d12_2bd7c9c561fcf61b.md)|fiend_helm|loss|inspect devil_oil / hellcoal_concentrate|enter cellar → enter courtyard → inspect war_bench / |False||
|[d12_508fa7a07ea3f787](states/d12_508fa7a07ea3f787.md)|bandage_roll|loss|inspect salvage_cloth / bandage_roll,sinew_cord|enter cellar → enter courtyard → inspect war_bench / |True|c_8ecb614a6055|
|[d12_0332450ff72f2d8b](states/d12_0332450ff72f2d8b.md)|fiend_alloy_scale|gain|inspect crucible / |craft 2 fiend_alloy → inspect fiend_alloy / fiend_alloy_sheet|True||
|[d12_b396f69cf0969c6b](states/d12_b396f69cf0969c6b.md)|fiend_alloy_scale|loss|inspect fiend_alloy_sheet / fiend_alloy_scale|inspect fiend_alloy_scale / |True|c_4957886b01fc|
|[d12_044e21425b224134](states/d12_044e21425b224134.md)|brimite_blade_blank|loss|inspect brimite_ingot / brimite_blade_blank|inspect brimite_blade_blank / |True|c_d6fbc47d772b|
|[d12_4892e4fbb1fad417](states/d12_4892e4fbb1fad417.md)|fiend_rivet|loss|inspect fiend_plate / fiend_strip|enter cellar → enter courtyard → inspect war_bench / |True|c_d63a71475678|
|[d12_2b682b0f9a8b12f4](states/d12_2b682b0f9a8b12f4.md)|fiend_rivet|gain|inspect inventory / |inspect fiend_strip / fiend_rivet|True||
|[d12_996d46f5a59bfdc4](states/d12_996d46f5a59bfdc4.md)|chain_net|gain|inspect crucible / |craft 2 sinew_cord → inspect sinew_cord / chain_net|True|c_615176e11dc7|
|[d12_a92f408263c9541e](states/d12_a92f408263c9541e.md)|hellfire_bomb|loss|inspect rubble / rubble_chunk|enter cellar → enter courtyard → inspect war_bench / |False||
|[d12_c22b3ec6c829109c](states/d12_c22b3ec6c829109c.md)|hunter_gauntlets|loss|inspect sinew_cord / hunter_gauntlets,war_strap|enter cellar → enter courtyard → inspect war_bench / |True|c_1c1c73203a7d|
|[d12_5053683c26d2e1de](states/d12_5053683c26d2e1de.md)|hunter_gauntlets|gain|inspect crucible / |craft 2 iron_nugget → inspect iron_nugget / iron_bar|True||
|[d12_db9cf8a8d4ddadac](states/d12_db9cf8a8d4ddadac.md)|padded_tunic|loss|inspect sinew_cord / padded_tunic|enter cellar → enter courtyard → inspect war_bench / |False||

四个正例中，scale、chain_net、hunter_gauntlets 是“公开配方制作→检查产物”；rivet 是检查已有新产物。它们可由普通短计划产生，不证明名称语义预测准确。scale 的解释还将后续信息源说成工作台，而实际收益来自产物检查。八个负例中六个优先访问工作台，两个重复检查最终目标；工作台确是公开执行前提，但不等价于未知配方的信息入口。

## 去重后的返回排名

按照检查目标合并 inspect/visit，按照制作并检查的产物合并不同批量的 craft 意图；运输原子动作单独保留。保留原排名第一次出现的代表，不从低于 Top3 的未返回候选补位，不挑别名中结果更好的分支。

原返回 148 个 ID，实际 143 个不同方向；5 个状态有重复排名意图，同意图别名的必要知识结果分歧为 0。去重 Top3 覆盖 15/50（15/27 有机会状态），Top2 覆盖 11/50。首选无用但较低排名有效有 9 例；另有 12 例菜单存在机会却未返回有效方向。

J0/J3 实际探索意图相同 12/50；J3 首选未关联入口带来知识为 0，不同 Top3 中为 3。不能把排名覆盖当成已经执行的收益，也不能无成本试遍 Top3。

## 可观测互补条件

L 只在 C2 的停滞/冷却触发成立、J3 提出从未尝试且未检查、有公开制作配方、估计成本有界的新方向时启用，并沿用 C3 的执行保护。方向成本来自公开路线和材料条件；实际原生动作数仅在诊断表中独立列出。四个正例都有此前关于所选物品的尝试记录，多数没有达到无进展门槛或处在入口冷却期，因此 L 没有调用它们。保持阈值冻结，不根据四个正例反推“更合适”的门槛。

公开关系支持分为：已有配方/依赖、只有工作台前提、已有试制配方但下游连接未证实、仅对象/产物可见。自动统计的“同提及公开边”只作查阅索引，不是对推理正确性的语义证明。仅凭生成解释无法证明模型主要依赖名称联想；未披露的下游连接始终标为假设。


|公开证据类型|状态数|
|---|---|
|known_station_prerequisite_only|14|
|disclosed_recipe_or_dependency_direction|20|
|disclosed_recipe_direction_plus_unverified_downstream_link|8|
|public_object_or_production_only_no_disclosed_goal_edge|8|

**Oracle Upper Bound：14/50。** 它用事后标签在 J0/J3 中逐状态取优，保留 10 并增加 4；不可实现、未训练、未部署，不能作为融合算法的结果。

## 其余 38 例与全部公开特征

所有状态都保留在下表和独立证据页中。配方是否完整是当前公开表的保守判断；新知识间隔与原生必要关系不同。字段来源和全量值见 [50 行配对数据](../../results/stage13/llm_pairs.json)、[按配对类别的公开条件分布](../../results/stage13/llm_summary.json)。


|状态|类别|同方向|公开无进展步数|独立入口数|新产物|J3 先前尝试|重复检查/工作台|公开配方支持|估计 J0/J3 步数|实际 J0/J3 步数|
|---|---|---|---|---|---|---|---|---|---|---|
|[d12_b2926ff775c6769c](states/d12_b2926ff775c6769c.md)|both_no_necessary_information|False|0|1|False|False|True|False|None/3|1/3|
|[d12_1c4969f7d6f4b0fc](states/d12_1c4969f7d6f4b0fc.md)|both_no_necessary_information|False|1|0|False|True|True|False|1/1|1/1|
|[d12_437b4653a9a80655](states/d12_437b4653a9a80655.md)|both_no_necessary_information|True|0|0|False|True|True|True|None/None|1/1|
|[d12_0e9af1845a24d13b](states/d12_0e9af1845a24d13b.md)|both_no_necessary_information|True|3|0|True|True|False|True|1/1|1/1|
|[d12_1cd1a634b22e2a0a](states/d12_1cd1a634b22e2a0a.md)|both_no_necessary_information|True|2|0|False|True|False|False|None/None|1/1|
|[d12_2bd7c9c561fcf61b](states/d12_2bd7c9c561fcf61b.md)|loss|False|0|5|False|False|True|False|1/3|1/3|
|[d12_8d93a9fe38ae0edb](states/d12_8d93a9fe38ae0edb.md)|both_no_necessary_information|False|0|1|False|False|False|False|1/None|1/1|
|[d12_b5a72f68b5457ab1](states/d12_b5a72f68b5457ab1.md)|both_no_necessary_information|False|0|0|False|True|True|False|None/1|1/1|
|[d12_cbcc6b27dabe6ad3](states/d12_cbcc6b27dabe6ad3.md)|both_useful|True|1|0|True|True|False|True|1/1|1/1|
|[d12_1a6be59b8adf2971](states/d12_1a6be59b8adf2971.md)|both_no_necessary_information|False|3|1|False|True|True|False|None/1|1/1|
|[d12_2b84d3d36487c9b2](states/d12_2b84d3d36487c9b2.md)|both_no_necessary_information|False|0|0|False|False|True|False|None/3|1/3|
|[d12_84a8b7d14c832282](states/d12_84a8b7d14c832282.md)|both_no_necessary_information|True|1|1|True|True|True|True|2/2|1/1|
|[d12_508fa7a07ea3f787](states/d12_508fa7a07ea3f787.md)|loss|False|0|1|False|False|True|False|1/3|1/3|
|[d12_053962d91bc03253](states/d12_053962d91bc03253.md)|both_no_necessary_information|False|0|2|True|True|False|True|1/1|1/1|
|[d12_0ee9424f300fd429](states/d12_0ee9424f300fd429.md)|both_no_necessary_information|True|1|0|False|True|True|True|2/2|1/1|
|[d12_1112504715d6d930](states/d12_1112504715d6d930.md)|both_no_necessary_information|False|0|2|False|False|True|False|None/3|1/3|
|[d12_0332450ff72f2d8b](states/d12_0332450ff72f2d8b.md)|gain|False|2|0|False|True|False|True|1/2|1/2|
|[d12_e2783165405ff34b](states/d12_e2783165405ff34b.md)|both_no_necessary_information|False|0|0|False|True|True|False|None/1|1/1|
|[d12_b396f69cf0969c6b](states/d12_b396f69cf0969c6b.md)|loss|False|1|0|True|True|True|False|1/1|1/1|
|[d12_3a1444e457139495](states/d12_3a1444e457139495.md)|both_no_necessary_information|False|0|0|True|True|True|False|1/1|1/1|
|[d12_17c5deb0c6ac6acf](states/d12_17c5deb0c6ac6acf.md)|both_no_necessary_information|False|0|1|False|False|True|False|None/3|1/3|
|[d12_03a8396e3b50ad83](states/d12_03a8396e3b50ad83.md)|both_no_necessary_information|False|1|0|False|False|True|False|1/1|1/1|
|[d12_2310e2d3684d6e00](states/d12_2310e2d3684d6e00.md)|both_no_necessary_information|True|0|0|False|True|True|True|None/None|1/1|
|[d12_044e21425b224134](states/d12_044e21425b224134.md)|loss|False|1|0|True|True|True|False|1/1|1/1|
|[d12_9b491521dcc01365](states/d12_9b491521dcc01365.md)|both_no_necessary_information|False|14|0|False|True|True|False|None/1|1/1|
|[d12_7aba559853f3978b](states/d12_7aba559853f3978b.md)|both_no_necessary_information|False|0|1|False|False|True|False|None/3|1/3|
|[d12_1e291e83c3ae6288](states/d12_1e291e83c3ae6288.md)|both_no_necessary_information|False|4|0|False|False|True|False|1/1|1/1|
|[d12_4892e4fbb1fad417](states/d12_4892e4fbb1fad417.md)|loss|False|0|2|False|False|True|False|1/3|1/3|
|[d12_27d4508a1abb9ee2](states/d12_27d4508a1abb9ee2.md)|both_useful|True|1|0|True|True|False|True|1/1|1/1|
|[d12_2b682b0f9a8b12f4](states/d12_2b682b0f9a8b12f4.md)|gain|False|0|1|True|True|False|True|1/1|1/1|
|[d12_8694b7913dc729f7](states/d12_8694b7913dc729f7.md)|both_no_necessary_information|False|0|1|False|False|True|False|None/3|1/3|
|[d12_996d46f5a59bfdc4](states/d12_996d46f5a59bfdc4.md)|gain|False|2|0|False|True|False|True|1/2|1/2|
|[d12_eaae67b21b57e5d9](states/d12_eaae67b21b57e5d9.md)|both_no_necessary_information|False|0|0|False|True|True|False|None/1|1/1|
|[d12_b5e67d08463a4c9c](states/d12_b5e67d08463a4c9c.md)|both_no_necessary_information|True|1|0|True|True|True|True|2/2|1/1|
|[d12_3a50cbb76467507a](states/d12_3a50cbb76467507a.md)|both_no_necessary_information|True|1|0|True|True|True|True|2/2|1/1|
|[d12_a92f408263c9541e](states/d12_a92f408263c9541e.md)|loss|False|0|4|False|False|True|False|1/3|1/3|
|[d12_01c83c35e4b3f13b](states/d12_01c83c35e4b3f13b.md)|both_no_necessary_information|False|2|2|False|False|True|True|1/2|1/2|
|[d12_7a79977e9ab99d44](states/d12_7a79977e9ab99d44.md)|both_no_necessary_information|False|0|0|False|True|True|False|None/1|1/1|
|[d12_2964f51279aa9f71](states/d12_2964f51279aa9f71.md)|both_no_necessary_information|False|5|0|True|True|True|False|None/1|1/1|
|[d12_50b2047c44eb9489](states/d12_50b2047c44eb9489.md)|both_no_necessary_information|False|5|0|False|True|True|False|1/1|1/1|
|[d12_c22b3ec6c829109c](states/d12_c22b3ec6c829109c.md)|loss|False|0|2|False|False|True|False|1/3|1/3|
|[d12_5053683c26d2e1de](states/d12_5053683c26d2e1de.md)|gain|False|3|0|False|True|False|True|1/2|1/2|
|[d12_edea7c24b75cf3bb](states/d12_edea7c24b75cf3bb.md)|both_no_necessary_information|True|0|0|False|True|True|True|None/None|1/1|
|[d12_b722bac888259e22](states/d12_b722bac888259e22.md)|both_no_necessary_information|False|0|0|True|True|False|True|1/1|1/1|
|[d12_2f6a0c1e72839f91](states/d12_2f6a0c1e72839f91.md)|both_no_necessary_information|False|0|0|True|True|False|True|None/2|1/4|
|[d12_db9cf8a8d4ddadac](states/d12_db9cf8a8d4ddadac.md)|loss|False|0|2|False|False|True|False|1/3|1/3|
|[d12_61af4f652315aaae](states/d12_61af4f652315aaae.md)|both_no_necessary_information|False|0|2|True|True|False|True|1/1|1/1|
|[d12_dc6e7aaa56e84ae2](states/d12_dc6e7aaa56e84ae2.md)|both_no_necessary_information|False|0|0|False|False|True|False|None/2|1/2|
|[d12_44fff422fc987cfb](states/d12_44fff422fc987cfb.md)|both_no_necessary_information|False|0|1|True|True|False|True|1/1|1/1|
|[d12_ab8371feb0410772](states/d12_ab8371feb0410772.md)|both_no_necessary_information|True|0|1|False|True|True|True|None/None|1/1|

## 成本与执行负面结果


|方法|必要知识状态|总动作|拒绝动作|无新公开配方重复检查|无产出制作|环境损失状态|已知执行延迟状态|可完成目标动作被改写且窗口未完成|
|---|---|---|---|---|---|---|---|---|
|C0|10|50|3|4|3|3|0|0|
|J3|6|82|2|13|2|3|2|1|
|L|10|50|3|4|3|3|0|0|

最后一列只是短窗口内错失即时执行的诊断，不是完整任务失败。J3 替换一次可实际制作的最终 bandage_roll 动作为库存检查后，四步窗口没完成；完整原生反馈见该状态页。纯覆盖 C2/C3 仅恢复了 J3 未恢复的铁条检查状态，而且该增益由解析格式差异解释；两种方案都未达到采用门槛。

扩大公开文本识别后，J0 为 11、J3 仍为 6，J3 变为新增 4、丢失 9；这是补充敏感性，原 4/8 主结果保留。
