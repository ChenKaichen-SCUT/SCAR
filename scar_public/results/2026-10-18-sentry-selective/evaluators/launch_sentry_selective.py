import argparse,json,os,shutil,subprocess,tarfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--full',action='store_true');a=p.parse_args()
root=Path('/root/scar_sentry_selective_20261018');code=root/'frozen'
if not a.full:
    root.mkdir(exist_ok=False);code.mkdir()
    with tarfile.open('/root/sentry_selective_source.tgz') as tar:tar.extractall(code,filter='data')
base=Path('/root/scar_research_20261015');deps=Path('/root/scar_core_valid_20261017')
old=Path('/root/scar_sentry_foundation_20261018/evaluation');prior=Path('/root/scar_sentry_persistent_20261018_v2/evaluation')
python=str(base/'venv/bin/python');key=str(base/'private/deepseek.key')
env=dict(os.environ,PYTHONPATH=f'{deps}/deps:{code}:{deps}/Sentry:{base}/source/AgentOdyssey:{base}/causal_adapter_20261016/deps',
    AGENTODYSSEY_ROOT=str(base/'source/AgentOdyssey'),OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
jobs=[]
if not a.full:
    with (root/'diagnostic.log').open('w') as log:
        proc=subprocess.Popen([python,'/root/diagnose_sentry_selective.py'],cwd=code,env=env,stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
    jobs.append(dict(phase='diagnostic',pid=proc.pid))
else:
    assert (root/'diagnostic.json').exists()
    for game in ('remnant','mark','metropolis'):
        target=root/'evaluation'/game;cache=target/'shared_api';cache.mkdir(parents=True,exist_ok=False)
        for source in (prior/game/'shared_api').glob('*.response.json'):shutil.copy2(source,cache/source.name)
        seed=json.loads((old/game/'initial_receipt.json').read_text())['hash_seed']
        with (root/f'{game}_selective_full.log').open('w') as log:
            proc=subprocess.Popen([python,'-m','scar_public.experiments.sentry_persistent_trial','--root',str(target),
                '--old',str(old/game),'--mode','selective','--key',key],cwd=code,env=dict(env,PYTHONHASHSEED=seed),
                stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
        jobs.append(dict(game=game,phase='full',pid=proc.pid))
(root/('full_jobs.json' if a.full else 'jobs.json')).write_text(json.dumps(jobs,indent=2))
print(json.dumps(jobs))
