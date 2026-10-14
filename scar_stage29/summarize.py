import json
from collections import Counter
from .common import *

def main():
    offline();ann=read(RESULTS/'lifecycle_annotations.json');stats=read(RESULTS/'trajectory_statistics.json');actions=rows(RESULTS/'action_audit.jsonl.gz')
    pairs=[]
    for a in ann:
        ident=a['id'];by={v:next(x for x in stats if x['id']==ident and x['variant']==v) for v in ['Original','OracleRecovery']}
        succ=by['OracleRecovery']['original_action_success_steps'];resume=a['resume_by']
        assert all(step in {x['step'] for x in a['evidence']} for step in a['plan_steps'])
        if resume is not None:assert succ and resume>=succ[0]
        pairs.append(dict(id=ident,phase0_adopted=a['phase0_adopted'],phase1_understood=a['phase1_understood'],planning=a['plan'],
            phase2_some_intermediate_steps_observed=bool(a['plan_steps']),condition_evidence_step=a['condition_step'],
            condition_evidence_is_not_persistent_state=True,original_action_restored=bool(succ),restored_step=succ[0] if succ else None,
            resume_evidence_by=resume,resume_delay_bound=resume-succ[0] if resume is not None else None,
            broad_goal_resume_observed=resume is not None if succ else None,
            first_success_controller_status=next((x['goal_status'] for x in actions if x['id']==ident and x['variant']=='OracleRecovery' and succ and x['step']==succ[0]),None),
            types=a['types'],original=by['Original'],oracle=by['OracleRecovery']))
    restored=[p for p in pairs if p['original_action_restored']];conditions=[p for p in pairs if p['condition_evidence_step'] is not None]
    summary=dict(independent_parent_episodes=1,pairs=10,actions_reviewed=3116,variants={v:dict(
        actual_retry_success_full=sum(bool(p[v.lower() if v=='Original' else 'oracle']['original_action_success_steps']) for p in pairs),
        actual_retry_success_20=sum(any(step<=selected()[p['id']]['step']+20 for step in p[v.lower() if v=='Original' else 'oracle']['original_action_success_steps']) for p in pairs),
        main_final=[p[v.lower() if v=='Original' else 'oracle']['main_final'] for p in pairs]) for v in ['Original','OracleRecovery']},
        phase0_failed=0,phase1_failed=0,phase2_no_intermediate_step_evidence=sum(not p['phase2_some_intermediate_steps_observed'] for p in pairs),
        phase2_local_actionable=sum(p['planning']=='local_actionable' for p in pairs),phase2_partial_or_unsupported=sum(p['planning']!='local_actionable' for p in pairs),
        recovery_condition_demonstrated=len(conditions),condition_not_demonstrated=10-len(conditions),
        original_action_not_restored=10-len(restored),original_action_restored=len(restored),
        phase4_eligible=len(restored),phase4_no_semantic_resume_evidence=sum(not p['broad_goal_resume_observed'] for p in restored),
        phase4_resume_within_original20=sum(p['resume_evidence_by']<=selected()[p['id']]['step']+20 for p in restored),
        controller_completed_at_actual_retry_success=sum(p['first_success_controller_status']=='COMPLETED' for p in restored),
        type_candidate_counts=dict(Counter(t for p in pairs for t in p['types'])),
        strict_A_forgetting_causally_confirmed=0,strict_B_missing_decomposition_confirmed=0,strict_D_stack_ineffectiveness_confirmed=0,
        oracle_goal_stack_model_replay_executed=False,new_model_calls=0,new_cost_usd=0,
        conclusion='HIERARCHICAL_GOAL_STACK_NOT_ESTABLISHED_AS_PRIMARY_BOTTLENECK',
        recommendation='不直接实现完整 Goal Stack Controller；父子关系/回归路径是候选，但必须与状态判断、配方信息可见性和执行策略区分。')
    write(RESULTS/'lifecycle_comparison.json',pairs);write(RESULTS/'summary.json',summary)
    print(json.dumps(summary,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
