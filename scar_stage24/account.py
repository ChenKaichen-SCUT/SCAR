"""Reconcile saved responses with local billing ledger; no model access."""
import math
import sqlite3
from collections import Counter
from .common import *
from .analyze import final_folder
from scar.providers.deepseek import estimate_cost
from scar_stage22.provider import prices_at


def main():
    offline();integrity=check_freeze();allq=[];completed=[]
    for game in GAMES:
        folder=final_folder(game);s=read(folder/'summary.json');q=rows(folder/'requests.jsonl.gz');allq+=q
        assert s['status'] in ['step_limit','native_done','agent_decision_exhausted']
        assert len(q)==s['requests']
        with sqlite3.connect(f'file:{RUNTIME}/runs/{game}__AGC/budget.sqlite?mode=ro',uri=True) as db:
            ledger=db.execute('select id,charged,status from requests').fetchall()
        assert {x[0] for x in ledger}=={r['request_id'] for r in q}
        assert all(x[2]=='ok' for x in ledger)
        assert math.isclose(sum(x[1] for x in ledger),s['cost_usd'],abs_tol=1e-12)
        receipt=read(RESULTS/'verification'/f"{game}__{'resumed' if 'resumed' in folder.parts else 'first_pass'}.json")
        assert receipt['passed'] and receipt['exact_native_steps']==s['steps']
        completed.append(dict(game=game,status=s['status'],actions=s['steps'],summary=str((folder/'summary.json').relative_to(ROOT)),verification=receipt))
    for q in allq:
        assert q['status']=='ok'
        assert q['unit_prices']==prices_at(q['raw_response'].get('created') or q['start'])
        assert math.isclose(estimate_cost(q['usage'],q['unit_prices']),q['cost_usd'],abs_tol=1e-12)
        assert q['charged_or_reserved_usd']==q['cost_usd']
    with sqlite3.connect(f'file:{RUNTIME}/budget.sqlite?mode=ro',uri=True) as db:
        ledger=db.execute('select id,charged,status from requests').fetchall()
    assert {x[0] for x in ledger}=={q['request_id'] for q in allq} and len(ledger)==len(allq)
    total=sum(q['cost_usd'] for q in allq)
    assert math.isclose(sum(x[1] for x in ledger),total,abs_tol=1e-12)
    result=dict(passed=True,unique_new_requests=len(allq),cost_usd=total,
        ledger_statuses=dict(Counter(x[2] for x in ledger)),unsettled_reservations=0,unknown_billing=0,
        invalid_json_responses=sum(bool(q.get('parse_exception')) for q in allq),
        truncated_responses=sum(q['raw_response']['choices'][0]['finish_reason']=='length' for q in allq),
        per_response_pricing_verified=True,account_invoice_available=False,new_analysis_model_calls=0,
        original_requests_in_continuations_counted_once=True,
        unit_prices=[json.loads(s) for s in sorted({json.dumps(q['unit_prices'],sort_keys=True) for q in allq})])
    write(RESULTS/'cost_reconciliation.json',result)
    write(RESULTS/'completion.json',dict(complete=True,games=completed,freeze_integrity=integrity,
        original_baseline_reruns=0,additional_seeds=0,hybrid_policy_continuations=['remnant','mark']))
    logs=RESULTS/'logs';logs.mkdir(exist_ok=True)
    for p in sorted(RUNTIME.glob('*.log'))+sorted((RUNTIME/'logs').glob('*.log')):
        (logs/(p.name+'.gz')).write_bytes(gzip.compress(p.read_bytes(),mtime=0))
    print(json.dumps(result))

if __name__=='__main__':main()
