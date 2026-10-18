import json,os,subprocess
from pathlib import Path
root=Path('/root/scar_plan_20261018');base=Path('/root/scar_research_20261015');old=Path('/root/scar_core_valid_20261017');code=root/'frozen'
for name,world in [('failed_source','mark_r1'),('positive_source','mark_r0')]:
    seed=json.loads((old/'evaluation'/world/'manifest.json').read_text())['hash_seed']
    env=dict(os.environ,PYTHONPATH=f'{old}/deps:{code}:{old}/Sentry:{base}/source/AgentOdyssey:{base}/causal_adapter_20261016/deps',
        AGENTODYSSEY_ROOT=str(base/'source/AgentOdyssey'),PYTHONHASHSEED=seed,OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
    with (root/(name+'.log')).open('w') as log:
        proc=subprocess.Popen([str(base/'venv/bin/python'),'/root/plan_probe.py',name],cwd=code,env=env,stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
    print(json.dumps(dict(name=name,pid=proc.pid)))
