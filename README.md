# SCAR / AgentOdyssey

按《指引.md》实现的状态条件化失败记忆与动作修复实验。官方基线、游戏、模型权重均在仓库外下载；本仓库只提交我们的实现、实验配置、测试记录及结果分析。V3 的实际动作轨迹以压缩 JSONL 发布；完整引擎状态快照保存在实验服务器。

**实验已完成，研究判断为 PARTIAL（局部有效）。** 正式诊断 288 组、200 步长程 45 组、统一预算上限 45 组均已结束。SCAR 的 Recovery@20 为 94.44%，简单恢复为 83.33%，官方 STM 为 91.67%；主线收益不稳定且误拦截较高，不能宣称整体优于现有方法。全阶段保守 API 费用估算 $14.834561，低于 $20 上限。

完整结果见 [中文实验报告](reports/实验报告.md)，逐局数值见 [all_runs.csv](results/all_runs.csv)，冻结协议见 [实验协议](reports/实验协议.md)。报告包含负面结果、样本限制、完整成本及重放审计。

**修订轮已完成，结论为 PARTIAL：干预风险降低，但整体性能未改善。** 仅运行新版 SCAR：3 组开发测试、72 个诊断案例、3 组长程及 3 组费用约束实验；四个基线和旧 SCAR 直接复用历史记录。长程保持每游戏种子 101、最多 200 步。诊断 FBR 从 77.69% 降至 25.00%，但 Recovery@20 从 94.44% 降至 87.50%，长程平均主线奖励从 5.00 降至 3.67。新增费用 $1.190747，项目累计 $16.025309。234 个动作抽查全部精确重放，318 对跨轮初始状态全部匹配。详见 [修订版中文报告](reports/修订版实验报告.md) 和 [修订轮协议](reports/修订轮协议.md)。这是已见案例回归比较，不能作为新盲测；第一轮源码和结果保持不变。

**V3 实验批次与审计已完成，当前版本的整体性能优势主张为 NO-GO。** 困难诊断 445 组已评测（443 正常结束、2 次 V3 方法中止）；15 局长程中 14 局跑满 200 步，V3 remnant 在 133 步中止。所有方法均在新困难集与种子 909 上实际运行，失败计入完整分母，没有选择性重跑。困难集 Recovery@40：STM 62.92%、SimpleRecovery 53.93%、原 SCAR 46.07%、V2 56.18%、V3 53.93%；长程观察到的主线奖励均值为 STM 6.33、V3 3.00。每游戏仅一个配对种子，不作总体显著性结论。1,388 次抽查全部精确重放，服务器 68 项测试通过。本轮保守 API 费用 $7.104774，项目累计 $23.130083；用户已授权本批解除原 $20 上限，账本未重置。真实目标切换类型仍缺失，覆盖要求为部分完成。见 [V3 最终实验报告](reports/v3/最终实验报告.md)、[逐局结果](results/v3/formal/tables/all_runs.csv)、[方法中止处理说明](reports/v3/方法中止处理说明.md)及[复现指南](reports/v3/复现指南.md)。V1/V2 实现、旧结果和旧报告保持不变；本轮已停止新增实验。

**指引4的机制归因已完成，新增 API 费用为 $0。** 复核全部 89 个 family、2,150 次 V3 决策，并在 321 个冻结状态上执行 692 个首动作反事实分支。K=10 已验证路径数为 C0/C1 271、C2/C3 275（均非新 Agent 的闭环恢复成绩）；额外候选上界从 276 提高到 295。发现条件作用范围错误、单候选占比高及容器/材料序列管理问题，但尚不能证明多步价值函数是主要瓶颈。机制 A/B 均建议有针对性修改，暂不实现 V4。见 [完整中文机制归因报告](reports/v3/机制级归因分析.md)、[冻结协议与原始分支](results/v3/attribution/)。此前所有正式实验代码与结果保持不变。

## 固定环境

- Python 3.12；CPU 推理/检索，无 CUDA 依赖。
- [AgentOdyssey](https://github.com/agentodyssey/agentodyssey) 提交 `248430692a9d4a61d38c6c03ab2126287faaf450`。
- `deepseek-flash`，非思考模式，所有方法相同的模型、温度与输出上限，参数见 `configs/protocol.json`。
- 官方 VanillaRAG 使用官方默认 `Qwen/Qwen3-Embedding-0.6B`，权重版本 `97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3`，CPU 上运行。
- 官方 STM 窗口 5；LongContext 保留完整历史；未启用额外 reflection/summarization。

价格来自 [DeepSeek 官方定价](https://api-docs.deepseek.com/quick_start/pricing/)，统一用高峰美元单价作保守估计：每百万缓存命中输入 $0.006、未命中输入 $0.30、输出 $1.20。估算值不等同于账户账单。[思考模式文档](https://api-docs.deepseek.com/guides/thinking_mode/)对应参数为 `thinking.type=disabled`。

## 安装和运行

```bash
export SCAR_WORKSPACE=/root/scar_workspace
export PATH="$HOME/.local/bin:$PATH" # 确保已安装的 uv 在 PATH 中
git clone https://github.com/ChenKaichen-SCUT/SCAR.git "$SCAR_WORKSPACE/project"
cd "$SCAR_WORKSPACE/project"
bash scripts/bootstrap.sh
export AGENTODYSSEY_ROOT="$SCAR_WORKSPACE/dependencies/agentodyssey"
export PYTHONPATH="$SCAR_WORKSPACE/project:$AGENTODYSSEY_ROOT"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONHASHSEED=0
PY="$SCAR_WORKSPACE/venv/bin/python"
"$PY" -m pytest tests "$AGENTODYSSEY_ROOT/tests" -q --junitxml=results/tests.xml
"$PY" scripts/api_probe.py --key-file /secure/path/miyao.txt --runtime "$SCAR_WORKSPACE/runtime"
"$PY" -m scar.experiments.run --stage smoke --workers 4 --runtime "$SCAR_WORKSPACE/runtime" --key-file /secure/path/miyao.txt
"$PY" -m scar.experiments.run --stage pilot --workers 8 --runtime "$SCAR_WORKSPACE/runtime" --key-file /secure/path/miyao.txt
"$PY" -m scar.experiments.run --stage collect --workers 8 --runtime "$SCAR_WORKSPACE/runtime" --key-file /secure/path/miyao.txt
"$PY" -m scar.diagnostics.build --runtime "$SCAR_WORKSPACE/runtime" --output "$SCAR_WORKSPACE/runtime/ao_fr_frozen"
"$PY" scripts/audit_holdout.py --runtime "$SCAR_WORKSPACE/runtime" --cases-dir "$SCAR_WORKSPACE/runtime/ao_fr_frozen"
"$PY" scripts/audit_initial_goals.py --cases "$SCAR_WORKSPACE/runtime/ao_fr_frozen/cases.json"
"$PY" -m scar.experiments.run --stage diagnostic --workers 16 --cases "$SCAR_WORKSPACE/runtime/ao_fr_frozen/cases.json" --runtime "$SCAR_WORKSPACE/runtime" --key-file /secure/path/miyao.txt --algorithms SCARAgent ShortTermMemoryAgent VanillaRAGAgent SimpleFailureRecovery
"$PY" -m scar.experiments.run --stage long --workers 16 --runtime "$SCAR_WORKSPACE/runtime" --key-file /secure/path/miyao.txt
"$PY" -m scar.experiments.run --stage cost --workers 16 --runtime "$SCAR_WORKSPACE/runtime" --key-file /secure/path/miyao.txt
"$PY" -m scar.experiments.analyze --runtime "$SCAR_WORKSPACE/runtime" --output results
"$PY" -m scar.diagnostics.rule_accuracy --runtime "$SCAR_WORKSPACE/runtime" --cases "$SCAR_WORKSPACE/runtime/ao_fr_frozen/cases.json" --output results/rule_accuracy_frozen.json
"$PY" scripts/audit_artifacts.py --runtime "$SCAR_WORKSPACE/runtime" --output results
"$PY" scripts/recovery_costs.py --runtime "$SCAR_WORKSPACE/runtime" --output results
"$PY" scripts/diagnostic_uncertainty.py --runtime "$SCAR_WORKSPACE/runtime" --output results
"$PY" scripts/report_details.py --runtime "$SCAR_WORKSPACE/runtime" --output results
"$PY" scripts/posthoc_checks.py --runtime "$SCAR_WORKSPACE/runtime" --output results
```

上述采集/构造命令用于新的运行目录；不要覆盖本轮冻结数据。精确重放与重算应使用服务器现存 `runtime/ao_fr_frozen` 和 `runtime/runs`，从分析命令开始。重新调用随机 LLM 建立数据会形成新的实验，不能保证同一数据集。`scripts/finish_formal.py` 可在诊断完成后顺序执行长程、预算与审计，并用文件锁防止重复调度；脚本校验核心实现和配置与冻结记录一致。

安装需要 `uv`。`scripts/bootstrap.sh` 使用本轮服务器导出的 `requirements-cpu.lock`，先从官方 CPU wheel 源安装 PyTorch，再安装其余锁定依赖；上游和本项目采用 editable、`--no-deps --no-build-isolation` 安装，避免默认引入 vLLM/CUDA。服务器实际版本另存于 `results/environment-lock-server.txt`。网络受限时可传输已验证的依赖与官方仓库，但需要在目标服务器重新测试。

图表生成使用独立的本地 matplotlib 环境，版本记录在 `reports/figures/plot_environment.json`；读取分析结果后执行 `python3 scripts/plot_results.py --results results --output reports/figures`。实验和 CPU 检索本身均在服务器执行。

API Key 可通过仅所有者可读的密钥文件或 `DEEPSEEK_API_KEY` 传入。不要把密钥写入命令参数值、Git 或报告。代码不读取服务器密码。

## 实现与实验口径

`scar/agents/scar/` 分别实现公开反馈诊断、条件失败记忆、可执行局部修复计划、规则冲突更新与安全重试；SCAR 的基础策略直接继承官方 STM。`scar/baselines/` 为精确可观察状态缓存、冷却重试和一次普通 LLM 重规划基线。`scar/integration.py` 提供真实 Agent 工厂注册与统一 provider 配置，不覆盖上游文件。

上游此提交存在一个运行时缺口：STM 调用的 `construct_user_prompt_long_context` 不在配置类中。兼容层补齐该方法，格式与官方 LongContext 相同；STM、SCAR、SimpleRecovery 共用修复。统一 provider 对无效 JSON 有限重试，禁止静默变成 wait；所有方法均记录额外请求、失败请求和费用。

引擎 `step_invalid_action` 主要标记解析与参数错误，未覆盖所有语义拒绝。因此结果同时列出官方 IAR/RIAR 与公开规则反馈得到的语义失败率/重复语义失败率；两种口径不可混用。FBR 使用策略完成决策后，在独立引擎副本重放候选动作得到的反馈标签，策略本身不能读取该标签。此标签依赖明确拒绝文本，其限制需和结果一起解释。在线 CRA 每 10 步审计至多 10 条规则，属于探索性诊断，不能冒充冻结独立状态集上的 CRA。

快照保留引擎实例、在线 step-rule 状态、游戏 RNG、Python/NumPy RNG，剥离 provider、API Key 和 Agent 研究记忆。研究记忆单独保存。仅加载自己生成的可信 pickle；每一正式步骤生成独立 checkpoint，最后写入提交标记。中断后仅从完整 checkpoint 恢复。环境随机性可重放，但远程 LLM 不保证位级确定。

AO-FR 优先挖掘官方 STM 自然轨迹；可补充明确标记的真实引擎动作前缀合成案例，不伪造反馈。恢复可达性必须由完整动作见证和两次独立重放验证。限定搜索找不到见证的案例标为“未验证”，从 Recovery 分母排除。条件释放变体与母案例共享 family 和数据划分，统计按 family 聚类，不能当成两个独立机制。若 C 类型或其他类型数量不足，如实报告。

完整游戏包含三个游戏、三个测试种子、五个方法，每局最多 200 步。另执行每局 API 上限 $0.15 的真正成本约束运行；请求前按保守上界预留额度，额度不足即保存已提交步骤。全阶段共享 $20 总上限，smoke/pilot 累计上限 $3。不做模块消融。所有测试及对比属于独立 DeepSeek 实验，不是官方 Qwen Challenge 排名。

## 服务器数据

工作目录：`/root/scar_workspace/project`；第三方依赖：`/root/scar_workspace/dependencies`；完整实验：`/root/scar_workspace/runtime`。

每个 `runtime/runs/<task_id>/` 包括请求 JSONL、执行尝试、引擎日志、不可覆盖的完整步骤 checkpoint、记忆、状态与结果摘要。`runtime/ao_fr_frozen` 存放冻结数据集及验证信息。GitHub 不上传第三方代码、模型权重、凭据和大型原始快照；发布的是我们的代码、元数据、结果表与分析报告。任务标识包含算法、游戏、种子及配置/实现 hash；已完成任务不会重跑。

最终审计抽查 1,152 个步骤，全部精确重放；384 个初始状态与冻结源一致。初期 12 个 smoke 故障及 hash 随机化修正前的 73 个诊断运行均保留，后者标记为 `diagnostic_provisional` 并从正式比较中整体排除。


## 2026-10-19 独立服务器备份

已保存另一批 DeepSeek + 全历史 ReAct 实验的[完整服务器快照](server_backups/agentodyssey-20261019/README.md)，包含代码、完整轨迹、引擎快照和 API 审计。其版本命名与上面的 SCAR V1/V2/V3 独立；原有实验文件保持不变。

[最佳版本备注](server_backups/agentodyssey-20261019/BEST_VERSIONS.md)：三游戏历史主版本 `feedback_v3`（1/24、17/17、20/31，Remnant 中途失败）；Remnant 最高完整运行记录为 `no_repeat`（3/24，300 步）；最新 v3r7 未提分。完整备份分为 43 块，附逐文件 SHA-256 和还原脚本。
