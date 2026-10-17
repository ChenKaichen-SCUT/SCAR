"""Summarize actual LLM continuations, requests, and evidence-triggered revisions."""
import argparse
from collections import Counter
import json
from pathlib import Path


def arm(root,name):
    run=root/'runtime'/('llm_'+name)/'evidence_decision_v10/metropolis'
    current=json.loads((run/'current.json').read_text())
    manifest=json.loads((run/'manifest.json').read_text())
    rows=[json.loads(p.read_text()) for p in sorted((run/'trace').glob('*.json'))
          if int(p.stem)<=current['steps']]
    responses=[json.loads(r['response']) for r in rows]
    agent=json.loads((run/'checkpoints'/current['checkpoint']/'agent.json').read_text())
    reviews=[dict(step=r['step'],proposal=x['guarded_evidence_review']['action'],
        executed=r['action'],reasoning=x.get('reasoning'),review=x['guarded_evidence_review'],
        observation=r['observation'],next_observation=r['next_observation'])
        for r,x in zip(rows,responses) if 'guarded_evidence_review' in x]
    events=[];previous=10
    for r in rows:
        if r['scores']['quest']!=previous:
            events.append(dict(step=r['step'],action=r['action'],score=r['scores']['quest'],
                               observation=r['next_observation']))
            previous=r['scores']['quest']
    attempts=[json.loads(l) for l in (run/'api/attempts.jsonl').read_text().splitlines()]
    first=next(r for r in attempts if r['event']=='started')
    return dict(arm=name,manifest=manifest,current=current,continuation_actions=len(rows),
        charged_acquisition_actions=1,total_actions_including_acquisition=len(rows)+1,
        initial_quest_score=10,quest_gain=current['scores']['quest']-10,
        first_request_hash=first['request_hash'],reviews=reviews,
        rejection_count=len(agent.get('resource_decision_rejections',[])),
        fallback_actions=sum(x.get('decision_source')=='evidence_review_fallback' for x in responses),
        gavel_attempts=[dict(step=r['step'],action=r['action'],feedback=r['next_observation'])
                        for r in rows if r['action']=='craft 1 gavel_club'],
        craft_commands=dict(Counter(r['action'] for r in rows if r['action'].startswith('craft '))),
        quest_events=events,last_actions=[dict(step=r['step'],action=r['action']) for r in rows[-15:]],
        last_observation=rows[-1]['next_observation'] if rows else None,
        ledger=agent.get('resource_evidence'),
        executed_with_evidence_repair=[r['step'] for r in reviews])


def main():
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();arms=[arm(a.root,n) for n in ('control','reuse')]
    result=dict(scope='One development continuation per arm; same checkpoint and prompts, unpaired LLM samples',
        all_complete=all(r['current']['complete'] for r in arms),arms=arms,
        same_initial_request=arms[0]['first_request_hash']==arms[1]['first_request_hash'],
        total_api_requests=sum(r['current']['usage']['requests'] for r in arms),
        unknown_charge_attempts=sum(r['current']['usage']['unknown_charge_attempts'] for r in arms),
        configured_peak_usd_estimate=sum(r['current']['usage']['peak_usd_estimate'] for r in arms))
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='arms'}))
    for r in arms:
        print(json.dumps(dict(arm=r['arm'],steps=r['current']['steps'],score=r['current']['scores']['quest'],
            reviews=len(r['reviews']),fallback=r['fallback_actions'],gavel_attempts=len(r['gavel_attempts']),
            last_actions=r['last_actions'][-3:])))


if __name__=='__main__':main()
