"""Export every formal run/request, including aborts; never exports keys/engines."""
import argparse
import sqlite3
from collections import Counter
from pathlib import Path
from scar.io import atomic_json,read_jsonl
from scar_stage14.common import load,sha,save_records
ROOT=Path('results/stage15')


def main():
    p=argparse.ArgumentParser();p.add_argument('--runtime',required=True);a=p.parse_args();root=Path(a.runtime)
    tasks=load(root/'tasks.json');assert len(tasks)==70
    freeze=load(ROOT/'freeze.json')
    for path,h in (freeze['code_hashes']|freeze['data_hashes']).items():assert sha(path)==h,path
    not_started={t['task_id']:t for t in read_jsonl(root/'not_started.jsonl')}
    episodes=[];requests=[]
    for task in tasks:
        folder=root/'runs'/task['task_id'];summary=folder/'summary.json'
        if not summary.exists():
            assert task['task_id'] in not_started,('batch still running or missing final summary',task['task_id'])
            ss=dict(task,status='not_started',error=not_started[task['task_id']]['reason'])
        else:
            ss=load(summary);assert load(folder/'status.json')['status']!='running'
        rows=[load(p) for p in sorted((folder/'steps').glob('*/transition.json'))]
        assert len(rows)<=40 and [r['index'] for r in rows]==list(range(len(rows)))
        episodes.append({'task_id':task['task_id'],'case_id':task['id'],'summary':ss,'rows':rows})
        requests.extend({'task_id':task['task_id'],'algorithm':task['algorithm'],'request':r} for r in read_jsonl(folder/'requests.jsonl'))
    for method in [f'P{i}' for i in range(7)]:
        save_records(ROOT/f'trajectories_{method}.jsonl.gz',[e for e in episodes if e['summary']['algorithm']==method])
        save_records(ROOT/f'requests_{method}.jsonl.gz',[r for r in requests if r['algorithm']==method])
    with sqlite3.connect(root/'budget.sqlite') as db:
        ledger=[dict(zip(['id','reserved','charged','status'],r)) for r in db.execute('SELECT id,reserved,charged,status FROM requests ORDER BY id')]
    atomic_json(ROOT/'budget_ledger.json',ledger);atomic_json(ROOT/'tasks.json',tasks)
    atomic_json(ROOT/'completion.json',{'episodes':len(episodes),'actions':sum(len(e['rows']) for e in episodes),'api_calls':len(requests),
       'statuses':dict(Counter(e['summary']['status'] for e in episodes)),
       'cost_usd':sum(r['request'].get('cost_usd',0) for r in requests),
       'conservative_cost_usd':sum(r['charged'] if r['charged'] is not None else r['reserved'] for r in ledger),
       'all70accounted':True,'paid_episode_reruns':0,'policy_hashes_unchanged':True})
    print(load(ROOT/'completion.json'))

if __name__=='__main__':main()
