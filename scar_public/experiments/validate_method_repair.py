"""Selected frozen-proposal real-engine check; no new LLM or oracle action."""
import argparse,json
from pathlib import Path
from time import perf_counter
from scar.environment import AGENT_ID,restore
from scar_public.method_repair import MethodMemory,MethodController
from scar_public.experiments.replay_real_reuse import execute

def main():
    p=argparse.ArgumentParser();p.add_argument('old',type=Path);p.add_argument('out',type=Path);a=p.parse_args()
    run=a.old/'runtime/attributes_structured/evidence_repair_v11/metropolis'
    checkpoint=run/'checkpoints/0093';a.out.mkdir(parents=True,exist_ok=False)
    env=restore(checkpoint/'environment.pkl',a.out)
    memory=MethodMemory();memory.load(json.loads((checkpoint/'agent.json').read_text()))
    c=MethodController(memory);c.context_scope='attributes'
    original=json.loads((run/'trace/0094.json').read_text());proposal=json.loads(original['response'])
    text=env.obs[AGENT_ID]['text'];assert text==original['observation']
    memory.prompt(text);c.resume(text);c.prepare_decision(text,93)
    failed={**proposal,'action':proposal['guarded_evidence_review']['action']}
    review=c.review_proposal(failed,text);assert review
    c.record_rejection(review,93)
    assessment=c.assess_switch(proposal);assert assessment['block']
    baseline_rows=[json.loads(p.read_text()) for p in sorted((run/'trace').glob('*.json')) if int(p.stem)>=94]
    completion=next((r['step'] for r in baseline_rows if 'Stage completed: '+review['original_task'] in r['next_observation']),None)
    report=dict(scope='Selected failure repair; frozen LLM proposal, programmatic continuation, not held-out evaluation',
        checkpoint=str(checkpoint),api_requests=0,original_action=original['action'],review=assessment,
        baseline_completion_step=completion,baseline_actions=completion-93 if completion else None,
        trace=[],initial_scores=json.loads(json.dumps(env.scores)),
        task=review['original_task'])
    def no_llm(*args):raise RuntimeError('No new language call allowed in frozen-proposal check')
    parsed=c.finalize_decision(proposal,text,93,no_llm,'')
    start=perf_counter()
    for step in range(93,129):
        if step>93:
            memory.prompt(text);c.resume(text);c.prepare_decision(text,step)
            if report['task'] in memory.model.completed:break
            parsed=c.method_condition_step(text,step)
            if not parsed:
                plan=memory.model.acquisition(review['action'].split()[-1])
                if not plan.get('plan'):
                    report['stop_reason']=plan;break
                parsed=dict(action=plan['plan'][0],decision_source='observed_dependency_plan',frame=memory.frame)
        c.after_decision(parsed,text,step);memory.update(parsed,text,step)
        text,done=execute(env,parsed['action'])
        report['trace'].append(dict(step=step+1,action=parsed['action'],decision_source=parsed.get('decision_source'),
            feedback=text,scores=json.loads(json.dumps(env.scores))))
        if done:break
    report.update(actions=len(report['trace']),wall_seconds=perf_counter()-start,
        public_task_completed=any('Stage completed: '+report['task'] in r['feedback'] for r in report['trace']),
        final_scores=json.loads(json.dumps(env.scores)))
    (a.out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k not in ('trace','review','stop_reason')}))

if __name__=='__main__':main()
