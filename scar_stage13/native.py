"""Stage13 zero-API branches. Executor copied unchanged from Stage12 except explicit limit.
Native truth is consulted only after each public action.
"""
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

OUT=Path('results/stage13')


def branch(state, candidate, case, limit=4):
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
            for index in range(min(limit,state['remaining_actions'])):
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


def verify_freeze():
    f=json.loads((OUT/'freeze.json').read_text())
    prior=json.loads((OUT/'prior_manifest.json').read_text())
    for p,h in (f['frozen_hashes']|prior).items():
        assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p


def one(job):
    import socket
    def denied(*args,**kwargs): raise RuntimeError('Stage13 forbids all network calls inside native workers')
    socket.socket.connect=denied
    s,case,plan=job
    with open('/dev/null','w') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        b=branch(s,plan['candidate'],case,plan['limit'])
    return dict(plan,branch=b,api_calls=0)


def main(output,verify=None,workers=8):
    verify_freeze()
    states={s['state_id']:s for s in json.loads(Path('results/stage12/diagnostic/states.json').read_text())}
    cases={c['id']:c for c in json.loads(Path('results/stage11/cases.json').read_text())}
    plan=json.loads((OUT/'supplement_plan.json').read_text())['jobs']
    jobs=[(states[p['state_id']],cases[states[p['state_id']]['case_id']],p) for p in plan]
    with ProcessPoolExecutor(max_workers=workers,mp_context=mp.get_context('spawn')) as pool:
        records=list(pool.map(one,jobs))
    checks=[]
    old={r['state_id']:r['branches'] for r in map(json.loads,gzip.open('results/stage12/diagnostic/native_branches.jsonl.gz','rt'))}
    for r in records:
        if r['kind']=='truncation_sensitivity':
            original=old[r['state_id']][r['candidate']['id']]
            assert r['branch']['trace'][:4]==original['trace'],(r['state_id'],r['candidate']['id'])
            checks.append({'state_id':r['state_id'],'candidate_id':r['candidate']['id'],'first4_unchanged':True})
    if verify:
        saved=list(map(json.loads,gzip.open(verify,'rt')))
        assert saved==records,'Independent replay disagrees'
    else:
        with gzip.open(output,'wt') as f:
            for r in records:f.write(json.dumps(r,ensure_ascii=False)+'\n')
    result={'passed':True,'branches':len(records),'actions_per_replay':sum(r['branch']['actions'] for r in records),
        'replayed_twice':True,'independent_replay':bool(verify),'first4_checks':checks,
        'api_calls':0,'network_disabled_in_workers':True,'new_cost_usd':0}
    atomic_json(str(output)+'.verification.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='first4_checks'}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--verify');p.add_argument('--workers',type=int,default=8)
    a=p.parse_args();main(a.output,a.verify,a.workers)
