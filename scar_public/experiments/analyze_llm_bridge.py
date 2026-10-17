"""Summarize committed game records without reading hidden evaluator state."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import time


def read(path):
    return json.loads(path.read_text())


def summarize(directory):
    status=read(directory/'current.json')
    checkpoint=directory/'checkpoints'/status['checkpoint']/'agent.json'
    agent=read(checkpoint)
    traces=[read(p) for p in sorted((directory/'trace').glob('*.json'))
            if int(p.stem)<=status['steps']]
    trials=agent.get('resource_trials',[])
    selections=[r for r in trials if 'selection' in r]
    executions=[r for r in trials if 'events' in r]
    actions=[]
    for r in traces:
        response=json.loads(r['response'])
        if response.get('decision_source')=='resource_competition':
            actions.append(dict(step=r['step'],action=r['action'],scores=r['scores'],
                controller=response['resource_competition'],observation=r['observation'],
                next_observation=r['next_observation']))
    api=[json.loads(line) for line in (directory/'api/attempts.jsonl').read_text().splitlines()]
    started=[r['started_utc'] for r in api if r['event']=='started']
    progress=[];previous=0
    for r in traces:
        if r['scores'].get('quest',0)>previous:
            progress.append(dict(step=r['step'],action=r['action'],score=r['scores']['quest'],
                next_observation=r['next_observation']))
        previous=r['scores'].get('quest',0)
    return dict(game=directory.name,method=directory.parent.name,manifest=read(directory/'manifest.json'),
        current=status,wall_seconds=status['updated_utc']-min(started) if started else None,
        decision_sources=dict(Counter(json.loads(r['response']).get('decision_source','llm') for r in traces)),
        search_attempts=len(agent.get('resource_attempts',[])),
        selection_statuses=dict(Counter(r['selection']['status'] for r in selections)),
        execution_statuses=dict(Counter(r['status'] for r in executions)),
        grounding_rejections=dict(Counter(r.get('reason','') for r in trials if r.get('status')=='GROUNDING_UNKNOWN')),
        actual_controller_actions=actions,selected_trials=selections,execution_records=executions,
        quest_progress=progress,last_frame=agent.get('frame'),
        last_actions=[dict(step=r['step'],action=r['action']) for r in traces[-20:]],
        last_observation=traces[-1]['next_observation'] if traces else None,
        discrimination_events=sum(bool(e.get('discriminated')) for r in executions for e in r['events']),
        trace_hash_chain=hashlib.sha256(''.join(hashlib.sha256((directory/'trace'/f"{r['step']:04d}.json").read_bytes()).hexdigest() for r in traces).encode()).hexdigest())


def main():
    parser=argparse.ArgumentParser();parser.add_argument('root',type=Path)
    parser.add_argument('baseline_root',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args()
    result=dict(scope='one-run reused-game development comparison; not causal or held-out evidence',
        observed_at_utc=time.time(),new_runs=[],comparators=[])
    for game in ('remnant','mark','metropolis'):
        directory=args.root/'bridge1/resource_competition_v8'/game
        if not (directory/'current.json').exists():continue
        row=summarize(directory);result['new_runs'].append(row)
        for stage,method in [('round7','obligation_v6'),('round1','stm'),('round1','longcontext'),('round1','reflact')]:
            base=args.baseline_root/stage/method/game
            manifest=read(base/'manifest.json')
            assert manifest['initial_snapshot_sha256']==row['manifest']['initial_snapshot_sha256']
            result['comparators'].append(dict(game=game,method=method,manifest=manifest,current=read(base/'current.json')))
        print(json.dumps(dict(game=game,steps=row['current']['steps'],complete=row['current']['complete'],
            quest=row['current']['scores']['quest'],search_attempts=row['search_attempts'],
            selections=row['selection_statuses'],executions=row['execution_statuses'],
            controller_actions=len(row['actual_controller_actions']),grounding_rejections=row['grounding_rejections'])),flush=True)
    result['all_complete']=len(result['new_runs'])==3 and all(r['current']['complete'] for r in result['new_runs'])
    methods=sorted({r['method'] for r in result['new_runs']+result['comparators']})
    result['score_table']={m:{r['game']:r['current']['scores']['quest']
        for r in result['new_runs']+result['comparators'] if r['method']==m} for m in methods}
    args.output.write_text(json.dumps(result,indent=2,ensure_ascii=False))


if __name__=='__main__':main()
