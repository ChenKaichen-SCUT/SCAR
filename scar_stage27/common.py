from pathlib import Path
from scar_stage24.common import read,write,sha,rows,gzwrite,offline,ROOT,ENGINE,ENGINE_COMMIT,MODEL,AGENT_ID

RESULTS=ROOT/'results/stage27'
REPORTS=ROOT/'reports/stage27'
RUNTIME=Path('/mnt/Space0/scar_dependencies/stage27_runtime')
PARENT=ROOT/'results/stage25/runs/remnant__s42__AGC-v2'

UNDERSTANDING_SYSTEM='''You are auditing a saved text-game failure, not playing the game.
Use only the supplied public observation, history and feedback. Do not invent recipes,
quantities, object properties or hidden quest conditions. Distinguish established facts
from uncertainty. Return one JSON object with exactly these four string fields:
"failure_reason": why the attempted action failed;
"missing_preconditions": the necessary condition(s) established by this feedback, and what remains unknown;
"next_priority": what information or resource should be obtained first to recover;
"goal_validity": whether the current goal remains supported, needs a changed subgoal, or cannot be judged.
Be concise. An action can fail without invalidating its larger goal.'''

GROUNDING_HEADER='''\n\nOffline diagnostic supplement: public state compiled from this trajectory's past observations only.
Historical facts may be stale; quotes do not establish that a condition still holds.
Null/unknown means not established, not absent. This supplement supplies no action recommendation.
Keep the original JSON output schema.\n'''

def check_freeze(only_diagnostic=False):
    f=read(RESULTS/'freeze.json')
    for n,h in f['files'].items():
        if not only_diagnostic or n.startswith('scar_stage27/') or n=='results/stage27/failure_database.jsonl.gz':
            assert sha(ROOT/n)==h,n
    if not only_diagnostic:
        for n,h in f['engine_files'].items():assert sha(ENGINE/n)==h,n
    return dict(project_files=len(f['files']),engine_files=len(f['engine_files']))

def samples():return rows(RESULTS/'failure_database.jsonl.gz')
