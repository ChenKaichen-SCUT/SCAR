"""Launch a frozen six-arm development batch in an independent directory."""
import argparse,json,os,shutil,subprocess,tarfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--continue-full',action='store_true');a=p.parse_args()
root=Path('/root/scar_sentry_persistent_20261018_v2');code=root/'frozen'
if not a.continue_full:
    root.mkdir(exist_ok=False);code.mkdir()
    with tarfile.open('/root/sentry_persistent_source.tgz') as tar:tar.extractall(code,filter='data')
base=Path('/root/scar_research_20261015');deps=Path('/root/scar_core_valid_20261017')
old=Path('/root/scar_sentry_foundation_20261018/evaluation')
python=str(base/'venv/bin/python');key=str(base/'private/deepseek.key')
env=dict(os.environ,PYTHONPATH=f'{deps}/deps:{code}:{deps}/Sentry:{base}/source/AgentOdyssey:{base}/causal_adapter_20261016/deps',
    AGENTODYSSEY_ROOT=str(base/'source/AgentOdyssey'),OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
jobs=[]
for game in ('remnant','mark','metropolis'):
    target=root/'evaluation'/game;cache=target/'shared_api'
    if not a.continue_full:
        cache.mkdir(parents=True)
        for source in (old/game/'shared_api').glob('*.response.json'):shutil.copy2(source,cache/source.name)
    seed=json.loads((old/game/'initial_receipt.json').read_text())['hash_seed']
    for mode in ('advice','execute'):
        args=[python,'-m','scar_public.experiments.sentry_persistent_trial','--root',str(target),
            '--old',str(old/game),'--mode',mode,'--key',key]
        if a.continue_full:assert (target/mode/'probe_result.json').exists()
        else:args+=['--stop-after-repair','12']
        label='full' if a.continue_full else 'probe'
        with (root/f'{game}_{mode}_{label}.log').open('w') as log:
            proc=subprocess.Popen(args,cwd=code,env=dict(env,PYTHONHASHSEED=seed),stdout=log,
                stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
        jobs.append(dict(game=game,mode=mode,phase=label,pid=proc.pid))
(root/('full_jobs.json' if a.continue_full else 'jobs.json')).write_text(json.dumps(jobs,indent=2))
print(json.dumps(jobs))
