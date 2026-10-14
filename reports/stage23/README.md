# Stage23：Minimal Controller Reset Ablation

结论 **CONTROLLER_LIMIT_CONFIRMED**；1 条母轨迹、10 个检查点、30 个完整轨迹槽位。第一章完成 Origin/Reset/Oracle = 0/0/1；有主线增量 = 0/3/3；新增模型请求 2217，usage 费用 $1.908718692。

- [实验报告](Stage23实验报告.md)
- [三版本轨迹对比](三版本轨迹对比.md)
- [reset 前后行为变化](reset前后行为变化分析.md)
- [stale goal 统计](stale_goal统计.md)
- [wait 统计](wait行为统计.md)
- [关键反事实案例](关键反事实案例.md)
- [Stage18.1 开发建议](Stage18.1开发建议.md)
- [运行前协议](预登记实验协议.md)
- [机器可读结果](../../results/stage23/aggregate.json)、[费用](../../results/stage23/cost_reconciliation.json)、[证据索引](../../results/stage23/evidence_index.csv)

## 离线重算

使用冻结的 AgentOdyssey 引擎和现有 Python 环境，设置 `AGENTODYSSEY_ROOT` 与 `PYTHONPATH` 后，在仓库根目录运行：

```bash
export PYTHONHASHSEED=0
export AGENTODYSSEY_ROOT=/mnt/Space0/scar_dependencies/agentodyssey_stage22
export PYTHONPATH="$PWD:$AGENTODYSSEY_ROOT"
export HF_HUB_OFFLINE=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
/mnt/Space0/scar_dependencies/venv/bin/python -m scar_stage23.analyze
/mnt/Space0/scar_dependencies/venv/bin/python -m scar_stage23.audit
/mnt/Space0/scar_dependencies/venv/bin/python -m scar_stage23.verify --start 35
/mnt/Space0/scar_dependencies/venv/bin/python -m scar_stage23.report
/mnt/Space0/scar_dependencies/venv/bin/python -m scar_stage23.package
```

`verify --start` 可依次传入 33、35、52、64、70、100、179、193、244、271 重放全部分支；这些分析入口主动禁用网络，不会调用模型。完整物理分叉快照、原 Agent 记忆、原始模型请求/响应、决策及终点记忆均已归档，运行时缓存和密钥不上传。原环境代码与下载依赖不重复上传。

请勿将 `batch` 当作分析入口；它是冻结的实验执行器。已完成分支有幂等保护，本轮没有为低分再次采样。
