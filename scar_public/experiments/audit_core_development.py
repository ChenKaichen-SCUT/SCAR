"""Public-only packet applicability on old V16 trajectories, no provider calls."""
import json
from pathlib import Path
from scar_public.core_planner import CorePlannerAgent

root=Path('/root/scar_task_progress_20261017/corrected')
rows=[]
for game in ('remnant','mark','metropolis'):
    run=root/game/'observe'
    for step in (25,50,75,100,125,150,175,200,225,250,275):
        agent=CorePlannerAgent(None,'Return JSON.')
        agent.notebook.load(json.loads((run/'checkpoints'/f'{step:04d}'/'agent.json').read_text()))
        row=json.loads((run/'trace'/f'{step+1:04d}.json').read_text())
        text=row['observation'];agent.notebook.prompt(text);agent.controller.prepare_decision(text,step)
        packet,ms=agent.decision_packet(json.loads(row['response']),text,step)
        rows.append(dict(game=game,step=step,action=row['action'],focus=packet['focus'],
            candidates=len(packet['candidates']),recommendation=packet['recommendation'],rejected=packet['rejected'],ms=ms))
print(json.dumps(rows,indent=2))
