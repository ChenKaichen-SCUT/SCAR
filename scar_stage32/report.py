"""Only the repaired single-seed experiment is reported as new data."""
from scar_stage31.report import save,table
from .common import *

def main():
    offline();assert SEEDS==[42];m=read(RESULTS/'metrics.json');p=read(RESULTS/'paired_comparison.json')[0];c=read(RESULTS/'conclusion.json')
    cost=read(RESULTS/'cost_reconciliation.json');v=read(RESULTS/'verification.json');case=read(RESULTS/'case_review.json');anomalies=read(RESULTS/'response_anomalies.json')
    saer=next(x for x in m if x['method']=='SAER');baseline_=next(x for x in m if x['method']=='AGC-v2');a=saer['counts'];rc=saer['reflection_counts']
    folder=RESULTS/'runs'/ident(42);rr=rows(folder/'trajectory.jsonl.gz');dds=[dict(step=r['step'],decision=r['decision'],applied=True) for r in rr]
    if saer['terminal']:dds.append(dict(step=saer['terminal']['step'],decision=saer['terminal']['decision'],applied=False))
    syntax=[]
    for e in dds:
        for i,r in enumerate(e['decision']['saer_records'],1):
            if r.get('syntax_feedback_received') or r.get('returned_format_issues'):
                syntax.append(dict(step=e['step'],index=i,decision_reached_environment=e['applied'],received=r.get('syntax_feedback_received'),
                    returned_issues=r.get('returned_format_issues'),candidate=r['candidate'],final_proposal=r.get('final_proposal'),
                    native_assessment=e['decision']['attempts'][i-1],first_call=r['first_call'],last_call=r['last_call']))
    write(RESULTS/'syntax_repair_audit.json',syntax)
    verdict=c['verdict'];interpretation={
        'NATIVE_DECISION_EXHAUSTED':'本局仍出现原生决策耗尽，必须按保存的失败原因审计，不能认定语法/执行问题已完全消除。',
        'SINGLE_SEED_REGRESSION':'本局主线或章节终点低于已有同种子对照，不支持扩大运行。',
        'SINGLE_SEED_PROGRESS':'本局主线或章节终点高于已有同种子对照，但单次采样不能确认普遍收益。',
        'NO_MAIN_PROGRESS_GAIN':'本局没有显示主线或章节终点改善；局部错误变化与任务推进需分开判断。'}[verdict]
    comparison=table(['版本','记录来源','动作','结束状态','主线','第一章','拒绝','重复失败','wait','新区域','移出后变暗','请求'],[
        [x['method'],'本次修复后新运行' if x['method']=='SAER' else '原有Stage25，仅引用',x['counts']['actions'],x['status'],x['counts']['main_final'],x['counts']['chapter1'],
         x['counts']['public_rejected'],x['counts']['repeated_failure'],x['counts']['wait'],x['counts']['new_areas'],x['counts']['removal_visibility_lost'],x['requests']] for x in m])
    state=table(['版本','拒绝/100动作','重复缺条件','原生非法','资源保有影子风险','回取循环','所有变暗','新公开签名','恢复≤20/全部'],[
        [x['method'],f"{x['rates_per100']['public_rejected']:.2f}",x['counts']['repeated_missing_conditions'],x['counts']['native_invalid'],x['counts'].get('shadow_required_resource_custody_risk',0),
         x['counts']['reacquisition_cycles'],x['counts']['visibility_lost'],x['counts']['new_public_signatures'],f"{x['counts']['recoveries20']}/{x['counts']['recoveries']}"] for x in m])
    refl=table(['口径','预测','warning','warning后改变','拒绝→接受','接受→拒绝','避免变暗','引入变暗'],[
        [scope,*[rc.get(scope+'_'+key,0) for key in ['reflections','warnings','warning_changes','rejected_to_accepted','accepted_to_rejected','avoided_visibility_loss','introduced_visibility_loss']]] for scope in ['all','applied']])
    limits='只有一个环境种子、每方法一次模型采样；历史对照与新运行时间不同，模型随机数未配对。任务摘要、后果预测、额外调用和格式反馈共同存在，未隔离单个模块，也没有等token预算对照。不能据此宣布显著优于基线，或排除记忆、探索与长期规划解释。'
    save(REPORTS/'Stage32实验报告.md',f'''# Stage32 修复后单种子实验报告

结论：**{verdict}**。{interpretation}

## 范围与完成状态

按用户最新指示，停止原运行，修复不完整动作语法的反馈，只从原始初始状态重跑 remnant seed42 一次，上限300动作。旧Stage32离线样本、在线记录与报告已从当前版本移除，未混入以下统计；不再运行seed43/44，不新增离线模型调用。原有Stage25 seed42对照仅引用，其他基线不修改、不重跑。

{comparison}

第一章依据原生chapter≥1，全任务依据complete；SAER全任务完成为{a['full_complete']}。官方challenge_eval.py重新评分见official_scores.json。若未到300步，真实终止原因及所有失败提案保留，不拿少执行形成的低错误总数作为效率收益。

## 修复内容及语法效果

原重试只说“动作无效”，缺少实际提案和公开签名的差异。现在候选与最终决策都附简短接口契约；若原生检查要求重试，下一轮明确展示上一返回提案、参数数量、公开参数名、所需格式及引号问题。仍沿用原生最多三次动作修复和一次目标置信度复核，没有增加重试上限、自动补写对象或控制器代选动作。SAER风险仍是建议，不增加硬否决。

零API回归已验证候选错误、最终错误、缺参、多词参数引号、未知verb、状态/记忆保存、token计数及高风险保持执行；见smoke.json。这证明反馈链按设计工作，不保证随机模型此后永不产生格式错误。

本次格式诊断反馈轮次{rc.get('syntax_diagnostic_feedback_rounds',0)}，返回格式问题提案{rc.get('invalid_returned_proposals',0)}，候选无效跳过反思{rc.get('invalid_candidate_skips',0)}。原生动作修复{rc.get('native_action_retries',0)}次、目标置信度复核{rc.get('native_confidence_reviews',0)}次；格式异常与重复失败/目标复核分别保存。完整链见syntax_repair_audit.json，原始模型请求及三阶段角色未省略。

## 执行一致性、探索与效率

{state}

共同窗口为{p['common_actions']}动作，拒绝 A/B={p['AGC_v2']['public_rejected']}/{p['SAER']['public_rejected']}，重复失败 A/B={p['AGC_v2']['repeated_failure']}/{p['SAER']['repeated_failure']}。首次动作分歧在{p['first_action_divergence']}步；之后相同动作序号不表示相同状态。完整原始计数、每百动作比率、前置条件类别和逐步索引均保存。

重复失败为同地点同动作在解决前再次被拒；恢复只表示先前被拒动作后来被接受，不等于任务恢复。新公开签名不等于新规则，新区域不等于有效探索。资源保有影子风险沿用Stage31事后诊断，不进入SAER，也不等于关键资源损害真值。全部移出/转存/卸装/消费事件和公开库存改变见resource_events.jsonl.gz；地面可回收物不按销毁统计。明确条件丢失报告照明变化，未隔离的长程损害保持未知。

## 反思收益与风险

{refl}

all包括后续被原生复核弃用的反思；applied仅指产生该步实际动作的最后一次反思，避免多轮审查重复计环境收益。应用warning后的改变为{rc.get('applied_warning_changes',0)}/{rc.get('applied_warnings',0)}；其中实际新公开状态{rc.get('warning_changed_new_state',0)}、新区域{rc.get('warning_changed_new_area',0)}、主线增量{rc.get('warning_changed_quest_gain',0)}、wait{rc.get('warning_changed_wait',0)}。

候选与最终动作在同状态/RNG下原生分支对照；拒绝避免/引入只证明局部可行性差异，不证明长期奖励因果。没有风险硬否决不等于没有软性误导，合理候选被改成wait或失败动作、低风险预测仍失败、高风险候选保持执行都单列于动作反思审计。

## 本次费用与异常

只统计修复后的 **{cost['new_requests']}** 次请求，输入 **{cost['input_tokens']:,}**、输出 **{cost['output_tokens']:,}** token，usage计价 **${cost['cost_usd']:.9f}**。旧运行不计入本次费用；费用是按保存usage和冻结单价核算，供应商结算账单不可见。统一峰时参考${saer['peak_reference_cost_usd']:.9f}。模型参数不变，分析/验证新调用0。

修复后请求/100实际动作={100*saer['requests']/max(1,a['actions']):.2f}，对照={100*baseline_['requests']/baseline_['counts']['actions']:.2f}；该比率含终止决策调用，任务状态和调用预算不同。最大输入{saer['max_prompt_tokens']:,}token；原输入链没有额外截断。新运行响应/字段异常{sum(x['new'] for x in anomalies)}条，逐条见response_anomalies.json；原生动作语法问题另见syntax_repair_audit，不把输出length和上下文溢出混为一谈。

## 可重算性与边界

保存响应精确复放{v['exact_native_actions']}动作、{v['exact_model_contexts']}模型上下文，状态/RNG、反馈、奖励、AGC、任务摘要、记忆与实际token一致；另有{v['isolated_probe_actions']}个隔离候选/最终原生探针。冻结源码、费用账本和请求ID一致。基线沿用此前已核验数据，本次不复制旧SAER记录。

{limits}

当前仅完成单种子诊断，不自动扩展mark/metropolis，也不根据本局结果再次调参或重开任务。
''')
    examples=[]
    for category,items in case['online_examples'].items():
        for item in items:
            x=item['reflection'];left=x['candidate_native'];right=x['final_native'];prediction=x['prediction'] or {}
            examples.append([category,x['step'],x['index'],left['action'] if left else None,right['action'] if right else None,left['accepted'] if left else None,
                right['accepted'] if right else None,prediction.get('goal_risk'),x['final_applied'],prediction.get('reason')])
    terminal=saer['terminal']
    termination=('没有原生决策耗尽。' if not terminal else '第'+str(terminal['step'])+'次决策终止：'+json.dumps([dict(proposal=x['proposal'],reasons=x['reasons']) for x in terminal['decision']['attempts']],ensure_ascii=False))
    save(REPORTS/'动作反思与语法审计.md',f'''# 修复后动作反思与语法审计

{termination}

## 格式重试完整索引

{table(['步','原生轮次','已给诊断','返回格式问题','候选','最终','原生原因'],[[x['step'],x['index'],x['received'],x['returned_issues'],x['candidate'],x['final_proposal'],x['native_assessment']['reasons']] for x in syntax])}

上表全部包含，不按是否修复成功筛选。returned_issues为空表示格式检查通过，不保证环境前置条件满足；原生重复失败保护和目标置信度复核仍保留。控制器没有自动填写参数，只有模型最终提案进入环境。

## 同状态候选/最终对照

{refl}

{table(['类别','动作步','反思轮','候选','最终','候选接受','最终接受','风险','实际应用','预测理由'],examples)}

每类机械选择最早出现案例，全部符合索引见case_review.json：{json.dumps({k:len(v) for k,v in case['all_qualifying_indexes'].items()},ensure_ascii=False)}。完整原生分支与源状态哈希在online_native_probes.jsonl.gz。接受不等于任务推进，warning标签不等于客观损害真值；原候选改变后无进展亦不能单凭外观认定因果损害。
''')
    save(REPORTS/'三游戏扩展与研究判断.md',f'''# 修复后单种子研究判断

**{verdict}**。{interpretation}

主线相对已有对照变化{p['main_delta']}，第一章变化{p['chapter_delta']}，原生决策耗尽{p['extra_method_early_stop']}。语法修复解决的是重试反馈缺乏具体错误信息；不能据此假定数量、容量、资源可恢复性和长期规划已经解决。

{limits}

本轮不足以直接确认三游戏扩展价值；遵照用户只运行一个种子的要求，未运行其他种子或游戏。关于未来评估，等调用预算、摘要与预测分离、更多独立采样仍是尚缺证据，本轮没有实施。
''')
    save(REPORTS/'README.md',f'''# Stage32 修复后单种子

只记录修复后seed42一次运行。**{verdict}**，新请求{cost['new_requests']}，usage费用${cost['cost_usd']:.9f}。旧Stage32结果已从当前目录和当前Git版本移除，Git历史未改写。

- [实验报告](Stage32实验报告.md)
- [语法修复与单种子协议](语法修复与单种子协议.md)
- [动作反思和语法审计](动作反思与语法审计.md)
- [研究判断](三游戏扩展与研究判断.md)
- [Git变更记录](Git变更记录.md)

配置冻结依赖、PYTHONHASHSEED=0、AGENTODYSSEY_ROOT和PYTHONPATH后，依次运行scar_stage32.verify --archive-only、analyze、cases、report、validate_analysis模块可复算，均零API；不要运行batch复算。原始响应、轨迹、局部反事实、逐步证据、模型usage和冻结哈希均在results/stage32。下载依赖和凭据不上传。
''')
    print(json.dumps(dict(verdict=verdict,seed=42,syntax_audit_rows=len(syntax))),flush=True)

if __name__=='__main__':main()
