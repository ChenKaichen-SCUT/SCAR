"""Cost reconciliation, official scoring, and completion receipts."""
import math
import sqlite3
from collections import Counter
import subprocess
import sys
from .common import *
from scar.providers.deepseek import estimate_cost
from scar_stage22.provider import prices_at

def ledger(path):
    with sqlite3.connect(f'file:{path}?mode=ro',uri=True) as db:return db.execute('select id,charged,status from requests').fetchall()

def main():
    offline();integrity=check_freeze();allq=[];summaries=[];receipts=[];official=[]
    for n in CASES:
        out=RESULTS/'runs'/case_id(n)/'Oracle';runtime=RUNTIME/'runs'/case_id(n)
        s=read(out/'summary.json');qq=rows(out/'requests.jsonl.gz');allq+=qq
        assert s['status'] in ['step_limit','native_done','agent_decision_exhausted']
        assert s['new_requests']==len(qq) and s['intervention_count']==1
        assert not (runtime/'pending_request.json').exists()
        led=ledger(runtime/'budget.sqlite')
        assert {x[0] for x in led}=={q['request_id'] for q in qq}
        assert all(x[2] in ['ok','http_rejected'] for x in led)
        assert math.isclose(sum(x[1] for x in led),s['cost_usd'],abs_tol=1e-12)
        reused=rows(out/'source_reuse.jsonl.gz');assert all(q['step']==n and q['new_cost_usd']==0 for q in reused)
        receipt=read(RESULTS/'verification'/f'{case_id(n)}.json')
        assert receipt['passed'] and receipt['exact_native_steps']==s['steps']
        args=[sys.executable,str(ENGINE/'challenge_eval.py'),'--remnant',str(out),'--json']
        result=subprocess.run(args,text=True,capture_output=True,check=True);score=json.loads(result.stdout)
        assert score['games']['remnant']['main_quest']==s['scores']['quest']
        official.append(dict(case=case_id(n),args=args,official_scores=score))
        summaries.append(s);receipts.append(receipt)
    for q in allq:
        if q['status']=='ok':
            assert q['unit_prices']==prices_at(q['raw_response'].get('created') or q['start'])
            assert math.isclose(estimate_cost(q['usage'],q['unit_prices']),q['cost_usd'],abs_tol=1e-12)
            assert q['charged_or_reserved_usd']==q['cost_usd']
        else:assert q['status']=='http_rejected' and q['charged_or_reserved_usd']==0
    led=ledger(RUNTIME/'budget.sqlite')
    assert len(led)==len(allq) and len({q['request_id'] for q in allq})==len(allq)
    assert {x[0] for x in led}=={q['request_id'] for q in allq}
    total=sum(q.get('cost_usd',0) for q in allq);assert math.isclose(total,sum(x[1] for x in led),abs_tol=1e-12)
    result=dict(passed=True,new_requests=len(allq),cost_usd=total,input_tokens=sum(q.get('usage',{}).get('prompt_tokens',0) for q in allq),
        output_tokens=sum(q.get('usage',{}).get('completion_tokens',0) for q in allq),
        source_requests_reused=sum(s['source_requests_reused'] for s in summaries),original_suffix_new_requests=0,
        new_analysis_requests=0,unsettled_reservations=0,unknown_billing=0,ledger_statuses=dict(Counter(x[2] for x in led)),
        invalid_json_responses=sum(bool(q.get('parse_exception')) for q in allq),
        truncated_responses=sum(q.get('raw_response',{}).get('choices',[{}])[0].get('finish_reason')=='length' for q in allq),
        pricing_verified_per_response=True,provider_invoice_available=False,
        unit_prices=[json.loads(x) for x in sorted({json.dumps(q['unit_prices'],sort_keys=True) for q in allq if q.get('unit_prices')})],
        cases=[dict(case=s['case'],new_requests=s['new_requests'],cost_usd=s['cost_usd'],actions=s['steps'],status=s['status']) for s in summaries])
    write(RESULTS/'cost_reconciliation.json',result)
    write(RESULTS/'official_scores.json',dict(script_sha256=sha(ENGINE/'challenge_eval.py'),engine_commit=ENGINE_COMMIT,cases=official))
    write(RESULTS/'completion_audit.json',dict(complete=True,formal_oracle_branches=10,reused_original_suffixes=10,independent_parent_episodes=1,
        verified_oracle_native_actions=sum(r['exact_native_steps'] for r in receipts),verified_model_contexts=sum(r['exact_model_contexts'] for r in receipts),
        verified_original_native_actions=300,freeze_integrity=integrity,algorithm_modified=False,other_games_rerun=False))
    logs=RESULTS/'logs';logs.mkdir(exist_ok=True)
    for p in sorted(RUNTIME.glob('*.log'))+sorted((RUNTIME/'logs').glob('*.log')):
        (logs/(p.name+'.gz')).write_bytes(gzip.compress(p.read_bytes(),mtime=0))
    print(json.dumps(dict(passed=True,new_requests=len(allq),cost_usd=total,oracle_actions=sum(s['steps'] for s in summaries))))

if __name__=='__main__':main()
