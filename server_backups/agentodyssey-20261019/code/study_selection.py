"""Frozen exploratory selection rule, not a statistical significance test."""
from mechanism_study_core import VARIANTS
GAMES=['remnant','metropolis']
PRIORITY=['no_hypothesis','no_execution','no_repeat','no_checks']

def select(reference,runs):
    evidence={};eligible=[]
    for variant in PRIORITY:
        rs={g:runs.get(g+'__ab_'+variant,{}) for g in GAMES}
        valid=all(r.get('completion_reason') in ['step_limit','environment_done'] and r.get('returncode')==0 and not r.get('scoring_error') for r in rs.values())
        gains={g:rs[g].get('main_quest',0)-reference[g]['main'] for g in GAMES}
        qualifies=valid and gains['remnant']>0 and gains['metropolis']>=0
        evidence[variant]={'valid_pair':valid,'main_gains':gains,'eligible_for_exploratory_removal':qualifies}
        if qualifies:eligible.append(variant)
    # Remove at most one group; do not combine individually tested deletions without testing interaction.
    best=max(eligible,key=lambda v:(evidence[v]['main_gains']['remnant']/24+evidence[v]['main_gains']['metropolis']/31,-PRIORITY.index(v))) if eligible else None
    return {'selected_ablation':best,'disabled_components':sorted(VARIANTS[best]) if best else [],'evidence':evidence,
            'interpretation':'exploratory single-trajectory selection; nonselection is inconclusive, not proof a component works; removal is not proof universal uselessness',
            'rule':'at most one removal; both runs completed with valid scores; Remnant strictly improves, Metropolis does not regress at the 300-step budget; maximize normalized total gain; fixed tie order'}
