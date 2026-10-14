"""Reconcile the three formal runs and six user-cancelled partial runs."""
import math
import sqlite3
from collections import Counter
from .common import *
from scar.providers.deepseek import estimate_cost
from scar_stage22.provider import prices_at


def ledger(path):
    with sqlite3.connect(f'file:{path}?mode=ro',uri=True) as db:
        return db.execute('select id,charged,status from requests').fetchall()


def main():
    offline();integrity=check_freeze();allq=[];cases=[]
    scope=read(RESULTS/'scope_amendment.json');cancellation=read(RUNTIME/'user_cancellation.json')
    assert cancellation['retained_seeds']==[42] and cancellation['cancelled_seeds']==[43,44]
    for game,seed in CASES:
        ident=case_id(game,seed);folder=RESULTS/'runs'/ident;runtime=RUNTIME/'runs'/ident
        s=read(folder/'summary.json');qq=rows(folder/'requests.jsonl.gz');allq+=qq
        formal=seed==42
        assert len(qq)==s['requests']
        led=ledger(runtime/'budget.sqlite')
        assert {x[0] for x in led}=={q['request_id'] for q in qq}
        assert all(x[2] in ['ok','http_rejected'] for x in led)
        assert math.isclose(sum(x[1] for x in led),s['cost_usd'],abs_tol=1e-12)
        assert not (runtime/'pending_request.json').exists()
        receipt=None
        if formal:
            assert s['status'] in ['step_limit','native_done','agent_decision_exhausted']
            receipt=read(RESULTS/'verification'/f'{ident}.json')
            assert receipt['passed'] and receipt['exact_native_steps']==s['steps']
        else:
            assert s['status']=='infrastructure_error'
            assert s['error']['type']=='IntegrityError' and 'user cancelled this seed' in s['error']['message']
            assert ident in {c['case'] for c in cancellation['cases']}
            with sqlite3.connect(f'file:{runtime}/budget.sqlite?mode=ro',uri=True) as db:
                trigger=db.execute("select sql from sqlite_master where type='trigger' and name='stage25_user_cancel'").fetchone()
            assert trigger and 'BEFORE INSERT' in trigger[0] and 'RAISE(ABORT' in trigger[0]
            assert max(q['start'] for q in qq)<=cancellation['requested_at_unix']
        cases.append(dict(case=ident,game=game,seed=seed,formal=formal,status=s['status'] if formal else 'user_cancelled',
            raw_status=s['status'],actions=s['steps'],requests=len(qq),cost_usd=s['cost_usd'],
            input_tokens=s['input_tokens'],output_tokens=s['output_tokens'],verification=receipt,
            summary=str((folder/'summary.json').relative_to(ROOT))))
    for q in allq:
        if q['status']=='ok':
            assert q['unit_prices']==prices_at(q['raw_response'].get('created') or q['start'])
            assert math.isclose(estimate_cost(q['usage'],q['unit_prices']),q['cost_usd'],abs_tol=1e-12)
            assert q['charged_or_reserved_usd']==q['cost_usd']
        else:assert q['status']=='http_rejected' and q['charged_or_reserved_usd']==0
    led=ledger(RUNTIME/'budget.sqlite');ids={q['request_id'] for q in allq}
    guards=[x for x in led if x[0] not in ids]
    assert len(guards)==6 and all(x[1]==0 and x[2]=='episode_budget_abort' for x in guards)
    assert ids=={x[0] for x in led if x[0] in ids} and len(led)==len(allq)+6
    assert len(ids)==len(allq)
    total=sum(q.get('cost_usd',0) for q in allq)
    assert math.isclose(sum(x[1] for x in led),total,abs_tol=1e-12)
    groups={}
    for name,formal in [('formal',True),('user_cancelled',False)]:
        subset=[c for c in cases if c['formal']==formal]
        groups[name]={key:sum(c[key] for c in subset) for key in ['actions','requests','cost_usd','input_tokens','output_tokens']}
        groups[name]['cases']=len(subset)
    result=dict(passed=True,unique_new_requests=len(allq),cost_usd=total,groups=groups,cases=cases,
        ledger_statuses=dict(Counter(x[2] for x in led)),zero_cost_pre_dispatch_cancellation_guards=len(guards),
        cancelled_cases_no_api_request_started_after_cancellation=True,
        unsettled_reservations=0,unknown_billing=0,
        invalid_json_responses=sum(bool(q.get('parse_exception')) for q in allq),
        truncated_responses=sum(q.get('raw_response',{}).get('choices',[{}])[0].get('finish_reason')=='length' for q in allq),
        per_response_pricing_verified=True,account_invoice_available=False,new_analysis_model_calls=0,
        scope_reference='results/stage25/scope_amendment.json',
        unit_prices=[json.loads(s) for s in sorted({json.dumps(q['unit_prices'],sort_keys=True) for q in allq if 'unit_prices' in q})])
    write(RESULTS/'cost_reconciliation.json',result)
    write(RESULTS/'effective_completion.json',dict(complete=True,formal_cases=[c for c in cases if c['formal']],
        cancelled_cases=[c for c in cases if not c['formal']],freeze_integrity=integrity,
        original_baseline_reruns=0,formal_seeds=[42],raw_batch_complete_false_reason='six user cancellations, not six algorithm failures'))
    logs=RESULTS/'logs';logs.mkdir(exist_ok=True)
    for p in sorted(RUNTIME.glob('*.log'))+sorted((RUNTIME/'logs').glob('*.log')):
        (logs/(p.name+'.gz')).write_bytes(gzip.compress(p.read_bytes(),mtime=0))
    write(RESULTS/'cancellations.json',cancellation)
    print(json.dumps(dict(passed=True,groups=groups,total_usd=total)))


if __name__=='__main__':main()
