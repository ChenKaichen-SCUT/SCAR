# 最佳版本备注：按本次服务器实际记录区分

这里的版本命名只对应此服务器快照，不对应 SCAR 主仓库另一批 V1/V2/V3 实验。依据是 [逐局轨迹索引](metadata/run_index.json)、对应协议及官方评分文件，不是版本号新旧。

## 建议优先保留的三游戏主版本：feedback_v3

这是用户此前指定回退到的 `1/24、17/17、20/31` 版本，在本轮已测三游戏主版本中记录的合计主线表现最高。

| 游戏 | 主线分数 | 实际步数 | 必须保留的限制 |
|---|---:|---:|---|
| Remnant | 1/24 | 157 | 方法中途失败，未跑满 500 步；不能写成成功完成的 500 步结果 |
| Mark | 17/17 | 496 | 完成全部主线 |
| Metropolis | 20/31 | 500 | 本服务器现有记录中的该游戏最高分 |

源码：[feedback_v3_core.py](code/feedback_v3_core.py)、[feedback_v3_agent.py](code/feedback_v3_agent.py)；入口：[eval_feedback_v3.py](code/eval_feedback_v3.py)；协议：[protocol_feedback_v3.json](records/protocol_feedback_v3.json)；结果：[feedback_v3_status.json](records/feedback_v3_status.json)。服务器当前相关源码全部匹配原冻结协议哈希。

**这个推荐不代表 v3 在三个游戏都最好，也不代表稳定优势。** v3 的 Remnant 方法中止必须与分数一起报告。

## 分游戏最高记录

| 游戏 | 版本 | 得分与步数 | 备注 |
|---|---|---|---|
| Remnant | `feedback_v3 + no_repeat` | **3/24，300 步完整运行** | 关闭重复动作硬拦截的消融；增分在 45、150、270 步。同一变体在 Metropolis 只有 8/31，不能当作三游戏通用最佳。 |
| Mark | `feedback_v2` | **17/17，240 步完成** | 与 v3 和全历史基线并列满分，本次记录中完成步数最少；v3 为 496 步，全历史基线为 316 步。 |
| Metropolis | `feedback_v3` | **20/31，500 步** | 最高观察分数，不代表接近解决整个游戏。 |

Remnant 的 `no_execution` 消融也观察到 3/24，但在第 165 步方法失败，不能代替上表的完整运行记录。

Remnant 最高分消融源码：[mechanism_study_core.py](code/mechanism_study_core.py)、[mechanism_study_agent.py](code/mechanism_study_agent.py)。变体由 `AO_STUDY_VARIANT=no_repeat` 选择，入口为 [eval_mechanism_study.py](code/eval_mechanism_study.py)，协议和完整结果分别见 [protocol_mechanism_study.json](records/protocol_mechanism_study.json)、[mechanism_study_status.json](records/mechanism_study_status.json)。相关源码全部匹配冻结哈希。

## 后续 Remnant 版本的定位

| 版本 | 得分 / 步数 | 增分步骤 | 死亡次数 | 定位 |
|---|---|---|---:|---|
| v3r2_verified | 2/24，500 步 | 32、84 | 7 | 历史成功路径参考 |
| v3r4 | 2/24，300 步 | 33、77 | 2 | 后续控制修正参考 |
| v3r6 | 2/24，300 步 | 30、163 | 4 | 最近一轮改进的冻结对照基础；**不是历史最高分版本** |
| v3r7 | 2/24，300 步 | 46、80 | 1 | 最新失败改进，未超过 v3r6；不推荐标为最佳 |

v3r7 的 55 项离线检查通过，但在线仍存在状态过期、修复目标偏移及无净进展的修复。19 个被选择的修复方案只有 9 个按原顺序完整执行，第二分之后 220 步无增分。详见 [完整行为报告](analysis/v3r7/performance_review.html)。最新版本的单次死亡减少不能归因于某个机制，也不能抵消没有提分的事实。

v4/v5 按用户要求已退出后续研究路线；其代码和所有已产生结果仍作为历史资料保留。

## 复查路径

还原后的 `workspace/runs/<run_id>/agent_adam_davis/agent_log.jsonl` 保存原始动作、公开反馈与奖励；`workspace/control_audit/<run_id>.jsonl` 保存决策与控制干预；`workspace/telemetry/<run_id>/` 保存模型请求、响应和使用量。三游戏 v3 的 run ID 分别为 `remnant__feedback_v3`、`mark__feedback_v3`、`metropolis__feedback_v3`；Remnant 最佳完整运行 ID 为 `remnant__ab_no_repeat`。
