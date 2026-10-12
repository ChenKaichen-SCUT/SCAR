"""Run exactly frozen diagnostic queries; never launch Stage B implicitly."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import random

from scar.io import atomic_json, read_jsonl
from scar.providers.deepseek import DeepSeekProvider,BudgetLedger
from scar_stage12.prompts import validate

OUT=Path('results/stage12/diagnostic')


def query(job):
    spec,state,cfg,root,key,workers=job
    name=spec['state_id']+'-'+spec['method']+'-r'+str(spec['replicate'])
    folder=root/'queries'/name;folder.mkdir(parents=True,exist_ok=False)
    result={k:spec[k] for k in ['state_id','method','replicate']}
    try:
        provider=DeepSeekProvider(cfg,folder/'requests.jsonl',root/'budget.sqlite',key,workers)
        required=('action','reasoning') if spec['method']=='J2' else ('selected_candidate_id','ranked_candidate_ids',
            'reason','hypothesized_connection','confidence','expected_information','alternative_if_failed')
        response=provider.generate(spec['user'],spec['system'],required=required)
        parsed=response['parsed'];errors=validate(parsed,spec['method'],state['candidates'])
        result.update(status='invalid_schema' if errors else 'completed',parsed=parsed,validation_errors=errors)
    except Exception as exc:
        result.update(status='failed',error_type=type(exc).__name__,validation_errors=['no_valid_response'])
    rows=read_jsonl(folder/'requests.jsonl')
    result.update(requests=len(rows),cost_usd=sum(r.get('cost_usd',0) for r in rows),
                  charged_or_reserved_usd=sum(r.get('charged_or_reserved_usd',0) for r in rows))
    atomic_json(folder/'result.json',result)
    return result


def main(runtime,key,workers=8):
    root=Path(runtime);root.mkdir(parents=True,exist_ok=True)
    if (root/'launched.json').exists():raise RuntimeError('Diagnostic batch already launched; no automatic resampling')
    freeze=json.loads((OUT/'freeze.json').read_text())
    for p,h in (freeze['code_hashes']|freeze['data_hashes']|freeze['prior_file_hashes']).items():
        assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
    specs=json.loads((OUT/'frozen_queries.json').read_text());states={s['state_id']:s for s in json.loads((OUT/'states.json').read_text())}
    cfg=json.loads(Path('configs/protocol_stage12_diagnostic.json').read_text());assert len(specs)==120
    random.Random(20261012).shuffle(specs)
    atomic_json(root/'launched.json',{'queries':len(specs),'config':cfg,'order':[{k:s[k] for k in ['state_id','method','replicate']} for s in specs]})
    records=[]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for r in pool.map(query,[(s,states[s['state_id']],cfg,root,key,workers) for s in specs]):
            records.append(r)
            atomic_json(root/'progress.json',{'phase':'diagnostic_judgments','completed':len(records),'total':len(specs)})
            print(json.dumps({k:r.get(k) for k in ['state_id','method','replicate','status','requests','cost_usd']}),flush=True)
    atomic_json(OUT/'judgments.json',records)
    with (OUT/'requests.jsonl').open('w') as f:
        for r in records:
            name=r['state_id']+'-'+r['method']+'-r'+str(r['replicate'])
            for request in read_jsonl(root/'queries'/name/'requests.jsonl'):
                f.write(json.dumps({'state_id':r['state_id'],'method':r['method'],'replicate':r['replicate'],'request':request},ensure_ascii=False)+'\n')
    ledger=BudgetLedger(root/'budget.sqlite',cfg['total_budget_usd'])
    with ledger.connect() as db:pending=db.execute("SELECT COUNT(*) FROM requests WHERE status='reserved'").fetchone()[0]
    atomic_json(OUT/'completion.json',{'judgments':len(records),'requests':sum(r['requests'] for r in records),
        'completed':sum(r['status']=='completed' for r in records),'ledger_usd':ledger.total(),'pending':pending,
        'no_paid_resampling':True,'stageB_started':False})
    atomic_json(root/'progress.json',{'phase':'judgments_completed','judgments':len(records),'ledger_usd':ledger.total()})


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--runtime',required=True);p.add_argument('--key',default='/root/.scar-deepseek-key');p.add_argument('--workers',type=int,default=8);a=p.parse_args();main(a.runtime,a.key,a.workers)
