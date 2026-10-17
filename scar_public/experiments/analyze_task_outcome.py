"""Success-first outcome audit; include every arm and failure, not just savings."""
import argparse,json
from collections import Counter
from pathlib import Path
from scar_public.provider import usage_summary


def analyze_pair(pair,require_complete=True,control=None):
    manifest=json.loads((pair/'manifest.json').read_text());arms={};traces={}
    if control:
        baseline=json.loads((control/'manifest.json').read_text())
        assert baseline['initial_sha256']==manifest['initial_sha256']
        manifest['reused_control']=str(control);manifest['control_source_manifest_sha256']=baseline['source_manifest_sha256']
    for arm in ('v14','v15'):
        root=(control if control and arm=='v14' else pair)/arm;status=json.loads((root/'current.json').read_text())
        if require_complete:assert status['complete'],(pair,arm)
        rows=[json.loads(p.read_text()) for p in sorted((root/'trace').glob('*.json'))]
        memory=json.loads((root/'checkpoints'/status['checkpoint']/'agent.json').read_text())
        traces[arm]={r['step']:r for r in rows};source=Counter();reports=[]
        for row in rows:
            source[json.loads(row['response']).get('decision_source','llm')]+=1
            for line in row['next_observation'].splitlines():
                if line.startswith('Stage completed'):reports.append(dict(step=row['step'],line=line))
        decisions=memory.get('outcome_decisions',[])
        chosen=[r['chosen'] for r in decisions if r.get('chosen')]
        arms[arm]=dict(status=status,main_quest_passed=any(r['main_quest_passed'] for r in rows),
            quest_score=status['scores']['quest'],actions=len(rows),llm_calls=sum(len(r['provider_calls']) for r in rows),
            actual_decision_sources=dict(source),stage_reports=reports,
            outcome_decisions=len(decisions),selected_supported=sum(c['role_supported'] for c in chosen),
            selected_exploratory=sum(not c['role_supported'] for c in chosen),
            rejections=dict(Counter(e['reason'] for r in decisions for e in r.get('rejected',[]))),
            releases=dict(Counter(r['reason'] for r in decisions if r.get('status')=='RELEASED')),
            charged_requests=sum(c['new_requests'] for r in rows for c in r['provider_calls']),
            new_paid_usd=sum(c['paid_usd'] for r in rows for c in r['provider_calls']),
            outcome_observations=memory.get('outcome_probes',[]))
    common=sorted(set(traces['v14'])&set(traces['v15']));divergence=None;provider_divergence=None;matched_prefix=True;unequal_common_draws=[]
    for s in common:
        a,b=traces['v14'][s],traces['v15'][s]
        if a['action']!=b['action'] and divergence is None:divergence=s
        ca,cb=a['provider_calls'],b['provider_calls']
        same_calls=len(ca)==len(cb) and all(x['prompt_sha256']==y['prompt_sha256'] and x['response_sha256']==y['response_sha256'] for x,y in zip(ca,cb))
        if not same_calls and provider_divergence is None:provider_divergence=s
        if divergence is None and provider_divergence is None:
            matched_prefix &= a['before_digest']==b['before_digest'] and a['after_digest']==b['after_digest']
        for x,y in zip(ca,cb):
            if x['prompt_sha256']==y['prompt_sha256'] and x['response_sha256']!=y['response_sha256']:unequal_common_draws.append(s)
    assert traces['v14'][common[0]]['before_digest']==traces['v15'][common[0]]['before_digest']
    return dict(game=manifest['game'],manifest=manifest,arms=arms,first_action_divergence=divergence,
        first_provider_divergence=provider_divergence,unequal_identical_prompt_draws=unequal_common_draws,
        matched_worlds_before_first_action_or_provider_divergence=matched_prefix,usage=usage_summary(pair/'api'),
        qualification='Full-budget development comparison, one trajectory per arm, no statistical or held-out claim; shared API caching makes wall-clock arm comparison unfair')


def main():
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--partial',action='store_true');a=p.parse_args()
    games=('remnant','mark','metropolis')
    development=[analyze_pair(a.root/'full'/g,not a.partial) for g in games]
    runs=[analyze_pair(a.root/'corrected'/g,not a.partial,control=a.root/'full'/g) for g in games]
    charges=[r['usage'] for r in development+runs]
    out=dict(runs=runs,initial_development=development,
        successes={arm:sum(r['arms'][arm]['main_quest_passed'] for r in runs) for arm in ('v14','v15')},
        requests=sum(r['requests'] for r in charges),estimated_usd=sum(r['peak_usd_estimate'] for r in charges),
        unknown_charge_attempts=sum(r['unknown_charge_attempts'] for r in charges),partial=a.partial,
        cost_scope='All initial six and corrected three trajectories; reused V14 controls charged once; initial V15 contains documented implementation defects')
    (a.root/('analysis_partial.json' if a.partial else 'analysis.json')).write_text(json.dumps(out,indent=2))
    print(json.dumps({k:v for k,v in out.items() if k not in ('runs','initial_development')}))
    print(json.dumps([{ 'game':r['game'],'divergence':r['first_action_divergence'],
        'arms':{arm:{k:v for k,v in s.items() if k in ('main_quest_passed','quest_score','actions','llm_calls','actual_decision_sources','rejections','releases')} for arm,s in r['arms'].items()}} for r in runs]))


if __name__=='__main__':main()
