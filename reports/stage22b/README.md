# Stage22-B：指引23 零新增模型调用诊断

**结论：DESIGN_LIMIT；不启动 500 步正式评测。** 冻结 Stage18-Fixed，审计 mark 的 Stage18、STM、LongContext 共 900 步。原生全状态匹配 824 步；Stage18 与 LongContext 各300，STM224。新增模型请求/费用为 0；未修改算法，未跑补丁 A/B。

- [mark 环境失败案例分析](mark环境失败案例分析.md)
- [Stage18 与 LongContext 路径差异](Stage18与LongContext路径差异.md)
- [失败类型分类统计](失败类型分类统计.md)
- [工程问题排查与修复边界](工程问题排查与修复边界.md)
- [500 步评测建议与最终结论](500步评测建议与最终结论.md)
- [关键证据原文](关键证据原文.md)

## 数据与统计口径

`results/stage22b/step_audit/`：各300行，完整 observation、最新公开指令、事后实际阶段、所选动作、动作历史、反馈、公开库存/位置差分与世界状态引用。`agent_audit/`：各300行，完整保存状态前后、完整模型 messages、模型 reasoning 和控制决定。`native/`：只发布严格匹配的原生完整状态与变化；STM缺失后76步不补造。压缩 JSONL 从1开始的行号与动作号一致。

[逐步CSV台账](../../results/stage22b/step_ledger.csv)、[900步证据索引](../../results/stage22b/evidence_index.csv)、[指标JSON](../../results/stage22b/metrics.json)、[信息首次公开](../../results/stage22b/information_matrix.json)、[工程检查](../../results/stage22b/engineering_checks.json)、[分类统计](../../results/stage22b/classification.json)、[七条公开可达分支](../../results/stage22b/public_recovery_witnesses_summary.json)均可重算。`mark_controller_contrasts.jsonl.gz` 保留全部214次旧原生覆盖反事实，并补充目标知识获取维度。

隐藏世界与完整任务定义仅用于事后阶段标注、原生哈希/反馈验证；没有进入正式 Agent 输入。人工可达分支用原公开文本选择动作，原生引擎自然负责执行隐藏规则。它只证明第一阶段可达，不是补丁政策。所有方法主线 complete 均为 false；两基线的10分指完成第一章。

## 重算

使用已准备的官方引擎和原始结果，无需 API 密钥。导出路径后依次执行：

```bash
export AGENTODYSSEY_ROOT=/mnt/Space0/scar_dependencies/agentodyssey_stage22
export PYTHONPATH="$PWD:$AGENTODYSSEY_ROOT"
export HF_HUB_OFFLINE=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
/mnt/Space0/scar_dependencies/venv/bin/python -m scar_stage22b.analyze
/mnt/Space0/scar_dependencies/venv/bin/python -m scar_stage22b.engineering
/mnt/Space0/scar_dependencies/venv/bin/python -m scar_stage22b.report
/mnt/Space0/scar_dependencies/venv/bin/python -m scar_stage22b.verify
```

如需从原数据重构 Agent，按三个方法分别执行 `python -m scar_stage22b.reconstruct --method METHOD`；如需重新原生回放，执行 `python -m scar_stage22b.native --method METHOD`。它们从 `results/stage22/runs/mark__METHOD` 读取，不依赖未上传的付费请求缓存；所有分析入口均禁止网络连接。原始 Python 哈希顺序未固定，所以重新原生回放可能在不同步骤停止，脚本必须保留首个不一致，不允许反复重试到匹配为止。重算现有统计不需要重新原生回放。

分析期间的快照深拷贝修正和原始/最终回放收据见 `analysis_events.json`。源码哈希及成品校验见 `verification.json` 与 `artifact_manifest.json`；压缩文件的 gzip 时间戳可能随重新生成改变，但统计和记录内容应一致。原 Stage22 的完整轨迹、模型请求、配置和结果保持原提交，不上传下载的引擎、依赖或密钥。
