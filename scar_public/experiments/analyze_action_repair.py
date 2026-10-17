"""Audit actual action exposure, public completion and ALL development charges."""
import argparse,json
from collections import Counter
from pathlib import Path
from scar_public.provider import usage_summary
from scar_public.action_repair import acknowledged


def analyze(root):
    manifest=json.loads((root/'manifest.json').read_text());arms={};traces={}
    for arm in ('observe','execute'):
        p=root/arm;status=json.loads((p/'current.json').read_text());assert status['complete']
        memory=json.loads((p/'checkpoints'/status['checkpoint']/'agent.json').read_text())
        rows=[json.loads(q.read_text()) for q in sorted((p/'trace').glob('*.json'))]
        traces[arm]={r['step']:r for r in rows};actual=[];overridden=[]
        for event in memory.get('action_events',[]):
            row=traces[arm].get(event['step']+1)
            entry=dict(event=event,executed_action=row['action'] if row else None)
            if row and row['action']==event['action']:
                entry['confirmed_by_final_acknowledgment']=acknowledged(row['action'],row['next_observation'])
                entry['final_decision_source']=json.loads(row['response']).get('decision_source')
                actual.append(entry)
            else:overridden.append(entry)
        calls=[c for r in rows for c in r['provider_calls']]
        arms[arm]=dict(status=status,actions=len(rows),llm_calls=len(calls),
            newly_charged_requests=sum(c['new_requests'] for c in calls),
            newly_charged_usd=sum(c['paid_usd'] for c in calls),
            actor_seconds=sum(r['actor_seconds'] for r in rows),
            actual_program_actions=len(actual),actual_program_phases=dict(Counter(e['event']['phase'] for e in actual)),
            final_program_source_actions=sum(e['final_decision_source']=='evidence_action_program' for e in actual),
            compiled_actions_recertified_by_base_controller=sum(e['final_decision_source']!='evidence_action_program' for e in actual),
            program_execution=actual,overridden_program_actions=overridden,
            program_outcomes=memory.get('action_outcomes',[]),
            compilation_events=memory.get('action_compilations',[]),
            extra_llm_review_events=len(memory.get('intent_interventions',[])),
            completion_reports=[dict(step=r['step'],line=l) for r in rows for l in r['next_observation'].splitlines() if l.startswith('Stage completed')],
            action_sequence=[dict(step=r['step'],action=r['action'],llm_calls=len(r['provider_calls']),
                decision_source=json.loads(r['response']).get('decision_source')) for r in rows])
    common=sorted(set(traces['observe'])&set(traces['execute']))
    first=common[0]
    comparisons=[dict(step=s,same_before=traces['observe'][s]['before_digest']==traces['execute'][s]['before_digest'],
        same_action=traces['observe'][s]['action']==traces['execute'][s]['action'],
        same_after=traces['observe'][s]['after_digest']==traces['execute'][s]['after_digest']) for s in common]
    assert comparisons[0]['same_before']
    return dict(manifest=manifest,arms=arms,same_start_digest=True,
        first_action_divergence=next((r['step'] for r in comparisons if not r['same_action']),None),
        comparisons=comparisons,total_paid=usage_summary(root/'api'),
        qualification='Selected development continuation; one trajectory per arm, not independent validation. Post-intervention RNG consumption and LLM prompts can diverge. Shared-cache wall times are not a fair speed comparison.')


def main():
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);a=p.parse_args()
    versions={v:{g:analyze(a.root/v/g) for g in ('metropolis','remnant')} for v in ('pairs','pairs_v2','pairs_v3')}
    charges=[r['total_paid'] for games in versions.values() for r in games.values()]
    out=dict(versions=versions,requests=sum(r['requests'] for r in charges),
        estimated_usd=sum(r['peak_usd_estimate'] for r in charges),
        unknown_charge_attempts=sum(r['unknown_charge_attempts'] for r in charges),
        primary_version='pairs_v3',
        development_failures=['pairs: broad actor goal did not bind to a public task; no mechanism exposure',
            'pairs_v2: resumed run omitted ancestor public prefix; no mechanism exposure',
            'native: initial combat handling aborted the program after five actions'],
        cost_scope='All paid attempts in all three versions; copied completed cache responses are not charged again; native and final replay use zero API calls')
    (a.root/'analysis.json').write_text(json.dumps(out,indent=2))
    print(json.dumps({k:v for k,v in out.items() if k!='versions'}))
    for g,r in versions['pairs_v3'].items():
        print(json.dumps(dict(game=g,arms={k:{n:v for n,v in arm.items() if n in ('status','actions','llm_calls','actual_program_actions','actual_program_phases','extra_llm_review_events','program_outcomes')} for k,arm in r['arms'].items()})))


if __name__=='__main__':main()
