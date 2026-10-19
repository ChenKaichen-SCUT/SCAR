import hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
R=Path('/root/agentodyssey-benchmark-20261018');repo=R/'agentodyssey'
assert json.loads((R/'feedback_v3r6_300_status.json').read_text())['all_processes_stopped']
for n in ['feedback_v3r7_agent.py','feedback_v3r7_core.py']:
    shutil.copyfile(R/n,repo/'agents'/n)
assert (R/'feedback_v3r5_core.py').read_bytes()==(repo/'agents/feedback_v3r5_core.py').read_bytes()
env=os.environ.copy();env.update({'PYTHONPATH':str(repo)+':'+str(R),'AO_MAX_STEPS':'300','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1'})
checks=[]
for args in [[str(R/'test_feedback_v3r7.py')],['-m','unittest','-v','test_feedback_v3r7_agent'],[str(R/'verify_v3r7_launch_remote.py')],[str(R/'test_v3r7_public_path_remote.py')],[str(R/'replay_v3r7_remote.py')]]:
    result=subprocess.run([str(R/'.venv/bin/python')]+args,cwd=R,env=env,capture_output=True,text=True,timeout=180)
    checks.append({'command':args,'returncode':result.returncode,'output_tail':(result.stdout+result.stderr)[-12000:]})
    print(json.dumps({'command':args,'returncode':result.returncode}),flush=True)
    if result.returncode:
        (R/'feedback_v3r7_preflight.json').write_text(json.dumps({'passed':False,'checks':checks},indent=2));print(checks[-1]['output_tail']);raise SystemExit(1)
names=['feedback_v3r7_agent.py','feedback_v3r7_core.py','feedback_v3r5_core.py','test_feedback_v3r7.py','test_feedback_v3r7_agent.py','eval_feedback_v3r7.py','run_feedback_v3r7.py','test_v3r7_public_path_remote.py','analyze_v3r7_remote.py','replay_v3r7_remote.py']
receipt={'passed':True,'provider_calls':0,'checks':checks,'source_sha256':{n:hashlib.sha256((R/n).read_bytes()).hexdigest() for n in names}}
(R/'feedback_v3r7_preflight.json').write_text(json.dumps(receipt,indent=2));print('PREFLIGHT PASSED')
