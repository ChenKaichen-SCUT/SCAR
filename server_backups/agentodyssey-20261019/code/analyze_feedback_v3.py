"""Evaluation-only artifact, never imported by agents."""
import argparse,collections,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parent);a=p.parse_args();R=a.root
def rows(p):return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()] if p.exists() else []
state=json.loads((R/'feedback_v3_status.json').read_text()) if (R/'feedback_v3_status.json').exists() else {}
report={'method':'feedback_v3','single_trajectory_per_game':True,'runs':[],'limits':'Developed using previous failures; these games are development evaluation, not independent held-out validation or significance evidence.'}
for g in ['remnant','mark','metropolis']:
    rid=g+'__feedback_v3';log=rows(R/'runs'/rid/'agent_adam_davis/agent_log.jsonl');au=rows(R/'control_audit'/f'{rid}.jsonl')
    ds=[x for x in au if x['event']=='decision'];os=[x['outcome'] for x in au if x['event'] in ['outcome','terminal_outcome'] and x.get('outcome')]
    gains=[r['step']+1 for r in log if r['reward'].get('quest',0)]
    tests=[{'step':o['step'],**o['hypothesis_test']} for o in os if o.get('hypothesis_test')]
    errors=[];api={}
    for suffix in ['', '__controller']:
        es=rows(R/'telemetry'/(rid+suffix)/'api_calls.jsonl');done=[e for e in es if e['event']=='completed'];errors += [e for e in es if e['event']=='error']
        api[suffix or 'actor']={'completed':len(done),'prompt_tokens':sum((e.get('usage') or {}).get('prompt_tokens',0) for e in done),'completion_tokens':sum((e.get('usage') or {}).get('completion_tokens',0) for e in done)}
    report['runs'].append({'game':g,'status':state.get('runs',{}).get(rid,{}).get('status'),'completion_reason':state.get('runs',{}).get(rid,{}).get('completion_reason'),
       'steps':len(log),'main':sum(r['reward'].get('quest',0) for r in log),'supplementary':sum(sum(r['reward'].get(k,0) for k in ['side_quest','exploration','craft','unique_kill']) for r in log),
       'main_gain_steps':gains,'last_main_gain':gains[-1] if gains else None,'controller_calls':sum(x['event']=='controller' for x in au),'repairs':sum(x['event']=='repair' for x in au),
       'decision_sources':dict(collections.Counter(x['dispatch']['source'] for x in ds)),
       'rejection_kinds':dict(collections.Counter(b['kind'] for x in ds for r in x['dispatch']['rejected'] for b in r['blockers'])),
       'observed_target_effect_steps':[o['step'] for o in os if o.get('objective_effect_observed')],
       'dependency_deficit_reduced_steps':[o['step'] for o in os if o.get('dependency_deficit_reduced')],
       'test_results':tests,'test_result_counts':dict(collections.Counter(t['outcome'] for t in tests)),
       'executed_known_blockers':[{'step':x['step'],'action':x['action'],'check':x['check']} for x in ds if x['check']['blockers']],
       'algorithm_stalled_events':[{'step':x['step'],'dispatch':x['dispatch']} for x in au if x['event']=='algorithm_stalled'],
       'inspection_count':sum(x['action'].startswith('inspect ') for x in log),'api':api,'api_errors':errors,
       'official_full_budget_completed':bool(log and (len(log)==500 or log[-1].get('episode_done')))})
(R/'feedback_v3_diagnostics.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=True))
