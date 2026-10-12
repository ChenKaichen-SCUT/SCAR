"""Independent zero-API physical replay and action-only quantity/resource audit."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import contextlib
import copy
import gzip
import multiprocessing as mp
from pathlib import Path
import re
import tempfile
from scar.io import atomic_json,digest
from scar_stage14.common import load,records,save_records,sha


def episode(job):
    ep,case,repeats=job
    from scar.environment import AGENT_ID,restore,snapshot,state_digest
    from scar.diagnostics.build import transition
    from scar_sequence.supplement import goal_reached
    from scar_sequence.resource_audit import census
    from scar_stage8.evaluate import one_action
    from scar_sequence.evaluate import physical
    from scar_v3.state import parse_action
    repetitions=[]
    for _ in range(repeats):
        with tempfile.TemporaryDirectory() as tmp,open('/dev/null','w') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
            env=restore(gzip.decompress(Path(f"results/stage11/initial_states/{case['id']}.pkl.gz").read_bytes()),tmp)
            assert state_digest(env)==case['state_hash'];audit=[]
            for row in ep['rows']:
                before=copy.deepcopy(env.obs[AGENT_ID]);assert before==row['observation'],(ep['task_id'],row['index'],'before')
                raw=snapshot(env);action=row['executed_action'];p=parse_action(action)
                actual=one_action(raw,action,tmp)
                variants=[]
                if p.verb=='craft':
                    for n in [1,2,3,4]:
                        v=one_action(raw,f'craft {n} {p.target}',tmp)
                        variants.append({k:v[k] for k in ['action','actual_output','consumed']})
                env=restore(raw,tmp);result=transition(env,action)
                assert result['after']==row['next_observation'],(ep['task_id'],row['index'],'after')
                assert result['semantic_rejection']==row['semantic_rejection']
                assert physical(env,case)==row['physical_after']
                assert goal_reached(env,case['goal'])==row['diagnostic_goal_reached']
                world=census(env,list(env.world.objects));named={env.world.objects[k].name:v for k,v in world.items()}
                loss={n:v-named.get(n,0) for n,v in actual['after_counts'].items() if v>named.get(n,0)}
                dominates=[]
                for v in variants:
                    union=set(v['consumed'])|set(actual['consumed'])
                    if v['actual_output']>=actual['actual_output'] and all(v['consumed'].get(n,0)<=actual['consumed'].get(n,0) for n in union):
                        if v['actual_output']>actual['actual_output'] or any(v['consumed'].get(n,0)<actual['consumed'].get(n,0) for n in union):dominates.append(v['action'])
                hp=lambda o:float(re.search(r'My health is at ([\d.]+)',o['text'])[1])
                audit.append({'index':row['index'],'action':action,'actual_output':actual['actual_output'],
                  'consumed':actual['consumed'],'produced':actual['produced'],'environment_loss':loss,'batch_variants':variants,
                  'locally_dominated_by':dominates,'goal':row['diagnostic_goal_reached'],'state_hash':state_digest(env),
                  'health_loss':hp(before)-hp(result['after']),'health_after':hp(result['after']),
                  'quantity_scope':'native action-only census; excludes subsequent step/NPC events; evaluation-only',
                  'waste_scope':'Pareto batch domination only; extra output is not automatically waste; future marginal material utility UNKNOWN'})
            repetitions.append(audit)
    assert all(x==repetitions[0] for x in repetitions)
    return {'task_id':ep['task_id'],'case_id':case['id'],'algorithm':ep['summary']['algorithm'],'rows':repetitions[0]}


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--repeats',type=int,default=1);p.add_argument('--workers',type=int,default=8);a=p.parse_args()
    root=Path('results/stage15');freeze=load(root/'freeze.json')
    for path,h in (freeze['code_hashes']|freeze['data_hashes']).items():assert sha(path)==h,path
    cases={c['id']:c for c in load('results/stage11/cases.json')}
    eps=[e for m in [f'P{i}' for i in range(7)] for e in records(root/f'trajectories_{m}.jsonl.gz')]
    assert len(eps)==70
    with ProcessPoolExecutor(max_workers=a.workers,mp_context=mp.get_context('spawn')) as pool:
        out=list(pool.map(episode,[(ep,cases[ep['case_id']],a.repeats) for ep in eps]))
    dest=Path(a.output);dest.mkdir(parents=True,exist_ok=True)
    save_records(dest/'native_audit.jsonl.gz',out)
    result={'passed':True,'episodes':len(out),'actions':sum(len(x['rows']) for x in out),'repeats':a.repeats,
       'api_calls':0,'digest':digest(out),'policy_hashes_unchanged':True,
       'assertions':['each before/after observation','physical resource state','goal possession','semantic rejection','initial physical hash','repeated action-only and full-step audit']}
    atomic_json(dest/'verification.json',result);print(result)

if __name__=='__main__':main()
