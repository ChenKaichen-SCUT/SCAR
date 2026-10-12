"""Necessary residual witnesses from fixed historical prefixes; no new tasks.

Select EVERY unfinished first task/target commitment in the 30 reference
episodes. Exclude a stale recorded goal when its actual craft targets another
product. Selection is frozen before these native outcomes; executor unchanged.
"""
import argparse
import contextlib
import datetime
import gzip
import hashlib
import tempfile
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp
from pathlib import Path
from scar.io import atomic_json,digest
from scar_stage14.common import ROOT,load,episodes,sha,records,save_records
from scar_stage14.intents import normalize
from scar_stage12.public import primitive_candidate
from scar_stage14.native import one
from scar_stage14.replay import verify_freezes
from scar_stage14.audit import initialize
from scar_v3.state import parse_action


def plan():
    assert not (ROOT/'residual_replay_freeze.json').exists()
    epmap={ep['task_id']:(ep,case,path) for _,_,ep,case,path in episodes()};jobs=[];excluded=[]
    for c in load(ROOT/'full_reference_commitments.json'):
        if c['actual_closure']['complete']:continue
        ep,case,path=epmap[c['task_id']];r=ep['rows'][c['start_index']];p=parse_action(r['executed_action'])
        if p.verb=='craft' and p.target!=c['target']:
            excluded.append(dict(c,reason='recorded preparation goal was not accepted: actual craft targets another product'));continue
        pub={'controller':r['stage7_state_before'],'observation':r['observation'],'remaining_actions':40-r['index']}
        i=normalize(pub,primitive_candidate(r['executed_action']),{'target':c['target'],'operation':'craft_inspect','evidence':c['public_evidence']})
        assert i['target']==c['target']
        sid='r14_'+digest([c['task_id'],c['start_index'],c['target']])[:16]
        k,_=initialize(case,r['observation']['step'])
        for old in ep['rows'][:r['index']]:k.observe(old['next_observation'],old['executed_action'],cutoff=r['observation']['step'])
        jobs.append({'state_id':sid,'source_task':c['task_id'],'source_index':r['index'],'case_id':ep['case_id'],
            'source_file':path,'source_file_sha256':sha(path),'public':pub,'intent':i,'knowledge':k.to_dict(),
            'family':c['family'],'method':c['method'],'actual_commitment':c})
    atomic_json(ROOT/'residual_replay_plan.json',{'jobs':jobs,'excluded':excluded,'api_calls':0,
        'selection':'all unfinished first task/target public exploratory commitments, S1/E0/E1; no new native outcome filtering',
        'main_comparison_unchanged':50,'max_window':8,'executor_unchanged':True})
    atomic_json(ROOT/'residual_replay_freeze.json',{'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'hashes':{str(p):sha(p) for p in [ROOT/'residual_replay_plan.json',Path('scar_stage14/residual_replay.py')]}})
    print({'selected_residual_witnesses':len(jobs),'unaccepted_stale_intents':len(excluded)})


def materialize():
    from scar.environment import AGENT_ID,restore,snapshot,state_digest
    from scar.diagnostics.build import transition
    verify_freezes()
    for p,h in load(ROOT/'residual_replay_freeze.json')['hashes'].items():assert sha(p)==h,p
    epmap={ep['task_id']:ep for _,_,ep,_,_ in episodes()};states=[]
    (ROOT/'residual_checkpoints').mkdir(exist_ok=True)
    with open('/dev/null','w') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        for job in load(ROOT/'residual_replay_plan.json')['jobs']:
            ep=epmap[job['source_task']];raw=gzip.decompress(Path('results/stage11/initial_states',job['case_id']+'.pkl.gz').read_bytes())
            with tempfile.TemporaryDirectory() as tmp:
                env=restore(raw,tmp)
                for row in ep['rows'][:job['source_index']]:
                    assert env.obs[AGENT_ID]==row['observation']
                    result=transition(env,row['executed_action']);assert result['after']==row['next_observation']
                assert env.obs[AGENT_ID]==job['public']['observation']
                raw=snapshot(env);path=ROOT/'residual_checkpoints'/(job['state_id']+'.pkl.gz')
                path.write_bytes(gzip.compress(raw,mtime=0))
                states.append({'state_id':job['state_id'],'case_id':job['case_id'],'snapshot_path':str(path),
                    'snapshot_sha256':hashlib.sha256(raw).hexdigest(),'physical_hash':state_digest(env),
                    'remaining_actions':job['public']['remaining_actions'],'historical_prefix_verified':job['source_index']})
    target=ROOT/'residual_checkpoint_manifest.json'
    if target.exists():assert load(target)==states,'independent checkpoint reconstruction differs'
    else:atomic_json(target,states)
    print({'historical_checkpoints_reconstructed':len(states),'prefix_observations_exact':True})


def run(output,verify=None):
    verify_freezes()
    for p,h in load(ROOT/'residual_replay_freeze.json')['hashes'].items():assert sha(p)==h,p
    ss={s['state_id']:s for s in load(ROOT/'residual_checkpoint_manifest.json')};cases={c['id']:c for c in load('results/stage11/cases.json')}
    jobs=[(ss[j['state_id']],j['public'],j['intent'],cases[j['case_id']]) for j in load(ROOT/'residual_replay_plan.json')['jobs']]
    with ProcessPoolExecutor(max_workers=8,mp_context=mp.get_context('spawn')) as pool:out=list(pool.map(one,jobs))
    if verify:assert list(records(verify))==out,'independent residual native results differ'
    else:save_records(output,out)
    result={'passed':True,'branches':len(out),'actions_per_replay':sum(r['branch']['actions'] for r in out),
        'each_replayed_twice':True,'independent_local_replay':bool(verify),'network_disabled':True,'api_calls':0,'new_model_cost_usd':0}
    atomic_json(str(output)+'.verification.json',result);print(result)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['plan','materialize','run']);p.add_argument('--output');p.add_argument('--verify');a=p.parse_args()
    if a.action=='plan':plan()
    elif a.action=='materialize':materialize()
    else:run(a.output,a.verify)
