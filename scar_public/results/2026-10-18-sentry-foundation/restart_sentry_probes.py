import json,os,subprocess
from pathlib import Path
root=Path('/root/scar_sentry_foundation_20261018');base=Path('/root/scar_research_20261015');old=Path('/root/scar_core_valid_20261017');code=root/'frozen'
env=dict(os.environ,PYTHONPATH=f'{old}/deps:{code}:{old}/Sentry:{base}/source/AgentOdyssey:{base}/causal_adapter_20261016/deps',AGENTODYSSEY_ROOT=str(base/'source/AgentOdyssey'))
jobs=json.loads((root/'jobs.json').read_text())
for job in jobs:
    if job['kind']!='probe':continue
    world=job['world'];block=old/'evaluation'/world;seed=json.loads((block/'manifest.json').read_text())['hash_seed']
    log=root/(world+'_probe.log');log.rename(root/(world+'_probe_original_cache_miss.log'))
    with log.open('w') as f:
        proc=subprocess.Popen([str(base/'venv/bin/python'),'/root/sentry_history_probe_amended.py','--block',str(block),
            '--out',str(root/'probes'/world),'--key',str(base/'private/deepseek.key')],cwd=code,
            env=dict(env,PYTHONHASHSEED=seed),stdout=f,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
    job['original_pid']=job['pid'];job['pid']=proc.pid;job['evaluator_amendment']='temperature JSON0.0 cache identity'
(root/'jobs.json').write_text(json.dumps(jobs,indent=2));print(json.dumps(jobs[-2:]))
