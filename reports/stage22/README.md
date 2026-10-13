# Stage22 / Stage18-Fixed：300 步官方三游戏预实验

**非 TTCL 正式排名：300 步，DeepSeek Flash；不是 500 步 Qwen 评测。**

本目录由 `指引22.md` 驱动。研究算法仅原始 Stage18；后续阶段策略不参与。

**15/15 局完成，4500 个环境动作、5666 次模型请求，usage 计价 $1.296062。结论 NO-GO：不建议当前冻结版直接进入 500 步正式评测。** 所有局到达 300 步，均未完成完整主线。

| 方法 | remnant | mark | metropolis | 主线均值 | 辅助均值 |
| --- | --- | --- | --- | --- | --- |
| Stage18-Fixed | 1 | 0 | 7 | 2.666667 | 4.000000 |
| NoMemoryAgent | 1 | 0 | 4 | 1.666667 | 8.000000 |
| ShortTermMemoryAgent | 1 | 10 | 4 | 5.000000 | 11.666667 |
| LongContextAgent | 1 | 10 | 8 | 6.333333 | 9.333333 |
| VoyagerAgent | 1 | 3 | 4 | 2.666667 | 5.666667 |

每组合只有一次模型采样。官方原生初始化未固定进程哈希种子，metropolis 的主线地点参数存在差异，不能把分差解释为严格配对的算法因果效应。其余复现限制和 CPU 检索恢复记录完整保留。

- [300 步科研总结与 NO-GO 判断](300步实验科研总结.md)
- [完整主结果、成本、时长与曲线](三游戏五算法主结果表.md)
- [控制器贡献与失败诊断](控制器贡献与失败诊断.md)
- [模型调用与解析异常](模型调用与解析异常.md)
- 逐游戏：[remnant](remnant_逐游戏案例.md) / [mark](mark_逐游戏案例.md) / [metropolis](metropolis_逐游戏案例.md)
- [工程修复与算法差异审计](工程修复与算法差异审计.md)
- [官方评测协议核验](官方评测协议核验.md)
- [复现与运行事件记录](复现与运行事件记录.md)
- [冻结配置及文件哈希](../../results/stage22/freeze.json)
- [零模型调用自检](../../results/stage22/preflight.json)
- [最终完整性检查与原生回放覆盖](../../results/stage22/verification.json)

原始 Stage18 提交：`2c2f7ecc03b0e326f26cdf85ce13e2415b374e33`。
官方 AgentOdyssey 提交：`248430692a9d4a61d38c6c03ab2126287faaf450`。
运行前冻结提交：`7621a9417294ce3cc1ce54d1b09bb049eae9e631`。结果发布提交单独记录；不会因分析结果修改该冻结版本。

## 运行环境

Python 3.12、CPU PyTorch、官方 AgentOdyssey 依赖与 OpenAI SDK；Voyager 使用固定的 Qwen3-Embedding-0.6B。官方仓库、Python 环境和模型权重保存在 SCAR 仓库外，不上传第三方下载副本。`AGENTODYSSEY_ROOT` 与 `PYTHONPATH` 必须指向冻结的官方检出。

```bash
export AGENTODYSSEY_ROOT=/mnt/Space0/scar_dependencies/agentodyssey_stage22
export PYTHONPATH=/mnt/Space0/AINative/scar_agentodyssey:$AGENTODYSSEY_ROOT
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 HF_HUB_OFFLINE=1
/mnt/Space0/scar_dependencies/venv/bin/python -m scar_stage22.preflight
```

正式运行只启动一次：

```bash
/mnt/Space0/scar_dependencies/venv/bin/python -m scar_stage22.batch \
  --runtime /mnt/Space0/scar_dependencies/stage22_runtime
```

密钥通过本地私有文件或环境变量注入，不写入配置、日志或 Git。已完成目录会被跳过，不重新抽样。运行代码不读取其他游戏或历史轮次的轨迹；冻结核验读取的旧文件仅为源代码/协议哈希，不会进入 agent prompt。

结果目录中的 `config.json` 为官方环境导出的最终运行状态，用于未改动的 `challenge_eval.py`。`trajectory.jsonl.gz` 的动作编号从 1 开始，另附 `official_zero_based_log_step`；每行保存原始观测、动作、反馈、奖励、累计评分及状态哈希。`requests.jsonl.gz` 保存完整消息、回复和真实 usage，包括 Voyager 的非动作调用。

## 零 API 复算

在安装官方依赖并检出上面固定提交后，沿用前述环境变量。以下操作读取已保存数据，不启动新实验、不需要模型密钥：

```bash
/mnt/Space0/scar_dependencies/venv/bin/python -m scar_stage22.analyze
/mnt/Space0/scar_dependencies/venv/bin/python -m scar_stage22.verify
/mnt/Space0/scar_dependencies/venv/bin/python -m scar_stage22.research_report
```

`verify` 默认使用已导出的费用账本；在原本地环境可加 `--runtime /mnt/Space0/scar_dependencies/stage22_runtime` 对原 SQLite 账本核验。原生回放收据通过输入文件和反事实文件哈希复用；完整通过与仅前缀通过分别记录。主线原始分数由未修改的官方脚本读取 15 份 config，手工聚合与官方输出交叉断言一致。

主要机器数据：`main_results.csv`、`per_run.json`、`method_aggregates.json`、`progress_curves.csv`、`prompt_curves.csv`、`cost_ledger.json`。证据索引：`evidence.jsonl.gz`、`case_evidence.jsonl.gz`、`all_stage18_decisions.jsonl.gz`、`same_state_local_contrasts.jsonl.gz`。原始轨迹与请求在 `results/stage22/runs/`，共 15 组，第三方代码、模型权重、私钥及运行缓存不上传。
