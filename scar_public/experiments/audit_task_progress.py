"""Zero-API public-state audit at the predeclared continuation checkpoints."""
import json
from pathlib import Path
from scar_public.task_progress import ProgressMemory, ProgressController


def main():
    root=Path('/root/scar_task_outcome_20261017/corrected'); result=[]
    for game,step in [('remnant',177),('mark',220),('metropolis',145)]:
        run=root/game/'v15'; m=ProgressMemory(); m.load(json.loads((run/'checkpoints'/f'{step:04d}'/'agent.json').read_text()))
        c=ProgressController(m); c.context_scope='attributes'
        row=json.loads((run/'trace'/f'{step+1:04d}.json').read_text()); m.prompt(row['observation']); c.prepare_decision(row['observation'],step)
        parsed=json.loads(row['response']); choice=c.navigation(row['observation'],step,parsed)
        result.append(dict(game=game,step=step,baseline_action=parsed['action'],tasks=[r['quote'] for r in m.progress_tasks.values()],
                           choice=choice,new_api_requests=0))
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
