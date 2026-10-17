"""Report task outcomes before navigation savings; retain all development arms."""
import argparse, json
from collections import Counter
from pathlib import Path
from scar_public.provider import usage_summary
from scar_public.public_model import state_from_text


def analyze(run, arm, complete):
    manifest=json.loads((run/'manifest.json').read_text()); root=run/arm
    status=json.loads((root/'current.json').read_text())
    if complete: assert status['complete'],root
    rows=[json.loads(p.read_text()) for p in sorted((root/'trace').glob('*.json'))]
    memory=json.loads((root/'checkpoints'/status['checkpoint']/'agent.json').read_text())
    navigation=[]; sources=Counter(); unbound=0; craft_audits=0
    start=manifest['start_step']; observed=set()
    if manifest.get('checkpoint'):
        prior=json.loads((Path(manifest['checkpoint'])/'agent.json').read_text())
        observed={state_from_text(x).get('location') for x in prior['observations']}
    for row in rows:
        before=state_from_text(row['observation']); after=state_from_text(row['next_observation']); observed.add(before['location'])
        response=json.loads(row['response']); source=response.get('decision_source','llm'); sources[source]+=1
        audit=response.get('intent_audit')
        if row['action'].startswith('craft ') and audit:
            craft_audits+=1; unbound+=audit['intent']['status']=='UNBOUND_TASK'
        if source=='task_frontier_execution':
            navigation.append(dict(step=row['step'],action=row['action'],task=response['progress_choice']['task'],
                from_location=before['location'],to_location=after['location'],
                changed_location=after['location']!=before['location'],
                newly_observed_location=after['location'] not in observed,
                originally_proposed=response['progress_choice']['proposed']))
        observed.add(after['location'])
    return dict(arm=arm,status=status,actions=len(rows),llm_calls=sum(len(r['provider_calls']) for r in rows),
        main_quest_passed=any(r['main_quest_passed'] for r in rows),decision_sources=dict(sources),
        navigation=navigation,confirmed_moves=sum(n['changed_location'] for n in navigation),
        new_locations=sum(n['newly_observed_location'] for n in navigation),
        craft_audits=craft_audits,unbound_craft_audits=unbound,
        reminder_retentions=sum(e['kind']=='REMINDER_RETAINS_TASK' and e['step']>=start for e in memory.get('progress_events',[])))


def main():
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--partial',action='store_true');a=p.parse_args()
    runs=[]; charges=[]
    for group in ('selected','selected_v2','full','ablation','corrected'):
        for manifest in sorted((a.root/group).glob('*/manifest.json')):
            m=json.loads(manifest.read_text()); arms={}
            for arm in m['arms']:
                if not (manifest.parent/arm/'current.json').exists():
                    assert a.partial;continue
                arms[arm]=analyze(manifest.parent,arm,not a.partial)
            u=usage_summary(manifest.parent/'api');charges.append(u)
            runs.append(dict(group=group,game=m['game'],manifest=m,arms=arms,usage=u))
    baseline=json.loads(Path('/root/scar_task_outcome_20261017/analysis.json').read_text())
    controls={r['game']:{v:{k:r['arms'][v][k] for k in ('quest_score','main_quest_passed','llm_calls','actions')} for v in ('v14','v15')} for r in baseline['runs']}
    out=dict(runs=runs,frozen_controls=controls,partial=a.partial,
        requests=sum(u['requests'] for u in charges),estimated_usd=sum(u['peak_usd_estimate'] for u in charges),
        unknown_charge_attempts=sum(u['unknown_charge_attempts'] for u in charges),
        qualification='Development data only; separate selected-state continuations from initial-world full runs; all source versions and failures retained')
    (a.root/('analysis_partial.json' if a.partial else 'analysis.json')).write_text(json.dumps(out,indent=2))
    print(json.dumps({k:v for k,v in out.items() if k not in ('runs','frozen_controls')}))
    print(json.dumps([dict(group=r['group'],game=r['game'],arms={arm:dict(step=s['status']['steps'],quest=s['status']['scores']['quest'],
        deaths=s['status']['scores']['death'],passed=s['main_quest_passed'],llm_calls=s['llm_calls'],nav=len(s['navigation']),new_locations=s['new_locations']) for arm,s in r['arms'].items()}) for r in runs]))


if __name__=='__main__':main()
