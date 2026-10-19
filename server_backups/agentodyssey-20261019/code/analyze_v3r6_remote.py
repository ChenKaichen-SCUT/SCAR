"""Post-run analysis; never imported into the acting policy."""
import hashlib,html,json,re
from collections import Counter
from pathlib import Path
from analyze_v3r4_remote import metrics,rows
R=Path('/root/agentodyssey-benchmark-20261018');rid='remnant__v3r6_300_20261019';oldid='remnant__v3r4_300_20261019'
def main():
    p=json.loads((R/'feedback_v3r6_300_protocol.json').read_text());status=json.loads((R/'feedback_v3r6_300_status.json').read_text())
    assert status['all_processes_stopped']
    new=metrics(rid);old=metrics(oldid);api=rows(R/'telemetry'/rid/'api_calls.jsonl');done=[x for x in api if x.get('event')=='completed']
    audit=rows(R/'control_audit'/f'{rid}.jsonl');dec=[x for x in audit if x.get('event')=='decision'];trace=rows(R/'runs'/rid/'agent_adam_davis/agent_log.jsonl')
    sf=R/'runs'/rid/'agent_adam_davis/memory/feedback_v3r6_state.json';state=json.loads(sf.read_text()) if sf.exists() else {}
    authority=state.get('v3r6_authority_audit',[]);emergency=state.get('v3r5_emergency_audit',{})
    emergency_veto=[{'step':d['step'],'action':r['action'],'blockers':r['blockers']} for d in dec for r in d['dispatch'].get('rejected',[]) if r['action'].startswith(('attack ','eat ')) and any(b['kind']=='same_failed_action_context' and b['detail'].get('reason')==['no net contract progress on return to relevant state'] for b in r['blockers'])]
    overrides=[]
    for d in dec:
        if any(w['kind']=='task_no_progress_requires_reassessment' for w in d['check'].get('warnings',[])):
            i=d['step']-1;t=trace[i] if i<len(trace) else None
            overrides.append({'step':d['step'],'action':d['action'],'source':d['dispatch']['source'],'next_feedback':t['next_observation']['text'] if t else None,'reward':t['reward'] if t else None})
    frozen={n:hashlib.sha256((R/n).read_bytes()).hexdigest()==h for n,h in p['source_sha256'].items()};protected={n:hashlib.sha256((R/n).read_bytes()).hexdigest()==h for n,h in p['previous_artifacts_preserved_sha256'].items()}
    result={'new':new,'frozen_v3r4':old,'quest_difference':new['main_quest']-old['main_quest'],'status':status,
      'api':{'completed_calls':len(done),'input_tokens':sum(x['usage']['prompt_tokens'] for x in done),'uncached_input_tokens':sum(x['usage'].get('prompt_cache_miss_tokens',x['usage']['prompt_tokens']) for x in done),'output_tokens':sum(x['usage']['completion_tokens'] for x in done),'truncated_calls':sum(x.get('finish_reason')=='length' for x in done),'errors_or_stops':[x for x in api if x.get('event') not in ['started','completed']]},
      'authority':{'events':dict(Counter(x['event'] for x in authority)),'unique_demoted_step_actions':len({(x['step'],x['action']) for x in authority if x['event']=='heuristic_veto_demoted'}),'executed_advisory_overrides':overrides,'emergency_parent_progress_vetoes':emergency_veto},
      'emergency_outcomes':emergency.get('progress',[]),'protected_artifacts_unchanged':protected,'frozen_sources_match':frozen,
      'interpretation':'One stochastic rollout vs frozen prior result. Combined authority and emergency correction; no separate ablation or statistical claim.'}
    run=status['runs'][rid];result['valid_run']=new['steps']==300 and run.get('returncode')==0 and all(frozen.values()) and all(protected.values()) and len(new['runtime_policy_load'])==1
    (R/'feedback_v3r6_300_analysis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    pairs=[('步数','steps'),('主线分数 /24','main_quest'),('增分步骤','quest_gain_steps'),('末段无增分步数','steps_since_last_quest_gain'),('模型调用','calls_through_last_decision'),('本地动作','local_steps'),('死亡步骤','death_steps'),('环境拒绝步骤','denial_steps'),('出现净状态循环的观察数','net_cycle_observations')]
    table='<table><tr><th>指标</th><th>冻结 v3r4</th><th>本次 v3r6</th></tr>'+''.join('<tr><th>'+label+'</th><td>'+html.escape(str(old[k]))+'</td><td>'+html.escape(str(new[k]))+'</td></tr>' for label,k in pairs)+'</table>'
    doc='<!doctype html><meta charset="utf-8"><title>Remnant 控制权限修正验证</title><style>body{font:16px/1.7 system-ui;max-width:1100px;margin:40px auto;padding:0 24px;color:#182b3a}table{border-collapse:collapse;width:100%}td,th{border:1px solid #cbd4dc;padding:10px;text-align:left}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f0f3f6;padding:18px}</style><h1>Remnant：应急进展与控制权限修正</h1><p>原机制把父任务无进展升级为动作禁令。本次保留环境条件检查，把无进展改为给新决策的警告，并暂停自动续行；攻击和回血分别评价效果。</p><p>运行有效性：'+str(result['valid_run'])+'；主线分数差值：'+str(result['quest_difference'])+'。没有重跑基线。</p>'+table+'<p>各一次轨迹，模型输出有随机性；不能据此证明稳定优势或归因到单一机制。循环观察和逆向动作都只是诊断信号，不自动等于浪费。</p><h2>控制权限与 API 审计</h2><pre>'+html.escape(json.dumps({'authority_events':result['authority']['events'],'executed_overrides':len(overrides),'emergency_parent_progress_vetoes':len(emergency_veto),'api':result['api']},ensure_ascii=False,indent=2))+'</pre><p><a href="feedback_v3r6_300_analysis.json">完整机器可读分析</a></p>'
    (R/'feedback_v3r6_300_report.html').write_text(doc,encoding='utf8')
    print(json.dumps({'valid_run':result['valid_run'],'steps':new['steps'],'quest':new['main_quest'],'old_quest':old['main_quest'],'calls':len(done),'emergency_bad_vetoes':len(emergency_veto),'executed_overrides':len(overrides)}))
if __name__=='__main__':main()
