"""Real-engine preflight: paired public-policy branches, two server replays.

Hidden quantities enter audit outputs only, after an action has been selected.
Fixed saved proposals are diagnostic, not claimed as model closed-loop results.
"""
import argparse
import contextlib
import copy
import gzip
import json
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import re
import tempfile
from scar_stage14.common import load,records,save_records
from scar.io import atomic_json,digest
from scar_stage15.controller import Controller15


def run_case(job):
    case,eps,states,repeats=job
    from scar.environment import AGENT_ID,restore,snapshot,state_digest
    from scar.diagnostics.build import transition
    from scar_sequence.supplement import goal_reached
    from scar_sequence.resource_audit import census
    from scar_stage8.evaluate import one_action
    out=[]
    with tempfile.TemporaryDirectory() as tmp,open('/dev/null','w') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        env=restore(gzip.decompress(Path(f"results/stage11/initial_states/{case['id']}.pkl.gz").read_bytes()),tmp)
        assert state_digest(env)==case['state_hash']
        checkpoints={};selected={s['index'] for s in states}
        for row in eps['rows']:
            assert env.obs[AGENT_ID]==row['observation'],(case['id'],row['index'],'prefix_observation')
            if row['index'] in selected:checkpoints[row['index']]=snapshot(env)
            actual=transition(env,row['executed_action'])
            assert actual['after']==row['next_observation']
        original_success=goal_reached(env,case['goal'])
        for s in states:
            branches={}
            for method in ['P0','P1','P2','P3','P4','P5','P6']:
                repeated=[]
                for repeat in range(repeats):
                    env=restore(checkpoints[s['index']],tmp)
                    controller=None if method=='P0' else Controller15.from_dict(s['variants'][method]['state'])
                    trace=[]
                    for j,proposal in enumerate(s['proposals']):
                        if goal_reached(env,case['goal']):break
                        before=copy.deepcopy(env.obs[AGENT_ID]);raw=snapshot(env)
                        action=s['original_actions'][j] if method=='P0' else controller.choose(before,proposal)
                        native=one_action(raw,action,tmp);env=restore(raw,tmp)
                        result=transition(env,action)
                        if controller:controller.observe(before,action,result['after'])
                        counts=census(env,list(env.world.objects));named={env.world.objects[k].name:v for k,v in counts.items()}
                        loss={n:v-named.get(n,0) for n,v in native['after_counts'].items() if v>named.get(n,0)}
                        hp=lambda obs:float(re.search(r'My health is at ([\d.]+)',obs['text'])[1])
                        trace.append({'index':s['index']+j,'proposal':proposal,'action':action,'before':before,'after':result['after'],
                            'feedback':result['feedback'],'rejected':result['semantic_rejection'],'done':result['done'],
                            'actual_output':native['actual_output'],'action_consumed':native['consumed'],'action_produced':native['produced'],
                            'environment_loss':loss,'goal':goal_reached(env,case['goal']),'physical_hash':state_digest(env),
                            'health_loss':hp(before)-hp(result['after']),
                            'decision':copy.deepcopy(controller.audit15) if controller else None,
                            'intent_after':copy.deepcopy(controller.intent15) if controller else None})
                        if result['done']:break
                    repeated.append({'trace':trace,'goal':goal_reached(env,case['goal'])})
                assert all(x==repeated[0] for x in repeated),s['id']+method
                branches[method]=repeated[0]
            out.append({'state_id':s['id'],'case_id':case['id'],'index':s['index'],'kinds':s['kinds'],'branches':branches})
    return {'case_id':case['id'],'original_success':original_success,'original_steps':len(eps['rows']),'states':out}


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--repeats',type=int,default=2);p.add_argument('--workers',type=int,default=8);args=p.parse_args()
    cases={c['id']:c for c in load('results/stage11/cases.json')};eps={e['case_id']:e for e in records('results/stage10/trajectories_S1.jsonl.gz')}
    states=list(records('results/stage15/preflight_jobs.jsonl.gz'))
    jobs=[(c,eps[k],[s for s in states if s['case_id']==k],args.repeats) for k,c in cases.items()]
    output=Path(args.output);output.mkdir(parents=True,exist_ok=True)
    with ProcessPoolExecutor(max_workers=args.workers,mp_context=mp.get_context('spawn')) as pool:
        rows=list(pool.map(run_case,jobs))
    save_records(output/'native_branches.jsonl.gz',[s for row in rows for s in row['states']])
    atomic_json(output/'summary.json',{'repeats':args.repeats,'cases':len(rows),'states':sum(len(r['states']) for r in rows),
        'actions_per_pass':sum(len(b['trace']) for r in rows for s in r['states'] for b in s['branches'].values()),
        'original_S1_successes':sum(r['original_success'] for r in rows),'original_S1_actions':sum(r['original_steps'] for r in rows),
        'original_case_replays':[{k:v for k,v in row.items() if k!='states'} for row in rows],
        'native_branches_digest':digest([s for row in rows for s in row['states']]),'api_calls':0})
    print(json.dumps(load(output/'summary.json')))

if __name__=='__main__':main()
