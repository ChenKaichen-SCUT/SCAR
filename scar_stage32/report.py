"""Complete Chinese reports from all preregistered runs and evidence."""
from collections import Counter
from scar_stage31.report import save,table
from .common import *

def main():
    offline();m=read(RESULTS/'metrics.json');p=read(RESULTS/'paired_comparison.json');c=read(RESULTS/'conclusion.json');cost=read(RESULTS/'cost_reconciliation.json')
    v=read(RESULTS/'verification.json');o=read(RESULTS/'offline_summary.json');case=read(RESULTS/'case_review.json');ref=rows(RESULTS/'reflection_audit.jsonl.gz')
    resources=rows(RESULTS/'resource_events.jsonl.gz');anomalies=read(RESULTS/'response_anomalies.json');verdict=c['verdict']
    count=lambda method,key:sum(x['counts'].get(key,0) for x in m if x['method']==method)
    rc=lambda method,key:sum(x['reflection_counts'].get(key,0) for x in m if x['method']==method)
    judgment={
        'PROGRESS_AND_RELIABILITY_SUPPORT':'达到本轮描述性的推进及可靠性标准，可考虑小规模跨游戏复核；尚不能认定反思单模块有效或排除记忆、规划解释。',
        'LOCAL_RELIABILITY_ONLY':'只支持局部执行可靠性改善，未达到稳定主线推进标准；目前不建议直接扩展三游戏。',
        'REGRESSION_OR_BLOCKING':'出现主线退步或额外方法早停，不支持当前版本直接扩展三游戏，必须保留并审计负面轨迹。',
        'NO_CLEAR_SUPPORT':'结果不足以支持稳定的推进及可靠性收益，目前不建议直接扩展三游戏。'}[verdict]
    limitations='三个环境种子、每方法每种子一次模型采样；历史对照与新实验运行时间不同，模型随机数未配对。Stage31 轨迹用于开发和离线诊断，本轮不能声称独立留出测试。公开任务历史、额外调用预算与后果预测一起变化，缺少等调用预算及分模块对照，不能将差异归为反思单模块的严格因果作用。'
    main_table=table(['种子','方法','结束状态','实际动作','主线','第一章','公开拒绝','重复失败','wait','恢复≤20/全部','请求'],[
        [x['seed'],x['method'],x['status'],x['counts']['actions'],x['counts']['main_final'],x['counts']['chapter1'],x['counts']['public_rejected'],x['counts']['repeated_failure'],x['counts']['wait'],
         f"{x['counts']['recoveries20']}/{x['counts']['recoveries']}",x['requests']] for x in m])
    common=table(['种子','共同动作窗口','拒绝 A/B','重复失败 A/B','首次动作分歧','主线差 B−A','章节差 B−A'],[
        [x['seed'],x['common_actions'],f"{x['AGC_v2']['public_rejected']}/{x['SAER']['public_rejected']}",f"{x['AGC_v2']['repeated_failure']}/{x['SAER']['repeated_failure']}",x['first_action_divergence'],x['main_delta'],x['chapter_delta']] for x in p])
    state=table(['种子','方法','拒绝/100动作','重复缺条件','原生非法','资源移出影子风险','移出后变暗','所有变暗','回取循环','新公开签名','新区域'],[
        [x['seed'],x['method'],f"{x['rates_per100']['public_rejected']:.2f}",x['counts']['repeated_missing_conditions'],x['counts']['native_invalid'],x['counts'].get('shadow_required_resource_custody_risk',0),
         x['counts']['removal_visibility_lost'],x['counts']['visibility_lost'],x['counts']['reacquisition_cycles'],x['counts']['new_public_signatures'],x['counts']['new_areas']] for x in m])
    reflection_table=table(['种子','预测 全部/应用','warning 全部/应用','应用warning后改变','应用拒绝→接受','应用接受→拒绝','应用避免/引入变暗','应用warning改变后 新状态/区域/主线/wait'],[
        [x['seed'],f"{x['reflection_counts'].get('all_reflections',0)}/{x['reflection_counts'].get('applied_reflections',0)}",f"{x['reflection_counts'].get('all_warnings',0)}/{x['reflection_counts'].get('applied_warnings',0)}",
         f"{x['reflection_counts'].get('applied_warning_changes',0)}/{x['reflection_counts'].get('applied_warnings',0)}",x['reflection_counts'].get('applied_rejected_to_accepted',0),x['reflection_counts'].get('applied_accepted_to_rejected',0),
         f"{x['reflection_counts'].get('applied_avoided_visibility_loss',0)}/{x['reflection_counts'].get('applied_introduced_visibility_loss',0)}",
         '/'.join(str(x['reflection_counts'].get(k,0)) for k in ['warning_changed_new_state','warning_changed_new_area','warning_changed_quest_gain','warning_changed_wait'])] for x in m if x['method']=='SAER'])
    costs=table(['种子','方法','输入token','输出token','峰值输入token','usage费用$','统一峰时参考$','原生语法修复/置信度复核'],[
        [x['seed'],x['method'],x['input_tokens'],x['output_tokens'],x['max_prompt_tokens'],f"{x['cost_usd']:.9f}",f"{x['peak_reference_cost_usd']:.9f}",
         f"{x['reflection_counts'].get('native_action_retries',0)}/{x['reflection_counts'].get('native_confidence_reviews',0)}"] for x in m])
    efficiency=table(['方法','请求/100动作','输入token/动作','统一峰时$/100动作'],[
        [method,f"{100*sum(x['requests'] for x in m if x['method']==method)/count(method,'actions'):.2f}",
         f"{sum(x['input_tokens'] for x in m if x['method']==method)/count(method,'actions'):.1f}",
         f"{100*sum(x['peak_reference_cost_usd'] for x in m if x['method']==method)/count(method,'actions'):.6f}"] for method in ['AGC-v2','SAER']])
    save(REPORTS/'Stage32实验报告.md',f'''# Stage32 SAER 实验报告

结论：**{verdict}**。{judgment}

## 设计与完整结果

按指引32，实现公开任务状态摘要、一次候选后果预测与一次软校准最终选择。算法及执行协议冻结提交 `eb2b7b6c385d01b20404350d57057fb4e4050875`。SAER 不引用 REC 规则、隐藏状态或任务路线；风险提示不禁止动作，不生成替代动作。原 AGC-v2 语法修复和目标置信度复核继续生效，逐调用日志将它们与 SAER 三阶段分开。

先完成 Stage31 全部77个预登记固定候选离线诊断，再启动 remnant seeds42/43/44，各最多300动作。三个 AGC-v2 完整对照复用900动作、970历史请求，不重跑。没有启动 mark/metropolis，失败局没有重新采样。A=AGC-v2，B=SAER。

{main_table}

官方 challenge_eval.py 重新评分并归档于 official_scores.json；第一章用原生 chapter≥1，全任务用原生 complete。第一章 A/B 为 {count('AGC-v2','chapter1')}/3、{count('SAER','chapter1')}/3，全任务分别 {count('AGC-v2','full_complete')}/3、{count('SAER','full_complete')}/3。全部失败、方法早停和负面结果纳入，不以动作少冒充效率优势。

## 执行可靠性、探索与资源状态

{state}

同地点同动作再次被拒计重复失败，允许期间状态变化；明确重复缺条件只含容量、材料、设施、工具、对象不可用、可见性，不把格式/未知原因归为缺条件。恢复指此前被拒动作后来得到接受，不等于任务恢复。新公开签名是抽取后的状态变化计数，不等于获取新规则；新区域不等于有效探索。

资源保有影子风险只沿用 Stage31 事后标记，未进入 SAER，也不是关键资源损害真值。资源移出、转存、卸装、消费等全部事件共有 {len(resources)} 条，原始库存/地面改变和反馈在 resource_events.jsonl.gz。丢在原地可回收的物品不能按不可逆损失统计，目标名匹配配方也不能证明“关键资源”；因此没有伪造错误丢弃准确率。明确条件破坏报告可见→黑暗，其他尚未隔离的长程条件损害保持未知。

{common}

共同窗口拒绝合计 {c['common_rejections_baseline']}→{c['common_rejections_saer']}；至少两对改善且合计降10%的预登记错误标准为 {c['threshold_error_reduction']}。共同动作号并非相同物理状态，首次分歧后不能视为严格配对反事实。

## 软反思的局部收益及代价

{reflection_table}

“全部”含原生修复/目标复核中随后被弃用的反思，“应用”只含产生该步实际动作的最后一次反思；不能将多轮审查重复计为多个环境收益。应用warning后的改变为 {rc('SAER','applied_warning_changes')}/{rc('SAER','applied_warnings')}。同状态候选与最终动作原生探针支持 {rc('SAER','applied_rejected_to_accepted')} 次拒绝→接受及 {rc('SAER','applied_accepted_to_rejected')} 次接受→拒绝；只是一步可行性，不是主线因果效应。

风险没有硬否决，仍可能通过模型最终选择产生软性过度谨慎。合理候选被改成 wait、拒绝动作或无进展动作均在《软反思与合法路径审计》中保留。高风险候选原样执行是机制允许的选择，不能自动算失败；low风险候选仍可能被环境拒绝。没有完整未来损害真值，不能把模型风险标签视作客观安全标签。

## 计算预算及异常

{costs}

{efficiency}

本轮新增 **{cost['new_requests']} 请求**，其中离线 {o['new_requests']}，在线 {cost['new_requests']-o['new_requests']}；输入 {cost['input_tokens']:,}、输出 {cost['output_tokens']:,} token，usage计价 **${cost['cost_usd']:.9f}**。历史成本只展示、不重复计账；供应商账单不可见。统一峰时参考剥离时段折扣，未提供等token预算比较。分析/重放新模型调用均0，未知计费0。

在线加历史对照的响应/字段异常 {len(anomalies)} 条，其中本轮新在线 {sum(x['new'] for x in anomalies)} 条；详见 response_anomalies.json。反思与动作响应按不同schema核验，预测不可解析时不重试、不阻断最终选择；原生格式错误走原工作流。SAER预测不可用 {rc('SAER','prediction_format_unavailable')} 次，候选格式跳过反思 {rc('SAER','invalid_candidate_skips')} 次。最大在线/对照输入 {max(x['max_prompt_tokens'] for x in m):,} token，保留原提示未截断；输出length问题与上下文溢出分开。

## 核验与判断边界

新增线上 {v['exact_native_actions']} 个动作、{v['exact_model_contexts']} 个模型上下文保存响应精确重放，动作、物理/RNG哈希、反馈、奖励、AGC、任务摘要和最终记忆一致；另有 {v['isolated_probe_actions']} 个隔离候选/最终原生探针。历史基线900动作/970上下文已由 Stage31 精确核验，本轮验证冻结哈希未变。离线154上下文及全部探针另行复放。账本、usage及请求ID逐项核对。

{limitations}

{judgment} 当前结果不够证明“不是记忆或规划，而只是缺少显式未来评估”。即使局部可靠性改善，也必须与真实主线推进和新增计算成本分别评价。本轮不据结果改算法，不直接实现后续阶段。
''')
    correspondence=[]
    for x in case['stage31_correspondence']:
        y=x['summary'];r=x['prediction'] or {};final=x['final'] or {}
        correspondence.append([x['id'],y['candidate'],y['final_action'],r.get('goal_risk'),y['final_accepted'],y['final_visible'],y['final_followup_accepted'],r.get('reason'),final.get('reasoning')])
    save(REPORTS/'与Stage31失败案例对应分析.md',f'''# 与 Stage31 失败案例对应分析

下面完整列出两个已执行条件损失和五个合法终止候选，没有挑选有利结果。其余70次拒绝的逐样本结果见离线验证报告。原状态、目标、全部预测和最终理由、原生分支在 case_review.json 及 offline/ID/result.json。

{table(['样本','旧候选','SAER最终选择','预测风险','原生接受','最终可见','随后原取物成功','预测理由','最终理由'],correspondence)}

Stage31 seed42 第114次决策在 drop/store torch 间重审至停；这些原生动作确实导致黑暗，但再取 rust_scrap 仍可成功。保持照明与短期容量恢复需要取舍，不能将丢失照明等同所有取物都不可行。

seed43 第294次决策首个 pick up cloth 被 REC 放行、原生可行，却由原 AGC 置信度复核触发后续重审，再转为 drop thread 被 REC 禁止。这里要区分原生工作流与 REC 的交互，本轮离线固定候选接受并不保证完整 AGC 会直接执行。

seed44 第149次决策的明确目标是拾取地上的 herb_tea，REC 却按制作成品保护 meadow_herb，阻断 drop 后拾取成品的原生可行路径。SAER 不再程序化绑定该配方；但模型预测仍可能自行误读或过度谨慎，因此须观察本轮真实最终选择，不能仅凭删除规则就宣称修复。

对应分析是同状态局部诊断，在线新轨迹没有强行回到旧检查点。不同随机轨迹的相同步数不等于同一失败阶段；在线首次动作分歧见 paired_comparison.json。没有用离线效果调整算法或挑选在线种子，也没有继续这些分支的长程模型采样。
''')
    examples=[]
    for name,items in case['online_examples'].items():
        for e in items:
            x=e['reflection'];a=x['candidate_native'];b=x['final_native'];pred=x['prediction'] or {}
            examples.append([name,f"s{x['seed']}:{x['step']}:{x['index']}",a['action'] if a else None,b['action'] if b else None,a['accepted'] if a else None,b['accepted'] if b else None,
                pred.get('goal_risk'),x['final_applied'],x['actual_quest_gain'],pred.get('reason')])
    save(REPORTS/'软反思与合法路径审计.md',f'''# 软反思与合法路径审计

SAER 风险硬否决数为0。不能据此推断完全不损害合法路径：风险提示可能改变模型选择，原 AGC 也可能要求重审。所有反思保存于 reflection_audit.jsonl.gz，含被后续原生复核弃用的提案；same-state native反馈见 online_native_probes.jsonl.gz。

{reflection_table}

下表按每种事件、每个种子首次出现机械选例；所有符合条件的索引都在 case_review.json 的 all_qualifying_indexes，没有只保留好例。

{table(['类别','种子:步:反思','候选','最终','候选接受','最终接受','风险','最终已应用','该步主线增量','预测理由'],examples)}

全部符合索引数：{json.dumps({k:len(v) for k,v in case['all_qualifying_indexes'].items()},ensure_ascii=False)}。

“拒绝避免”和“拒绝引入”只在相同状态、相同RNG分支比较原生结果，且单独报告是否最终实际执行。接受候选改成wait只证明选择变了，必须结合等待是否获得新状态/区域/任务奖励判断，不能仅凭动作名断言有害。照明损失也可能是可恢复且必要的容量取舍。长程任务得失没有由这些单步反事实隔离。

若发生原生决策耗尽，terminal及每个模型提案均归档，不因SAER没有硬否决而隐去继承工作流的早停。若预测格式失效，最终选择仍进行；保存原始输出，未付费重试预测。
''')
    save(REPORTS/'三游戏扩展与研究判断.md',f'''# 是否扩展到 TTCL 三游戏

**{verdict}**。{judgment}

主线或章节改善 {c['main_better_pairs']}/3，共同窗口拒绝改善 {c['error_reduction_pairs']}/3；额外方法早停 {c['extra_method_early_stop']}。预登记标准、全部样本和费用保持不变，没有按结果降低门槛。

对科学假设的回答：当前只检验了“有限公开任务摘要＋额外候选/预测/最终调用”的组合机制。必须同时看已验证局部可行性变化和实际主线收益；不能把环境接受率直接替代长期执行能力，也不能从未完成任务反推出某个模块必然无效。

{limitations}

后续若获新的实验授权，等调用预算、摘要单独作用和预测校准的分离值得先澄清；这只是研究判断，本轮没有增加任何新算法、追加种子或其他游戏。原生AGC置信度复核、模型schema遵循等属于工程/工作流问题，未知条件下资源取舍、可恢复性评估与长程探索可能是独立机制问题；当前数据未隔离它们。
''')
    save(REPORTS/'README.md',f'''# Stage32 SAER

结论 **{verdict}**。77个固定候选离线诊断，remnant三个种子在线对比；新增 {cost['new_requests']} 模型请求，usage费用 ${cost['cost_usd']:.9f}。全部正反例、失败和异常保留。

- [实验报告](Stage32实验报告.md)
- [机制与冻结协议](机制设计与预登记协议.md)
- [离线验证](离线验证报告.md)
- [Stage31案例对应](与Stage31失败案例对应分析.md)
- [软反思和合法路径](软反思与合法路径审计.md)
- [三游戏扩展判断](三游戏扩展与研究判断.md)
- [Git与变更记录](Git变更记录.md)

代码在 agents/saer 与 scar_stage32。复算配置冻结依赖环境、PYTHONHASHSEED=0、AGENTODYSSEY_ROOT及PYTHONPATH后，依次运行 `python -m scar_stage32.offline_analyze`、`python -m scar_stage32.verify --archive-only`、`python -m scar_stage32.analyze`、`python -m scar_stage32.cases`、`python -m scar_stage32.offline_report`、`python -m scar_stage32.report`、`python -m scar_stage32.validate_analysis`。全部使用保存响应，零API。不要用 batch 复算。

results/stage32 保存原始请求、完整轨迹、公开状态摘要、候选/预测/最终决策、原生反事实、逐动作索引、可重算CSV/JSON、模型usage费用和冻结哈希。完整历史基线按原路径引用；下载依赖、私钥和私有运行目录不上传。
''')
    print(json.dumps(dict(verdict=verdict,reports=6)),flush=True)

if __name__=='__main__':main()
