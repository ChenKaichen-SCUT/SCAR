"""Chinese reports driven by all ten outcomes, without reward-based exclusion."""
from .common import *
from scar_stage25.report import table,pct

def md(name,text):(REPORTS/name).write_text(text.strip()+'\n')

def main():
    offline();check_freeze();source=read(RESULTS/'source_failure_statistics.json');metrics=read(RESULTS/'paired_metrics.json')
    pairs=read(RESULTS/'paired_comparison.json');con=read(RESULTS/'conclusion.json');cost=read(RESULTS/'cost_reconciliation.json')
    diag=read(RESULTS/'diagnostics.json');audit=read(RESULTS/'completion_audit.json');rec=read(RESULTS/'original_failure_recovery.json')
    lookup={(m['start'],m['variant']):m for m in metrics};d={x['start']:x for x in diag}
    verdict=con['classification'];no_gain=not con['main_improved'] and not con['oracle_chapter1']
    early=[m for m in metrics if m['variant']=='Oracle' and m['status']=='agent_decision_exhausted']
    early_note='本轮a28分支在绝对决策225四次提出同一个非法 `pick up 10 coin`（接口不接受该数量参数），用尽3次额外动作重试。实际执行197个续跑动作，停在绝对a224，剩余76步未执行；其余9个分支到a300。四次均返回完整JSON且finish_reason=stop，不是传输或截断异常。该结果完整计入，未修复或重跑。'
    assert len(early)==1 and early[0]['start']==28 and early[0]['last_step']==224
    interpretation=('10个单步Oracle分支均未增加最终主线奖励，第一章仍为0/10。该干预没有恢复长期任务推进；它不排除连续动作纠错或更好的状态理解可能有效。' if no_gain else
        f"{con['main_improved']}/10个分支最终主线增加，{con['oracle_chapter1']}/10完成第一章。按预登记门槛判为{verdict}，不把同一母轨迹的检查点当独立样本。")
    pairtable=table(['检查点','失败类型','剩余动作预算','Original主线','Oracle主线','差值','Oracle首章','Oracle动作','终止'],[
        [p['start'],p['subtype'],301-p['start'],p['original_main'],p['oracle_main'],p['main_difference'],'是' if p['oracle_chapter1'] else '否',p['oracle_actions'],p['oracle_status']] for p in pairs])
    class_table=table(['类别','数量','比例及分母','典型证据'],[
        ['A 格式/接口错误','3个提案，涉及2个决策',f"{3/324:.2%}，分母324个模型提案",'a175一次、a177两次write quiet；均在环境执行前被拒'],
        ['B 状态/前置条件不满足',34,f"{34/300:.2%}，分母300个执行动作",'a54手满；a60缺工作台；a136没拿写字工具'],
        ['C 连续同动作/同公开上下文失败',1,f"{1/300:.2%}；占34个B类失败的{1/34:.2%}",'a31→32重复lockpick library；C与B重叠'],
        ['D 严格8步无新公开信息代理',source['counts'].get('D_zero_information_window8',0),'0/300','没有满8步连续零新信息；不能据此断言无规划停滞']])
    subtype_table=table(['B子类','数量','占34个实际失败'],[[k,v,pct(v/34)] for k,v in source['subtype_counts'].items()])
    recovery_table=table(['失败动作','原动作','下一动作','首次后续被接受动作','相同动作20步内成功','后20步主线增量'],[
        [r['step'],r['action'],r['next_action'],r['first_accepted_after'] or '无',r['same_action_success_within20'] or '无',r['main_gain_next20']] for r in rec])
    md('ActionFailureReplay分析报告.md',f'''
# Action Failure Replay：完整母轨迹审计

数据只有 Stage25 remnant seed42 一条母轨迹：300个实际动作、324个模型提案，主线奖励1，未完成第一章。每一步的观察、当前目标、全部提案、实际执行、反馈、下一观察和进度变化已写入 `results/stage26/action_failure_replay.jsonl.gz`，与原始轨迹行号一一对应。

{class_table}

这不是四个互斥分箱。A使用提案分母，B/C/D使用执行动作分母，C包含在B中；不能把表中数量或百分比直接相加。原生 `step_invalid_action` 为0，34次是公开反馈中的语义拒绝，不能把二者混为一谈。

{subtype_table}

B描述已经观察到的环境拒绝原因，不一概指控Agent“明知状态还做错”：第一次缺工具/工作台反馈可能是在发现此前未知约束。只有当前可见条件或此前同上下文失败提供支持时，才谈失败经验利用。完整已公开前因、首个反馈和后续恢复可由逐步记录核查。

## 连续失败与恢复

连续任意失败区段共有7组：28–29、31–32、60–61、85–86、135–136、269–270、289–290，最长2步。严格同动作且同公开上下文的相邻重复只有a32；非连续同上下文复发还有a34重复a28的enter library，合计2个复发终点。没有三连相同失败。a289/a290虽然都制作paper失败，但数量参数不同，不能算“完全相同动作”。

{recovery_table}

首次后续动作被接受只证明结束了局部拒绝，不证明恢复主线。相同动作成功在20步内按完整动作字符串匹配，数量/目标变化不算相同；未出现不是宣称永久不可恢复。

## 主线停滞与合法动作

唯一主线增量在a39进入library。a40公开指引要求先武装再追寻ash；此后261步中，28步环境拒绝、233步动作被接受但无主线增量。全轨迹有265步“被接受但无主线增量”。这包括合理准备、战斗和生存，不能全标为无效动作；但它说明仅统计接口错误无法解释大多数后续预算。

严格D代理为0，是因为新敌人、战斗反馈和库存操作会不断产生新公开信息。另有{len(source['short_public_state_cycles'])}个≤8步公开状态回环终点，存在区段重叠，也包含教程规定操作；它们不是同样数量的独立失败循环。原始公开状态签名忽略时间/HP等变化，有状态回环不代表完整原生状态相同。所有区段在 `source_failure_statistics.json:short_public_state_cycles` 中保留。

a60制作wood_plank缺工作台；a85装备torch失败；a122装备wooden_rod失败；a130成功装备容器；a133成功制作torch；a136写字缺工具；a214最终成功写quiet；a235/289/290制作缺材料。Agent有时能恢复局部操作，但这些成功没有转化为第二个主线阶段。a82、209、257发生死亡，不能仅用低wait次数描述这段行为是有效探索。

![母轨迹失败位置](figures/original_failure_timeline.png)

观察层面的结论：**实际被拒动作主要是B类状态/前置条件错误；整局长期停滞不能等同于格式错误或连续重复失败。** 是否值得新增动作层，应结合[Oracle结果](OracleActionCorrection实验结果.md)，而非单凭失败次数选择模块。
''')
    short=table(['检查点','首步新信息 原/Oracle','后续20步新状态 原/Oracle','后续20步拒绝 原/Oracle','后续20步回环 原/Oracle','前20步主线增量 原/Oracle'],[
        [n,f"{int(lookup[n,'Original']['first_action']['public_progress']['informative'])}/{int(lookup[n,'Oracle']['first_action']['public_progress']['informative'])}",
         f"{lookup[n,'Original']['windows']['following20']['new_states']}/{lookup[n,'Oracle']['windows']['following20']['new_states']}",
         f"{lookup[n,'Original']['windows']['following20']['failures']}/{lookup[n,'Oracle']['windows']['following20']['failures']}",
         f"{lookup[n,'Original']['windows']['following20']['cycle_ends']}/{lookup[n,'Oracle']['windows']['following20']['cycle_ends']}",
         f"{lookup[n,'Original']['windows']['first20']['main_gain']}/{lookup[n,'Oracle']['windows']['first20']['main_gain']}"] for n in CASES])
    windows=table(['检查点','版本','前5步信息/实际动作','前20步信息/实际动作','新主线阶段状态数','后续动作总失败','末段无主线增量动作'],[
        [m['start'],m['variant'],f"{m['windows']['first5']['informative']}/{m['windows']['first5']['actual_actions']}",f"{m['windows']['first20']['informative']}/{m['windows']['first20']['actual_actions']}",m['new_main_state_count'],m['counters']['public_failed'],m['tail_without_main_progress']] for m in metrics])
    md('OracleActionCorrection实验结果.md',f'''
# Oracle Action Correction 实验结果

结论：**{verdict}**。{interpretation}

{pairtable}

Original全部复用同一已验证母轨迹的对应后缀，新增模型调用0；Oracle只替换各分支的第一步。原始第一章为0/10，Oracle为{con['oracle_chapter1']}/10，全主线为{con['oracle_full_quest']}/10。配对主线：提高{con['main_improved']}、持平{con['main_tied']}、降低{con['main_worse']}。所有分支均列出，没有按结果删样本。

{early_note} 这说明Stage25原母轨迹“未被格式错误终止”不是可靠性保证。它是分支后续发生的A类提案错误，不能加进原母轨迹34个环境失败或误记为环境内四连失败。原始证据在 `runs/remnant_a028/Oracle/decision_exhausted.json` 与该局请求日志；重试本身仍没有生成有效动作。

10个检查点从a28到a270，剩余预算273至31步，不能把不同起点的绝对任务机会混在一起。原生阶段状态数按 `chapter:stage:complete` 的新增状态组合计算，仅用于离线评价；不把动态敌人击杀数量冒充主线子目标数。

## 同状态第一步和短期结果

每个Oracle第一步均从完全相同的原生状态、公开观察、记忆、目标和原模型提案出发。10个修正动作均被原生环境接受且没有即时死亡，这是预先筛选条件，不能作为“模块有效率100%”。即时主线奖励、HP变化、反馈和信息变化逐例见 `diagnostics.json:first_step`。

{short}

“后续20步”明确排除被修正的第一步，避免把保证通过的动作计作独立恢复证据；“前20步”包含替换动作。若因原生结束或冻结算法终止窗口不足，保留实际分母并标为censored，完整前5/20及后续5/20统计在 `paired_metrics.json:windows`。

局部效率也有正面结果：a28、a32分支的首次主线奖励分别在绝对a29、a33获得，比Original的a39提前10步和6步；a37分支却延后至a46。三个分支最终仍停在1。排除干预动作后的20步中，新公开状态数4个分支增加、6个减少；环境拒绝数5个减少、4个增加、1个持平；主线增量10个配对均相同。不能只展示短期改善分支。

只有1个检查点满足“Oracle首步有新公开信息、Original首步没有”；失败反馈本身也可能是新规则信息，不能把所有原生拒绝当作毫无信息价值。单步接受性与信息量不是同一个指标。

{windows}

![短期状态与拒绝对比](figures/short_term_comparison.png)

## 长期结果

![配对主线曲线](figures/paired_main_progress.png)

单步改变可以改变后续信息、动作失败和路径，但这些指标与主线成功不等价。Original的主线最终为1，不代表每个检查点后都有1点新增：a39之前的检查点原后缀包含一次主线增量，a39之后的原后缀增量为0。所有指标从同一检查点的公开前缀初始化，避免把已知观察当作新发现。

## 可归因范围

同状态原生第一步的差异可以归于这一次动作替换；后续LLM因新反馈重新采样，供应商没有可锁定的采样种子，Original又复用旧样本，所以不能将所有长期差值都精确归于动作替换。10个分支共享一条母轨迹和相互重叠的原始后缀，不是10个独立任务或随机试验，不做显著性检验。

Oracle只保证当步可接受，不保证完成原动作的全部前置条件，也不保证最优选择。a136只丢cloth腾一只手，a235只检查容器；它们不是持续的动作可行性层。为严格保持memory，控制器已写入STM的原提案未重写，下一步通过真实反馈感知执行结果，短期存在一条提案/执行不一致记录。阴性结果只否定“这组单次合法动作替换足以恢复”，不能证明所有动作纠错无价值或规划缺陷已被唯一隔离。
''')
    cases=[]
    for n in CASES:
        a=d[n];o=lookup[n,'Original'];v=lookup[n,'Oracle'];f=a['first_step']
        original_chain=' → '.join(f"a{x['step']} {x['action']}" for x in a['original_next5'])
        oracle_chain=' → '.join(f"a{x['step']} {x['action']}" for x in a['oracle_next5'])
        cases.append(f'''## a{n}：{CASES[n]['subtype']}

原动作 `{f['original_action']}`；Oracle `{f['oracle_action']}`。依据：{CASES[n]['basis']}

原反馈首行：`{f['original_feedback'].splitlines()[0]}`

Oracle反馈首行：`{f['oracle_feedback'].splitlines()[0]}`

原后续5步：{original_chain}。

Oracle后续5步：{oracle_chain}。

最终主线 {o['main']}→{v['main']}；首章 {int(o['chapter1'])}→{int(v['chapter1'])}；后续20步拒绝 {o['windows']['following20']['failures']}→{v['windows']['following20']['failures']}。Oracle末段连续 {v['tail_without_main_progress']} 动作无主线增量。第一步后的目标与记忆遵循原更新机制，没有继续Oracle纠错。

原始证据：`results/stage26/checkpoints/{case_id(n)}/oracle_probe.json`；分支轨迹 `results/stage26/runs/{case_id(n)}/Oracle/trajectory.jsonl.gz`（第1行是a{n}）；首步后细节及所有主线里程碑见 `results/stage26/case_evidence/{case_id(n)}.json`。''')
    md('关键反事实案例.md','# 10个关键反事实案例\n\n全部预选检查点均列出，不按收益选例。原始观察、反馈、提案和目标记录保留在机器可重算文件中。\n\n'+'\n\n'.join(cases))
    direction=('不建议依据本轮直接开发新的通用Action Reliability Layer。优先研究任务相关状态理解与多步执行，重点属于 State Grounding 与 Exploration/Planning；同一非法提案在有限重试中反复出现仍是明确的接口工程问题，不能忽略，但缺少它是整局主因的证据。Failure Memory优先级较低。' if no_gain else
        '存在局部恢复证据，可继续研究有明确状态前提的轻量动作可靠性；仍需将State Grounding、模型采样与长期规划分开验证，不能直接宣布普遍有效。')
    md('下一阶段机制建议.md',f'''
# 下一阶段机制判断

{direction}

**1. remnant主要失败原因是什么？** 已执行且被拒的动作主要属于B类前置条件/状态不一致（34次）；格式错误只有3个提案且已被现有重试恢复，严格相同动作/上下文的连续失败只有1个复发终点。整局a39后有233个被接受但无主线奖励的动作，持续完成局部战斗、恢复、搬动物品，未形成下一主线阶段的执行序列。{interpretation} 因此，观察上是状态条件处理与任务相关多步推进的混合问题；不能仅凭这些数据把“长期规划能力不足”定为唯一根因。

**2. Action-level workflow是否值得继续优化？** 基础语法检查和有限重试已有工程价值，应该保留，但a28分支决策225四次重复非法批量拾取后停止，证明泛化的重试提示仍可能无法修复接口错误。其余九个分支没有这一提前终止，主线仍无提升，故接口错误不能独自解释全部阴性结果。本轮未测试持续纠错、全部动作前置条件修复或最优Oracle计划；不能说动作层没有空间。是否继续投入应以能否解决真实材料/容器/工具状态条件并带来主线增量为标准，不能只降低invalid或增加接受率。新模块开发在本阶段没有发生。

**3. 下一步属于哪一类？**

| 方向 | 本轮直接证据 | 判断 |
|---|---|---|
| Action Reliability / Interface Repair | 原母轨迹3个格式错误已恢复；a28分支又出现四次相同非法提案并停止 | 有明确工程故障；不能宣称已完全解决，也不能直接包装为主要机制贡献 |
| State Grounding | 11次手容量、工具/工作台/装备/材料等明确拒绝 | 有具体问题，需区分首次规则发现与已有反馈未利用 |
| Failure Memory | 严格连续相同失败只有a32；非连续同上下文复发另有a34 | 缺少“主导整局失败”的多点证据，低优先级 |
| Exploration/Planning | a39后261步无主线增加，233步动作已被接受；单次Oracle的长期结果见配对表 | 值得诊断任务相关性、跨动作依赖和生存/任务冲突；尚不能唯一归因 |

普通接口重试、记录真实执行和字段校验属于工程问题。如何用公开反馈区分“新事件”和“目标进展”、将已发现约束转化为跨动作资源配置，以及在生存压力中维持主线依赖，可能形成独立研究问题；本轮只提供候选证据，不据一次母轨迹宣布论文机制成立。

没有进入Stage27，没有新增记忆/规划/规则模块，没有增加500步评测，没有重跑失败分支。若后续再做诊断，必须重新明确所检验的干预及可识别范围，而不是根据本轮结果在同一冻结样本上反复调参。
''')
    costtable=table(['检查点','新请求','输入token','输出token','计价USD','实际续跑动作'],[[n,lookup[n,'Oracle']['new_requests'],lookup[n,'Oracle']['input_tokens'],lookup[n,'Oracle']['output_tokens'],f"{lookup[n,'Oracle']['cost_usd']:.9f}",lookup[n,'Oracle']['actual_actions']] for n in CASES])
    md('Stage26实验报告.md',f'''
# Stage26：Action Failure Diagnosis

**最终判定：{verdict}。** {interpretation}

本轮按指引26完成完整动作审计与10个检查点的一次动作修正实验。数据来自Stage25 remnant seed42的**一条**失败母轨迹，不能写成10条独立失败任务。Stage25-AGC-v2代码、模型、提示、记忆机制、环境和评分全部冻结；mark/metropolis及其他基线未运行。

{pairtable}

## 主要发现

{class_table}

原轨迹a39后主线不再增加；261步尾段中28次动作被拒，233次动作被接受却没有主线增量。严格D无信息代理为0，反映新战斗/库存事件仍不断出现，不能把“有新信息”当作完成目标。格式、状态可执行性与多步任务推进是不同层次。

Oracle只改变一次发给环境的动作，10个替换均当步被接受。长期配对结果为：提高{con['main_improved']}、持平{con['main_tied']}、降低{con['main_worse']}；首章Original 0/10、Oracle {con['oracle_chapter1']}/10。局部接受率由选择条件保证，短期新状态/失败次数变化应结合最终主线看。完整前5/20步、排除首步的后续5/20步和关键状态变化见[Oracle结果](OracleActionCorrection实验结果.md)。

局部并非完全无收益：a28/a32分支首次主线增量分别提前10步/6步，但a37延后7步，最终得分均未提高。排除替换动作后的20步，4个分支新状态更多、6个更少；5个分支拒绝更少、4个更多、1个相同，主线增量均无配对差异。

{early_note}

{direction}

## 实验约束与可归因性

冻结代码提交 `ec7ef26`，checkpoint及源文件清单提交 `800096d5f3ba2426870540d66de7f8d8550b41ae`；付费续跑在两者提交后启动。10个检查点及Oracle动作在任何新模型调用之前预选并验证，没有按结果换点、换动作或调参。每分支只使用原300步上限的剩余预算，总可执行上限1994步，最多10并行。

Original直接复用原后缀。Oracle首步的模型请求精确复用原响应，其后按真实新观察使用同一冻结Agent继续。为保持memory，act中已经写入的原提案不被Oracle改写；模型通过下一条真实反馈看到实际动作结果。该限制、单次动作只保证接受而非修复全部前置条件、后续模型随机采样，以及十个分支同母轨迹的依赖性，都限制了长期因果解释。不能将阴性结果当作“任何动作层均无效”的证明，也不能将少数阳性结果当作显著提升。

## 成本与验证

{costtable}

新增模型请求 **{cost['new_requests']}** 次，输入 **{cost['input_tokens']}**、输出 **{cost['output_tokens']}** tokens，计价 **${cost['cost_usd']:.9f}**。首次动作复用旧响应 {cost['source_requests_reused']} 次，Original后缀、离线探测、回放、统计和报告新增模型调用均为0。按每次响应usage及保存价格逐条重算，与分支/全局SQLite账本一致；没有供应商发票，费用为可核验的本地计价。

新请求中另有4条解析/字段异常：a32分支绝对a160、a37分支a180、a136分支a231为长度截断伴随JSON不完整，a60分支a242返回内容缺action字段；均在冻结重试流程内恢复。它们与a28分支的四次语法错误不同，完整请求位置见 `response_anomalies.json` 和 `diagnostics.json`，没有因异常追加实验或调高输出上限。

原母轨迹300个动作及324个模型上下文完整重建；10个预选Oracle当步接受性检查通过；10个断点/续跑/单次替换/不改记忆和目标合同检查通过。所有Oracle分支共 **{audit['verified_oracle_native_actions']}** 个原生动作及 **{audit['verified_model_contexts']}** 个模型输入上下文通过禁网精确回放，核对原生状态哈希、反馈、奖励、决策、最终记忆；{audit['freeze_integrity']['project_files']}个项目文件和278个引擎文件完整性通过。官方原评分脚本重新确认主线结果，原始异常和有限重试终止均保留。

全部机器统计、证据索引与完整轨迹在 `results/stage26/`；分析/回放代码在 `scar_stage26/`。参见[完整动作分析](ActionFailureReplay分析报告.md)、[全部10个案例](关键反事实案例.md)、[下一阶段判断](下一阶段机制建议.md)、[Git变更记录](Git变更记录.md)。不修改算法来追求本轮reward。
''')
    md('README.md','''
# Stage26

- [实验报告与结论](Stage26实验报告.md)
- [Action Failure Replay完整分类](ActionFailureReplay分析报告.md)
- [Oracle Action Correction配对结果](OracleActionCorrection实验结果.md)
- [全部10个关键反事实案例](关键反事实案例.md)
- [下一阶段机制建议](下一阶段机制建议.md)
- [付费前冻结协议](预登记诊断协议.md)
- [Git变更记录](Git变更记录.md)

范围：1条Stage25 remnant母轨迹，10个检查点，10个原始后缀复用、10个单次Oracle续跑。不是10个独立任务。原模型和Agent未改。

数据：`results/stage26/action_failure_replay.jsonl.gz`逐动作公开证据；`source_failure_statistics.json`分类及原失败反馈；`original_failure_recovery.json`原始恢复；`paired_metrics.json`完整窗口统计；`paired_comparison.csv`逐检查点比较；`diagnostics.json`首步反事实/重试/终止；`evidence_index.jsonl.gz`逐分支行号及请求对应；`cost_reconciliation.json`费用核对。

在原依赖环境中设定匹配引擎的AGENTODYSSEY_ROOT及本仓库/引擎PYTHONPATH后，可禁网重算：

```bash
python -m scar_stage26.verify --start 28
python -m scar_stage26.analyze
python -m scar_stage26.diagnose
python -m scar_stage26.report
```

verify对协议中的其他检查点分别执行。account在保留原始SQLite账本的机器核验费用；每次请求的usage/价格/费用均已归档，可独立重算。prepare/source_audit及smoke属于已冻结的运行前证据，不要为重看结果重写原文件。run/batch会涉及付费API调用，不属于离线分析入口。

下载引擎、依赖环境、API密钥不上传；只归档本阶段代码及生成的实验/分析材料。
''')
    print(json.dumps(dict(reports=6,classification=verdict,new_model_calls=0)))

if __name__=='__main__':main()
