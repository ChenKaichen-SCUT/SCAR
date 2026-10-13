import json, tempfile, contextlib, io
from pathlib import Path
from scar.environment import restore, snapshot
from scar_stage17.environment import create_initial
from scar_stage17.oracle import Witness
from scar_stage17.common import load,write,RESULTS
old=load(RESULTS/'prior_task_inventory.json'); rows=[]
for game in ['robot_kingdom','saltglass','quarantine']:
 with tempfile.TemporaryDirectory() as d,contextlib.redirect_stdout(io.StringIO()):
  e,h=create_initial(game,170031,d); data=snapshot(e)
 prior={x['item'] for x in old if x['game']==game}
 for oid,obj in e.world.objects.items():
  if not obj.craft_ingredients or obj.name in prior:continue
  row={'game':game,'oid':oid,'name':obj.name}
  try:
   with contextlib.redirect_stdout(io.StringIO()):
    trial=restore(data);w=Witness(trial);trace=w.solve(oid)
   if not any(x['action'].startswith('craft ') and x['action'].split()[-1]==obj.name for x in trace):raise ValueError('natural preexisting target; no actual final craft')
   row.update(ok=True,steps=len(trace),actions=[x['action'] for x in trace])
  except Exception as ex:row.update(ok=False,error=str(ex))
  rows.append(row);write(RESULTS/'candidate_sweep.json',rows)
  print(game,obj.name,row.get('steps'),row.get('error'),flush=True)
