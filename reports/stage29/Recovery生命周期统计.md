# Recovery 生命周期统计

|阶段|失败/未观察到数量|分母及解释|
|---|---|---|
|0 未进入恢复状态|0/10|全部首步提出并登记恢复目标|
|1 不理解临时目标|0/10|理由理解缺口，不等于所有材料/状态都理解正确|
|2 完全没有中间条件或步骤|0/10|6 个局部可操作；4 个部分、未解依赖或错误材料计划|
|3 临时条件未得到完成证据|4/10|不是对潜在未尝试条件的穷尽证明；部分选择了替代路径|
|3 原失败动作在完整后缀未成功|5/10|设施已恢复但材料仍不足、替代方案和生存中断均保留|
|4 原动作成功后全程无语义回归证据|0/5|仅对 5 个原动作已恢复过程计分；不把剩余 5 个混入|
|4 未在检查点后20步内观察到语义回归|1/5|parent_a136；至212已有明确装备探索，不是始终未回归|


|检查点|局部条件证据步|原动作成功 Original/Oracle（全后缀）|Oracle 语义回归证据步|恢复规划|
|---|---|---|---|---|
|parent_a031|未证实|[]/[]|不适用|partial_unknown_acquisition|
|parent_a054|56|[]/[56]|58|local_actionable|
|parent_a060|61|[]/[62]|65|local_actionable|
|parent_a113|115|[121]/[115]|130|local_actionable|
|parent_a136|138|[214]/[141]|212|local_actionable|
|parent_a235|未证实|[]/[]|不适用|unsupported_material_plan|
|parent_a270|273|[]/[273]|274|local_actionable|
|oracle032_a256|未证实|[]/[]|不适用|partial_unknown_acquisition|
|oracle037_a122|123|[]/[]|不适用|local_actionable|
|oracle079_a165|未证实|[]/[]|不适用|partial_dependencies|


分解状态为局部可操作6/10、部分/信息依赖未解3/10、错误材料计划1/10；不是“6成功、4没有规划”。工具来源未知、正确配方未进上下文、子组件方法未解分别保留。原动作实际成功与条件满足是两个指标；未重试不是条件从未满足的证据。

## 语义回归与字面返回

Oracle parent_a054 在58改为武器材料采集；parent_a060 在65转武器制作；parent_a113 在130–132收集/存储制作材料；parent_a136 至212明确装备探索；parent_a270 在274回到装备目标。举证时点给出“至此已观察到”，不冒称穷尽所有同义表达后的首次时刻。对应实际原动作成功到举证时点间隔分别为2、3、15、71、1步。

这五个回归都不要求目标字符串完全相等，也不等同主线完成。parent_a113 在126死亡，后续资源重新收集是原方向的行为证据，不证明旧栈被保留。parent_a136 在141明确返回写quiet这一局部任务，而较大装备/容量目标的明确回归较晚；不能把两层混算。

## 目标存储与可见性

|检查点|Oracle目标区间数|归档有原字串/上下文无的动作数|首次原字串不在上下文的动作|
|---|---|---|---|
|parent_a031|44|62|43|
|parent_a054|34|44|56|
|parent_a060|45|42|66|
|parent_a113|43|41|115|
|parent_a136|32|44|138|
|parent_a235|9|55|241|
|parent_a270|7|26|275|
|oracle032_a256|6|43|258|
|oracle037_a122|27|52|128|
|oracle079_a165|24|51|170|


算法根据归档/消息中是否含归一化后的原目标完整字串计数，包含同义扩展中保留该字串的情况；没有该字串不排除语义改写。总计 Original+Oracle 为 876 个动作位置，Oracle为460。归档并未被 summary 输入直接暴露：见 `agents/agc/control.py:summary` 与 `agents/agc_v2/agent.py:_act`。这支持存在架构差异，但不是效果因果实验。

数据：[results/stage29/action_audit.jsonl.gz](../../results/stage29/action_audit.jsonl.gz)、[results/stage29/goal_segments.json](../../results/stage29/goal_segments.json)、[results/stage29/lifecycle_annotations.json](../../results/stage29/lifecycle_annotations.json)、[results/stage29/lifecycle_comparison.json](../../results/stage29/lifecycle_comparison.json)。`timelines/` 包含全部20条完整后缀的逐动作表，不是抽取有利片段。

## 全后缀行为计数

|检查点|版本|动作|公开拒绝|后缀内同动作再次拒绝|目标区间|死亡事件|
|---|---|---|---|---|---|---|
|parent_a031|Original|269|31|9|39|3|
|parent_a031|OracleRecovery|269|43|19|44|5|
|parent_a054|Original|246|26|7|36|3|
|parent_a054|OracleRecovery|246|38|13|34|4|
|parent_a060|Original|240|25|7|34|3|
|parent_a060|OracleRecovery|240|34|13|45|5|
|parent_a113|Original|187|13|2|26|2|
|parent_a113|OracleRecovery|187|26|7|43|4|
|parent_a136|Original|164|10|2|25|2|
|parent_a136|OracleRecovery|164|27|8|32|0|
|parent_a235|Original|65|6|0|9|1|
|parent_a235|OracleRecovery|65|8|0|9|0|
|parent_a270|Original|30|3|0|6|0|
|parent_a270|OracleRecovery|30|8|1|7|0|
|oracle032_a256|Original|44|15|5|8|1|
|oracle032_a256|OracleRecovery|44|5|1|6|1|
|oracle037_a122|Original|178|21|7|41|4|
|oracle037_a122|OracleRecovery|178|20|6|27|6|
|oracle079_a165|Original|135|21|4|23|1|
|oracle079_a165|OracleRecovery|135|20|3|24|3|


同动作再次拒绝只按后缀内相同动作字符串匹配，不要求环境状态相同，因此不是“无意义循环”或“错误重试”的自动判断。目标区间变化可能是同义改写、完成切换、战斗/死亡中断，不能直接计作目标丢失。是否忘记已有进度或没利用资源须查具体证据；oracle037 的146正确记住包中已有材料，与147误判手部空间并存。没有仅按移动/inspect动作把探索计为随机探索，因为无法仅从动作类型识别随机性。

全部结果来自 1 条 remnant 母轨迹及其相关分支，10 对检查点不是 10 个独立游戏；Original 后缀彼此重叠。分析覆盖 3,116 个动作出现位置、2,184 个不同源动作。阶段标注由本助手结合完整时间线和原始决策证据审阅，非独立人工盲审。规则计数与语义判断分开保存，不以代码断言冒称语义标签客观无误。

这里的“原目标”是检查点前 Agent 的目标，不自动等于游戏第一章主线，也不保证原失败动作是必要手段。语义回归只说明行为重新对应原目标，不能证明模型内部保留了父子链接；字符串消失同样不能证明遗忘。未做 Oracle Goal Stack 模型重放，因此不能套用该可选实验的“显著提升/无提升”判据。
