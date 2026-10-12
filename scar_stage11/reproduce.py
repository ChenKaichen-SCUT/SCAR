"""Portable zero-API replay by default; paid execution only under explicit flag."""
import argparse,contextlib,gzip,hashlib,json,tempfile
from pathlib import Path
from scar.io import atomic_json,digest
from scar.environment import restore,state_digest
from scar.diagnostics.build import transition
from scar_sequence.supplement import goal_reached
OUT=Path('results/stage11')
def main():
    p=argparse.ArgumentParser();p.add_argument('--runtime',required=True);p.add_argument('--replay-saved',action='store_true');p.add_argument('--run-closed-loop',action='store_true');p.add_argument('--key');p.add_argument('--workers',type=int,default=12);a=p.parse_args();root=Path(a.runtime);root.mkdir(parents=True,exist_ok=True)
    freeze=json.loads((OUT/'freeze.json').read_text());cases=json.loads((OUT/'cases.json').read_text())
    assert digest(cases)==freeze['dataset_digest']
    for name,h in (freeze['code_hashes']|freeze['data_hashes']).items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==h,name
    (root/'initials').mkdir(exist_ok=True);checks=[]
    with (root/'reproduce.log').open('w') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        for c in cases:
            assert c['game']=='robot_kingdom'
            raw=gzip.decompress((OUT/'initial_states'/f'{c["id"]}.pkl.gz').read_bytes());assert hashlib.sha256(raw).hexdigest()==c['snapshot_sha256'];assert state_digest(restore(raw))==c['state_hash'];(root/'initials'/f'{c["id"]}.pkl').write_bytes(raw)
        if a.replay_saved:
            refs={r['task_id']:r for r in json.loads((OUT/'replay_records.json').read_text())};by={c['id']:c for c in cases}
            for path in sorted(OUT.glob('trajectories_E*.jsonl.gz')):
                for ep in map(json.loads,gzip.open(path,'rt')):
                    c=by[ep['case_id']];env=restore(root/'initials'/f'{c["id"]}.pkl');mismatch=[]
                    for row,ref in zip(ep['rows'],refs[ep['task_id']]['state_hashes'],strict=True):
                        got=transition(env,row['executed_action'])
                        if state_digest(env)!=ref['state_hash'] or goal_reached(env,c['goal'])!=row['diagnostic_goal_reached'] or got['semantic_rejection']!=row['semantic_rejection']:mismatch.append(row['index'])
                    checks.append({'task_id':ep['task_id'],'steps':len(ep['rows']),'mismatches':mismatch})
    result={'api_calls':0,'initials':len(cases),'episodes_replayed':len(checks),'actions_replayed':sum(x['steps'] for x in checks),'checks':checks,'passed':all(not x['mismatches'] for x in checks)}
    atomic_json(root/'portable_replay.json',result);print(json.dumps({k:v for k,v in result.items() if k!='checks'}));assert result['passed']
    if a.run_closed_loop:
        if not a.key:raise ValueError('Explicit --key required for paid reproduction')
        if (root/'runs').exists() and any((root/'runs').iterdir()):raise ValueError('Refuse paid rerun on populated runtime')
        from scar_stage11.run import run_batch,make_tasks
        cfg=json.loads(Path('configs/protocol_stage11.json').read_text());tasks=make_tasks(cfg,cases)
        for t in tasks:t['initial_snapshot']=str(root/'initials'/f'{t["id"]}.pkl')
        atomic_json(root/'tasks.json',tasks);run_batch(cfg,root,a.key,tasks,a.workers)
if __name__=='__main__':main()
