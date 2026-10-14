"""Chinese reports; conclusions derived from all paired outcomes."""
from collections import Counter
from .common import *

def save(path,text):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text('\n'.join(x.rstrip() for x in text.splitlines())+'\n')

def table(headers,records):
    clean=lambda x:str(x).replace('|','／').replace('\n',' ')
    return '\n'.join(['|'+'|'.join(headers)+'|','|'+'|'.join('---' for _ in headers)+'|']+['|'+'|'.join(clean(x) for x in r)+'|' for r in records])

def main():
    offline();m=read(RESULTS/'metrics.json');pairs=read(RESULTS/'paired_comparison.json');c=read(RESULTS/'conclusion.json');cost=read(RESULTS/'cost_reconciliation.json');v=read(RESULTS/'verification.json')
    off=read(RESULTS/'offline_summary.json');coverage=read(RESULTS/'offline_coverage_review.json');case=read(RESULTS/'case_review.json');ctrl=rows(RESULTS/'controller_audit.jsonl.gz');anomalies=read(RESULTS/'response_anomalies.json');terminal_review=read(RESULTS/'terminal_review.json')
    index={x['case']:x for x in m};count=lambda method,key:sum(x['counts'].get(key,0) for x in m if x['method']==method)
    stop=[x for x in m if x['method']=='REC' and x['terminal']];nstop=len(stop)
    verdict=c['verdict'];judgment={
        'PROGRESS_SUPPORT':'达到本轮描述性的推进收益标准，支持小规模跨游戏验证，但没有证明控制层普遍必要。',
        'ERROR_REDUCTION_ONLY':'只达到错误减少标准，未确认长期推进收益；尚不足以直接扩大到三游戏。',
        'NO_CLEAR_SUPPORT':'未支持当前 REC 进入三游戏正式测试。局部风险检测存在价值，但当前实现没有证明长程收益，并暴露过度约束风险。'}[verdict]
    comparison=table(['种子','版本','状态','实际动作','主线','第一章','公开拒绝','重复失败','wait','恢复≤20步/全程','请求','本轮新增请求'],[
        [x['seed'],x['method'],x['status'],x['counts']['actions'],x['counts']['main_final'],x['counts']['chapter1'],x['counts']['public_rejected'],x['counts']['repeated_failure'],x['counts']['wait'],
         f"{x['counts']['recoveries20']}/{x['counts']['recoveries']}",x['requests'],x['new_requests']] for x in m])
    common=table(['种子','共同窗口','拒绝 A/B','重复失败 A/B','回取循环 A/B','移出物品后变暗 A/B','首次动作分歧 A/B'],[
        [p['seed'],p['common_actions'],f"{p['AGC_v2']['public_rejected']}/{p['REC']['public_rejected']}",f"{p['AGC_v2']['repeated_failure']}/{p['REC']['repeated_failure']}",
         f"{p['AGC_v2']['reacquisition_cycles']}/{p['REC']['reacquisition_cycles']}",f"{p['AGC_v2']['removal_visibility_lost']}/{p['REC']['removal_visibility_lost']}",
         f"{p['first_action_divergence']}: {p['divergence_A']} / {p['divergence_B']}"] for p in pairs])
    efficiencies=table(['种子','版本','拒绝/100动作','重复缺条件','原生非法','资源保有风险动作','已验证即时制作条件损失','回取循环','可见→黑暗','REC重审'],[
        [x['seed'],x['method'],f"{x['rates_per100']['public_rejected']:.2f}",x['counts']['repeated_missing_conditions'],x['counts']['native_invalid'],x['counts'].get('shadow_required_resource_custody_risk',0),
         x['verified_immediate_craft_condition_losses'],x['counts']['reacquisition_cycles'],x['counts']['visibility_lost'],x['controller'].get('rec_reconsider_calls',0)] for x in m])
    costs=table(['种子','版本','输入token','输出token','峰值输入','usage费用$','本轮新增$','统一峰时参考$'],[
        [x['seed'],x['method'],x['input_tokens'],x['output_tokens'],x['max_prompt_tokens'],f"{x['cost_usd']:.9f}",f"{x['new_cost_usd']:.9f}",f"{x['peak_reference_cost_usd']:.9f}"] for x in m])
    efficiency_cost=table(['方法','请求/100实际动作','输入token/动作','统一峰时$/100实际动作','原生语法修复','原生置信度重审','REC额外重审'],[
        [method,f"{100*sum(x['requests'] for x in m if x['method']==method)/count(method,'actions'):.2f}",
         f"{sum(x['input_tokens'] for x in m if x['method']==method)/count(method,'actions'):.1f}",
         f"{100*sum(x['peak_reference_cost_usd'] for x in m if x['method']==method)/count(method,'actions'):.6f}",
         sum(x['controller']['native_action_retries_total'] for x in m if x['method']==method),
         sum(x['controller']['native_confidence_reviews_total'] for x in m if x['method']==method),
         sum(x['controller'].get('rec_reconsider_calls',0) for x in m if x['method']==method)] for method in ['AGC-v2','REC']])
    limitations='三个环境种子，每种方法每种子一次模型采样，模型随机数未配对；历史对照与新运行时间不同。seed42 及其衍生历史后缀已用于开发和诊断，不能声称是独立留出验证。REC 同时增加公开状态可见性和约束重审，本轮没有分离二者的效果。小样本差异不支持显著优劣或普遍必要性结论。'
    save(REPORTS/'Stage31实验报告.md',f'''# Stage31 REC 设计与验证实验报告

结论：**{verdict}**。{judgment}

本地完成三个 remnant 配对种子，REC 的 {nstop}/3 局因方法决策耗尽提前终止，所有早停与负面结果保留。A=Stage25 AGC-v2，B=Stage31 REC。不把提前停止造成的少动作、少错误或低总费用算作效率收益。

## 设计、复用与完成状态

先用 Stage29/30 的 20 条历史后缀离线验证，再以 `aa364b89352040b59fe0193be9324e63d41cb640` 冻结 REC、运行脚本和协议。原 AGC-v2、模型、官方环境和评分不变，只有 REC 的公开状态摘要及最多两次额外约束重审是实验处理。没有隐藏配方、手写物品路线或替代动作。

AGC-v2 seed42 复用完整 300 步；seed43/44 精确复用原 47 步并从第 48 步续跑。共复用 394 个环境动作和 423 个历史请求，没有重付历史样本。三个 REC 均从同种子的原始初始状态开始。全部上限 300 步；原生 done 或决策耗尽结束。早停没有重跑，其他游戏没有启动。

{comparison}

官方 `challenge_eval.py` 对六个记录重新评分，结果保存在 `official_scores.json`。主线与第一章口径和 Stage25 相同，第一章使用原生 `main_quest_progress.chapter >= 1`，全任务完成另见 metrics。AGC-v2 共 {count('AGC-v2','actions')} 动作、REC 共 {count('REC','actions')} 动作；第一章分别 {count('AGC-v2','chapter1')}/3、{count('REC','chapter1')}/3，全任务分别 {count('AGC-v2','full_complete')}/3、{count('REC','full_complete')}/3。

## 执行一致性与效率

{efficiencies}

“资源保有风险动作”是统一 Tracker 对实际执行动作的事后标记，不是已证实有害丢弃。即时制作条件损失只在原生探针的事前制作成功、事后失败时计数。本轮线上没有已执行的资源风险候选，适用制作前后探针为 0；表中的 0 表示没有证实案例，不是所有动作均证实无损失。回取循环指同地点移出后再取同名物，可能是合理容量管理，不能直接叫浪费。宽口径重复失败允许期间状态变化，与 REC 的严格不变状态判定不同；重复缺条件只纳入明确容量、材料、设施、工具、对象不可用、可见性类，排除未知原因与格式类。

共同动作窗口，A/B 按 AGC-v2/REC 排列：

{common}

共同窗口仍不是相同世界状态，因为模型早已分叉；只用于减轻早停截尾造成的暴露量差异。公开拒绝合计 {c['common_window_rejections_AGC_v2']} → {c['common_window_rejections_REC']}，下降的配对数为 {c['error_reduction_pairs']}/3。预登记要求没有额外早停才能将拒绝下降归为情况 B，本轮不得放宽。

一个关键归因限制是：三条 REC 都只在最终终止决策触发约束，每条三个被拦提案，没有成功重审后执行的动作。因此此前的拒绝减少不能归因于实际动作拦截；可能来自公开状态摘要、模型采样或二者交互，当前比较没有隔离。不能把影子离线 39 告警当作这些线上局的有效拦截数。

恢复指标只证明一次先前被拒动作后来被接受；恢复可能是捡回刚丢的材料，不等于主线恢复。详见逐动作 metrics 与 recovery 事件。未尝试探针的条件保持为未知，不按未发现损失补成完整状态一致。

## 费用、调用与异常

{costs}

{efficiency_cost}

这些是全部实际消耗的描述比率，包含终止提案；状态分布与任务长度不同，不能视作同工作量成本因果比较。REC 没有显示每实际动作 token/请求成本优势。

本轮新增 **{cost['new_requests']} 次模型请求**，输入 **{cost['input_tokens']:,}**、输出 **{cost['output_tokens']:,}** token，保存 usage 和原冻结单价核算 **${cost['cost_usd']:.9f}**；历史费用只展示，不重复计费。供应商账单不可见，因此这是 usage 计价，不是结算账单。统一峰时参考用于剥离时段折扣，早停总费用不能当成本优势。

全部保存请求中有 {len(anomalies)} 条响应/解析异常记录，其中 {sum(x['new'] for x in anomalies)} 条本轮新增；逐条来源、步号、请求 ID 和类型在 `response_anomalies.json`。动作语法不合规而 JSON 可解析的提案另保留于 decision/REC 审计。它们只走冻结的原生重审，不手工改响应或重采样原局。最大提示 {max(x['max_prompt_tokens'] for x in m):,} token；模型限制和参数见 freeze。输出 length 异常不能冒称上下文超限。

## 控制器收益与风险

离线 39 告警中，16 个照明效应和 2 个重复拒绝有直接局部证据；20 个资源移出告警尚未证明新的制作能力损失。在线同状态被拦提案探针、最终实际动作及早停分支完整保存。判断局部拒绝/照明损失避免时，不外推后续奖励。

seed42 的光源保护冲突、seed43 的原生置信度重审与 REC 交互、seed44 的“拾取成品却保护制作原料”冲突见《控制器逐提案与早停审计》。后者说明错误需求绑定可以重新制造控制器锁死。模型原提案合理不能单独证明控制器有害，所以本轮另用被拦动作→重试上一失败动作的原生两步分支核验可行性；不调用模型，不改变正式结果。

## 可重算性与判断边界

精确离线复放核验 {v['exact_native_actions']} 个在线轨迹动作、{v['exact_model_contexts']} 个模型上下文，状态、反馈、奖励、控制器、Tracker、最终记忆及终止提案一致。在线验证另有 {v['isolated_probe_actions']} 个隔离环境探针动作；终止链专项审计另外重建 {terminal_review['replayed_actions']} 个物理动作并执行 {terminal_review['isolated_probe_actions']} 个原生提案探针。离线开发验证另有 3,116 动作、3,439 上下文和 57 个探针。分析和验证新增模型调用均为 0。账本无未知计费和未结算预留。

{limitations}

{judgment} 当前结果既不能证明“只靠 LLM 自主规划就足够”，也不能证明“必须加这种执行一致性控制层”。明确支持的是：约束应以真实行动意图和可恢复性为依据，局部风险检测不能直接升级为不可解除的禁止；本轮不据此修改算法或启动下一阶段。
''')
    exrows=[[x['id'],x['variant'],x['step'],x['evidence']['action'],x['evidence']['assessment']['decision'],x['note']] for x in coverage['examples']]
    save(REPORTS/'失败模式覆盖分析.md',f'''# 失败模式覆盖分析

全部 20 条历史后缀均纳入，只有一个独立母轨迹。它们是开发与诊断数据，不是独立测试集。REC 检测到部分照明保持问题，却未覆盖完整执行一致性问题。

3,116 动作有 448 次公开拒绝，只有 3 次拒绝动作触发 REC：2 次重复失败及 1 次实际未造成照明损失的转存。这不是错误召回率：大多数拒绝并非四条约束所针对，也没有完整人工任务损害标签。27 次移出物品后变暗中检测到 16 次（59.3%），11 次未检测，常见原因包括此前尚无同地点关联记录；原始事件清单在 offline_coverage_review。

资源保有告警 20 次全部被环境接受，但接受不等于正确。原生制作在这 20 次移出前已不可行，不能证实移出新增了即时制作损失，亦不能断言没有较长期损害。

{table(['检查点','版本','动作号','动作','判定','证据解释'],exrows)}

重要漏项包括：手部与容器的容量混淆、非制作型恢复目标、错误的资源获取方向、未知工具来源、战斗时序和多层依赖。保存旧配方可改善可见信息，但“旧配方在 Tracker 中”不证明进入当前目标摘要，更不证明约束足以把它转为有效执行。

告警无完整任务损害真值，因此不报告伪精确的 precision/recall。初检的 43 告警及通用 unknown/可见目的地修正全部保留；在线后算法未修订。在线反例还表明，仅按产品名匹配配方，会把拾取成品误绑定为制作任务，属于本次实现的实质缺陷。
''')
    save(REPORTS/'离线误动作拦截统计.md',f'''# 离线误动作检测与局部反事实

此处是对既存轨迹的影子判定，没有实际改变历史动作，不能叫“已阻止 39 个错误”。

{table(['类型','告警动作数','可验证结果'],[
 ['公开必需资源移出',20,'20 次动作成功；20 次事前制作已经不可行，未隔离新增损失'],
 ['同公开状态重复失败',2,'两次实际均被环境拒绝'],
 ['已观察条件丢失风险',17,'16 次实际变暗且同状态 wait 保持可见；1 次转存失败、照明未丢失'],
 ['设施离开风险',0,'没有样本，不能宣称有效'],
 ['未检测到约束',3077,'不等于无影响、不等于正确']])}

全部 3,116 动作、3,439 个保存上下文原生重放一致。57 个额外零 API 探针由 20×2 个事前/事后 craft 及 17 个同状态 wait 组成。wait 只用于局部信息条件对照，不是建议动作；16 个可见分支没有通过死亡重生伪造可见性。资源移出可能仍在地面可回收，本轮不把它与材料销毁混为一谈。

每条告警的观察、理由、需求、引用、源文件行号和实际反馈见 offline_action_audit.jsonl.gz。完整探针、源状态哈希、反馈、奖励见 offline_native_probes.jsonl.gz；逐例判定在 offline_native_validation.json。初检证据见 pre_freeze_review。所有 39 条保留，未只展示命中案例。
''')
    oldrows=[[x['step'],x['evidence']['action'],x['shadow']['decision'],x['note']] for x in case['stage25_cases']]
    save(REPORTS/'与Stage25失败案例对应分析.md',f'''# 与 Stage25 失败案例对应分析

下表重审 Stage25 seed42 的实际失败动作，在其真实公开前缀上运行同一 REC 影子判定。该判定不会改变原基线结果，不能假设新模型必然在这些动作号到达相同状态。

{table(['Stage25动作号','原动作','影子判定','机制对应'],oldrows)}

Stage25 的 tool/facility/capacity/material 约束互相叠加，单纯保存目标或配方没有解决其可行执行。本轮 REC 针对资源、重复失败和经验照明的约束，仍不能生成缺失的获取路径，也不能代表完整状态模型。

{common}

每对首次动作分歧通常发生在进入上述失败阶段之前，因此不能按相同动作号声称“已修复 Stage25 第 N 步”。对照比较依据相同失败类型、实际前置条件、正式奖励与同状态探针。完整首/末失败证据、全部干预窗口、所有主线增量和终止记录在 case_review.json。

在线新增反例尤其重要：REC seed44 的显式目标是拾取地上 herb_tea，却被绑定为制作该成品，因而保护 meadow_herb。原模型多次说明可直接拾取、丢下原料可回收，仍被拒绝至早停。这不是旧 Stage25 数据证明的普遍现象，而是本轮新控制器实际引入的需求语义错误。seed42 则显示保护照明即使有公开依据，也不自动给出容量恢复办法。

这些现象属于状态/目标/执行语义的交互。不能依据一次轨迹分叉把差异归为严格控制器因果；局部原生反事实及其边界见审计报告。
''')
    blocks=[x for x in ctrl if x['record']['check']['decision']=='RECONSIDER'];kinds=Counter(k['kind'] for x in blocks for k in x['record']['check']['reasons'])
    stopblocks=[]
    for x in stop:
        n=x['terminal']['step'];records=[z for z in ctrl if z['case']==x['case'] and z['step']==n]
        lines=[]
        for z in records:
            p=z['native_probe'];retry=p.get('then_retry_last_rejected_action') if p else None
            if p is None:
                extra=next(t for t in terminal_review['cases'] if t['case']==x['case'])
                p=next(t for t in extra['records'] if t['index']==z['proposal_index']).get('native')
            lines.append([z['proposal_index'],(z['record']['proposal'] or {}).get('action'),z['record']['check']['decision'],
                '; '.join(r['kind'] for r in z['record']['check']['reasons']),p['accepted'] if p else '无探针',
                p['visible'] if p else '无探针',f"{retry['action']}: {retry['accepted']}" if retry else '无后续探针'])
        stopblocks.append(f"## {x['case']}\n\n正式执行 {x['counts']['actions']} 步，第 {n} 次决策终止；主线 {x['counts']['main_final']}。\n\n"+table(['提案号','原模型动作','REC','依据','原生接受','原生可见','随后重试上一失败动作'],lines))
    save(REPORTS/'控制器逐提案与早停审计.md',f'''# 控制器逐提案与早停审计

在线共有 {len(blocks)} 个 RECONSIDER 提案，分类为 {dict(kinds)}。逐提案原始 JSON、公开约束、实际动作与同状态探针均保留；passed_to_agc 表示交给原 AGC-v2 继续判断，不等于执行。

同状态探针有 {sum(x['local_rejection_avoided'] for x in ctrl)} 个提案的拒绝被随后实际接受动作避免，{sum(x['local_visibility_loss_avoided'] for x in ctrl)} 个提案的照明损失被随后实际动作避免。这是提案数，可能多个提案共用一个环境决策，不可加成独立收益次数；更不是主线奖励提升。被拦提案中原生可接受的有 {sum(x['candidate_accepted_by_native'] is True for x in ctrl)} 个，接受亦不自动证明有价值。

{(chr(10)*2).join(stopblocks)}

seed42 保护照明的规则有历史公开损失依据，但连续候选只在 drop/store 光源之间切换。原生分支证实这些动作确实导致黑暗，但接着 `pick up rust_scrap` 仍成功。也就是说，照明损失不是该次取物的硬性不可行条件；保护照明与短期收集存在取舍，不能把停止执行计为收益。没有继续调用模型，不能声称释放约束后一定完成任务。

seed43 第 294 次决策的首个提案为 `pick up cloth`，REC 允许，但原 AGC-v2 因目标置信度低要求重审。原生同状态探针证实该提案可执行。随后模型转为 `drop thread`，错误声称只持 1 thread 时手已满；三个提案均被 REC 拦截而终止。这是原生置信度工作流、模型重审漂移与新约束的交互，不能简化为 REC 直接覆盖了首个动作。原始提示及 `terminal_review.json` 保存完整判断链。

seed44 的根本问题是目标到需求的绑定：`Obtain healing by picking up herb_tea` 被当成制造 herb_tea，导致 `drop meadow_herb` 总被资源规则拦截。最后几条模型理由明确指出地上已有成品、无须制作、丢下原料可以回收。同状态原生分支证实 `drop meadow_herb` 后 `pick up herb_tea` 成功且保持可见，支持“该约束挡住了一条局部可行恢复路径”。仍不能声称随后一定治愈或推进主线。

三个终止决策中，REC 异常中断原 AGC-v2 `_act`，使原生 terminal counters 未进入最终 decision 字段；分析通过保存的首个 ALLOW 提案、实际提示和 AGC 判定复原 seed43 一次置信度重审、seed44 一次语法修复。记录值与重建值分别保存，避免漏算模型调用。完整请求和 usage 没有遗漏。

本轮未针对这些结果修改 `agents/rec_v1`、放宽约束、增加重审上限或重跑早停局。若后续研究继续，首先需要把“当前目标的一个可能实现手段”与“当前动作真正需要的条件”分开；这只是诊断建议，没有在本轮开发新机制。
''')
    save(REPORTS/'三游戏测试与研究判断.md',f'''# 是否进入 TTCL 三游戏测试

**{verdict}**。{judgment}

本轮主线改善 {c['progress_better_pairs']}/3，REC 额外决策早停 {nstop}/3；第一章 A/B 为 {count('AGC-v2','chapter1')}/3、{count('REC','chapter1')}/3。局部错误下降与真实推进必须分开，不能用早停后少执行的部分制造有利比率。

对最终问题的回答：**目前尚不能确认长程 Agent 必须加入执行一致性控制层，更不能确认当前 REC 是可行答案。** 公开资源和条件的持续维护有可验证的局部问题，也有局部检测收益；但本轮约束不完整、目标绑定不准确，可能把合法恢复路径变成不可解除的禁令。

普通工程问题包括产品名匹配把拾取误当制作、未知状态处理、公开数量和容器更新的保守性、重审耗尽后的可靠性。这些缺陷应与“目标—状态—动作约束如何保持一致”的研究假设分开。后者可能涉及多种实现手段、条件可恢复性、资源暂时移出与真正损失、风险提示如何避免死锁；当前实验没有隔离这些机制，也没有证明更复杂控制器一定有效。

{limitations}

因此当前不扩展 mark/metropolis，不把前序诊断写成排除了状态理解/记忆/规划，不启动下一阶段。若未来获新指引，应先明确干预的条件语义和评价真值，再决定最小验证；不能依据本轮负面结果直接追加一串补丁。
''')
    save(REPORTS/'README.md',f'''# Stage31

结论：**{verdict}**。三组 remnant 配对；本轮新增 {cost['new_requests']} 请求，usage 计价 ${cost['cost_usd']:.9f}。包含全部早停和反例。

- [实验报告](Stage31实验报告.md)
- [REC设计](REC设计文档.md)
- [失败模式覆盖](失败模式覆盖分析.md)
- [离线检测统计](离线误动作拦截统计.md)
- [Stage25案例对应](与Stage25失败案例对应分析.md)
- [控制器与早停审计](控制器逐提案与早停审计.md)
- [三游戏判断](三游戏测试与研究判断.md)
- [冻结前协议](预登记实验协议.md)

复算只使用归档响应：配置原冻结环境、PYTHONHASHSEED=0 和 AGENTODYSSEY_ROOT 后，运行 `python -m scar_stage31.verify --archive-only`、`python -m scar_stage31.terminal_review`、`python -m scar_stage31.analyze`、`python -m scar_stage31.offline_review`、`python -m scar_stage31.cases`、`python -m scar_stage31.report`、`python -m scar_stage31.validate_analysis`。全部零 API；不要运行 batch 来复算。精确包版本、原环境哈希在 freeze 和既有环境配置内，下载依赖不上传。

results/stage31 包含统计 CSV/JSON、完整新请求/轨迹、逐动作证据索引、REC 每个提案、原生探针、最终记忆及成本核验。AGC-v2 seed42 完整数据通过原 Stage25 路径引用，其余基线的原 47 步归档保留并与续跑合并；new_requests 单独保存新增调用。
''')
    print(json.dumps(dict(verdict=verdict,reports=9,rec_early_stops=nstop)),flush=True)

if __name__=='__main__':main()
