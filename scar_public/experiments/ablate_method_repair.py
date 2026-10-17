"""Selected exact-checkpoint gate ablations with a shared continuation executor.

No LLM calls. This isolates resource loss before identical capacity restoration;
it does not pretend the deliberately fixed continuation is a free LLM baseline.
"""
import argparse,json
from pathlib import Path
from time import perf_counter
from scar.environment import AGENT_ID,restore
from scar_public.method_repair import MethodMemory,MethodController
from scar_public.experiments.replay_real_reuse import execute

def run(run,out,mode):
    out.mkdir(parents=True,exist_ok=False);cp=run/'checkpoints/0093'
    env=restore(cp/'environment.pkl',out);m=MethodMemory();m.load(json.loads((cp/'agent.json').read_text()))
    c=MethodController(m);c.context_scope='attributes';text=env.obs[AGENT_ID]['text']
    source=json.loads((run/'trace/0094.json').read_text());proposal=json.loads(source['response'])
    m.prompt(text);c.resume(text);c.prepare_decision(text,93)
    review=c.review_proposal({**proposal,'action':proposal['guarded_evidence_review']['action']},text)
    c.record_rejection(review,93);report=c.assess_switch(proposal)
    reject={'none':False,'goal':report['task_support']['status']=='UNKNOWN',
            'resource':report['resource']['status']!='MATERIAL_OPTION_PRESERVED','joint':report['block']}[mode]
    task=review['original_task'];target=review['action'].split()[-1]
    oldrows=[json.loads(p.read_text()) for p in sorted((run/'trace').glob('*.json')) if int(p.stem)>=94]
    old_completion=next((r['step'] for r in oldrows if 'Stage completed: '+task in r['next_observation']),None)
    result=dict(mode=mode,gate_rejects=reject,review=report,baseline_completion_step=old_completion,
                baseline_actions=old_completion-93 if old_completion else None,trace=[],api_requests=0)
    start=perf_counter()
    for step in range(93,129):
        if step>93:
            m.prompt(text);c.resume(text);c.prepare_decision(text,step)
            if task in m.model.completed:break
        if step==93 and not reject:parsed=proposal
        else:
            parsed=c.enabling_action(text,step)
            if not parsed:
                plan=m.model.acquisition(target)
                if not plan.get('plan'):result['stop_reason']=plan;break
                parsed=dict(action=plan['plan'][0],decision_source='shared_observed_dependency_executor',frame=m.frame)
        c.after_decision(parsed,text,step);m.update(parsed,text,step)
        text,done=execute(env,parsed['action'])
        result['trace'].append(dict(step=step+1,action=parsed['action'],feedback=text,scores=json.loads(json.dumps(env.scores))))
        if done:break
    result.update(actions=len(result['trace']),wall_seconds=perf_counter()-start,
        public_task_completed=any('Stage completed: '+task in r['feedback'] for r in result['trace']),
        final_scores=json.loads(json.dumps(env.scores)))
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('old',type=Path);p.add_argument('out',type=Path);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False)
    runpath=a.old/'runtime/attributes_structured/evidence_repair_v11/metropolis'
    rows=[run(runpath,a.out/mode,mode) for mode in ('none','goal','resource','joint')]
    payload=dict(scope='Development checkpoint, common programmatic continuation, no LLM calls or edited resources',rows=rows)
    (a.out/'result.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2))
    print(json.dumps([{k:r[k] for k in ('mode','gate_rejects','actions','public_task_completed','wall_seconds')} for r in rows]))

if __name__=='__main__':main()
