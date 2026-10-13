import tempfile,contextlib,io
from pathlib import Path
from unittest.mock import patch
from scar_stage17.preflight import MockProvider
from scar_stage17.environment import create_initial
from scar_stage17.build import graph
from scar.environment import state_digest,AGENT_ID
from scar.io import digest
from scar_stage17.common import write,gzip_rows,load,RESULTS
from scar_stage17 import run,analyze,replay
class Offline(MockProvider):
 def __init__(self,*a,**k):super().__init__()
 def begin_step(self,s):pass
result=[]
with tempfile.TemporaryDirectory() as d:
 root=Path(d);output=root/'results';output.mkdir()
 e,h=create_initial('robot_kingdom',171903,root/'init')
 t=dict(task_id='preflight-old-bandage',game_name='robot_kingdom',target_item='bandage_roll',target_amount=1,initial_seed=171903,initial_state_hash=state_digest(e),initial_public_history_hash=digest(h),objective_text='Craft and obtain 1 bandage_roll within 100 actions.',dependency_depth=1,family='old-dev-bandage')
 gzip_rows(output/'initial_public_histories.jsonl.gz',[dict(task_id=t['task_id'],history=h,observation=e.obs[AGENT_ID])])
 write(output/'tasks.json',[t]);write(output/'evaluator_truth.json',{t['task_id']:dict(recipes=graph(e,'obj_cloth_roll')[0])})
 with patch.object(run,'RESULTS',output),patch.object(run,'SharedDeepSeekProvider',Offline):
  for m in ['A0','A1','A2','A3','A4']:
   with contextlib.redirect_stdout(io.StringIO()):row=run.execute(t,m,root/'runtime',None)
   assert row['status'] in ('success','step_limit','game_failure'),row
   with patch.object(replay,'RESULTS',output):r=replay.replay_one(t,m,root/('replay-'+m))
   result.append(dict(method=m,status=row['status'],steps=row['steps'],replay=r['passed']))
 class Interrupt(Offline):
  def begin_step(self,step):
   if step==4:raise SystemExit('synthetic process interruption')
 with patch.object(run,'RESULTS',output),patch.object(run,'SharedDeepSeekProvider',Interrupt):
  import shutil
  saved=load(output/'runs'/f"{t['task_id']}__A2"/'summary.json')
  shutil.rmtree(output/'runs'/f"{t['task_id']}__A2")
  try:run.execute(t,'A2',root/'recovery_runtime',None)
  except SystemExit:pass
 with patch.object(run,'RESULTS',output),patch.object(run,'SharedDeepSeekProvider',Offline):
  recovered=run.execute(t,'A2',root/'recovery_runtime',None)
 assert recovered['final_state_hash']==saved['final_state_hash'] and recovered['steps']==saved['steps']
 with patch.object(analyze,'RESULTS',output),patch.object(analyze,'ROOT',root):analyze.main()
 assert load(output/'analysis.json')['complete']
 write(RESULTS/'pipeline_acceptance.json',dict(passed=True,runs=result,analysis=True,interrupted_run_recovery_identical=True,formal_runs=0,api_calls=0))
