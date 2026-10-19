"""Post-run audit. Evaluation-only code may read rewards; agents cannot import it."""
import argparse,collections,html,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parent);a=p.parse_args();R=a.root
def rows(p):return [json.loads(s) for s in p.read_text(encoding='utf-8').splitlines() if s.strip()] if p.exists() else []
report={'method':'feedback_v2','one_run_per_game':True,'scope':'Observational single-trajectory evidence; no statistical significance or causal effect size. No baseline reruns.', 'runs':[]}
for game in ['remnant','mark','metropolis']:
    rid=game+'__feedback_v2';path=R/'runs'/rid/'agent_adam_davis/agent_log.jsonl';log=rows(path)
    audit=rows(R/'control_audit'/f'{rid}.jsonl');ds=[x for x in audit if x['event']=='decision'];reviews=[x for x in audit if x['event']=='controller'];repairs=[x for x in audit if x['event']=='repair']
    outcomes=[x['outcome'] for x in audit if x['event'] in ['outcome','terminal_outcome'] and x.get('outcome')]
    checks=collections.Counter();executed_bad=[];unknown_failures=[];trials=[]
    for d in ds:
        for c in d['check']['blockers']+d['check']['warnings']:checks[c['kind']]+=1
        if d['check']['blockers']:executed_bad.append({'step':d['step'],'action':d['action'],'blockers':d['check']['blockers']})
    for o in outcomes:
        if o.get('failure_attribution'):unknown_failures.append(o['step'])
        if o.get('hypothesis_test'):trials.append({'step':o['step'],**o['hypothesis_test']})
    cycle_events=[{'step':x['step'],**x['net_cycle']} for x in audit if x['event'] in ['outcome','terminal_outcome'] and x.get('net_cycle')]
    gain=[x['step']+1 for x in log if x['reward'].get('quest',0)]
    api={}
    for suffix in ['', '__controller']:
        ev=rows(R/'telemetry'/(rid+suffix)/'api_calls.jsonl')
        api['actor' if not suffix else 'controller']={'completed':sum(x['event']=='completed' for x in ev),'errors':sum(x['event']=='error' for x in ev),
            'prompt_tokens':sum((x.get('usage') or {}).get('prompt_tokens',0) for x in ev if x['event']=='completed'),
            'completion_tokens':sum((x.get('usage') or {}).get('completion_tokens',0) for x in ev if x['event']=='completed')}
    entry={'game':game,'steps':len(log),'main_quest':sum(x['reward'].get('quest',0) for x in log),
        'supplementary':sum(sum(x['reward'].get(k,0) for k in ['side_quest','exploration','craft','unique_kill']) for x in log),
        'main_gain_steps':gain,'last_main_gain_step':gain[-1] if gain else None,
        'controller_calls':len(reviews),'last_controller_step':reviews[-1]['step'] if reviews else None,
        'repairs':len(repairs),'constraint_fallbacks':[x for x in audit if x['event']=='constraint_fallback'],
        'repair_success_count':sum(not x['remaining_blockers'] for x in repairs),
        'executed_check_counts':dict(checks),'executed_blocker_cases':executed_bad,
        'indeterminate_failure_steps':unknown_failures,'hypothesis_trials':trials,
        'rejected_model_claims':[x['accepted'] for x in reviews if x['accepted']['rejected_claims']],
        'net_cycle_events':cycle_events,'api':api,
        'pending_tasks_final':ds[-1]['packet']['pending_tasks'] if ds else [],
        'score_is_final':len(log)==500 or bool(log and log[-1].get('episode_done'))}
    # These are explicitly evaluation-only case audits, not actor rules or prompts.
    if game=='mark':
        entry['known_failure_audit']={'armor_objective_observed':any('Craft any armor' in x['observation']['text'] for x in log),
            'successful_armor_crafts':[{'step':x['step']+1,'action':x['action']} for x in log if x['action'].startswith('craft ') and any(k in x['action'] for k in ['cloth_tunic','leather_vest','copper_mail','steel_plate_armor']) and 'successfully crafted' in x['next_observation']['text']]}
    if game=='metropolis':
        entry['known_failure_audit']={'cipher_observed':any('AURUM-NOCTIS' in x['observation']['text'] for x in log),
            'cipher_written_successfully':[x['step']+1 for x in log if x['action'].startswith('write ') and 'AURUM-NOCTIS' in x['action'] and 'I wrote on ' in x['next_observation']['text']],
            'restoration_clause_written_to_legal_brief':[x['step']+1 for x in log if x['action'].startswith('write ') and 'RESTITUERE-LEGEM-PRIMAM' in x['action'] and 'legal_brief' in x['action']],
            'note':'Different text on a legal brief can be intentional; inspect goal bindings and reward events before labeling an error.'}
    report['runs'].append(entry)
report['main_mean']=sum(x['main_quest'] for x in report['runs'])/3
report['all_final']=all(x['score_is_final'] for x in report['runs'])
report['verdict']='Requires score plus mechanism-case review; detecting or blocking a bad action alone is not evidence that the task is solved.'
(R/'feedback_v2_diagnostics.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'all_final':report['all_final'],'main_mean':report['main_mean'],'runs':[{k:r[k] for k in ['game','steps','main_quest','supplementary','controller_calls','repairs']} for r in report['runs']]},ensure_ascii=True))
