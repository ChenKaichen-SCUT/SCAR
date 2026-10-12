"""Real-engine Stage A branches. Native truth never chooses a branch action."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import contextlib
import copy
import gzip
import hashlib
import json
import multiprocessing as mp
from pathlib import Path
import tempfile

from scar.environment import AGENT_ID, restore, snapshot, state_digest
from scar.diagnostics.build import transition
from scar.io import atomic_json, digest
from scar_sequence.resource_audit import census
from scar_sequence.supplement import goal_reached
from scar_stage8.evaluate import one_action
from scar_stage12.public import controller, confirmed, next_action, primitive_candidate, PLAN_LIMIT
from scar_v3.state import parse_action

OUT=Path('results/stage12/diagnostic')


def branch(state, candidate, case):
    raw=gzip.decompress(Path(state['snapshot_path']).read_bytes())
    assert hashlib.sha256(raw).hexdigest()==state['snapshot_sha256']
    outcomes=[]
    for repeat in range(2):
        with tempfile.TemporaryDirectory() as tmp:
            env=restore(raw,tmp);ctrl=controller(state['public_controller'],state['observation'])
            assert state_digest(env)==state['physical_hash']
            initial_known={n for n,r in ctrl.table.recipes.items() if r.get('ingredients')}
            keys={case['object_names'][oid] for oid in case['recipe_graph']}
            relevant={case['object_names'][oid] for oid in set(case['materials'])|set(case['products'])}
            traces=[];used=set();stop='action_limit'
            for index in range(min(PLAN_LIMIT,state['remaining_actions'])):
                action=next_action(ctrl,candidate,traces)
                if action is None:stop='public_plan_complete_or_blocked';break
                signature=digest([action,ctrl.context(action)])
                if signature in used:stop='same_context_repeat_suppressed';break
                used.add(signature)
                # Native cost/legality auditing starts AFTER the public action.
                before=copy.deepcopy(env.obs[AGENT_ID]);checkpoint=snapshot(env)
                native=one_action(checkpoint,action,tmp)
                env=restore(checkpoint,tmp)  # restore RNG after isolated action dispatch
                result=transition(env,action)
                ctrl.observe(before,action,result['after'])
                counts=census(env,list(env.world.objects))
                named={env.world.objects[k].name:v for k,v in counts.items()}
                loss={n:v-named.get(n,0) for n,v in native['after_counts'].items() if n in relevant and v>named.get(n,0)}
                now={n for n,r in ctrl.table.recipes.items() if r.get('ingredients')}
                p=parse_action(action)
                traces.append({'index':index,'action':action,'before':before,'after':result['after'],
                    'feedback':ctrl.table.state['feedback'],'rejected':result['semantic_rejection'],
                    'new_public_recipes':sorted(now-initial_known),'new_key_recipes':sorted((now-initial_known)&keys),
                    'action_consumption':native['consumed'],'action_production':native['produced'],
                    'unrelated_craft':p.verb=='craft' and native['actual_output']>0 and p.target not in keys,
                    'unrelated_key_input_consumption':{n:v for n,v in native['consumed'].items()
                       if n in relevant and p.verb=='craft' and p.target not in keys},
                    'environment_key_loss':loss,'state_hash':state_digest(env),'goal':goal_reached(env,case['goal'])})
                if result['done'] or traces[-1]['goal']:stop='environment_or_goal_terminal';break
                if p.verb=='inspect' and (candidate['kind'] in {'inspect','general'} or p.target==candidate['target']):
                    stop='inspection_attempt_completed';break
            all_new=sorted({n for r in traces for n in r['new_key_recipes']})
            outcomes.append({'candidate':candidate,'trace':traces,'stop':stop,'actions':len(traces),
                'new_key_recipes':all_new,'useful':bool(all_new),
                'one_step_useful':bool(traces and traces[0]['new_key_recipes']),
                'rejections':sum(r['rejected'] for r in traces),
                'unrelated_craft':any(r['unrelated_craft'] for r in traces),
                'unrelated_key_input_consumption':any(r['unrelated_key_input_consumption'] for r in traces),
                'environment_key_loss':any(r['environment_key_loss'] for r in traces),
                'final_hash':state_digest(env),'goal':goal_reached(env,case['goal'])})
    assert outcomes[0]==outcomes[1],state['state_id']
    return dict(outcomes[0],replayed_twice=True)


def evaluate_state(job):
    state,case,judgments=job
    with open('/dev/null','w') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        candidates=state['candidates']+state['cropped_candidates'];extra=[]
        for j in judgments:
            if j['method']=='J2' and j.get('parsed') and not j.get('validation_errors'):
                extra.append(primitive_candidate(j['parsed']['action']))
        unique={c['id']:c for c in candidates+extra}
        evaluated={key:branch(state,c,case) for key,c in unique.items()}
    return {'state_id':state['state_id'],'case_id':state['case_id'],
            'branches':evaluated,'retained_ids':[c['id'] for c in state['candidates']],
            'cropped_ids':[c['id'] for c in state['cropped_candidates']],
            'free_proposal_extra_ids':[c['id'] for c in extra if c['id'] not in {x['id'] for x in candidates}],
            'api_calls':0}


def main(runtime,workers=8):
    root=Path(runtime);states=json.loads((OUT/'states.json').read_text())
    judgments=json.loads((OUT/'judgments.json').read_text())
    cases={c['id']:c for c in json.loads(Path('results/stage11/cases.json').read_text())}
    jobs=[(s,cases[s['case_id']],[j for j in judgments if j['state_id']==s['state_id']]) for s in states]
    records=[]
    with ProcessPoolExecutor(max_workers=workers,mp_context=mp.get_context('spawn')) as pool:
        for record in pool.map(evaluate_state,jobs):
            records.append(record)
            atomic_json(root/'evaluation_progress.json',{'states':len(records),'total':len(states),'api_calls':0})
    with gzip.open(OUT/'native_branches.jsonl.gz','wt') as f:
        for record in records:f.write(json.dumps(record,ensure_ascii=False)+'\n')
    summary={'states':len(records),'branches':sum(len(r['branches']) for r in records),
             'actions':sum(b['actions'] for r in records for b in r['branches'].values()),
             'each_branch_replayed_twice':True,'passed':True,'api_calls':0}
    atomic_json(OUT/'native_verification.json',summary);print(json.dumps(summary))


def preflight():
    states=json.loads((OUT/'states.json').read_text());cases={c['id']:c for c in json.loads(Path('results/stage11/cases.json').read_text())}
    checks=[]
    with open('/dev/null','w') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        # Fixed one per family, all retained candidates. No outcome-based resampling.
        for state in states[::5]:
            for candidate in state['candidates']:
                b=branch(state,candidate,cases[state['case_id']])
                checks.append({'state_id':state['state_id'],'candidate_id':candidate['id'],
                    'bounded':b['actions']<=min(4,state['remaining_actions']),'roundtrip_native':b['replayed_twice']})
    result={'checks':checks,'passed':all(r['bounded'] and r['roundtrip_native'] for r in checks),
            'outcome_values_not_used_to_select_states_or_change_protocol':True,'api_calls':0}
    atomic_json(OUT/'preflight.json',result);print(json.dumps({'checks':len(checks),'passed':result['passed']}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--runtime');p.add_argument('--workers',type=int,default=8);p.add_argument('--preflight',action='store_true');a=p.parse_args()
    if a.preflight:preflight()
    else:main(a.runtime,a.workers)
