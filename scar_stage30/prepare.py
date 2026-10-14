"""Freeze public-failure-only goal hierarchies before any new responses."""
from .common import *

SUBGOALS={
 'missing_lockpick_tool':['The availability of a lockpick tool is known from public evidence.'],
 'missing_writing_tool':['The availability of a writing tool is known from public evidence.'],
 'missing_workbench':['The accessibility of a workbench is known from public evidence.'],
 'missing_furnace':['The accessibility of a furnace is known from public evidence.'],
 'hand_capacity':['The available hand space and held objects are established from public evidence.'],
 'container_capacity':['The available space and contents of the affected container are established from public evidence.'],
 'insufficient_ingredients':['The required ingredients and quantities are known from public evidence.',
                            'The availability of those publicly known ingredients is established.'],
}

def main():
    offline();out=[]
    assert not (RESULTS/'freeze.json').exists()
    for ident,s in selected().items():
        meta=read(CHECKPOINTS/ident/'meta.json')
        assert s['failure_reason'] in s['post_failure_observation']['text']
        nodes=[dict(level=0,goal=s['current_goal']),dict(level=1,goal=CASES[ident])]
        nodes.extend(dict(level=2,goal=g) for g in SUBGOALS[s['failure_type']])
        stack=dict(goal_stack=nodes)
        addition='\n\nCurrent goal hierarchy:\n'+json.dumps(stack,ensure_ascii=False,indent=2)+'\n'
        d=dict(meta,baseline_suffix=meta['suffix'],suffix=addition,goal_stack=stack,
               source_checkpoint=str((CHECKPOINTS/ident).relative_to(ROOT)),
               injection='first_decision_including_native_retries_only',
               level0_scope='checkpoint original agent objective; not a substituted whole-game quest',
               knowledge_source=dict(step=s['step'],public_quote=s['failure_reason'],source=s['source_trajectory'],line=s['source_line']),
               oracle_boundary='Only epistemic subconditions of the already disclosed failure. No ingredient names/quantities, locations, recipes, acquisition paths, action sequence, hidden data, or post-checkpoint information added.',
               hierarchy_status='publicly justified partial hierarchy; unknown dependencies remain unknown, not an omniscient complete plan')
        write(RESULTS/'checkpoints'/ident/'meta.json',d)
        out.append(dict(id=ident,failure_step=s['step'],remaining=meta['remaining'],type=s['failure_type'],goal_stack=stack,
                        meta_sha256=sha(RESULTS/'checkpoints'/ident/'meta.json'),
                        checkpoint_files={p.name:sha(p) for p in (CHECKPOINTS/ident).iterdir() if p.is_file()},
                        baseline=str((ROOT/f'results/stage28/runs/{ident}/OracleRecovery').relative_to(ROOT))))
    write(RESULTS/'checkpoint_manifest.json',dict(passed=True,cases=out,independent_parent_episodes=1,
            total_maximum_new_actions=sum(x['remaining'] for x in out),new_model_calls=0))
    print(json.dumps(dict(cases=len(out),new_model_calls=0)))

if __name__=='__main__':main()
