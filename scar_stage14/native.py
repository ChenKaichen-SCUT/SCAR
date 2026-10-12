"""Stage14 native witness generation. Native truth only audits chosen actions."""
import argparse
import contextlib
import copy
import gzip
import hashlib
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import tempfile
from scar.io import atomic_json
from scar_stage14.common import ROOT,OLD,load,sha,records,save_records
from scar_stage14.executor import Executor
from scar_stage14.replay import verify_freezes,cache


def branch(state,public,intent,case):
    from scar.environment import AGENT_ID,restore,snapshot,state_digest
    from scar.diagnostics.build import transition
    from scar_sequence.resource_audit import census
    from scar_sequence.supplement import goal_reached
    from scar_stage8.evaluate import one_action
    from scar_v3.state import parse_action
    raw=gzip.decompress(Path(state['snapshot_path']).read_bytes())
    assert hashlib.sha256(raw).hexdigest()==state['snapshot_sha256']
    outcomes=[]
    for repeat in range(2):
        with tempfile.TemporaryDirectory() as tmp:
            env=restore(raw,tmp);e=Executor(public,intent)
            assert state_digest(env)==state['physical_hash']
            known={n for n,r in e.ctrl.table.recipes.items() if r.get('ingredients')}
            keys={case['object_names'][oid] for oid in case['recipe_graph']}
            relevant={case['object_names'][oid] for oid in set(case['materials'])|set(case['products'])}
            trace=[]
            while (action:=e.next()) is not None:
                # No native state/score was supplied to normalization or next().
                before=copy.deepcopy(env.obs[AGENT_ID]);checkpoint=snapshot(env)
                native=one_action(checkpoint,action,tmp);env=restore(checkpoint,tmp)
                result=transition(env,action);e.observe(action,before,result['after'])
                counts=census(env,list(env.world.objects));named={env.world.objects[k].name:v for k,v in counts.items()}
                loss={n:v-named.get(n,0) for n,v in native['after_counts'].items() if n in relevant and v>named.get(n,0)}
                now={n for n,r in e.ctrl.table.recipes.items() if r.get('ingredients')};p=parse_action(action)
                trace.append({'index':len(trace),'action':action,'before':before,'after':result['after'],
                    'feedback':e.ctrl.table.state['feedback'],'rejected':result['semantic_rejection'],
                    'new_public_recipes':sorted(now-known),'new_key_recipes':sorted((now-known)&keys),
                    'action_consumption':native['consumed'],'action_production':native['produced'],
                    'unrelated_craft':p.verb=='craft' and native['actual_output']>0 and p.target not in keys,
                    'unrelated_key_input_consumption':{n:v for n,v in native['consumed'].items() if n in relevant and p.verb=='craft' and p.target not in keys},
                    'environment_key_loss':loss,'state_hash':state_digest(env),'goal':goal_reached(env,case['goal'])})
                if result['done'] and not e.stop:e._finish('environment_terminal')
            outcomes.append({'trace':trace,**e.result(),'final_hash':state_digest(env),
                'goal':goal_reached(env,case['goal']),'reused':False})
    assert outcomes[0]==outcomes[1],(state['state_id'],intent['id'])
    return dict(outcomes[0],replayed_twice=True)


def one(job):
    import socket
    def denied(*args,**kwargs):raise RuntimeError('Stage14 native workers forbid network/model API')
    socket.socket.connect=denied
    state,pub,intent,case=job
    with open('/dev/null','w') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        b=branch(state,pub,intent,case)
    return {'state_id':state['state_id'],'intent_id':intent['id'],'branch':b,'api_calls':0}


def main(output,verify=None,workers=8):
    verify_freezes()
    for p,h in load(ROOT/'replay_freeze.json')['hashes'].items():assert sha(p)==h,p
    ss={s['state_id']:s for s in load(OLD/'states.json')};pubs=load(ROOT/'intent_public_inputs.json')
    cases={c['id']:c for c in load('results/stage11/cases.json')};plan=load(ROOT/'replay_plan.json')['jobs']
    jobs=[(ss[r['state_id']],pubs[r['state_id']],r['intent'],cases[ss[r['state_id']]['case_id']]) for r in plan]
    out=[]
    with ProcessPoolExecutor(max_workers=workers,mp_context=mp.get_context('spawn')) as pool:
        for row in pool.map(one,jobs):
            out.append(row);atomic_json(str(output)+'.progress.json',{'complete':len(out),'total':len(jobs),'api_calls':0})
    old=cache();checks=0
    for r in out:
        prefix=[]
        for t in r['branch']['trace']:
            prefix.append(t['action']);saved=old[r['state_id']].get(tuple(prefix))
            if saved:assert saved['row']==t,(r['state_id'],prefix);checks+=1
    if verify:assert list(records(verify))==out,'Independent native replay differs'
    else:save_records(output,out)
    result={'passed':True,'branches':len(out),'actions_per_replay':sum(r['branch']['actions'] for r in out),
        'each_replayed_twice':True,'independent_local_replay':bool(verify),'historical_prefix_checks':checks,
        'network_disabled':True,'api_calls':0,'new_model_cost_usd':0}
    atomic_json(str(output)+'.verification.json',result);print(result)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--verify');p.add_argument('--workers',type=int,default=8)
    a=p.parse_args();main(a.output,a.verify,a.workers)
