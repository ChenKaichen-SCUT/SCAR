# Failure-to-Recovery 分类统计

|实际在线阶段/代理指标|全事件|仅母轨迹|
|---|---|---|
|下一决策明确提及正确缺口（规则命中）|292/334（87.4%）|31/34（91.2%）|
|新结构化恢复目标|18/334（5.4%）|2/34（5.9%）|
|较宽口径：新目标或理由中的恢复意图|237/334（71.0%）|22/34（64.7%）|
|20 步内至少一个被接受的相关恢复动作|279/302（92.4%）|30/32（93.8%）|
|20 步内至少两个相邻的相关恢复动作|149/302（49.3%）|20/32（62.5%）|
|20 步内原失败动作成功|114/260（43.8%）|11/30（36.7%）|
|先有相关恢复动作，再原动作成功|109/260（41.9%）|11/30（36.7%）|
|原 goal 字符串切换后返回|2/302（0.7%）|2/32（6.2%）|
|20 步内主线奖励增加的事件窗口|8/302（2.6%）|6/32（18.8%）|


下一决策三分类（另列无后续动作）：

|类别|数量|
|---|---|
|Failure acknowledged only|74|
|Recovery objective generated|237|
|No recovery|23|
|Unobserved|2|


## 按缺口分类

|缺口类型|事件|下一步理解|新 goal|恢复意图|完整窗口|局部闭环/适用|
|---|---|---|---|---|---|---|
|combat_blocks_exit|32|28/31|4|28|29|13/29|
|container_capacity|15|15/15|1|10|13|3/13|
|container_nesting|9|8/9|2|9|9|0/0|
|equipment_slot_occupied|4|3/4|0|4|4|1/4|
|hand_capacity|114|109/114|5|99|104|66/104|
|insufficient_ingredients|30|24/30|2|9|20|1/20|
|locked_exit|26|21/26|1|8|26|6/26|
|missing_furnace|1|1/1|0|0|1|0/1|
|missing_lockpick_tool|5|5/5|0|5|5|0/5|
|missing_workbench|8|6/7|0|3|7|1/7|
|missing_writing_tool|19|16/19|0|13|19|10/19|
|no_path|5|2/5|0|5|3|1/3|
|not_craftable|4|1/4|0|2|2|0/0|
|not_edible|1|1/1|0|1|1|0/0|
|not_equippable|20|16/20|0|12|20|0/0|
|not_writable|7|5/7|1|4|7|0/0|
|object_not_held_or_visible|12|8/12|0|10|11|0/11|
|object_unavailable|10|10/10|0|5|7|0/7|
|target_not_held|10|10/10|2|8|10|7/10|
|unknown_object|3|3/3|0|2|3|0/0|
|unspecified_rejection|1|0/1|0|0|1|0/1|


## 口径与重算

这些是相关轨迹上的描述统计。336 个事件来自 1 条母轨迹及其 10 条既有分支，窗口重叠；不能视作 336 个独立游戏。规则检测的“理解”是实际 reasoning 提及缺口，不等同整个世界状态理解正确。宽口径恢复意图不等同合格子计划，相关动作被接受也可能只是丢下/捡回。只有 302 个事件有完整 20 步窗口，另外 34 个右删失；其中不可装备、不可制作等本身无效动作不纳入原动作应成功的分母，最终该分母为 260。所有事件仍保留在数据库中。

拒绝/接受沿用冻结的公开反馈提取器与原生 invalid-action 标志，是可重算代理，不是全量独立人工动作效用审查。本轮 Oracle parent_a054 第 73 步 “Failed to lockpick…already unlocked” 未命中冻结拒绝正则；补充字段 supplemental_failure_steps 保留此负面反馈，表中明确区分，不改变预登记原动作恢复统计。336 个历史事件窗口的原动作成功未发现这类标记冲突。所有原始反馈保留。goal 字符串未返回不能推出未恢复原任务，等价改写、合法替代路径与生存优先都需要语义核验。全部 10 个配对的前 20 步由本助手核对原文，非独立人工盲审。


四阶段不是简单漏斗：原 Agent 可能没有改 goal 字段，却用原目标下的动作恢复；也可能合理放弃原失败动作。不同分母已经明列，不得拿 18/334 与 109/260 相减当作转化流失。

[results/stage28/failure_recovery_database.jsonl.gz](../../results/stage28/failure_recovery_database.jsonl.gz) 为全部 336 事件的完整数据库：失败前 observation、inventory、location、goal、动作、公开反馈、历史动作、后 5/20 步及最终结果、源文件/行号均可追溯。[results/stage28/failure_recovery_chains.jsonl.gz](../../results/stage28/failure_recovery_chains.jsonl.gz) 保留命中理由原句。分类规则冻结在 [scar_stage28/chain.py](../../scar_stage28/chain.py)；无新增分析模型调用。
