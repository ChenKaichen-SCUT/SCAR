"""Render Stage28 reports solely from saved measurements and cited evidence."""
from collections import Counter
from .common import *

def table(headers,records):
    return '|'+ '|'.join(headers)+'|\n|'+ '|'.join(['---']*len(headers))+'|\n'+'\n'.join('|'+ '|'.join(str(x).replace('|','/').replace('\n',' ') for x in r)+'|' for r in records)+'\n'
def ratio(n,d):return f'{n}/{d}（{100*n/d:.1f}%）' if d else '不适用'
def yn(v):return '是' if v else '否'
def put(name,text):(REPORTS/name).write_text(text)
def link(path):return f'[{path}](../../{path})'

def main():
    offline();c=read(RESULTS/'chain_statistics.json');s=read(RESULTS/'summary.json');pairs=read(RESULTS/'paired_comparison.json')
    reviews=read(RESULTS/'selected_pair_semantic_review.json');v=read(RESULTS/'verification.json');cost=read(RESULTS/'cost_reconciliation.json')
    a=c['all'];o=s['variants']['Original'];b=s['variants']['OracleRecovery'];adopted=sum(r['initial_recovery_goal_adopted'] for r in reviews)
    local=s['clear_local_improvement'];long=s['clear_long_improvement']
    assert local and not long, 'Rewrite interpretation if actual predeclared result differs; do not reuse a mismatching narrative.'
    conclusion='LOCAL_RECOVERY_GAIN_WITHOUT_LONG_HORIZON_GAIN'
    description='单次恢复目标提示能改善部分局部恢复，但没有提高本轮长期主线表现；证据支持“恢复目标组织是部分薄弱环节”，不足以确认它是主要或唯一瓶颈。'
    stats=table(['实际在线阶段/代理指标','全事件','仅母轨迹'],[
        ['下一决策明确提及正确缺口（规则命中）',ratio(a['understanding_next'],a['post_failure_observed']),ratio(c['parent']['understanding_next'],c['parent']['post_failure_observed'])],
        ['新结构化恢复目标',ratio(a['structured_objective_next'],a['post_failure_observed']),ratio(c['parent']['structured_objective_next'],c['parent']['post_failure_observed'])],
        ['较宽口径：新目标或理由中的恢复意图',ratio(a['formation_next'],a['post_failure_observed']),ratio(c['parent']['formation_next'],c['parent']['post_failure_observed'])],
        ['20 步内至少一个被接受的相关恢复动作',ratio(a['full20_execution_any'],a['full20']),ratio(c['parent']['full20_execution_any'],c['parent']['full20'])],
        ['20 步内至少两个相邻的相关恢复动作',ratio(a['full20_consecutive_execution'],a['full20']),ratio(c['parent']['full20_consecutive_execution'],c['parent']['full20'])],
        ['20 步内原失败动作成功',ratio(a['full20_successful_retry'],a['full20_retry_scorable']),ratio(c['parent']['full20_successful_retry'],c['parent']['full20_retry_scorable'])],
        ['先有相关恢复动作，再原动作成功',ratio(a['full20_closed_local_loop'],a['full20_retry_scorable']),ratio(c['parent']['full20_closed_local_loop'],c['parent']['full20_retry_scorable'])],
        ['原 goal 字符串切换后返回',ratio(a['full20_goal_string_return'],a['full20']),ratio(c['parent']['full20_goal_string_return'],c['parent']['full20'])],
        ['20 步内主线奖励增加的事件窗口',ratio(a['full20_main_gain_events'],a['full20']),ratio(c['parent']['full20_main_gain_events'],c['parent']['full20'])]])
    limitations='''这些是相关轨迹上的描述统计。336 个事件来自 1 条母轨迹及其 10 条既有分支，窗口重叠；不能视作 336 个独立游戏。规则检测的“理解”是实际 reasoning 提及缺口，不等同整个世界状态理解正确。宽口径恢复意图不等同合格子计划，相关动作被接受也可能只是丢下/捡回。只有 302 个事件有完整 20 步窗口，另外 34 个右删失；其中不可装备、不可制作等本身无效动作不纳入原动作应成功的分母，最终该分母为 260。所有事件仍保留在数据库中。

拒绝/接受沿用冻结的公开反馈提取器与原生 invalid-action 标志，是可重算代理，不是全量独立人工动作效用审查。本轮 Oracle parent_a054 第 73 步 “Failed to lockpick…already unlocked” 未命中冻结拒绝正则；补充字段 supplemental_failure_steps 保留此负面反馈，表中明确区分，不改变预登记原动作恢复统计。336 个历史事件窗口的原动作成功未发现这类标记冲突。所有原始反馈保留。goal 字符串未返回不能推出未恢复原任务，等价改写、合法替代路径与生存优先都需要语义核验。全部 10 个配对的前 20 步由本助手核对原文，非独立人工盲审。
'''
    put('Stage28失败恢复链分析报告.md',f'''# Stage28 失败恢复链分析报告

结论：**{conclusion}**。{description}

Stage25-AGC-v2、模型、基础提示生成链和环境未修改。实验适配层只在失败后首个决策中追加一个临时恢复目标，正常的语法重试/置信度复审保留；不强写控制器、不给行动序列、位置或隐藏规则。模型自行把目标写入 goal_description 的比例为 {adopted}/10。Original 精确复用保存的后缀，Oracle 各采样一次，绝对动作上限仍为 300。

## 实验一：观察原 Agent 的完整恢复链

{stats}

并非“理解之后完全不能形成恢复意图”：宽口径意图已有 {a['formation_next']}/{a['post_failure_observed']}，完整窗口内也观察到 {a['full20_closed_local_loop']} 个局部闭环。真正需要解释的是为什么这些局部行为难以稳定地组合成更长任务，而不是把很低的新 goal 字段比例直接解释成没有恢复能力。

## 实验二：10 个配对检查点

{table(['指标','Original','Oracle Recovery'],[
 ['新增模型请求',0,s['new_requests']],['实际续跑动作',o['actions'],b['actions']],
 ['前 5 步公开拒绝动作合计',o['short_rejections'],b['short_rejections']],
 ['前 5 步原失败动作再次拒绝',o['short_repeated_original_rejections'],b['short_repeated_original_rejections']],
 ['前 20 步原失败动作成功',str(o['medium_actual_retry_success'])+'/10',str(b['medium_actual_retry_success'])+'/10'],
 ['前 20 步局部恢复闭环',str(o['medium_closed_loop'])+'/10',str(b['medium_closed_loop'])+'/10'],
 ['第一章完成',str(o['chapter1'])+'/10',str(b['chapter1'])+'/10'],
 ['最终主线奖励（按检查点顺序）',o['main_final'],b['main_final']]])}

原动作成功配对：双方 {s['local_actual_retry_pair_counts']['both']}、仅 Original {s['local_actual_retry_pair_counts']['Original_only']}、仅 Oracle {s['local_actual_retry_pair_counts']['Oracle_only']}、双方均未成功 {s['local_actual_retry_pair_counts']['neither']}。净增 {s['local_net_improvement']}/10，达到预登记局部阈值；最终主线更高 {s['main_improved']}/10、更低 {s['main_worsened']}/10，未达到长期阈值。预登记阈值是描述标准，不是统计显著性。

改善也不是全面的：前 5 步拒绝总数为 {o['short_rejections']} → {b['short_rejections']}，原失败动作再次拒绝均为 {o['short_repeated_original_rejections']}。这些负面/持平指标与局部恢复成功一起保留。

其中 parent_a054 的命中只是丢下再捡回铁条，不能称为新增资源；parent_a113 更快取出木杆后仍错误装备，而 Original 后来制作了 torch。较清晰的局部案例为 parent_a060 到工作台制作木板、parent_a136 取得 pen/paper 后写字、parent_a270 清出容器空间后存储。这些收益没有排除负面分支，也没有转化成本轮第一章完成。

## 能支持什么，不能支持什么

支持：把明确缺口变成活跃目标能改变部分实际恢复行为。不能支持：纯粹恢复目标生成是长期失败的主要根因；已有记忆/状态理解完全充分；任何增加恢复控制器都会有效。Oracle 后仍出现手部容量、照明、物品用途、材料链与生存中断的交互问题。目标采纳不是执行保证，原失败动作的前置条件也不一定是全局最优子目标。

{limitations}

Original 是保存的模型样本，Oracle 是新的模型采样，没有供应商配对随机种子。相同检查点状态/记忆与环境 RNG 已验证，但后续差异仍混入采样分叉；因此称配对提示干预证据，不称严格隔离的因果效应。初始资源恢复不等于长期规划已经解决。

## 验证与费用

新增请求 {s['new_requests']}，input token {s['input_tokens']:,}，output token {s['output_tokens']:,}；usage 与保存单价核算费用 **${s['cost_usd']:.9f}**，不是供应商账单。无未知计费、无悬而未决预留。不重跑失败分支。

精确离线重放 {v['exact_native_actions']} 个 Original/Oracle 环境动作、{v['exact_model_contexts']} 个已保存模型上下文；另有 {v['isolated_probe_actions']} 次隔离可行性探针，均不回传 Agent、无模型调用。旧代码和数据哈希保持不变，冻结提交 `07c8284`。详见 [实验结果](OracleRecoveryObjective实验结果.md)、[机制建议](下一步机制设计建议.md)、[预登记](预登记诊断协议.md)。
''')
    bytype=table(['缺口类型','事件','下一步理解','新 goal','恢复意图','完整窗口','局部闭环/适用'],[
        [t,d['events'],str(d['understanding_next'])+'/'+str(d['post_failure_observed']),d['structured_objective_next'],d['formation_next'],d['full20'],str(d['full20_closed_local_loop'])+'/'+str(d['full20_retry_scorable'])] for t,d in c['by_type'].items()])
    put('Failure-to-Recovery分类统计.md',f'''# Failure-to-Recovery 分类统计

{stats}

下一决策三分类（另列无后续动作）：

{table(['类别','数量'],list(a['recovery_classes'].items()))}

## 按缺口分类

{bytype}

## 口径与重算

{limitations}

四阶段不是简单漏斗：原 Agent 可能没有改 goal 字段，却用原目标下的动作恢复；也可能合理放弃原失败动作。不同分母已经明列，不得拿 18/334 与 109/260 相减当作转化流失。

{link('results/stage28/failure_recovery_database.jsonl.gz')} 为全部 336 事件的完整数据库：失败前 observation、inventory、location、goal、动作、公开反馈、历史动作、后 5/20 步及最终结果、源文件/行号均可追溯。{link('results/stage28/failure_recovery_chains.jsonl.gz')} 保留命中理由原句。分类规则冻结在 {link('scar_stage28/chain.py')}；无新增分析模型调用。
''')
    pairtable=[];eff=[];probe_table=[]
    for p in pairs:
        x=p['variants']['Original'];y=p['variants']['OracleRecovery'];out=y['summary']
        pairtable.append([p['id'],p['action'],yn(x['windows']['20']['successful_original_retry'])+'/'+yn(y['windows']['20']['successful_original_retry']),
            str(x['windows']['5']['rejected'])+'/'+str(y['windows']['5']['rejected']),str(x['final_main'])+'/'+str(y['final_main']),
            out['steps'],out['status'],out['new_requests'],f"${out['cost_usd']:.6f}"])
        for variant in ['Original','OracleRecovery']:
            z=p['variants'][variant];w=z['windows']['20'];short=z['windows']['5'];pp=z['probes']
            eff.append([p['id'],variant,short['repeated_original_rejection'],len(short['holding_increases']),len(short['new_public_state_steps']),
                len(w['new_location_events']),str(w['rejected'])+'/'+str(w['rejected']+len(w['supplemental_failure_steps'])),w['wait'],yn(w['consecutive_execution']),w['successful_original_retry_steps']])
            probe_table.append([p['id'],variant]+[next((yn(q['accepted']) for q in pp if q['continuation_step']==n),'无') for n in [0,5,20,z['summary']['steps']]])
    exception_rows=rows(RESULTS/'exceptions.jsonl.gz');ec=Counter(e['kind'] for e in exception_rows)
    put('OracleRecoveryObjective实验结果.md',f'''# Oracle Recovery Objective 实验结果

## 设置与公平性

10 个拒绝后检查点，原始状态/AGC 记忆/控制器一致。7 个来自母轨迹，3 个来自 Stage26 的既有相关分支；独立母轨迹只有 1 条。每个 Original 使用已保存后缀，每个 Oracle 新采样一次，不重跑对照。prompt 唯一新增段落在首个决策及其原生重试中使用；后续完全按原 Agent 输入链。恢复目标来自当前失败反馈，不含配方、位置、行动序列。所有10个 goal 字段与 control_after 都确认采纳。

## 逐检查点结果

下表斜杠为 Original / Oracle；原动作恢复指 20 步内真实执行成功。

{table(['检查点','原失败动作','原动作恢复 O/R','前5拒绝 O/R','最终主线 O/R','Oracle 动作','终止','新请求','费用'],pairtable)}

主线提高 {s['main_improved']}/10、下降 {s['main_worsened']}/10；第一章 {o['chapter1']}/10 → {b['chapter1']}/10。不能把容量释放或无关制作计作主线完成。所有分支均进入汇总，包括没有收益或退步的分支。

“恢复条件”和“恢复原动作”须分开：oracle037_a122 的 Original 125、Oracle 123 均已进入含 workbench 的 hall，设施目标已有公开达成证据，但都未在 20 步内成功 craft lockpick；剩余材料/容量问题仍然存在。parent_a136 的 Oracle 138 取得 pen 后，直到 141 持有 paper 才写字成功。未重试原动作的 Original 也可能曾释放过容量，因此表中“否”仅表示未观察到原动作成功，不表示临时条件从未满足。

## 短期与中期行为

{table(['检查点','版本','5步原动作再拒绝','5步持有增加事件','5步新公开状态','20步新区域事件','20步拒绝 冻结/含补充','20步wait','连续恢复动作代理','原动作成功步'],eff)}

持有增加只是公开手部/装备数量增加，可能是捡回已拥有物品或黑暗结束后重新可见，不等同获得缺失资源。新状态采用冻结公开状态签名（忽略时间/HP）；战斗或反复搬运造成的变化不等同任务推进。连续恢复动作代理必须结合逐条理由与反馈阅读。

## 隔离原生可行性探针

{table(['检查点','版本','0步','5步','20步','最后状态'],probe_table)}

每个探针只在隔离副本重试原失败动作，不改变正式环境，不返回模型。成功说明该时刻原动作可执行；失败可能来自其他缺口或位置变化，不能推断此前从未恢复。探针 0 全拒绝；该表与实际执行成功步是不同测量。

## 异常、成本与复现

{table(['记录类型','数量'],sorted(ec.items()))}

confidence_review 是原生目标复审，不是 API 错误；hard_retry 是原有语法约束处理。全部原始响应、请求、重试和终止见 {link('results/stage28/exceptions.jsonl.gz')}。不为不理想输出另行重采样。

新增 {cost['new_requests']} 请求，{cost['input_tokens']:,} 输入 / {cost['output_tokens']:,} 输出 token，${cost['cost_usd']:.9f}。费用按每次实际 usage 和当时单价重算，非供应商 invoice。{link('results/stage28/request_accounting.csv')} 提供逐请求明细，{link('results/stage28/paired_comparison.json')} 提供全量配对统计，{link('results/stage28/verification.json')} 提供离线验证收据。

10 个初始检查点、第一次未加提示的输入逐字一致、每次唯一追加段落、后续完整模型上下文、动作/状态/反馈/控制器均已精确核验。分析代码和隔离探针没有调用模型。不同随机模型样本是本实验主要因果限制。
''')
    cases=[]
    for r in reviews:
        ident=r['id'];p=next(p for p in pairs if p['id']==ident)
        cases.append(f"## {ident}\n\n原目标：{p['goal']}。原动作：`{p['action']}`。提示：{p['objective']}\n\n首步 Agent 目标：`{r['model_goal']}`；控制器登记一致。\n\n{r['oracle_finding']}\n\n{r['original_comparison']}\n\n证据：Oracle 动作 {', '.join(map(str,r['oracle_evidence_steps']))}；{link(r['oracle_evidence'])}，{link(r['original_evidence'])}。逐步原始 reasoning、feedback 和控制器状态均保留；动作号为绝对动作号，文件中行号以证据索引为准。\n")
    put('典型失败案例.md','# Stage28 全部 10 个配对案例核查\n\n本助手核查全部选定对的前 20 步，非独立人工评审。以下同时保留局部收益、无收益与反例，不根据最终分数倒推原因。\n\n'+'\n'.join(cases))
    put('下一步机制设计建议.md',f'''# 下一步机制设计建议

**{conclusion}**。{description}

## 对核心问题的回答

本轮不能确认“主要限制已经不是记忆或状态理解，而只是缺少 workflow control”。实际在线轨迹里，{a['understanding_next']}/{a['post_failure_observed']} 提及正确缺口、{a['formation_next']}/{a['post_failure_observed']} 有恢复意图，也存在局部恢复闭环；所以“完全没有失败→目标→执行”不符合证据。10 个提示均被采纳，原失败动作成功从 {o['medium_actual_retry_success']}/10 到 {b['medium_actual_retry_success']}/10，说明把缺口提升为当前目标能帮助一部分局部操作。最终主线更高 {s['main_improved']}/10，第一章 {o['chapter1']}/10 → {b['chapter1']}/10，长期收益未确认。

## 最符合证据的解释

1. 部分失败具有目标组织成分：工作台、写字工具和容器空间案例，提示后出现直接可验证的恢复链。
2. 执行中的约束交互仍明显：保留 torch 与腾手拿材料冲突；对当前手部空间或包可访问性的判断错误；取出物品后错误装备；具备设施但仍缺材料。目标文本正确并未让这些问题消失。
3. 临时目标的必要性、结束与原任务回归不能忽略。开锁可由 key 替代、craft usable item 可换配方；执着恢复某个失败动作可能偏离更大的任务。提示正确描述局部缺口，不代表已给出全局正确计划。
4. 生存优先和随机轨迹分叉影响恢复链。不能把所有战斗中断都叫无关探索，也不能从新旧不同模型轨迹直接认定某控制器机制造成全部差异。

Stage27 同样只证明了在其诊断口径下模型多能解释失败、那一种结构化输入没有带来整体收益，不能据此排除当前状态维护、信息失效或记忆利用的其他机制。

## 是否开发 Resource-grounded Recovery Controller

值得保留为**局部恢复研究候选**，暂不将其定位为已验证的长期瓶颈解决方案，也不直接进入完整 Controller 开发。本轮较接近指引情况 C，但“局部提升 + 长期无提升”不是对唯一机制的证明。尤其铁条丢下再捡回是代理指标正例、任务进展反例，应在未来诊断中区分条件恢复、资源净增长、原任务恢复三个层次。

若用户后续要求推进，优先用现有轨迹进一步核验资源条件何时满足、何时再次失效，以及生存打断后恢复链能否继续；新增实验应覆盖多个独立初始任务和模型采样，并包含等长度非恢复提示对照，以区分恢复目标内容、额外注意力与采样效应。需要额外实验才能判断机制价值；这些未在 Stage28 实施。

本轮没有添加失败解释器、状态提取模块、记忆模块、规划器、恢复控制器或新的行动规则。所有改动是独立诊断适配与分析代码。
''')
    put('README.md','''# Stage28 复现入口

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
''')
    write(RESULTS/'interpretation.json',dict(label=conclusion,local_gain=local,long_gain=long,adopted=adopted,
        primary_bottleneck_confirmed=False,new_controller_implemented=False,description=description))
    print(json.dumps(dict(reports=7,label=conclusion)),flush=True)

if __name__=='__main__':main()
