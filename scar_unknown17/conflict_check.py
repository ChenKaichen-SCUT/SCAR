"""Post-hoc same-state overproduction conflict; not a new policy evaluation."""
import argparse
import contextlib
import gzip
import json
from pathlib import Path
from scar.io import atomic_json
from scar_unknown17.audit import branch,save_state


def main():
    p=argparse.ArgumentParser();p.add_argument('--runtime',required=True);a=p.parse_args();root=Path(a.runtime);out=Path('results/unknown17')
    cid='sequence-7e32e0ff916aaa50'
    case=next(c for c in json.loads((out/'cases.json').read_text()) if c['id']==cid)
    ep=next(e for e in map(json.loads,gzip.open(out/'trajectories_FIFOCombined.jsonl.gz','rt')) if e['case_id']==cid)
    index=25;assert ep['rows'][index]['executed_action']=='craft 2 astrolabe_core'
    raw=(root/'runs'/ep['task_id']/'steps'/f'{index:04}'/'environment.pkl').read_bytes()
    # Both branches use the same continuation. Replace the last two no-progress
    # actions by the public goal's craft and pickup, staying within the original
    # remaining 15 actions. This is explicit evaluator guidance, never scored.
    suffix=[r['executed_action'] for r in ep['rows'][index+1:-2]]+['craft 1 orrery_blade','pick up orrery_blade']
    with open(root/'conflict_check.log','w') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        variants=[branch(raw,[f'craft {n} astrolabe_core']+suffix,case) for n in [1,2]]
    result={'case_id':cid,'method':'FIFOCombined','index':index,'state':save_state(raw,cid,'overproduction-conflict'),
        'variants':variants,'same_suffix':True,'total_episode_actions':index+1+len(suffix),'api_calls':0,
        'selection':'posthoc failure with all recipe names discovered and batch2 intermediate production; not tuned formal policy',
        'scope':'Local interaction between batch heuristic and future resource needs. Evaluator adds the same final goal actions to both branches; neither is a model recovery result.'}
    atomic_json(out/'overproduction_counterfactual.json',result)
    print(json.dumps({'quantity1_quantity2_goals':[v['goal'] for v in variants],'total_actions':result['total_episode_actions'],'api_calls':0}))

if __name__=='__main__':main()
