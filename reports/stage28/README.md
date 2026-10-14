# Stage28 复现入口

先阅读 [总报告](Stage28失败恢复链分析报告.md) 与 [预登记](预登记诊断协议.md)。代码目录 `scar_stage28`；数据目录 `results/stage28`。下载的环境和 Python 依赖不提交。

环境变量沿用 Stage25：`AGENTODYSSEY_ROOT` 指向冻结 AgentOdyssey checkout（提交 248430692a9d4a61d38c6c03ab2126287faaf450），将仓库和环境加入 `PYTHONPATH`，设置 `PYTHONHASHSEED=0`、`HF_HUB_OFFLINE=1`。Python 为既有 scar_dependencies/venv。不要重跑付费 batch 来复算报告。

不涉及模型调用的重算命令：

```bash
python -m scar_stage28.verify
python -m scar_stage28.analyze
python -m scar_stage28.review
python -m scar_stage28.report
python -m scar_stage28.audit
```

verify 同时用本地私有 runtime SQLite 对账；仅使用公开归档时运行 `python -m scar_stage28.verify --archive-only`，跳过私有账本，仍精确重放动作/上下文并从 requests.jsonl.gz 重算逐请求 usage 和费用。该模式明确标注未核验私有账本。本轮保存的是完整含账本验证结果。audit 的凭据排除扫描需要本地密钥文件，公开复算无需运行这一步。原始事件分类由冻结 chain.py 产生；重新运行会重写 gzip 文件时间戳，所以如需重算应写入隔离副本，避免使冻结文件的字节哈希变化。

`prepare`、`smoke`、`freeze` 是已完成的无网络准备流程；`batch` 是唯一付费执行入口，已完成时不应重新请求。新代码不被生产 Agent 导入。`selected_pair_semantic_review.json` 为逐案例核查，`evidence_index.jsonl.gz` 为原始行号/绝对动作/请求索引，`artifact_manifest.json` 为文件哈希清单。
