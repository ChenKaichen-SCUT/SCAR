import json,os,subprocess,sys,tarfile
from pathlib import Path
root=Path('/root/scar_plan_v2_20261018');code=root/'frozen'
if not root.exists():
    code.mkdir(parents=True)
    with tarfile.open('/root/plan_v2_source.tgz') as archive:archive.extractall(code,filter='data')
base=Path('/root/scar_research_20261015');old=Path('/root/scar_core_valid_20261017')
env=dict(os.environ,PYTHONPATH=f'{old}/deps:{code}:{old}/Sentry:{base}/source/AgentOdyssey:{base}/causal_adapter_20261016/deps',
    AGENTODYSSEY_ROOT=str(base/'source/AgentOdyssey'),OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
jobs=json.loads((root/'jobs.json').read_text()) if (root/'jobs.json').exists() else []
for name in sys.argv[1:]:
    assert name in ('mark_r0','mark_r1','metropolis_r1','metropolis_7537')
    assert name not in [j['name'] for j in jobs]
    block=old/'evaluation'/name if name!='metropolis_7537' else Path('/root/scar_compact_independent_20261017/evaluation/metropolis/main')
    hash_seed=json.loads((block/'manifest.json').read_text())['hash_seed']
    with (root/(name+'.log')).open('w') as log:
        process=subprocess.Popen([str(base/'venv/bin/python'),'-m','scar_public.experiments.obstacle_trial',
            '--agent','plan','--reuse-api',f'/root/scar_plan_20261018/evaluation/{name}/api','--reuse-api',f'/root/scar_objective_v2_20261018/evaluation/{name}/api','--reuse-api',f'/root/scar_objective_20261018/evaluation/{name}/api','--reuse-api',f'/root/scar_hypothesis_v2_20261018/evaluation/{name}/api','--reuse-api',f'/root/scar_hypothesis_20261018/evaluation/{name}/api','--block',str(block),'--root',str(root/'evaluation'/name),
            '--key',str(base/'private/deepseek.key')],cwd=code,env=dict(env,PYTHONHASHSEED=hash_seed),
            stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    jobs.append(dict(name=name,block=str(block),pid=process.pid))
(root/'jobs.json').write_text(json.dumps(jobs,indent=2));print(json.dumps(jobs))
