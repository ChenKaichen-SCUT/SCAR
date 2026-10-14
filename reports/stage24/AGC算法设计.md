# Stage24：AGC 算法设计与运行前协议

本阶段独立实现 Adaptive Goal Control Agent，不修改 Stage18 原源码，不将 Stage23 的 reset 版本升级为正式 Stage18.1。用户确认允许原 action/reasoning JSON 增加 goal_description 与公开证据字段。本设计在付费实验前冻结，后续不按结果调参。

## 流程与边界

公开 observation → State Extractor → Goal State Tracker / Progress Monitor → 同一个 LLM → Action Reliability Controller → EXECUTE 或 RECONSIDER → 原生环境。

LLM 声明当前子目标与 action；控制器可原样登记环境显式指令，但不生成任务、替代动作或建议物品/NPC/路径。每个模型目标必须附带当前观测、最近五条公开观测或已有目标证据中的逐字引文。逐字匹配只能证明证据来源，不能证明模型目标在语义上正确。通用控制包没有游戏名、物品/NPC/地图/任务常量，也不接触 reward、隐藏配置或主线状态。

目标记录包括 goal_description、creation_step、evidence、last_progress_step、status。保留最多 8 个已撤销目标元数据和当前目标；原 STM5 与最近五条公开观测只在本游戏内维护，不保存完整历史。审计轨迹由运行器写盘，不作为长期记忆回灌。

状态：有新公开信息或状态变更时 ACTIVE；最近 8 步 informative≤1 且同一动作至少出现 5 次，或同上下文动作失败至少 3 次，转 SUSPICIOUS。新显式公开指令替代旧目标时，将旧目标 INVALID 并登记原文。只有与字面目标动作相符的明确不可能反馈才使用不可达 INVALID；不能从预算耗尽或普通缺材料推断不可达。字面目标动作被接受、或公开位置已满足字面 enter 目标时 COMPLETED。不推断自由自然语言目标的隐藏完成条件，也不运行隐藏环境反事实作决策。

进展记录 observation 新签名、库存/手持/装备变化、位置变化、新实体、新反馈事件。新签名去掉时钟、HP、stamina 和地面数量波动；移动往返只有首次新状态算 informative，避免将循环当持续进展。公开容器内容仅在明确观察时解析。最多保留 256 个状态、事件哈希及实体名，窗口为 8；这些是有界新颖性代理，不是官方任务进度。材料数量变化、NPC 自行出现等也可能带来新状态，最终效果要以官方奖励评价。

Failure Memory 最多 12 条，仅记录实际执行后公开失败的 action、公开上下文哈希、结果、反馈引文和次数。上下文改变后旧失败不再作为同状态禁止依据，不将失败推广为物品永久禁令；成功执行相同动作/上下文会撤销该失败项。LLM 摘要显示当前上下文最多 6 条、其他近期最多 3 条失败证据。

Action Reliability Controller 检查：缺失/非法动作语法、目标/引文格式、引文是否公开、是否延用 INVALID/COMPLETED 目标；同公开上下文失败≥2 次；停滞中的 wait/重复提案；目标 SUSPICIOUS。只输出 EXECUTE/RECONSIDER 和证据原因，不输出候选动作。

每个环境动作最多一次额外 reconsider（共两次模型请求）。重复失败、停滞等软理由要求一次重考虑后，可以执行 LLM 再次选择的动作，同时标记 bounded_soft_release，避免控制器自身形成无限模型调用循环。若仍违反语法、公开证据或失效目标等硬条件，记录 agent_decision_exhausted，当前运行终止，不发明 wait、不挑选另一动作、不重跑。提前结束占用该次唯一试验，保留实际动作数和未消耗预算，不能按满 300 步伪造轨迹。

原 system prompt 的游戏玩家身份、公开 action space、reasoning/action 格式和 STM5 用户提示保留，仅扩展用户批准的两个输出字段，并附加结构化目标、状态、进展、失败与重考虑摘要。没有额外 planner/critic/reflection/skill 模型角色。AGC 不继承 Stage18 的 S1/P1/P3、FIFO、事实表或动作覆盖机制，因此整体对比是新 workflow 对旧 workflow，不是单模块因果消融。

## 冻结实验设置

- 只运行 AGC；remnant、mark、metropolis 每游戏 1 个 seed42 全新从 0 开始的运行，最多 300 个环境动作，原生 done 提前终止；三个本地进程并行，不重新采样已有基线。
- 模型和传输接口完整复用 Stage22：deepseek-flash，temperature=0.7、top_p=0.8、presence_penalty=1.5、thinking disabled、输出最多 768 token、JSON response_format。最多 1800 个动作/重考虑逻辑请求，实际额外调用单独计费。
- 引擎提交 `248430692a9d4a61d38c6c03ab2126287faaf450` 与 challenge_eval.py 不改。采用 Stage22 同一实际初始世界哈希，恢复其无序集合 bootstrap 和配方展示次序；此工作仅位于环境准备层，AGC 只接收原公开 observation。三游戏记忆分别清空。
- 仍为 300 步研究实验，不是官方 500 步榜单参赛。奖励按原评分脚本统计 Main Quest 与 Supplementary（side_quest + exploration + craft + unique_kill），不改变成功标准。
- Stage18 的对照仅引用 Stage22 三条已有完整轨迹。Stage23 的十个 mark 检查点只有一条母轨迹且剩余预算不同，只作诊断参照，不和本次三个完整运行混合作为独立统计样本。
- 记录所有模型原请求、原响应、重考虑理由、最终动作、目标状态、进展代理、失败记忆、环境反馈、原生状态哈希、费用。离线逐步回放不增加模型调用。基线、低分 AGC 局均不重跑。

## 事先确定的诊断口径和判定

stale episode 定义为“同一登记目标持续至少 12 个动作且满足通用停滞窗口”的连续区段；同时报告 SUSPICIOUS/INVALID 事件、字面已满足目标仍被持有的步数、目标 reset/更换数量、平均持续长度。新旧方法的目标表达不同，不能仅以目标字段改名造成的 stale 下降宣布有效。目标更换率和公共行为指标一起报告。

通用行为指标对 Stage18 与 AGC 用同一离线提取器重算：wait 占实际动作比例、相邻相同动作比例、8 步停滞窗口数、有界新状态数量。平均目标长度按连续相同登记文本的区段计算（含尾段删失）；不把 SUSPICIOUS 次数直接与旧算法没有的状态标签比较。

对指引“明显”的操作化：mark Main Quest 至少 3 且超过旧结果，三游戏 Main Quest 平均超过 Stage18 的 8/3，mark wait 比例相对下降至少 20%，mark 上述共同 stale episode/步数下降且通用停滞步数下降，才报告“本次三局支持 AGC workflow 有效”。若 stale 降低但奖励无提升，只支持解除锁定不足以提高完成表现；若仍有 stale，先审计实现与证据，不边跑边改。全部三游戏正负结果均列出，第一章完成须由原生状态/明确公开反馈确认。

每游戏一次模型采样，不计算显著性、不宣称普遍优势。Stage18/AGC 模型请求量不同，比较按相同环境动作上限，额外请求及费用须明确报告。本轮不加新种子、不训练模型、不开发额外游戏策略。

## 代码结构

`agents/agc/state.py`：公开文本提取；`control.py`：目标/进展/失败与二值裁决；`agent.py`：同一 LLM、STM5、有限重考虑和保存恢复。`agents/stage18/__init__.py` 只重导出冻结类；`agents/__init__.py` 用 namespace 扩展同时访问原引擎 agents，不复制第三方代码。

`scar_stage24/`：共享接口适配、初态重建、测试、冻结、实验执行和离线分析。提交号和各文件增删行数在最终发布记录中保存；运行前冻结提交与实验后分析提交分开。
