"""Chinese reports from measured results and explicit evidence-reviewed annotations."""
from .common import *
from .analyze import save

def table(headers,lines):
    clean=lambda x:str(x).replace('|','／').replace('\n',' ')
    return '\n'.join(['|'+'|'.join(headers)+'|','|'+'|'.join('---' for _ in headers)+'|']+['|'+'|'.join(clean(x) for x in row)+'|' for row in lines])

def main():
    offline();s=read(RESULTS/'summary.json');pp=read(RESULTS/'paired_comparison.json');review=read(RESULTS/'semantic_review.json');cost=read(RESULTS/'cost_reconciliation.json');v=read(RESULTS/'verification.json');exceptions=read(RESULTS/'response_anomalies.json')
    av=s['variants']['OriginalRecovery'];bv=s['variants']['OracleGoalStack'];refs=s['variants']['UnpromptedReference'];verdict=s['pre_registered_verdict']
    limitations='只有 1 条独立 remnant 母轨迹，10 个相关检查点及重叠后缀，每个新分支仅一次模型采样。历史对照与新采样没有配对模型随机种子，轨迹差异不是严格因果效应。本轮只测试首次决策的公开证据部分层级，不是持续维护的全知目标栈；子条件表述与提示长度也改变了，不能把差异纯归因于层级格式。'
    paired=table(['检查点','20步成功重试 A/B','全后缀成功重试 A/B','条件达成 A/B','主线最终 A/B','动作数 A/B','首个动作分歧'],[
        [p['id'],f"{int(p['variants']['OriginalRecovery']['windows']['20']['successful_original_retry'])}/{int(p['variants']['OracleGoalStack']['windows']['20']['successful_original_retry'])}",
        f"{int(p['variants']['OriginalRecovery']['full']['successful_original_retry'])}/{int(p['variants']['OracleGoalStack']['full']['successful_original_retry'])}",
        f"{r['baseline_condition_step'] or '未证实'}/{r['condition_step'] or '未证实'}",
        f"{p['variants']['OriginalRecovery']['full']['main_final']}/{p['variants']['OracleGoalStack']['full']['main_final']}",
        f"{p['variants']['OriginalRecovery']['actions']}/{p['variants']['OracleGoalStack']['actions']}",r['first_action_divergence_step']] for p,r in zip(pp,review)])
    comparison=table(['指标','A: OriginalRecovery','B: OracleGoalStack'],[
        ['20 步原失败动作成功重试',f"{av['recovery20']}/10",f"{bv['recovery20']}/10"],
        ['全后缀成功重试',f"{av['recovery_full']}/10",f"{bv['recovery_full']}/10"],
        ['恢复条件有公开/原生证据',sum(r['baseline_condition_step'] is not None for r in review),sum(r['condition_step'] is not None for r in review)],
        ['第一章完成',av['chapter1'],bv['chapter1']],['最终主线分数逐例',av['main_scores'],bv['main_scores']],
        ['前20步拒绝总数',av['rejected20'],bv['rejected20']],['前20步原失败动作重复拒绝',av['repeated_original_rejections20'],bv['repeated_original_rejections20']],
        ['全部实际动作',av['actions'],bv['actions']],['全部拒绝',av['rejected_full'],bv['rejected_full']],['wait',av['wait'],bv['wait']],
        ['保存的模型请求',av['requests'],bv['requests']],['输入 token',av['input_tokens'],bv['input_tokens']],['输出 token',av['output_tokens'],bv['output_tokens']],
        ['usage 计价美元',f"{av['cost_usd']:.9f}（历史费用，本轮不重付）",f"{bv['cost_usd']:.9f}"]])
    conclusion=(
        '达到预登记的长期推进收益标准，支持下一阶段评估层级控制机制；仍不能宣称显著优越或唯一瓶颈。' if verdict=='SUPPORT_GOAL_STACK' else
        '达到局部恢复收益标准，但没有明确长期收益。可继续研究层级关系与资源/执行的交互，不能声称它是必要组件。' if verdict=='PARTIAL_SUPPORT' else
        '未达到预登记的明确局部或长期收益标准。本轮不支持直接开发 Hierarchical Goal Stack Controller；这不等于证明目标层级无用，也不排除持续维护机制。')
    save(REPORTS/'Stage30实验报告.md',f'''# Stage30 Oracle Goal Stack Replay 实验报告

结论：**{verdict}**。{conclusion}

{limitations}

## 实验设计与完成状态

复用 Stage28/29 的全部 10 个失败恢复检查点。A 是 Stage28 的 OracleRecovery（首次决策注入平铺恢复目标），B 是本轮层级目标；不是把未提示原始轨迹冒称为主要对照。额外参考的未提示后缀为 20 步 {refs['recovery20']}/10、全后缀 {refs['recovery_full']}/10 成功重试，不能拿这个较弱对照替代 A。

先冻结代码与目标栈（`72ed428`），再在本地运行 10 个新分支；原绝对上限 300 步。用户已确认首次决策注入，后续保持原输入链。所有正式分支及异常均保留，不重采样、不修改 Agent、不开发下一阶段。

模型沿用 `{MODEL['model']}`，temperature={MODEL['temperature']}、top_p={MODEL['top_p']}、max_tokens={MODEL['max_tokens']}；原五条短期记忆输入链不变。全部 10 个新分支到达原绝对 300 步上限，没有提前终止或重新运行。

## 核心指标

{comparison}

20 步逐检查点配对计数：{s['local_pair_counts']}；B 相对 A 的成功重试净差为 {s['local_net']}/10。最终主线改善 {s['main_better']}、退步 {s['main_worse']}；第一章改善 {s['chapter_better']}、退步 {s['chapter_worse']}。阈值预先规定为配对净增至少 3/10，仅为描述标准，非显著性检验。

## 逐检查点比较

A/B 依次为平铺恢复目标/层级目标。条件栏是有公开反馈或隔离原生探针支持的动作号；不是最早时刻估计，也不保证此条件一直保持。parent_a270 的 B=275 特指该步后的离线可行性探针，不是正式轨迹执行了存储。

{paired}

## 如何解读恢复与失败

成功重试是保守的行为终点，不等于净材料增加、较大目标完成或主线推进。丢下再捡回同一资源也可能命中；相反，换用合法替代方法可以有价值，即使原动作未恢复。公开条件、实际重试、原目标语义续接和真正奖励分开统计。

本轮唯一的成功重试净差来自 parent_a270：B 释放了包内空间，第 275 步后的隔离探针证明可以存 cloth，但正式轨迹没有存；274 还明确回到寻找装备的父目标。因此不能把 5→4 的差别解释为“层级组多一条忘记目标”。B 的 4 条成功重试全部都有较大原目标的语义续接证据，A 的 5 条也都有。B 全后缀拒绝 219 对 229、wait 28 对 33，存在小幅行为计数差异，但没有奖励收益，不构成稳定效率优势。

子目标完成、保持和原目标续接由本助手审阅公开轨迹及保存理由，原文证据见 `semantic_review.json`；不是独立盲评。完整逐动作索引与 20 份时间线供复算，不把词面目标变化直接判成遗忘。代表案例见《典型案例与阶段归因》。

## 验证与费用

精确原生离线回放核对 {v['exact_native_actions']} 个动作、{v['exact_model_contexts']} 个模型上下文；另做 {v['isolated_probe_actions']} 个隔离可行性探针，均没有新增模型调用。记录的状态、动作、反馈、奖励、控制器、最终记忆与请求逐一一致。

本轮新增 {cost['new_requests']} 次请求，输入 {cost['input_tokens']:,}、输出 {cost['output_tokens']:,} token，按冻结单价与逐响应 usage 核算 **${cost['cost_usd']:.9f}**。不是供应商结算账单。A/B 运行时段计价不同，费用差不能直接算作方法节省；统一到冻结峰时单价分别为 ${s['common_peak_rate_reference_usd']['OriginalRecovery']:.9f} / ${s['common_peak_rate_reference_usd']['OracleGoalStack']:.9f}。分析和离线验证调用模型 0 次；对照重跑 0 次。异常与原生重审详见 `exceptions.jsonl.gz`，不把原生重审冒称实验重采样。

全部请求均有成功响应与 usage，无未知计费。共有 5 个 JSON 异常：parent_a031 的 107/167/223、parent_a054 的 58 为输出达到 768 token 上限而未闭合；parent_a113 的 296 为 reasoning 内 `"quiet"` 未转义。全部由原生解析重试处理，未手工修复响应。共 {exceptions['hard_native_repair_attempts']} 次未执行的硬拒绝尝试、{exceptions['soft_native_reconsideration_attempts']} 次原生置信度重审；前者包含这些解析异常，也包含动作语法/重复拒绝。最大输入 {exceptions['max_prompt_tokens']} token，以上 length 均是输出上限，不是上下文超限。

## 研究判断

{conclusion}

一次性层级提示没有实现父子节点的持续存储、完成检测、栈弹出或资源状态校验。无论结果正负，均只能回答本轮受限 Oracle 的收益。Stage27/29 也未排除信息可见性、状态判断和执行约束，不能以“模型会解释失败”断言 grounding 不是问题。
''')
    stackrows=[]
    for ident in CASES:
        m=read(RESULTS/'checkpoints'/ident/'meta.json')
        stackrows.append([ident,m['failure_step'],m['original_action'],m['original_goal'],m['objective'], '; '.join(n['goal'] for n in m['goal_stack']['goal_stack'] if n['level']==2),m['remaining']])
    save(REPORTS/'OracleGoalStack构造与检查点.md','''# Oracle Goal Stack 构造与检查点

level 0 是检查点原目标；level 1 与 Stage28 临时恢复目标完全相同；level 2 是公开拒绝已经暗含的可用性/条件确认。兄弟节点没有动作顺序。子条件有些在初始 observation 中已经满足，必须标为已有而不能算新增知识。

禁止提供配方、材料清单/数量、位置或资源路径。本轮不直接使用 Stage29 纸面树，因为其中含当前短期上下文未必可见的旧配方。完整 JSON、公开来源原文、截止动作号与检查点文件哈希见 results/stage30/checkpoints/*/meta.json。未知依赖保持未知，因此不是全知层级上界。

'''+table(['检查点','失败动作号','原动作','level 0','level 1','level 2','剩余预算'],stackrows))
    efficiency=[]
    for p in pp:
        for variant in ['OriginalRecovery','OracleGoalStack']:
            w=p['variants'][variant]['windows']['20'];full=p['variants'][variant]['full']
            efficiency.append([p['id'],variant,len(w['recovery_execution_steps']),len(w['new_public_state_steps']),len(w['new_location_events']),w['accepted'],w['rejected'],w['wait'],len(w['repeated_original_rejection_steps']),full['main_gain']])
    save(REPORTS/'逐任务轨迹与恢复对比.md',f'''# 逐任务轨迹与恢复对比

{paired}

## 前20步的行为与信息变化

新公开状态为相对该检查点全部公开前缀首次出现的 signature，可能是库存改变/战斗，不能直接当作发现新知识或主线推进。恢复动作是理由与动作类型的公开规则代理；接受不代表策略正确。详细字段与完整后缀见 paired_comparison.json。

'''+table(['检查点','版本','相关接受动作','新公开状态','新区域','接受','拒绝','wait','原动作重复拒绝','全后缀主线增量'],efficiency))
    caseblocks=[]
    for r in review:
        caseblocks.append(f'''## {r['id']}

阶段归类：{r['category']}。{r['note']}

子目标：{r['subgoal_assessment']}。目标保持与续接：{r['maintenance_assessment']}。

首次执行动作分歧在 {r['first_action_divergence_step']}；A：`{r['first_a_action']}`，B：`{r['first_b_action']}`。不同模型采样，不能把该分歧直接称严格因果效应。

关键动作：A {r['baseline_evidence_steps']}；B {r['evidence_steps']}。完整原文（实际 observation、reasoning、feedback、控制器、请求 ID）保存在 `results/stage30/semantic_review.json`。B 恢复条件证据：{r['condition_step']}；成功重试后的较大原目标语义续接证据：{r['resume_by']}（有证据的“至迟”时刻，不声称最早，也不保证成功推进）。未恢复原操作时的替代父目标行动证据：{r['alternate_parent_progress_by']}。
''')
    save(REPORTS/'典型案例与阶段归因.md','# 典型案例与阶段归因\n\n同一套证据口径保留所有 10 对，包括有利、不利与无法隔离的情况。\n\n'+'\n'.join(caseblocks))
    save(REPORTS/'下一阶段机制判断.md',f'''# 是否开发 Hierarchical Goal Stack Controller

**{verdict}**。{conclusion}

主比较 20 步恢复为 {av['recovery20']}/10 → {bv['recovery20']}/10，长期主线改善 {s['main_better']}、退步 {s['main_worse']}。第一章为 {av['chapter1']}/10 → {bv['chapter1']}/10。全部正负检查点均纳入，不按效果删样本。

优先按轨迹证据区分：恢复条件是否真正满足、材料与照明是否保持、原操作和目标是否仍合理、完成后是否续接。不能用一个目标标题仍存在证明物理状态理解正确，也不能用标题改写证明目标已遗忘。

{limitations}

本轮到诊断结论为止，没有开发持续 Goal Stack、资源跟踪、执行监控或新 Agent，也没有自动启动下一阶段。
''')
    save(REPORTS/'README.md',f'''# Stage30

结论：{verdict}。新增 {cost['new_requests']} 次模型请求，usage 计价 ${cost['cost_usd']:.9f}。

- [实验报告](Stage30实验报告.md)
- [目标栈与检查点](OracleGoalStack构造与检查点.md)
- [逐任务轨迹与恢复对比](逐任务轨迹与恢复对比.md)
- [典型案例与阶段归因](典型案例与阶段归因.md)
- [下一阶段机制判断](下一阶段机制判断.md)
- [预登记协议](预登记实验协议.md)

复算：在已配置的本地环境设置 PYTHONHASHSEED=0 与 AGENTODYSSEY_ROOT，依次执行 `python -m scar_stage30.verify --archive-only`、`analyze`、`review`、`validate_analysis`、`report`、`audit`。后五项同为 scar_stage30 模块，均离线零模型调用。不要重新运行 batch 来复算；原生版本及全部输入哈希见 freeze.json。数据在 results/stage30，原检查点引用 results/stage28/checkpoints，环境依赖不上传。
''')
    print(json.dumps(dict(reports=6,verdict=verdict)))

if __name__=='__main__':main()
