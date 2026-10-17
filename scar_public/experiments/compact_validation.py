"""Frozen 12-episode screen orchestration. Run on the Linux experiment server."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time

from scar.io import atomic_json


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--key',required=True);a=p.parse_args()
    frozen=Path.cwd();manifest=frozen/'source_manifest.json'
    jobs=[dict(game=g,repeat=i,hash_seed=str(secrets.randbelow(2**32)))
          for i,g in enumerate(('remnant','mark','metropolis'))]
    assert not (a.root/'plan.json').exists(), 'Refuse duplicate study launch'
    atomic_json(a.root/'plan.json',dict(frozen_utc=time.time(),jobs=jobs,
        source_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),
        protocol='scar_public/experiments/compact_validation_protocol.txt',max_actions=3600))
    def work(job):
        block=a.root/'evaluation'/job['game'];block.mkdir(parents=True)
        env=dict(os.environ,PYTHONHASHSEED=job['hash_seed'])
        commands=[]
        def run(cmd,label):
            commands.append(dict(label=label,command=[x if x!=a.key else 'PRIVATE_KEY_FILE' for x in cmd]))
            atomic_json(block/'commands.json',commands)
            with (block/(label+'.log')).open('a') as log:
                subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        shared=[sys.executable,'-m','scar_public.experiments.core_trial','--game',job['game'],
                '--repeat',str(job['repeat']),'--steps','300','--key',a.key]
        run(shared+['--root',str(block/'main'),'--arms','continuation_generic','checked','sentry'],'main')
        traces=[json.loads(f.read_text()) for f in sorted((block/'main/continuation_generic/trace').glob('*.json'))]
        quota=sum('proposal' in json.loads(r['response'])['continuation'] for r in traces)
        atomic_json(block/'quota.json',dict(quota=quota,
            rule='Only scalar number of compact repair queries; no score/history/trigger time used'))
        scheduled=block/'scheduled';scheduled.mkdir()
        (scheduled/'api').symlink_to(block/'main/api',target_is_directory=True)
        run(shared+['--root',str(scheduled),'--arms','continuation_scheduled','--repair-quota',str(quota),
            '--initial',str(block/'main/initial.pkl'),'--initial-kind','paired-independent-snapshot'],'scheduled')
        run([sys.executable,'-m','scar_public.experiments.audit_compact_validation','--block',str(block)],'audit')
        atomic_json(block/'complete.json',dict(completed_utc=time.time()))
        return dict(game=job['game'],complete=True)
    with ThreadPoolExecutor(max_workers=3) as pool:
        results=list(pool.map(work,jobs))
    atomic_json(a.root/'pipeline_complete.json',dict(jobs=results,completed_utc=time.time()))


if __name__=='__main__':main()
