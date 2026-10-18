import json,os,subprocess,tarfile
from pathlib import Path
root=Path('/root/scar_effect_v3_20261018');base=Path('/root/scar_research_20261015');old=Path('/root/scar_core_valid_20261017');code=root/'frozen'
if not code.exists():
    code.mkdir(parents=True)
    with tarfile.open('/root/effect_v3_source.tgz') as tar:tar.extractall(code,filter='data')
jobs=[]
for name,world in [('mark_r0','mark_r0'),('mark_r1','mark_r1'),('route_value','metropolis_r1'),('failed_source','mark_r1'),('positive_source','mark_r0')]:
    assert not (root/(name+'.log')).exists()
    seed=json.loads((old/'evaluation'/world/'manifest.json').read_text())['hash_seed']
    env=dict(os.environ,PYTHONPATH=f'{old}/deps:{code}:{old}/Sentry:{base}/source/AgentOdyssey:{base}/causal_adapter_20261016/deps',
        AGENTODYSSEY_ROOT=str(base/'source/AgentOdyssey'),PYTHONHASHSEED=seed,OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
    with (root/(name+'.log')).open('w') as log:
        proc=subprocess.Popen([str(base/'venv/bin/python'),'/root/effect_probe_v3.py',name],cwd=code,env=env,stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
    jobs.append(dict(name=name,pid=proc.pid))
(root/'probe_jobs.json').write_text(json.dumps(jobs,indent=2));print(json.dumps(jobs))
