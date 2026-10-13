# Stage22 / Stage18-Fixed：300 步官方三游戏预实验

**非 TTCL 正式排名：300 步，DeepSeek Flash；不是 500 步 Qwen 评测。**

本目录由 `指引22.md` 驱动。研究算法仅原始 Stage18；后续阶段策略不参与。

- [工程修复与算法差异审计](工程修复与算法差异审计.md)
- [官方评测协议核验](官方评测协议核验.md)
- [冻结配置及文件哈希](../../results/stage22/freeze.json)
- [零模型调用自检](../../results/stage22/preflight.json)

原始 Stage18 提交：`2c2f7ecc03b0e326f26cdf85ce13e2415b374e33`。
官方 AgentOdyssey 提交：`248430692a9d4a61d38c6c03ab2126287faaf450`。

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
