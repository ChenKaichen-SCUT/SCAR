"""Public trajectory and telemetry analysis. Never imported by actors."""
import json,collections
from pathlib import Path
R=Path(__file__).resolve().parent
def rows(p):
    output=[]
    if p.exists():
        for x in p.read_text(encoding='utf-8').splitlines():
            try:output.append(json.loads(x))
            except json.JSONDecodeError:pass
    return output
state=json.loads((R/'mechanism_study_status.json').read_text())
report={'phase':state['phase'],'selection':state.get('selection'),'runs':[],'limits':'One trajectory per condition; developmental screening, no significance claim. Ablations use frozen v3; v4 changes multiple reliability mechanisms and is a separate validation.'}
for rid,status in state['runs'].items():
    log=rows(R/'runs'/rid/'agent_adam_davis/agent_log.jsonl');audit=rows(R/'control_audit'/(rid+'.jsonl'))
    ds=[x for x in audit if x.get('event')=='decision'];outcomes=[x['outcome'] for x in audit if x.get('event') in ['outcome','terminal_outcome'] and x.get('outcome')]
    rejects=[b for d in ds for r in d['dispatch']['rejected'] for b in r['blockers']]
    tests=[{'step':o['step'],**o['hypothesis_test']} for o in outcomes if o.get('hypothesis_test')]
    api={};errors=[]
    for suffix in ['', '__controller']:
        events=rows(R/'telemetry'/(rid+suffix)/'api_calls.jsonl');complete=[x for x in events if x['event']=='completed'];errors.extend([x for x in events if x['event']=='error'])
        api[suffix or 'actor']={'calls':len(complete),'prompt_tokens':sum((x.get('usage') or {}).get('prompt_tokens',0) for x in complete),'completion_tokens':sum((x.get('usage') or {}).get('completion_tokens',0) for x in complete)}
    gains=[{'step':r['step']+1,'gain':r['reward'].get('quest',0),'action':r['action']} for r in log if r['reward'].get('quest',0)]
    report['runs'].append({'id':rid,'game':status['game'],'variant':status['variant'],'status':status['status'],'completion_reason':status.get('completion_reason'),
        'steps':len(log),'main':sum(r['reward'].get('quest',0) for r in log),'main_at_300':sum(r['reward'].get('quest',0) for r in log[:300]),
        'supplementary':sum(sum(r['reward'].get(k,0) for k in ['side_quest','exploration','craft','unique_kill']) for r in log),
        'main_gain_actions':gains,'steps_since_last_main_gain':len(log)-(gains[-1]['step'] if gains else 0),
        'death_count':sum('I have died.' in r['next_observation']['text'] for r in log),'inspection_count':sum(r['action'].startswith('inspect ') for r in log),
        'dispatch_sources':dict(collections.Counter(d['dispatch']['source'] for d in ds)),
        'rejected_kinds':dict(collections.Counter(b['kind'] for b in rejects)),'zero_capacity_blocks':sum(b['kind']=='observed_hand_capacity' and b.get('detail',{}).get('count')==0 for b in rejects),
        'test_results':tests,'objective_effect_steps':[o['step'] for o in outcomes if o.get('objective_effect_observed')],
        'dependency_progress_steps':[o['step'] for o in outcomes if o.get('dependency_deficit_reduced')],
        'repairs':sum(x.get('event')=='repair' for x in audit),'api':api,'api_errors':errors})
(R/'mechanism_study_diagnostics.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'phase':report['phase'],'runs':[{k:r[k] for k in ['id','status','steps','main','main_at_300','completion_reason']} for r in report['runs']]}))
