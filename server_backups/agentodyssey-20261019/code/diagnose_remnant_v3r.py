"""Offline analysis of recorded public observations, never model/environment replay."""
import argparse,copy,json
from collections import Counter
from pathlib import Path
from feedback_v3r2_core import Ledger

def diagnose(root):
    root=Path(root);rid='remnant__v3r_20261018'
    rows=lambda p:[json.loads(l) for l in p.read_text(encoding='utf-8').splitlines()]
    log=rows(root/'runs'/rid/'agent_adam_davis/agent_log.jsonl')
    audit=rows(root/'control_audit'/(rid+'.jsonl'));decisions={r['step']:r for r in audit if r.get('event')=='decision'}
    def raw(r):
        try:return json.loads(r.get('response') or '{}')
        except json.JSONDecodeError:return {}
    overrides=[k for k,d in decisions.items() if raw(d).get('action') and raw(d)['action']!=d['action']]
    deaths=[i for i,r in enumerate(log,1) if 'I have died.' in r['next_observation']['text']]
    s=Ledger();counterfactual=[]
    for i,r in enumerate(log,1):
        s.advance(r['observation']['text']);d=decisions[i];packet=d['packet']
        s.focus=packet['focus_task_id'];s.objective=copy.deepcopy(packet['objective'])
        s.queue=list(packet['committed_short_plan'])
        if i in [88,97,107,181,301,497]:
            test=copy.deepcopy(s);proposed=raw(d);candidates=proposed.get('candidates') or [{'actions':[proposed['action']]}]
            action,check,dispatch=test.dispatch(candidates,s.focus)
            counterfactual.append({'step':i,'old_proposal':proposed['action'],'old_execution':d['action'],'old_source':d['dispatch']['source'],
              'revised_dispatch_on_same_public_history':action,'revised_preparation_proposal':s.preparation(),'candidate_check':check,'dispatch':dispatch})
        s.choose(r['action'],'recorded action; offline diagnostic only',s.focus)
    selected={r['step']:r for r in counterfactual}
    for i in [107,181,301,497]:assert selected[i]['revised_dispatch_on_same_public_history']==selected[i]['old_proposal'],selected[i]
    late=log[168:]
    return {'steps':len(log),'main_quest_score':sum(r['reward'].get('quest',0) for r in log),'last_reward_step':max(i for i,r in enumerate(log,1) if r['reward'].get('quest',0)),
      'actor_calls':sum(bool(d.get('response')) for d in decisions.values()),'actor_proposal_replacements':len(overrides),'replacement_steps':overrides,
      'execution_sources':dict(Counter(d['dispatch']['source'] for d in decisions.values())),
      'late_window':{'start':169,'end':500,'steps':len(late),'hall_or_library_moves':sum(r['action'] in ['enter hall','enter library'] for r in late)},
      'deaths':len(deaths),'death_steps':deaths,'drop_pick_plank_actions':sum(r['action'] in ['drop wood_plank','pick up wood_plank'] for r in log),
      'counterfactual_dispatch_checks':counterfactual,'provider_calls':0,
      'limitations':['A proposal replacement is not necessarily harmful; concrete examples and implementation establish the failure pathway.',
        'Counterfactual checks validate dispatcher behavior on fixed old histories, not subsequent environment outcomes or a score gain.',
        'Some model proposals contain unsupported assumptions, including a room staying lit. Allowing the choice does not certify the plan.',
        'Single development trajectory; combined changes do not identify component effects.']}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    r=diagnose(a.root);Path(a.output).write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in r.items() if k not in ['replacement_steps','counterfactual_dispatch_checks']},ensure_ascii=False))
