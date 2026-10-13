# 零API审计总报告

基于Stage20最终提交 `a034a69756432daebd16114854d8d266ff90a2d0`。本轮为只读事后审计，模型请求0、token 0、费用0；没有开发Stage21、改变旧策略或重新采样任务。动作编号为正式任务内动作数；终态“第N+1次动作选择”可以没有执行动作。

**判定：PARTIAL。** 完成11个停滞任务、44次指定拒绝、59个LOCATE、2个ACQUIRE与2个CRAFT提案的逐例审计。重建524次历史决策，191个真实规划快照/接受结果完全一致。

分类允许重叠。A=确证无尚未尝试且有公共依据的探索入口；B=公共入口存在但被控制器过滤（**广义包含18次固定额度过滤**）；C=B中同时有此前已公开、与当前必要依赖相关的新证据且额度耗尽；D=原始实际拒绝原因为 `not_a_current_dependency_or_blocker`，且提案仍有合法公共入口和可有界验证的材料假设。单纯ID字段匹配问题不直接算D。

另单列不涉及额度的候选遗漏，避免把“B=11”误读为11局都有相同BFS错误。A=0表示11局均找到可尝试入口，并不表示知道每个入口最终有用；未被单步回放验证的知识价值以及整个任务能否恢复均为UNKNOWN。

| 任务 | 停步/剩余 | 探索/18 | 逻辑请求/24 | 分类 | 非额度遗漏候选 |
| --- | --- | --- | --- | --- | --- |
| war_banner | 21/79 | 18 | 17 | B | 无 |
| cog_assembly | 21/79 | 18 | 14 | B,C | enter barracks |
| cog_crossbow | 20/80 | 14 | 8 | B | enter courtyard; enter watchtower |
| iron_nugget | 23/77 | 18 | 11 | B,C | enter courtyard |
| repair_kit | 23/77 | 18 | 11 | B,C | enter courtyard; enter watchtower |
| hellcoal_concentrate | 22/78 | 18 | 8 | B,C | enter courtyard; enter watchtower |
| ruin_spear | 30/70 | 18 | 9 | B,C | enter courtyard; enter watchtower |
| gate_cipher | 21/79 | 18 | 10 | B,C | enter courtyard |
| sharpened_blade | 21/79 | 18 | 13 | B,C | 无 |
| metal_strip | 21/79 | 18 | 8 | B | 无 |
| metal_plate | 21/79 | 18 | 9 | B,D | 无 |

A/B/C/D计数为 **0/11/7/1**，其中非额度候选遗漏7局；32次可确定证据层误拒、5次公共有界假设、7次其他应拒绝问题、0次无法分类。264个负例错误接受0。

D的直接例是metal_plate第11次动作选择：合法scrap_metal入口存在，LLM明确承认它与目标的关系尚未知，实际被依赖归属门槛拒绝。同状态一次store 1 scrap_metal公开metal_plate配方，原动作inspect desk没有该信息。该结果验证一个局部信息损失；不证明接受整条意图就会成功。cog_assembly、repair_kit、sharpened_blade还有被ID门槛先挡住的类似材料假设；它们不算实际D门槛直接触发，完整字段关系在44次报告中。

原生单步反事实 **37** 个，接受34、锁门拒绝3；14个分支公开新配方，7个分支有玩家HP损失。为恢复4个拒绝状态，仅回放47个保存的事实动作（教程前缀另计28步）；其余终态直接恢复已保存检查点。没有新闭环任务或模型重新采样。

独立核验进程再次执行相同37个分支、47个事实前缀动作和28个教程动作，逐项比对状态哈希与反馈；没有新增反事实候选。因此包含核验的实际原生动作调用合计224次：74次单步分支、94次事实前缀及56次教程动作。37是不同反事实的数量，并非全部原生动作调用数。详见 `verification.json`。

子目标结论：LOCATE 59个仅8个确认公共路径，不能等同拿到材料或全部工作台条件；其中7个随后由确定性模块完成父制作。ACQUIRE 2个都在未知材料路径、局部入口耗尽处挂起后被替换，0个取得目标。CRAFT两个分别在未公开配方/未证明当前依赖的接受门槛停止，并没有实际工作台制作失败轨迹。61个重点意图无P3抢占中断。

工程修正优先：证据字段关联、公开图中转候选、类型语义与五阶段完成记录。独立研究仅优先考虑“新公开证据触发的有界探索恢复”；更复杂的持续执行机制目前证据不足。详见《算法改进必要性评估》。

## 可重算交付

| 内容 | 文件 |
| --- | --- |
| 全部191次规划前公开状态与原请求索引 | `planning_states.jsonl.gz`、`state_index.json` |
| 11局原始终态、检查点哈希、候选全集 | `terminal_states.jsonl.gz`、`stall_audit.json` |
| 44次原提案/ID/字段关系分类 | `rejection_audit.json` |
| 61个重点意图逐动作与最早中断 | `intent_audit.json` |
| 2个CRAFT拒绝 | `craft_proposal_audit.json` |
| 事先保存的公开选择规则与单步原始反馈 | `counterfactual_plan.json`、`counterfactual_results.jsonl.gz` |
| 单步与原动作比较 | `branch_analysis.json` |
| 测试、独立核验和保护清单 | `test_receipt.json`、`verification.json`、`protected_manifest.json` |

上述结果位于 `results/stage20_audit/`，代码位于 `scar_stage20_audit/`。本地固定依赖已安装时：

```bash
bash scar_stage20_audit/run.sh extract
bash scar_stage20_audit/run.sh branches
bash scar_stage20_audit/run.sh analyze
bash scar_stage20_audit/run.sh test
bash scar_stage20_audit/run.sh report
bash scar_stage20_audit/run.sh verify
```

完整原生复核还需要本机保留的 `runtime/stage20/runs/` 物理检查点、`runtime/stage20/budget.sqlite` 及固定版本AgentOdyssey环境；这些私有运行文件未上传，不能声称仅克隆GitHub即可重放原生分支。已有公开审计产物和Stage20轨迹足以重新执行 `analyze`、`test`、`report`，不需要读取API密钥或重新获取模型回复。默认依赖位置为 `/mnt/Space0/scar_dependencies`，可用 `SCAR_DEPENDENCIES` 指向其他已安装位置。

每个进程在加载环境前阻断网络；未读取API密钥，也不调用模型或嵌入接口。extract重建的是已保存回复驱动的决策，branches只执行已列出的单步候选。没有因单步结果追加挑选有利分支。下载依赖和私有物理检查点不上传，只提交自有审计代码、状态索引、原始单步反馈与报告。Stage17—20所有跟踪文件逐字节保留。
