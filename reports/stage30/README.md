# Stage30

结论：NO_SUPPORT。新增 1716 次模型请求，usage 计价 $0.710318160。

- [实验报告](Stage30实验报告.md)
- [目标栈与检查点](OracleGoalStack构造与检查点.md)
- [逐任务轨迹与恢复对比](逐任务轨迹与恢复对比.md)
- [典型案例与阶段归因](典型案例与阶段归因.md)
- [下一阶段机制判断](下一阶段机制判断.md)
- [预登记协议](预登记实验协议.md)

复算：在已配置的本地环境设置 PYTHONHASHSEED=0 与 AGENTODYSSEY_ROOT，依次执行 `python -m scar_stage30.verify --archive-only`、`analyze`、`review`、`validate_analysis`、`report`、`audit`。后五项同为 scar_stage30 模块，均离线零模型调用。不要重新运行 batch 来复算；原生版本及全部输入哈希见 freeze.json。数据在 results/stage30，原检查点引用 results/stage28/checkpoints，环境依赖不上传。
