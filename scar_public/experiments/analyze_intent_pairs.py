"""Mechanism exposure and paired-prefix audit, separate from game outcome."""
import argparse,json,statistics
from collections import Counter
from pathlib import Path
from scar_public.provider import usage_summary


def analyze(root):
    manifest=json.loads((root/'manifest.json').read_text());arms={};traces={}
    for arm in ('observe','enforce'):
        p=root/arm;s=json.loads((p/'current.json').read_text())
        m=json.loads((p/'checkpoints'/s['checkpoint']/'agent.json').read_text())
        rows=[json.loads(q.read_text()) for q in sorted((p/'trace').glob('*.json'))]
        traces[arm]={r['step']:r for r in rows}
        audits=m['intent_audits'];times=[r['compute_and_assembly_ms'] for r in audits]
        events=m['intent_interventions']
        arms[arm]=dict(status=s,actions=len(rows),calls=sum(len(r['provider_calls']) for r in rows),
            charged_requests=sum(c['new_requests'] for r in rows for c in r['provider_calls']),
            actual_paid_usd=sum(c['paid_usd'] for r in rows for c in r['provider_calls']),
            actor_seconds=sum(r['actor_seconds'] for r in rows),
            review_count=len(events),changed_final_actions=sum(e.get('final_action_changed',False) for e in events),
            interventions=events,audit_counts=dict(Counter(r['status'] for r in audits)),
            review_compute_median_ms=statistics.median(times) if times else None,
            review_compute_total_ms=sum(times),
            completion_reports=[dict(step=r['step'],line=l) for r in rows for l in r['next_observation'].splitlines() if l.startswith('Stage completed')])
    common=sorted(set(traces['observe'])&set(traces['enforce']))
    comparisons=[]
    for step in common:
        a,b=(traces[arm][step] for arm in ('observe','enforce'))
        ca,cb=a['provider_calls'],b['provider_calls']
        comparisons.append(dict(step=step,same_before=a['before_digest']==b['before_digest'],
            same_action=a['action']==b['action'],same_after=a['after_digest']==b['after_digest'],
            same_first_llm_draw=bool(ca and cb and ca[0]['prompt_sha256']==cb[0]['prompt_sha256'] and ca[0]['response_sha256']==cb[0]['response_sha256']),
            both_programmatic=not ca and not cb))
    first_action=next((r['step'] for r in comparisons if not r['same_action']),None)
    first_review=next((e['step']+1 for e in arms['enforce']['interventions']),None)
    return dict(game=manifest['game'],manifest=manifest,arms=arms,comparisons=comparisons,
        first_review_step=first_review,first_action_divergence=first_action,
        verified_common_draws_before_first_review=all(r['same_before'] and r['same_action'] and r['same_after'] and
            (r['same_first_llm_draw'] or r['both_programmatic']) for r in comparisons if first_review is None or r['step']<first_review),
        total_paid=usage_summary(root/'api'),
        qualification='Selected paired development continuation; review can change frame/target even when the immediate command stays the same. Post-fork stochastic outcomes are not replicated causal effects. Shared-cache wall times are NOT a fair end-to-end runtime comparison.')


def main():
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);a=p.parse_args()
    rows=[analyze(p) for p in sorted((a.root/'pairs').iterdir()) if (p/'manifest.json').exists()]
    assert all(x['arms'][arm]['status']['complete'] for x in rows for arm in ('observe','enforce'))
    out=dict(runs=rows,requests=sum(r['total_paid']['requests'] for r in rows),
        estimated_usd=sum(r['total_paid']['peak_usd_estimate'] for r in rows),
        unknown_charge_attempts=sum(r['total_paid']['unknown_charge_attempts'] for r in rows))
    (a.root/'analysis.json').write_text(json.dumps(out,indent=2))
    print(json.dumps([{k:v for k,v in r.items() if k not in ('arms','comparisons','manifest')}|
        {'arms':{k:{n:v for n,v in s.items() if n not in ('interventions','completion_reports','audit_counts')} for k,s in r['arms'].items()}} for r in rows]))


if __name__=='__main__':main()
