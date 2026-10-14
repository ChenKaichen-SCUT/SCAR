"""Evidence-first case inventory; retain every positive and negative index."""
from agents.agc.state import extract
from .common import *

def main():
    offline();rr=rows(RESULTS/'reflection_audit.jsonl.gz')
    selected={};indexes={}
    tests={
        'rejection_avoided':lambda x:x['final_applied'] and x['rejected_to_accepted'],
        'rejection_introduced':lambda x:x['final_applied'] and x['accepted_to_rejected'],
        'visibility_loss_avoided':lambda x:x['final_applied'] and x['avoided_visibility_loss'],
        'visibility_loss_introduced':lambda x:x['final_applied'] and x['introduced_visibility_loss'],
        'accepted_candidate_changed_to_wait':lambda x:x['final_applied'] and x['accepted_candidate_to_wait'],
        'warning_kept':lambda x:x['final_applied'] and x['warning'] and not x['changed'],
        'low_risk_candidate_rejected':lambda x:bool(x['prediction'] and x['prediction']['goal_risk']=='low' and x['candidate_native'] and not x['candidate_native']['accepted']),
        'warning_change_quest_gain':lambda x:bool(x['final_applied'] and x['warning'] and x['changed'] and x['actual_quest_gain']),
        'terminal_reflection':lambda x:x['terminal'],
    }
    trajectories={seed:rows(RESULTS/'runs'/ident(seed)/'trajectory.jsonl.gz') for seed in SEEDS}
    for name,predicate in tests.items():
        matches=[x for x in rr if predicate(x)]
        indexes[name]=[dict(seed=x['seed'],step=x['step'],index=x['index']) for x in matches]
        # One first chronological example per seed; all qualifying indexes retained.
        chosen=[next(x for x in matches if x['seed']==seed) for seed in SEEDS if any(x['seed']==seed for x in matches)]
        selected[name]=[]
        for x in chosen:
            n=x['step'];source=trajectories[x['seed']]
            selected[name].append(dict(reflection=x,window=[dict(step=r['step'],action=r['action'],observation=r['observation'],feedback=r['feedback'],reward=r['reward']) for r in source[max(0,n-3):n+2]]))
    branch=[]
    for seed in SEEDS:
        a=rows(baseline(seed)/'trajectory.jsonl.gz');b=trajectories[seed]
        div=next((i for i,(x,y) in enumerate(zip(a,b)) if x['action']!=y['action']),None)
        branch.append(dict(seed=seed,first_action_divergence=div+1 if div is not None else None,
            baseline=None if div is None else a[div],saer=None if div is None else b[div],
            saer_main_events=[r for r in b if r['reward']['quest']],
            saer_first_rejection=next((r for r in b if extract(r['feedback'])['failed'] or r['feedback']['text'].find('Failed to')>=0),None)))
    write(RESULTS/'case_review.json',dict(all_qualifying_indexes=indexes,representative_rule='First chronological qualifying case; all qualifying indexes retained.',
        online_examples=selected,paired_first_divergence=branch,new_model_calls=0))
    print(json.dumps({k:len(v) for k,v in indexes.items()}),flush=True)

if __name__=='__main__':main()
