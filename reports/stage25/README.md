# Stage25：AGC-v2

正式范围：三个游戏各一次，seed42，300步；另六局按用户要求取消并单独记费。

- [科研总结报告](科研总结报告.md)
- [三游戏结果对比与费用](三游戏结果对比.md)
- [置信度和目标重评估](置信度与目标重评估分析.md)
- [动作可靠性及失败模式](动作可靠性与失败模式分析.md)
- [500步评测建议](500步评测建议.md)
- [最终范围修订](用户缩减实验范围.md)
- [原始冻结设计](AGC-v2设计与预登记.md)
- [Git变更和发布记录](Git变更记录.md)

实现：`agents/agc_v2/`。实验、禁网回放、统计与报告代码：`scar_stage25/`。原始轨迹/请求和可重算统计：`results/stage25/`。下载的引擎、虚拟环境、API密钥、SQLite运行账本不入Git；公开逐请求记录足以重算费用。

在已有依赖环境中，设置 `AGENTODYSSEY_ROOT` 和 `PYTHONPATH` 指向匹配引擎与本仓库，使用该虚拟环境Python执行：

```bash
python -m scar_stage25.verify --game remnant --seed 42
python -m scar_stage25.verify --game mark --seed 42
python -m scar_stage25.verify --game metropolis --seed 42
python -m scar_stage25.analyze
python -m scar_stage25.diagnose
python -m scar_stage25.report
```

这些分析入口禁用网络，不产生模型调用。`account`在保留原始本地SQLite账本的机器执行，以核对所有收费和六次零费用取消拦截；已发布 `cost_reconciliation.json`。图表需要matplotlib。冻结的原`batch`入口仍是九局历史协议，**不要调用它复现最终范围**；如日后明确授权新实验，应逐游戏显式指定seed42并使用独立输出目录，避免覆盖已有结果。
