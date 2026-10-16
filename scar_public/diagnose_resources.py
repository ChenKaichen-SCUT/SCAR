"""Fixed-prefix diagnostics; optional isolated real environment continuation.

The controller receives public text ONLY. The evaluator restores a trusted local
checkpoint after planning; no engine rules, score, or hidden state reach it.
"""
import argparse
import contextlib
import hashlib
import json
from pathlib import Path
import sys
from time import monotonic

from scar_public.obligations import ExecutionModel
from scar_public.resource_competition import ResourceGap
from scar_public.resource_trial import make_trial

CASES = (('mark',36,'oak_rod'),('metropolis',86,'gavel_club'),('remnant',174,'lockpick'))


def run(public_root, output, runtime=None):
    result = {'scope':'selected diagnostic checkpoints, not full-game evaluation', 'api_calls':0,
              'new_random_seeds':False,'baseline_reruns':0,'cases':[]}
    output = Path(output); output.mkdir(parents=True,exist_ok=False)
    for game,step,target in CASES:
        rows = json.loads((Path(public_root)/(game+'.public.json')).read_text(encoding='utf8'))
        # Slice BEFORE grounding. No later action/observation is passed to planner.
        prefix = [{'observation':r['observation'],'previous_action':rows[i-1]['action'] if i else None}
                  for i,r in enumerate(rows[:step])]
        model = ExecutionModel()
        for r in prefix: model.observe(r['observation'],r['previous_action'])
        text = prefix[-1]['observation']; start = monotonic()
        case = {'game':game,'next_step':step,'target':target,'horizon':6,
                'prefix_sha256':hashlib.sha256(json.dumps(prefix,sort_keys=True).encode()).hexdigest()}
        try:
            report,session = make_trial(model,text,target,horizon=6)
            case['selection'] = report
            case['planning_seconds'] = round(monotonic()-start,3)
            if session and runtime:
                # Import evaluator only here; this is never a model input.
                from scar.environment import restore, AGENT_ID
                cp = Path(runtime)/'round7/obligation_v6'/game/'checkpoints'/f'{step-1:04d}'/'environment.pkl'
                case['checkpoint_sha256'] = hashlib.sha256(cp.read_bytes()).hexdigest()
                run_dir = output/game; run_dir.mkdir()
                env = restore(cp,run_dir)
                assert env.obs[AGENT_ID]['text'] == text, 'public prefix/checkpoint mismatch'
                case['real_trace'] = []
                while action := session.action():
                    before = env.obs[AGENT_ID]['text']
                    with contextlib.redirect_stdout(sys.stderr):
                        obs,reward,done,info = env.step({AGENT_ID:action})
                        env.update_scores(reward)
                    after = obs[AGENT_ID]['text']
                    feedback = session.observe(after)
                    case['real_trace'].append({'action':action,'observation':before,'next_observation':after,
                                               'feedback':feedback,'environment_done':done})
                    if done: break
                case['execution'] = session.summary()
            elif session:
                case['execution'] = {'status':'PLANNED_ONLY','first_action':session.action()}
        except ResourceGap as error:
            case['status'] = 'GROUNDING_UNKNOWN'; case['reason'] = str(error)
        result['cases'].append(case)
        (output/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
        print(json.dumps({'game':game,'selection':case.get('selection',{}).get('status',case.get('status')),
              'execution':case.get('execution',{}).get('status'),'seconds':case.get('planning_seconds')},ensure_ascii=False),flush=True)
    return result


if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('--public-root',required=True)
    p.add_argument('--output',required=True); p.add_argument('--runtime')
    args=p.parse_args(); run(args.public_root,args.output,args.runtime)
