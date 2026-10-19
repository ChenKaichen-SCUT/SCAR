import hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
R=Path('/root/agentodyssey-benchmark-20261018');repo=R/'agentodyssey'
assert json.loads((R/'feedback_v3r2_verified_status.json').read_text())['all_processes_stopped']
for n in ['feedback_v3r3_agent.py','feedback_v3r3_core.py']:
    shutil.copyfile(R/n,repo/'agents'/n)
env=os.environ.copy();env.update({'PYTHONPATH':str(repo)+':'+str(R),'AO_MAX_STEPS':'300','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1'})
checks=[]
for args in [['-m','unittest','-v','test_feedback_v3r3','test_feedback_v3r3_agent'],[str(R/'verify_v3r3_launch_remote.py')]]:
    result=subprocess.run([str(R/'.venv/bin/python')]+args,cwd=R,env=env,capture_output=True,text=True,timeout=180)
    checks.append({'command':args,'returncode':result.returncode,'output_tail':(result.stdout+result.stderr)[-11000:]})
    print(json.dumps(checks[-1]))
    if result.returncode:
        (R/'feedback_v3r3_preflight.json').write_text(json.dumps({'passed':False,'checks':checks},indent=2));raise SystemExit(1)
receipt={'passed':True,'provider_calls':0,'checks':checks,'source_sha256':{n:hashlib.sha256((R/n).read_bytes()).hexdigest() for n in ['feedback_v3r3_agent.py','feedback_v3r3_core.py','test_feedback_v3r3.py','test_feedback_v3r3_agent.py','eval_feedback_v3r3.py','run_feedback_v3r3.py']}}
(R/'feedback_v3r3_preflight.json').write_text(json.dumps(receipt,indent=2));print('PREFLIGHT PASSED')
