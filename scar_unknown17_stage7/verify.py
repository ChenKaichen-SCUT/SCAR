"""Full physical replay, paired-state audit, accounting and frozen-file checks."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import contextlib
import gzip
import hashlib
import json
import multiprocessing as mp
from pathlib import Path
import sqlite3
import tempfile
from scar.environment import AGENT_ID,restore,state_digest
from scar.diagnostics.build import transition
from scar.io import atomic_json,read_jsonl,digest
from scar_sequence.supplement import goal_reached


def replay_episode(job):
    folder,case=job;folder=Path(folder)
    with tempfile.TemporaryDirectory() as tmp,open('/dev/null','w') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        env=restore(folder/'initial.pkl',tmp)
        mismatches=[];hashes=[];initial_hash=state_digest(env)
        if initial_hash!=case['state_hash']:mismatches.append({'kind':'initial_hash'})
        steps=sorted((folder/'steps').glob('*/transition.json'))
        for path in steps:
            row=json.loads(path.read_text())
            actual=transition(env,row['executed_action'])
            hashes.append({'index':row['index'],'state_hash':state_digest(env)})
            checkpoint=restore(path.parent/'environment.pkl',set_rng=False)
            if state_digest(env)!=state_digest(checkpoint):mismatches.append({'kind':'state','index':row['index']})
            if actual['semantic_rejection']!=row['semantic_rejection']:mismatches.append({'kind':'rejection','index':row['index']})
            if goal_reached(env,case['goal'])!=row['diagnostic_goal_reached']:mismatches.append({'kind':'goal','index':row['index']})
        return {'task_id':folder.name,'steps':len(steps),'initial_hash':initial_hash,'state_hashes':hashes,'mismatches':mismatches}


def verify(runtime,output='results/stage7',workers=8):
    root=Path(runtime);out=Path(output)
    freeze=json.loads((out/'freeze.json').read_text())
    code_errors=[name for name,sha in freeze['code_hashes'].items() if hashlib.sha256(Path(name).read_bytes()).hexdigest()!=sha]
    old_errors=[name for name,sha in freeze['prior_file_hashes'].items() if hashlib.sha256(Path(name).read_bytes()).hexdigest()!=sha]
    tasks=json.loads((root/'tasks.json').read_text());cases=json.loads((out/'cases.json').read_text());by_id={c['id']:c for c in cases}
    complete=json.loads((out/'completion.json').read_text())
    jobs=[(str(root/'runs'/t['task_id']),by_id[t['id']]) for t in tasks if (root/'runs'/t['task_id']/'initial.pkl').exists()]
    with ProcessPoolExecutor(max_workers=workers,mp_context=mp.get_context('spawn')) as pool:
        replays=list(pool.map(replay_episode,jobs))
    paired={}
    for c in cases:
        matching=[r for r in replays if r['task_id'].startswith(c['id']+'-')]
        paired[c['id']]={'methods':len(matching),'initial_hashes':sorted(set(r['initial_hash'] for r in matching))}
    request_totals={};all_ids=set();duplicates=[]
    from scar_unknown17_stage7.analyze import METHODS
    for method in METHODS:
        requests=[]
        with gzip.open(out/f'requests_{method}.jsonl.gz','wt') as f:
            for t in tasks:
                if t['algorithm']!=method:continue
                for row in read_jsonl(root/'runs'/t['task_id']/'requests.jsonl'):
                    if row['request_id'] in all_ids:duplicates.append(row['request_id'])
                    all_ids.add(row['request_id']);requests.append(row)
                    # Audit schema contains messages/usage/responses; no headers.
                    f.write(json.dumps({'task_id':t['task_id'],'request':row},ensure_ascii=False)+'\n')
        request_totals[method]={'api_calls':len(requests),'cost_usd':sum(r.get('cost_usd',0) for r in requests),
            'charged_or_reserved_usd':sum(r.get('charged_or_reserved_usd',0) for r in requests),
            'input_tokens':sum((r.get('usage') or {}).get('prompt_tokens',0) for r in requests),
            'output_tokens':sum((r.get('usage') or {}).get('completion_tokens',0) for r in requests),
            'statuses':dict(__import__('collections').Counter(r['status'] for r in requests))}
    with sqlite3.connect(root/'budget.sqlite') as db:
        ledger,pending=db.execute("select coalesce(sum(coalesce(charged,reserved)),0),sum(charged is null) from requests").fetchone()
    previous=0
    prior_ledgers={}
    for ledger_path in ['/root/scar_workspace/runtime/budget.sqlite','/root/scar_workspace/runtime_sequence/budget.sqlite','/root/scar_workspace/runtime_unknown17/budget.sqlite']:
        with sqlite3.connect(ledger_path) as db:value=db.execute('select coalesce(sum(coalesce(charged,reserved)),0) from requests').fetchone()[0]
        prior_ledgers[ledger_path]=value;previous+=value
    requests_sum=sum(r['charged_or_reserved_usd'] for r in request_totals.values())
    result={'complete':complete['fully_complete'],'code_mismatches':code_errors,'old_file_mismatches':old_errors,
        'protected_prior_file_count':len(freeze['prior_file_hashes']),
        'dataset_hash_matches':digest(cases)==freeze['dataset_digest'],
        'episodes_replayed':len(replays),'actions_replayed':sum(r['steps'] for r in replays),
        'replay_mismatches':[r for r in replays if r['mismatches']],
        'paired_families':paired,'request_totals':request_totals,'duplicate_request_ids':duplicates,
        'new_ledger_usd':ledger,'previous_ledger_usd':previous,'prior_ledgers':prior_ledgers,'project_total_usd':ledger+previous,
        'pending_reservations':pending or 0,'request_ledger_difference':requests_sum-ledger}
    result['passed']=all([result['complete'],not code_errors,not old_errors,result['dataset_hash_matches'],
        len(replays)==len(tasks),not result['replay_mismatches'],not duplicates,not pending,
        abs(requests_sum-ledger)<1e-8,abs(previous-28.977867894)<1e-8,
        all(v['methods']==6 and len(v['initial_hashes'])==1 for v in paired.values())])
    atomic_json(out/'verification.json',result)
    atomic_json(out/'replay_records.json',replays)
    print(json.dumps({k:v for k,v in result.items() if k not in {'paired_families','request_totals','replay_mismatches'}}))
    assert result['passed'], result
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--runtime',required=True);p.add_argument('--output',default='results/stage7');p.add_argument('--workers',type=int,default=8)
    a=p.parse_args();verify(a.runtime,a.output,a.workers)
