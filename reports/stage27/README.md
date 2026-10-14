# Stage27

- [实验报告](Stage27实验报告.md)
- [失败理解统计](PreconditionUnderstanding统计.md)
- [状态信息对比](StateSufficiency对比结果.md)
- [正负案例](典型成功失败案例.md)
- [研究判断](下一阶段方向判断.md)
- [预登记协议](预登记诊断协议.md)

代码 `scar_stage27/`；数据 `results/stage27/`。`failure_database.jsonl.gz` 为完整失败库；`paired_comparison.csv` 为 334 对表；`understanding_judgments.json` 为逐条规则/语义标签；`request_index.csv` 为每次付费请求索引。环境快照包含隐藏状态，只用于无网络原生核验，提示构建只读取公开 fixture。

可重算顺序：`python -m scar_stage27.grade`、`python -m scar_stage27.analyze`、`python -m scar_stage27.verify`、`python -m scar_stage27.report`、`python -m scar_stage27.audit`。这些命令均不新增模型调用。Python/依赖配置与 Stage26 相同。不要为重算报告运行 `batch`；它是产生新诊断回答的入口，已付费请求在私有 runtime 中有缓存。
