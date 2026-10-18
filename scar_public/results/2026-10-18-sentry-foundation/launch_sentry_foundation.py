"""One bounded frozen pilot; fresh worlds, concurrent arms, no baseline reruns."""
import json,os,subprocess,tarfile
from pathlib import Path
root=Path('/root/scar_sentry_foundation_20261018');root.mkdir(exist_ok=False)
code=root/'frozen';code.mkdir()
with tarfile.open('/root/sentry_foundation_source.tgz') as tar:tar.extractall(code,filter='data')
base=Path('/root/scar_research_20261015');old=Path('/root/scar_core_valid_20261017')
python=str(base/'venv/bin/python');key=str(base/'private/deepseek.key')
env=dict(os.environ,PYTHONPATH=f'{old}/deps:{code}:{old}/Sentry:{base}/source/AgentOdyssey:{base}/causal_adapter_20261016/deps',
    AGENTODYSSEY_ROOT=str(base/'source/AgentOdyssey'),OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
jobs=[]
for game in ('remnant','mark','metropolis'):
    block=root/'evaluation'/game;seed=str(int.from_bytes(os.urandom(4),'little'));taskenv=dict(env,PYTHONHASHSEED=seed)
    args=[python,'-m','scar_public.experiments.sentry_foundation_trial','--root',str(block),'--game',game]
    with (root/(game+'_prepare.log')).open('w') as log:
        subprocess.run(args+['--arm','prepare'],cwd=code,env=taskenv,stdout=log,stderr=subprocess.STDOUT,check=True)
    for arm in ('base','sentry','evidence'):
        with (root/(game+'_'+arm+'.log')).open('w') as log:
            proc=subprocess.Popen(args+['--arm',arm,'--key',key],cwd=code,env=taskenv,
                stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
        jobs.append(dict(kind='game',game=game,arm=arm,pid=proc.pid,hash_seed=seed))
for world in ('mark_r1','metropolis_r1'):
    block=old/'evaluation'/world;seed=json.loads((block/'manifest.json').read_text())['hash_seed']
    with (root/(world+'_probe.log')).open('w') as log:
        proc=subprocess.Popen([python,'-m','scar_public.experiments.sentry_history_probe','--block',str(block),
            '--out',str(root/'probes'/world),'--key',key],cwd=code,env=dict(env,PYTHONHASHSEED=seed),
            stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
    jobs.append(dict(kind='probe',world=world,pid=proc.pid))
(root/'jobs.json').write_text(json.dumps(jobs,indent=2));print(json.dumps(jobs))
