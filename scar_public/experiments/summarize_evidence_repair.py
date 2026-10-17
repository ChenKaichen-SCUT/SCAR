"""Regenerate the readable gap audit from immutable numeric records."""
import argparse
from collections import Counter
import json
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);a=p.parse_args();root=a.directory
    d=json.loads((root/'analysis.json').read_text());assert d['all_complete']
    matrix=json.loads((root/'local_matrix.json').read_text())
    validation=json.loads((root/'validation.json').read_text())
    carried=json.loads((root/'carried_validation.json').read_text())
    regret=json.loads((root/'profile_regret.json').read_text())
    lines=['THEORY, ALGORITHM AND GAME GAP AUDIT (2026-10-17)','',
        'Four-arm prospective development round. One 300-action run per game/arm,',
        'using a fresh default-seed physical snapshot shared by the four arms.',
        'Existing game templates, not new independent domains or repeated trials.',
        'No old baseline was rerun. No mid-run source changes.','',
        'Game          none    prompt   cache   structured']
    for game in ('remnant','mark','metropolis'):
        runs={r['arm']:r for r in d['runs'] if r['game']==game}
        lines.append(f"{game:12s} "+' '.join(f"{runs[arm]['score']:8}" for arm in ('none','prompt','cache','structured')))
    lines+=['',f"Environment-complete runs: {sum(r['environment_complete'] for r in d['runs'])}/12.",
        f"Evidence rejections: {sum(r['rejection_count'] for r in d['runs'])}.",
        f"Strong repair certificates: {sum(x['status']=='VERIFIED_STRONG_LOCAL_REPAIR' for r in d['runs'] for x in r['repairs'])}.",
        'Scores alone cannot be attributed to evidence when relevant opportunities',
        'or actual interventions are absent. LLM samples are unpaired.','',
        'THEORY AND IMPLEMENTATION',
        '- Prospective pathwise comparison to a specified verified reference; no',
        '  optimality or future-revisit value claim. UNKNOWN reference stays UNKNOWN.',
        '- Joint-profile enabling deficits and capacity/total-supply obstructions.',
        '  A capacity lower bound is not used as an infeasibility upper bound.',
        '- Cheap rejection after the main search quota; bounded strong local repair',
        '  follows actual feedback and introduces no new success exemptions.',
        '- Passive actual craft feedback, explicit guard scopes and epoch revocation.',
        '  Clock/attribute guards do not prove hidden temporal invariance.',
        '- Conditional deletion theorem explicitly needs time-independent sufficient',
        '  state. Actual game rejection is not claimed universally safe.','',
        'EXACT SMALL-MODEL AUDIT',
        f"Configurations: {matrix['configurations']}; grounding gaps: {matrix['gaps']}; changed selections: {matrix['changed_selection']}.",
        'The stronger cost test is implemented, but this matrix shows no additional',
        'selection benefit. Gate-off still computes cost vectors; its timing is not',
        'a comparison against legacy V10 computation.','',
        f"Actual grounded-query audit: {regret['additional_rejected_candidates']} additional profile-regret rejections in {regret['queries']} queries, but {regret['changed_selected_policies']} changed final policy selections.",
        'For example, drop coal_chunk then craft oak_rod has worst cost three like',
        'the reference, but loses one action in two profiles. Another candidate',
        'already ranks ahead, so the stronger rejection does not change the action.','',
        'EXPLORATORY FOLLOW-UP (selected after the prospective round began)']
    for r in d.get('followups',[]):
        control=next(x for x in d['runs'] if x['arm']=='structured' and x['game']==r['game'])
        fork=r['manifest']['diagnostic_fork']['start_step']
        lines += [f"{r['game']} from step {fork}: attributes scope score {r['score']}, frozen clock-scope score {control['score']}.",
            f"New continuation actions: {r['current']['steps']-fork}; evidence rejections: {r['rejection_count']}.",
            f"Repair statuses: {dict(Counter(x['status'] for x in r['repairs']))}.",
            'Initial state and spent budget retained; old clock-scoped facts were not',
            'imported into the new scope. No extra baseline was run. This selected',
            'follow-up is development evidence, not independent validation.']
    lines+=['','LATER CARRIED-CONTAINER REVISION (not deployed in those paid runs)',
        'A held bag occupies hand capacity and is excluded from movable modeled',
        'items. Detachment invalidates the certificate. Stale contents trigger a',
        'charged inspection, not invented material counts or a value certificate.',
        f"Real-engine local check: {carried['actions']} action(s), outcome {carried['outcome']['status']}, zero API calls.",
        'The first eligible context required a bag inspection. It revealed that',
        'one required timber was absent, so no verified continuation was returned.',
        'Earlier, the LLM had successfully crafted a gavel_splint, but equip failed',
        'because it was not equippable. Consuming an ingredient for a successful',
        'irrelevant craft is a concrete unresolved method-to-task alignment gap.',
        'The carried-container implementation passes 74 server tests; positive',
        'local policy behavior is unit-tested, not claimed as real-game success.',
        '', 'VALIDATION AND COST',
        f"Shadow validation actions: {validation['validation_actions']}; all rejected actions failed without visible progress: {validation['all_rejections_failed_without_visible_progress']}.",
        'Shadow observations are evaluator-only and were never fed to the agent.',
        f"New API requests (all runs): {d['requests']}; estimated configured-peak USD: {d['estimated_usd']:.6f}; unknown-charge attempts: {d['unknown_charge_attempts']}.",
        'Estimated prices are not billing receipts. Full per-run latency, request',
        'counts, failures and progress events are in analysis.json.',
        'The original 12-cell source and follow-up source are frozen separately.','',
        'UNRESOLVED',
        'Stable performance above prompt-only evidence/contextual caching; broader',
        'grounding coverage; predictive value of future evidence reuse; productive',
        'LLM method repair beyond the finite fragment; guard adequacy under hidden',
        'rule changes; formal repeated trials and independent originality.',
        'Do not describe this round as closing every research gap.']
    (root/'SUMMARY.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('\n'.join(lines))

if __name__=='__main__':main()
