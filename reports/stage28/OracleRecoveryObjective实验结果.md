# Oracle Recovery Objective 实验结果

## 设置与公平性

10 个拒绝后检查点，原始状态/AGC 记忆/控制器一致。7 个来自母轨迹，3 个来自 Stage26 的既有相关分支；独立母轨迹只有 1 条。每个 Original 使用已保存后缀，每个 Oracle 新采样一次，不重跑对照。prompt 唯一新增段落在首个决策及其原生重试中使用；后续完全按原 Agent 输入链。恢复目标来自当前失败反馈，不含配方、位置、行动序列。所有10个 goal 字段与 control_after 都确认采纳。

## 逐检查点结果

下表斜杠为 Original / Oracle；原动作恢复指 20 步内真实执行成功。

|检查点|原失败动作|原动作恢复 O/R|前5拒绝 O/R|最终主线 O/R|Oracle 动作|终止|新请求|费用|
|---|---|---|---|---|---|---|---|---|
|parent_a031|lockpick library|否/否|2/1|1/1|269|step_limit|290|$0.245426|
|parent_a054|pick up iron_bar|否/是|0/1|1/1|246|step_limit|284|$0.232903|
|parent_a060|craft 1 wood_plank|否/是|2/0|1/1|240|step_limit|275|$0.228981|
|parent_a113|take out wooden_rod small_bag_0|是/是|0/2|1/1|187|step_limit|197|$0.164430|
|parent_a136|write quiet paper_7|否/是|0/0|1/1|164|step_limit|186|$0.155616|
|parent_a235|craft 1 torch|否/否|0/1|1/1|65|step_limit|69|$0.058370|
|parent_a270|store 1 cloth small_satchel_0|否/是|0/0|1/1|30|step_limit|32|$0.023411|
|oracle032_a256|craft 1 glass_shard|否/否|1/2|1/1|44|step_limit|48|$0.037516|
|oracle037_a122|craft 1 lockpick|否/否|2/1|1/1|178|step_limit|194|$0.167839|
|oracle079_a165|craft 1 star_metal_sword|否/否|0/1|1/1|135|step_limit|148|$0.117039|


主线提高 0/10、下降 0/10；第一章 0/10 → 0/10。不能把容量释放或无关制作计作主线完成。所有分支均进入汇总，包括没有收益或退步的分支。

“恢复条件”和“恢复原动作”须分开：oracle037_a122 的 Original 125、Oracle 123 均已进入含 workbench 的 hall，设施目标已有公开达成证据，但都未在 20 步内成功 craft lockpick；剩余材料/容量问题仍然存在。parent_a136 的 Oracle 138 取得 pen 后，直到 141 持有 paper 才写字成功。未重试原动作的 Original 也可能曾释放过容量，因此表中“否”仅表示未观察到原动作成功，不表示临时条件从未满足。

## 短期与中期行为

|检查点|版本|5步原动作再拒绝|5步持有增加事件|5步新公开状态|20步新区域事件|20步拒绝 冻结/含补充|20步wait|连续恢复动作代理|原动作成功步|
|---|---|---|---|---|---|---|---|---|---|
|parent_a031|Original|1|0|0|2|4/4|0|否|[]|
|parent_a031|OracleRecovery|1|1|2|1|1/1|0|是|[]|
|parent_a054|Original|0|2|1|0|3/3|0|否|[]|
|parent_a054|OracleRecovery|1|2|1|0|1/2|0|否|[56]|
|parent_a060|Original|0|1|1|0|3/3|0|否|[]|
|parent_a060|OracleRecovery|0|1|4|0|1/1|1|是|[62]|
|parent_a113|Original|0|1|3|0|1/1|0|是|[121]|
|parent_a113|OracleRecovery|0|1|2|0|3/3|0|否|[115]|
|parent_a136|Original|0|0|1|0|2/2|0|否|[]|
|parent_a136|OracleRecovery|0|2|4|0|1/1|1|是|[141]|
|parent_a235|Original|0|1|1|0|0/0|3|是|[]|
|parent_a235|OracleRecovery|0|2|0|0|3/3|0|是|[]|
|parent_a270|Original|0|2|1|0|3/3|0|否|[]|
|parent_a270|OracleRecovery|0|1|3|0|6/6|0|是|[273]|
|oracle032_a256|Original|0|1|3|0|4/4|0|否|[]|
|oracle032_a256|OracleRecovery|0|1|0|0|4/4|0|否|[]|
|oracle037_a122|Original|1|0|1|0|4/4|0|否|[]|
|oracle037_a122|OracleRecovery|0|1|3|0|3/3|0|是|[]|
|oracle079_a165|Original|0|1|3|0|3/3|0|是|[]|
|oracle079_a165|OracleRecovery|0|2|2|0|3/3|0|否|[]|


持有增加只是公开手部/装备数量增加，可能是捡回已拥有物品或黑暗结束后重新可见，不等同获得缺失资源。新状态采用冻结公开状态签名（忽略时间/HP）；战斗或反复搬运造成的变化不等同任务推进。连续恢复动作代理必须结合逐条理由与反馈阅读。

## 隔离原生可行性探针

|检查点|版本|0步|5步|20步|最后状态|
|---|---|---|---|---|---|
|parent_a031|Original|否|否|是|是|
|parent_a031|OracleRecovery|否|否|否|是|
|parent_a054|Original|否|否|否|否|
|parent_a054|OracleRecovery|否|否|是|否|
|parent_a060|Original|否|否|否|否|
|parent_a060|OracleRecovery|否|否|否|否|
|parent_a113|Original|否|是|否|否|
|parent_a113|OracleRecovery|否|否|否|是|
|parent_a136|Original|否|否|否|否|
|parent_a136|OracleRecovery|否|是|否|否|
|parent_a235|Original|否|否|否|否|
|parent_a235|OracleRecovery|否|否|否|否|
|parent_a270|Original|否|否|否|否|
|parent_a270|OracleRecovery|否|否|否|否|
|oracle032_a256|Original|否|否|否|否|
|oracle032_a256|OracleRecovery|否|否|否|否|
|oracle037_a122|Original|否|否|否|否|
|oracle037_a122|OracleRecovery|否|否|否|否|
|oracle079_a165|Original|否|否|否|否|
|oracle079_a165|OracleRecovery|否|否|否|否|


每个探针只在隔离副本重试原失败动作，不改变正式环境，不返回模型。成功说明该时刻原动作可执行；失败可能来自其他缺口或位置变化，不能推断此前从未恢复。探针 0 全拒绝；该表与实际执行成功步是不同测量。

## 异常、成本与复现

|记录类型|数量|
|---|---|
|native_confidence_review|133|
|native_hard_retry|32|
|provider_or_json|11|


confidence_review 是原生目标复审，不是 API 错误；hard_retry 是原有语法约束处理。全部原始响应、请求、重试和终止见 [results/stage28/exceptions.jsonl.gz](../../results/stage28/exceptions.jsonl.gz)。不为不理想输出另行重采样。

新增 1723 请求，4,373,686 输入 / 271,532 输出 token，$1.431532680。费用按每次实际 usage 和当时单价重算，非供应商 invoice。[results/stage28/request_accounting.csv](../../results/stage28/request_accounting.csv) 提供逐请求明细，[results/stage28/paired_comparison.json](../../results/stage28/paired_comparison.json) 提供全量配对统计，[results/stage28/verification.json](../../results/stage28/verification.json) 提供离线验证收据。

10 个初始检查点、第一次未加提示的输入逐字一致、每次唯一追加段落、后续完整模型上下文、动作/状态/反馈/控制器均已精确核验。分析代码和隔离探针没有调用模型。不同随机模型样本是本实验主要因果限制。
