import hashlib,json,os,shutil,subprocess,tempfile
from pathlib import Path
R=Path('/root/agentodyssey-benchmark-20261018');repo=R/'agentodyssey';py=str(R/'.venv/bin/python')
receipt=R/'feedback_v3r_preflight.json';assert not (R/'feedback_v3r_protocol.json').exists(),'Policy frozen after launch'
protected={n:hashlib.sha256((R/n).read_bytes()).hexdigest() for n in ['agentodyssey/agents/feedback_v3_core.py','agentodyssey/agents/feedback_v3_agent.py','agentodyssey/agents/feedback_v2_core.py','agentodyssey/eval.py','v5_full500_budget.sqlite']}
for n in ['feedback_v3r_core.py','feedback_v3r_agent.py']:
    compile((R/n).read_text(),n,'exec');shutil.copy2(R/n,repo/'agents'/n)
env=os.environ.copy();env['PYTHONPATH']=str(repo)+':'+str(R)
tests=[]
for name in ['test_feedback_v3r.py','test_feedback_v3r_agent.py']:
    r=subprocess.run([py,str(R/name)],cwd=R,env=env,capture_output=True,text=True,timeout=120)
    tests.append({'name':name,'passed':r.returncode==0,'diagnostics':r.stdout+r.stderr})
    assert r.returncode==0,(name,r.stdout,r.stderr)
# Reconstruct the old public Remnant actions without a model: diagnostic tests,
# not a claim that the new policy would select those actions or improve its score.
import sys;sys.path.insert(0,str(R));from feedback_v3r_core import Ledger
log=[json.loads(line) for line in (R/'runs/remnant__feedback_v3/agent_adam_davis/agent_log.jsonl').read_text().splitlines()]
s=Ledger();zero_limits=[];deaths=0
for row in log:
    s.advance(row['observation']['text'])
    if s.hand_limit and s.hand_limit.get('count',0)<=0:zero_limits.append(s.step)
    if 'I revived at the starting point' in row['observation']['text']:
        deaths+=1;assert s.hand_limit is None
    s.choose(row['action'],'historical action for offline diagnostic only')
s.advance(log[-1]['next_observation']['text']);check=s.action_check('enter hall')
assert not zero_limits;assert not check['blockers'],check
trace_test={'actions_replayed':len(log),'zero_capacity_inferences':zero_limits,'death_resets_checked':deaths,'terminal_return_blockers':check['blockers'],'no_provider_calls':True}
smoke=[]
for g in ['remnant','mark','metropolis']:
    with tempfile.TemporaryDirectory(prefix='v3r-evaluator-check-') as tmp:
        tmp=Path(tmp);config=tmp/'agents.json';config.write_text(json.dumps({'agents':[{'agent_type':'LongContextAgent','agent_id':'agent_adam_davis','agent_name':'adam_davis','llm_name':'deepseek-flash','llm_provider':'openai'}]}))
        e=env.copy();e.update({'AO_API_BASE_URL':'http://127.0.0.1:8094/offline/v1','AO_CONTROL_AUDIT':str(tmp/'audit.jsonl'),'AO_CALL_LIMIT':'502','PYTHONHASHSEED':'42','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1'})
        r=subprocess.run([py,str(R/'eval_v3r_offline_smoke.py'),'--agents_config',str(config),'--game_name',g,'--max_steps','2','--seed','42','--run_dir',str(tmp/'run'),'--cumulative_config_save'],cwd=repo,env=e,capture_output=True,text=True,timeout=60)
        assert r.returncode==0,(g,r.stderr[-5000:],r.stdout[-2000:])
        rows=(tmp/'run/agent_adam_davis/agent_log.jsonl').read_text().splitlines();assert len(rows)==2
        smoke.append({'game':g,'real_evaluator_steps':2,'provider_calls':0,'network_tripwire':True,'keyword_save_and_terminal_hook_passed':True})
for n,h in protected.items():assert hashlib.sha256((R/n).read_bytes()).hexdigest()==h,n
result={'all_passed':True,'tests':tests,'frozen_trace_diagnostic':trace_test,'real_evaluator_interface_checks':smoke,'protected_unchanged':protected,
        'source_sha256':{n:hashlib.sha256((R/n).read_bytes()).hexdigest() for n in ['feedback_v3r_core.py','feedback_v3r_agent.py','eval_feedback_v3r.py','api_proxy_v3r.py','run_feedback_v3r.py']}}
receipt.write_text(json.dumps(result,indent=2));print(json.dumps(result))
