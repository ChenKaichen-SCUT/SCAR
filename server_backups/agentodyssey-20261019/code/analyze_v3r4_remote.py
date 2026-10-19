"""Post-run analysis only. Never imported by the agent or sent to a model."""
import hashlib,html,json,re
from collections import Counter
from pathlib import Path
R=Path('/root/agentodyssey-benchmark-20261018');NEW='remnant__v3r4_300_20261019';OLD='remnant__v3r2_verified_20261019'
def rows(p):
    out=[]
    if p.exists():
        for line in p.read_text().splitlines():
            try:out.append(json.loads(line))
            except json.JSONDecodeError:pass
    return out
def metrics(rid,limit=300):
    log=rows(R/'runs'/rid/'agent_adam_davis/agent_log.jsonl')[:limit]
    audit=rows(R/'control_audit'/(rid+'.jsonl'));decisions=[x for x in audit if x.get('event')=='decision' and x['step']<=len(log)]
    quests=[i+1 for i,r in enumerate(log) if r['reward'].get('quest',0)>0]
    invalid=[];deaths=[];reversals=[]
    def op(a):return ' '.join(a.split()[:2]) if a.startswith(('pick up ','take out ','talk to ')) else a.split()[0]
    for i,r in enumerate(log):
        t=r['next_observation']['text']
        if re.search(r'^(?:Cannot|Can\x27t|Failed|Invalid|Not enough)\b',t,re.M|re.I):invalid.append(i+1)
        if 'I have died.' in t:deaths.append(i+1)
        if i:
            a=log[i-1]['action'].split();b=r['action'].split()
            inverse=(len(a)==2 and a[0]=='drop' and b==['pick','up',a[1]]) or (len(a)==3 and a[:2]==['pick','up'] and b==['drop',a[2]]) or (len(a)==4 and a[0]=='store' and b==['take','out',a[2],a[3]]) or (len(a)==4 and a[:2]==['take','out'] and b==['store','1',a[2],a[3]])
            if inverse:reversals.append({'step':i+1,'actions':[log[i-1]['action'],r['action']]})
    return {'steps':len(log),'main_quest':sum(x['reward'].get('quest',0) for x in log),'main_quest_max':24,'last_quest_gain_step':quests[-1] if quests else 0,
      'steps_since_last_quest_gain':len(log)-(quests[-1] if quests else 0),'quest_gain_steps':quests,'death_steps':deaths,'denial_steps':invalid,
      'calls_through_last_decision':decisions[-1].get('model_calls',0) if decisions else 0,'local_steps':decisions[-1].get('local_steps',0) if decisions else 0,
      'action_verbs':dict(Counter(op(r['action']) for r in log)),'dispatch_sources':dict(Counter(x['dispatch']['source'] for x in decisions)),
      'rejected_reasons':dict(Counter(b['kind'] for x in decisions for r in x['dispatch'].get('rejected',[]) for b in r.get('blockers',[]))),
      'net_cycle_observations':sum(bool(x['packet'].get('net_cycle')) for x in decisions),'adjacent_inverse_pairs':reversals,
      'new_mechanism_state':decisions[-1]['packet'].get('v3r4_mechanisms') if decisions else None,'runtime_policy_load':[x for x in audit if x.get('event')=='policy_loaded']}
def main():
    p=json.loads((R/'feedback_v3r4_300_protocol.json').read_text());status=json.loads((R/'feedback_v3r4_300_status.json').read_text())
    assert status['all_processes_stopped'] and status['runs'][NEW]['status']=='finished'
    new=metrics(NEW);old=metrics(OLD);previous=metrics("remnant__v3r3_300_20261019")
    telemetry=rows(R/'telemetry'/NEW/'api_calls.jsonl');completed=[x for x in telemetry if x.get('event')=='completed']
    files=list((R/'runs'/NEW).rglob('feedback_v3r4_state.json'));state=json.loads(files[0].read_text()) if files else {}
    protected={n:hashlib.sha256((R/n).read_bytes()).hexdigest()==h for n,h in p['previous_artifacts_preserved_sha256'].items()}
    frozen={n:hashlib.sha256((R/n).read_bytes()).hexdigest()==h for n,h in p['source_sha256'].items()}
    result={'comparison':'One new v3r4 run vs the first 300 steps of the frozen, correctly launched v3r2 run. No baseline rerun. Same seed; stochastic model responses. Not an ablation or significance test.',
      'new':new,'old_first_300':old,'previous_v3r3':previous,'quest_difference':new['main_quest']-old['main_quest'],'status':status,
      'api':{'completed_calls':len(completed),'errors_or_stops':[x for x in telemetry if x.get('event') not in ['started','completed']],
        'truncated_calls':sum(x.get('finish_reason')=='length' for x in completed),'input_tokens':sum(x['usage']['prompt_tokens'] for x in completed),'output_tokens':sum(x['usage']['completion_tokens'] for x in completed)},
      'mechanism_audit':state.get('v3r4_audit',{}),'protected_artifacts_unchanged':protected,'frozen_sources_match':frozen}
    result['valid_run']=new['steps']==300 and status['runs'][NEW]['returncode']==0 and all(protected.values()) and all(frozen.values()) and len(new['runtime_policy_load'])==1
    (R/'feedback_v3r4_300_analysis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    labels=[('已执行步数','steps'),('主线得分（满分24）','main_quest'),('最后一次主线增分步','last_quest_gain_step'),('末段无主线增分步数','steps_since_last_quest_gain'),('模型调用数','calls_through_last_decision'),('本地执行步数','local_steps'),('出现净状态循环的观察数','net_cycle_observations')]
    trs=''.join('<tr><th>'+name+'</th><td>'+str(old[k])+'</td><td>'+str(new[k])+'</td></tr>' for name,k in labels)
    for name,k in [('死亡次数','death_steps'),('反馈拒绝次数','denial_steps'),('相邻逆向动作对','adjacent_inverse_pairs')]:trs+=f'<tr><th>{name}</th><td>{len(old[k])}</td><td>{len(new[k])}</td></tr>'
    body=f'''<!doctype html><meta charset="utf-8"><title>Remnant v3r4 · 300步验证</title><style>body{{font:16px/1.65 system-ui;max-width:1100px;margin:48px auto;padding:0 24px;color:#172238}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #ccd5e2;padding:10px;text-align:left}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#f4f6fa;padding:18px}}small{{color:#526071}}</style><h1>Remnant v3r4 · 300步验证</h1><p>状态与控制修正：保留主线指令、续执行目标动作、保持首选计划、统一动作检查。脚本路径测试独立于自主性能测试。</p><p>本轮有效性检查：{result['valid_run']}。主线差值：{result['quest_difference']:+g}。全部旧实验文件和配额账本保持不变。</p><table><tr><th>指标</th><th>旧 v3r2 前300步</th><th>新 v3r4 300步</th></tr>{trs}</table><p>仅各一条轨迹；不能归因到单独机制，也不能证明稳定提升。动作完成、局部条件解除与主线得分分开统计。相邻逆向动作是诊断指标，并非每次都无效。</p><h2>机制触发与最终状态</h2><pre>{html.escape(json.dumps(new['new_mechanism_state'],ensure_ascii=False,indent=2))}</pre><h2>执行来源与拒绝原因</h2><pre>{html.escape(json.dumps({'sources':new['dispatch_sources'],'rejections':new['rejected_reasons'],'api':result['api']},ensure_ascii=False,indent=2))}</pre><small>原始轨迹、逐步控制审计、API账本、协议和版本哈希均保留在实验目录。运行后统计不提供给智能体。</small>'''
    (R/'feedback_v3r4_300_report.html').write_text(body,encoding='utf8')
    print(json.dumps({'valid_run':result['valid_run'],'steps':new['steps'],'quest':new['main_quest'],'old_first_300_quest':old['main_quest'],'delta':result['quest_difference'],'calls':len(completed)}))
if __name__=='__main__':main()
