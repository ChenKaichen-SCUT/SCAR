# Stage26

- [实验报告与结论](Stage26实验报告.md)
- [Action Failure Replay完整分类](ActionFailureReplay分析报告.md)
- [Oracle Action Correction配对结果](OracleActionCorrection实验结果.md)
- [全部10个关键反事实案例](关键反事实案例.md)
- [下一阶段机制建议](下一阶段机制建议.md)
- [付费前冻结协议](预登记诊断协议.md)
- [Git变更记录](Git变更记录.md)

范围：1条Stage25 remnant母轨迹，10个检查点，10个原始后缀复用、10个单次Oracle续跑。不是10个独立任务。原模型和Agent未改。

数据：`results/stage26/action_failure_replay.jsonl.gz`逐动作公开证据；`source_failure_statistics.json`分类及原失败反馈；`original_failure_recovery.json`原始恢复；`paired_metrics.json`完整窗口统计；`paired_comparison.csv`逐检查点比较；`diagnostics.json`首步反事实/重试/终止；`evidence_index.jsonl.gz`逐分支行号及请求对应；`cost_reconciliation.json`费用核对。

在原依赖环境中设定匹配引擎的AGENTODYSSEY_ROOT及本仓库/引擎PYTHONPATH后，可禁网重算：

```bash
python -m scar_stage26.verify --start 28
python -m scar_stage26.analyze
python -m scar_stage26.diagnose
python -m scar_stage26.report
```

verify对协议中的其他检查点分别执行。account在保留原始SQLite账本的机器核验费用；每次请求的usage/价格/费用均已归档，可独立重算。prepare/source_audit及smoke属于已冻结的运行前证据，不要为重看结果重写原文件。run/batch会涉及付费API调用，不属于离线分析入口。

下载引擎、依赖环境、API密钥不上传；只归档本阶段代码及生成的实验/分析材料。
