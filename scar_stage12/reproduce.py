"""Independently repeat published Stage A branches without model access."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import contextlib
import gzip
import hashlib
import json
import multiprocessing as mp
from pathlib import Path

from scar.io import atomic_json
from scar_stage12.evaluate import branch

OUT=Path('results/stage12/diagnostic')


def one(job):
    state,case,record=job
    with open('/dev/null','w') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        checks=[]
        for key,saved in record['branches'].items():
            actual=branch(state,saved['candidate'],case)
            checks.append({'candidate_id':key,'passed':actual==saved,'actions':actual['actions']})
    return {'state_id':state['state_id'],'checks':checks,'passed':all(c['passed'] for c in checks)}


def main(output,workers=8):
    freeze=json.loads((OUT/'freeze.json').read_text())
    for p,h in (freeze['code_hashes']|freeze['data_hashes']|freeze['prior_file_hashes']).items():
        assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
    states=json.loads((OUT/'states.json').read_text());cases={c['id']:c for c in json.loads(Path('results/stage11/cases.json').read_text())}
    saved={r['state_id']:r for r in map(json.loads,gzip.open(OUT/'native_branches.jsonl.gz','rt'))}
    jobs=[(s,cases[s['case_id']],saved[s['state_id']]) for s in states]
    with ProcessPoolExecutor(max_workers=workers,mp_context=mp.get_context('spawn')) as pool:
        checks=list(pool.map(one,jobs))
    result={'api_calls':0,'states':len(checks),'branches':sum(len(c['checks']) for c in checks),
            'actions_per_replay':sum(r['actions'] for c in checks for r in c['checks']),
            'each_branch_replayed_twice':True,'checks':checks,'passed':all(c['passed'] for c in checks)}
    atomic_json(output,result);print(json.dumps({k:v for k,v in result.items() if k!='checks'}));assert result['passed']


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--workers',type=int,default=8);a=p.parse_args();main(a.output,a.workers)
