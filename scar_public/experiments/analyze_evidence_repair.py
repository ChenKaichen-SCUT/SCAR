"""Primary endpoints and mechanism coverage for all frozen four-arm game runs."""
import argparse
from collections import Counter
import json
import gzip
from pathlib import Path
from scar_public.resource_trial import public_outcome

def analyze(run):
    current=json.loads((run/'current.json').read_text());manifest=json.loads((run/'manifest.json').read_text())
    agent=json.loads((run/'checkpoints'/current['checkpoint']/'agent.json').read_text())
    rows=[json.loads(p.read_text()) for p in sorted((run/'trace').glob('*.json')) if int(p.stem)<=current['steps']]
    responses=[json.loads(r['response']) for r in rows]
    reviews=[dict(step=r['step'],review=x['guarded_evidence_review'],executed=r['action'])
        for r,x in zip(rows,responses) if x.get('guarded_evidence_review')]
    attempts=[json.loads(l) for l in (run/'api/attempts.jsonl').read_text().splitlines()]
    started=[r for r in attempts if r['event']=='started'];ended=[r for r in attempts if r['event']=='completed']
    trials=agent.get('resource_trials',[]);selections=[r['selection'] for r in trials if r.get('selection')]
    bank=agent.get('resource_evidence',{});audit=bank.get('audit',[])
    value=[c for r in selections for c in r.get('candidates',[])]
    evidence_prompts=0
    for path in (run/'api').glob('*.request.json.gz'):
        with gzip.open(path,'rt',encoding='utf-8') as stream:payload=json.load(stream)
        if any('Applicable real-feedback evidence (conditional local rules):' in m.get('content','') for m in payload['messages']):
            evidence_prompts+=1
    return dict(arm=manifest['evidence_mode'],game=manifest['game'],manifest=manifest,current=current,
        score=current['scores'].get('quest'),environment_complete=current['termination']=='environment',
        craft_actions=sum(r['action'].startswith('craft ') for r in rows),
        craft_failures=sum(r['action'].startswith('craft ') and public_outcome(r['next_observation'],r['action'])=='failure' for r in rows),
        rejection_count=len(agent.get('resource_decision_rejections',[])),reviews=reviews,
        requests_with_applicable_evidence=evidence_prompts,
        repairs=agent.get('evidence_repairs',[]),
        local_results=dict(Counter(r.get('status') for r in trials if r.get('status'))),
        selections=[dict(status=r['status'],value=r.get('prospective_value'),reuse=r.get('persistent_evidence',{})) for r in selections],
        candidate_decisions=dict(Counter(c['decision'] for c in value)),
        exclusion_events=sum(r.get('after',0)<r.get('before',0) for r in audit),
        revocations=dict(Counter(r.get('reason') for r in audit if r.get('kind')=='REVOKED')),
        passive_observations=agent.get('evidence_observation_audit',[]),
        applicable_prior_queries=sum(r.get('persistent_evidence',{}).get('reused',False) for r in selections),
        strict_filtered_queries=sum(r.get('persistent_evidence',{}).get('reused',False) for r in selections)
            if manifest['evidence_mode']=='structured' else 0,
        first_request_hash=started[0]['request_hash'] if started else None,
        request_span_seconds=(max(r['started_utc']+r.get('elapsed_s',0) for r in ended)-min(r['started_utc'] for r in started)) if ended else None,
        quest_events=[dict(step=r['step'],score=r['scores'].get('quest'),action=r['action']) for i,r in enumerate(rows)
            if r['scores'].get('quest')!=(rows[i-1]['scores'].get('quest') if i else 0)],
        final_actions=[r['action'] for r in rows[-12:]])

def main():
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    all_runs=[analyze(path.parent) for path in sorted((a.root/'runtime').glob('*/*/*/current.json'))]
    runs=[r for r in all_runs if r['manifest']['stage'] in ('none','prompt','cache','structured')]
    followups=[r for r in all_runs if r not in runs]
    result=dict(scope='Prospective single runs on three existing templates; not cross-domain or repeated validation',
        all_complete=len(runs)==12 and all(r['current']['complete'] for r in all_runs),runs=runs,followups=followups,
        requests=sum(r['current']['usage']['requests'] for r in all_runs),
        estimated_usd=sum(r['current']['usage']['peak_usd_estimate'] for r in all_runs),
        unknown_charge_attempts=sum(r['current']['usage']['unknown_charge_attempts'] for r in all_runs))
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k not in ('runs','followups')}))
    for r in all_runs:
        print(json.dumps({k:r[k] for k in ('game','arm','score','environment_complete','craft_failures','rejection_count','exclusion_events','strict_filtered_queries')}))

if __name__=='__main__':main()
