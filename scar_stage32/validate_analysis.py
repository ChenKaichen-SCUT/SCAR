"""Independent coverage, call accounting, and evidence integrity checks."""
import csv,math
from .common import *

def main():
    offline();check_freeze();assert read(RESULTS/'verification.json')['passed'];cost=read(RESULTS/'cost_reconciliation.json');metrics=read(RESULTS/'metrics.json')
    evidence=rows(RESULTS/'evidence_index.jsonl.gz');keyed={(x['case'],x['step']):x for x in evidence};assert len(keyed)==len(evidence)
    reflection=rows(RESULTS/'reflection_audit.jsonl.gz');probes=rows(RESULTS/'online_native_probes.jsonl.gz');assert len(reflection)==len(probes)
    allq=[];historical=[];receipts=[];total_actions=0
    for seed in SEEDS:
        for method,folder in [('AGC-v2',baseline(seed)),('SAER',RESULTS/'runs'/ident(seed))]:
            name=f'remnant__s{seed}__{method}';rr=rows(folder/'trajectory.jsonl.gz');qq=rows(folder/'requests.jsonl.gz');s=read(folder/'summary.json');m=next(x for x in metrics if x['case']==name)
            assert len(rr)==s['steps']==m['counts']['actions'];assert [r['step'] for r in rr]==list(range(1,len(rr)+1))
            assert s['initial_state_hash']==read(initial(seed)/'initial_public.json')['initial_state_hash'];assert s['max_steps']==300
            terminal=read(folder/'decision_exhausted.json') if (folder/'decision_exhausted.json').exists() else None
            assert (terminal is not None)==(s['status']=='agent_decision_exhausted')
            if s['status']=='step_limit':assert len(rr)==300
            decisions=[dict(step=r['step'],decision=r['decision'],row=r) for r in rr]
            if terminal:
                assert terminal['step']==len(rr)+1 and terminal['decision']['executed_action'] is None
                decisions.append(dict(step=terminal['step'],decision=terminal['decision'],row=None))
            for n,r in enumerate(rr,1):
                e=keyed[name,n];assert e['line']==n and e['action']==r['action'] and e['state_hash']==r['state_hash'] and e['state_hash_before']==r['state_hash_before']
                assert e['source']==str((folder/'trajectory.jsonl.gz').relative_to(ROOT));assert e['request_ids']==[q['request_id'] for q in qq if q['step']==n]
                assert r['action']==r['decision']['executed_action']==r['decision']['attempts'][-1]['proposal']['action'].strip()
                assert not r['decision']['controller_generated_action']
            for entry in decisions:
                d=entry['decision'];qs=[q for q in qq if q['step']==entry['step'] and q['status']=='ok']
                assert len(d['attempts'])==1+d['action_retry_calls']+d['confidence_review_calls']
                if method=='SAER':
                    assert not d['saer_risk_veto'] and not d['saer_generated_action'];assert len(d['saer_records'])==len(d['attempts'])
                    assert len(d['saer_calls'])==len(qs)
                    for call,q in zip(d['saer_calls'],qs):
                        assert call['input_tokens']==q['usage']['prompt_tokens'] and call['output_tokens']==q['usage']['completion_tokens']
                        assert call['response']==q['raw_response']['choices'][0]['message']['content']
                    for rec in d['saer_records']:
                        assert not rec['risk_veto'];assert rec['last_call']-rec['first_call']+1==(3 if 'prediction' in rec else 1)
                    if entry['row']:
                        assert entry['row']['input_tokens']==sum(q['usage']['prompt_tokens'] for q in qs)
                        assert entry['row']['output_tokens']==sum(q['usage']['completion_tokens'] for q in qs)
                else:assert len(qs)==len(d['attempts'])
            assert sum(r['reward']['quest'] for r in rr)==s['scores']['quest']==m['counts']['main_final']
            assert len(qq)==m['requests'];assert math.isclose(sum(q.get('cost_usd',0) for q in qq),m['cost_usd'],abs_tol=1e-12)
            (allq if method=='SAER' else historical).extend(qq);total_actions+=len(rr);receipts.append(dict(seed=seed,method=method,actions=len(rr),requests=len(qq)))
    assert SEEDS==[42];assert len(historical)==len(rows(baseline(42)/'requests.jsonl.gz'));assert len(evidence)==total_actions
    assert not (RESULTS/'offline').exists() and not (RESULTS/'samples.json').exists()
    assert len(allq)==cost['new_requests'] and len({q['request_id'] for q in allq})==len(allq)
    assert math.isclose(sum(q.get('cost_usd',0) for q in allq),cost['cost_usd'],abs_tol=1e-12)
    assert sum(q['usage']['prompt_tokens'] for q in allq)==cost['input_tokens'];assert sum(q['usage']['completion_tokens'] for q in allq)==cost['output_tokens']
    with (RESULTS/'request_index.csv').open() as f:ri=list(csv.DictReader(f))
    assert len(ri)==len(historical)+len(allq);assert sum(x['new']=='True' for x in ri)==len(allq)
    for name in ['Stage32实验报告.md','语法修复与单种子协议.md','动作反思与语法审计.md','三游戏扩展与研究判断.md']:
        assert (REPORTS/name).stat().st_size>100
    write(RESULTS/'analysis_verification.json',dict(passed=True,receipts=receipts,actions=total_actions,new_requests=len(allq),historical_requests=len(historical),
        all_samples_retained=True,all_call_roles_accounted=True,all_evidence_checked=True,raw_usage_verified=True,saer_risk_vetoes=0,new_model_calls=0))
    print(json.dumps(dict(passed=True,actions=total_actions,new_requests=len(allq))),flush=True)

if __name__=='__main__':main()
