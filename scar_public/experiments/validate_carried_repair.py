"""Post-hoc real-engine local policy check; all actions charged, no LLM calls.

Choose the first chronological grounded gavel context with a carried container
from the recorded follow-up. Do not choose on rollout success or alter resources.
"""
import argparse
from dataclasses import asdict
import json
from pathlib import Path

from scar.environment import AGENT_ID,restore
from scar_public.obligations import ExecutionModel
from scar_public.evidence_repair import scoped_problem
from scar_public.resource_trial import make_trial
from scar_public.resource_competition import ResourceGap
from scar_public.experiments.replay_real_reuse import execute

def main():
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False)
    run=a.root/'runtime/attributes_structured/evidence_repair_v11/metropolis'
    manifest=json.loads((run/'manifest.json').read_text());fork=Path(manifest['diagnostic_fork']['path'])
    # Reconstruct only public prefix history, then advance chronologically.
    from scar_public.resource_agent import EvidenceDecisionMemory
    memory=EvidenceDecisionMemory();memory.load(json.loads((fork/'agent.json').read_text()))
    model=memory.model;previous=memory.last_action;admissions=[];selected=None
    for path in sorted((run/'trace').glob('*.json')):
        row=json.loads(path.read_text());model.observe(row['observation'],previous);previous=row['action']
        try:
            problem=scoped_problem(model,row['observation'],'gavel_club','attributes')
            if not problem.source.get('fixed_carried_container'):continue
            report,session=make_trial(model,row['observation'],'gavel_club',problem=problem,
                horizon=6,require_profile_nondegradation=True)
            admissions.append(dict(step=row['step'],report=report))
            # First verified local policy, without conditioning on real outcome.
            if session:
                selected=(row,problem,report,session);break
        except ResourceGap as error:
            admissions.append(dict(step=row['step'],gap=str(error)))
            if str(error)=='attached container contents stale; inspect before planning':
                state=model.current
                bags=[name for name,b in model.containers.items() if state.get('holding',{}).get(name) and b.get('uncertain_after_craft')]
                if len(bags)==1:
                    selected=(row,None,None,None);inspection='inspect '+bags[0];break
    result=dict(scope='Selected local real-engine mechanism check, not an independent full-game result',
        api_calls=0,admissions=admissions,trace=[],selected=bool(selected))
    if selected:
        row,problem,report,session=selected;prior=row['step']-1
        cp=fork if prior==manifest['diagnostic_fork']['start_step'] else run/'checkpoints'/f'{prior:04d}'
        env=restore(cp/'environment.pkl',a.output);assert env.obs[AGENT_ID]['text']==row['observation']
        initial_scores=json.loads(json.dumps(env.scores))
        if session is None:
            text,done=execute(env,inspection);model.observe(text,inspection)
            result['trace'].append(dict(action=inspection,feedback=text,event={'status':'PAID_GROUNDING_OBSERVATION'}))
            try:
                problem=scoped_problem(model,text,'gavel_club','attributes')
                report,session=make_trial(model,text,'gavel_club',problem=problem,horizon=5,
                    require_profile_nondegradation=True)
            except ResourceGap as error:
                report={'status':'GROUNDING_UNKNOWN','reason':str(error)}
        result.update(step=row['step'],problem=asdict(problem) if problem else None,certificate=report,
            initial_scores=initial_scores)
        while session and session.action() and len(result['trace'])<6:
            action=session.action();text,done=execute(env,action);event=session.observe(text)
            result['trace'].append(dict(action=action,feedback=text,event=event))
            if done:break
        result.update(outcome=session.summary() if session else {'status':'NO_VERIFIED_CONTINUATION'},
            final_scores=env.scores,actions=len(result['trace']))
    (a.output/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k not in ('admissions','trace','problem','certificate')}))

if __name__=='__main__':main()
