"""Portable zero-API restore/replay; paid rerun only by explicit command."""
import argparse
import contextlib
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from scar.environment import restore,state_digest
from scar.diagnostics.build import transition
from scar.io import atomic_json,digest
from scar_unknown17.audit import initial


def main():
    p=argparse.ArgumentParser();p.add_argument('--runtime',required=True);p.add_argument('--replay-saved',action='store_true')
    p.add_argument('--run-closed-loop',action='store_true');p.add_argument('--key');a=p.parse_args();root=Path(a.runtime);root.mkdir(parents=True,exist_ok=True);out=Path('results/stage7')
    cs=json.loads((out/'cases.json').read_text());freeze=json.loads((out/'freeze.json').read_text())
    assert digest(cs)==freeze['dataset_digest']
    for name,h in freeze['code_hashes'].items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==h,name
    (root/'initials').mkdir(exist_ok=True)
    for c in cs:
        raw=initial(c);assert state_digest(restore(raw,set_rng=False))==c['state_hash']
        path=root/'initials'/f'{c["id"]}.pkl'
        if path.exists():assert path.read_bytes()==raw
        else:path.write_bytes(raw)
    replays=[]
    if a.replay_saved:
        expected={r['task_id']:r for r in json.loads((out/'replay_records.json').read_text())}
        with (root/'reproduce.log').open('w') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
            for path in sorted(out.glob('trajectories_C*.jsonl.gz')):
                for ep in map(json.loads,gzip.open(path,'rt')):
                    with tempfile.TemporaryDirectory() as tmp:
                        env=restore(root/'initials'/f"{ep['case_id']}.pkl",tmp);errors=[]
                        hashes=expected[ep['task_id']]['state_hashes']
                        for row,wanted in zip(ep['rows'],hashes):
                            transition(env,row['executed_action'])
                            if state_digest(env)!=wanted['state_hash']:errors.append(row['index'])
                        assert len(hashes)==len(ep['rows'])
                        replays.append({'task_id':ep['task_id'],'steps':len(ep['rows']),'mismatches':errors})
        assert len(replays)==102 and not any(r['mismatches'] for r in replays)
    result={'restored':17,'all_initial_hashes_match':True,'replayed_episodes':len(replays),
        'replayed_actions':sum(r['steps'] for r in replays),'api_calls':0,'replays':replays}
    atomic_json(root/'restoration.json',result);print(json.dumps({k:v for k,v in result.items() if k!='replays'}))
    if a.run_closed_loop:
        if (root/'runs').exists() and any((root/'runs').iterdir()):
            raise ValueError('Paid reproduction requires a fresh runtime. Do not resume adjudicated policy aborts or repeat completed episodes.')
        if not a.key:p.error('--key is required for an explicitly requested fresh paid rerun')
        subprocess.run([sys.executable,'-m','scar_unknown17_stage7.run','--runtime',str(root),'--key',a.key],check=True)
        subprocess.run([sys.executable,'-m','scar_unknown17_stage7.finish','--runtime',str(root)],check=True)

if __name__=='__main__':main()
