"""Native selected-prefix check of the automatic compiler, zero language calls."""
import argparse,json
from pathlib import Path
from scar.environment import AGENT_ID,restore
from scar_public.action_repair import ActionMemory,ActionController
from scar_public.experiments.replay_real_reuse import execute

def main():
    p=argparse.ArgumentParser();p.add_argument('old',type=Path);p.add_argument('out',type=Path);a=p.parse_args()
    run=a.old/'runtime/attributes_structured/evidence_repair_v11/metropolis';cp=run/'checkpoints/0093'
    a.out.mkdir(parents=True,exist_ok=False);env=restore(cp/'environment.pkl',a.out)
    m=ActionMemory();m.load(json.loads((cp/'agent.json').read_text()));c=ActionController(m);c.context_scope='attributes'
    original=json.loads((run/'trace/0094.json').read_text());parsed=json.loads(original['response'])
    text=env.obs[AGENT_ID]['text'];assert text==original['observation']
    m.prompt(text);c.resume(text);c.prepare_decision(text,93)
    review=c.review_proposal({**parsed,'action':parsed['guarded_evidence_review']['action']},text)
    assert review;c.record_rejection(review,93)
    choice=c.certified_repair(review,text,93)
    result=dict(scope='Previously inspected debugging checkpoint; no API or hidden policy inputs',review=review,trace=[],api_calls=0)
    for step in range(93,117):
        if step>93:
            m.prompt(text);c.resume(text);c.prepare_decision(text,step)
            if review['original_task'] in m.model.completed:break
            choice=c.method_condition_step(text,step)
        if not choice:break
        c.after_decision(choice,text,step);m.update(choice,text,step)
        text,done=execute(env,choice['action'])
        result['trace'].append(dict(step=step+1,action=choice['action'],certificate=choice.get('action_certificate'),
            observation=text,scores=json.loads(json.dumps(env.scores))))
        if done:break
    result.update(actions=len(result['trace']),public_task_completed=('Stage completed: '+review['original_task']) in text,
        compilations=m.action_compilations,events=m.action_events,outcomes=m.action_outcomes)
    (a.out/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k in ('scope','actions','public_task_completed','api_calls','outcomes')}))

if __name__=='__main__':main()
