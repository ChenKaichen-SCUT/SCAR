"""Replay real grounded queries where max-cost and pathwise tests disagree."""
import argparse
import json
from pathlib import Path
from scar_public.resource_agent import problem_from_data
from scar_public.resource_competition import compile_resources,select_experiment

def main():
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('output',type=Path);a=p.parse_args();cases=[]
    for current in sorted((a.root/'runtime').glob('*/*/*/current.json')):
        status=json.loads(current.read_text());run=current.parent
        agent=json.loads((run/'checkpoints'/status['checkpoint']/'agent.json').read_text())
        manifest=json.loads((run/'manifest.json').read_text())
        for trial in agent.get('resource_trials',[]):
            r=trial.get('selection',{});rejected=[c for c in r.get('candidates',[]) if c['decision']=='REJECT_PROFILE_REGRET']
            if not rejected:continue
            problem=problem_from_data(r['grounding']);allowed=None
            if r.get('persistent_evidence',{}).get('reused') and manifest['evidence_mode']=='structured':
                allowed={problem.target:sorted({tuple(pair) for aliases in r['behaviorally_equivalent_parameter_aliases'].values()
                    for pair in aliases[problem.target]})}
            compiled=compile_resources(problem,horizon=6,max_states=12000,allowed_profiles=allowed)
            older,_,_=select_experiment(compiled,prefix_depth=2,max_prefixes=40,expansion_budget=600,
                mode='preserve_opportunity',require_profile_nondegradation=False)
            newer,_,_=select_experiment(compiled,prefix_depth=2,max_prefixes=40,expansion_budget=600,
                mode='preserve_opportunity',require_profile_nondegradation=True)
            key=lambda x:(x['status'],x.get('prefix'),x.get('first_action'))
            assert key(newer)==key(r)
            cases.append(dict(stage=manifest['stage'],game=manifest['game'],step=trial['step'],
                newly_rejected=rejected,changed_selection=key(older)!=key(newer),
                original=r,gate_off=older,gate_on=newer))
    result=dict(scope='Post-hoc replay of actual grounded queries; no new LLM or game outcomes',
        cases=cases,queries=len(cases),additional_rejected_candidates=sum(len(c['newly_rejected']) for c in cases),
        changed_selected_policies=sum(c['changed_selection'] for c in cases),api_calls=0)
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k!='cases'}))
    for c in cases:print(json.dumps(dict(stage=c['stage'],game=c['game'],step=c['step'],changed=c['changed_selection'],
        contrasts=[dict(prefix=r['prefix'],upper=r['upper'],reference_upper=c['original']['baseline_upper'],
        value=r['profile_value']) for r in c['newly_rejected']])))

if __name__=='__main__':main()
