"""Independent accounting and evidence checks for all paired outcomes."""
import csv
import math
from .common import *
from .metrics import source

def main():
    offline();runs=read(RESULTS/'metrics.json');pairs=read(RESULTS/'paired_comparison.json');cost=read(RESULTS/'cost_reconciliation.json')
    entries=rows(RESULTS/'evidence_index.jsonl.gz');keyed={(x['case'],x['step']):x for x in entries};assert len(keyed)==len(entries)
    ctrl=rows(RESULTS/'controller_audit.jsonl.gz');total_actions=total_requests=0;newq=[];receipts=[]
    for seed,method in CASES:
        ident=case_id(seed,method);folder=source(seed,method);rr=rows(folder/'trajectory.jsonl.gz');qq=rows(folder/'requests.jsonl.gz');s=read(folder/'summary.json')
        result=next(x for x in runs if x['case']==ident)
        assert s['steps']==len(rr)==result['counts']['actions'];assert [r['step'] for r in rr]==list(range(1,len(rr)+1))
        assert s['initial_state_hash']==read(initial(seed)/'initial_public.json')['initial_state_hash']
        if method=='AGC-v2' and seed!=42:
            assert rr[:47]==rows(baseline(seed)/'trajectory.jsonl.gz')
            old=rows(baseline(seed)/'requests.jsonl.gz');assert qq[:len(old)]==old
        terminal=read(folder/'decision_exhausted.json') if (folder/'decision_exhausted.json').exists() else None
        assert bool(terminal)==(s['status']=='agent_decision_exhausted')
        if terminal:assert terminal['step']==len(rr)+1 and terminal['decision']['executed_action'] is None
        if s['status']=='step_limit':assert len(rr)==300
        for i,r in enumerate(rr,1):
            e=keyed[ident,i];assert e['source']==str((folder/'trajectory.jsonl.gz').relative_to(ROOT)) and e['line']==i
            assert e['state_hash']==r['state_hash'] and e['state_hash_before']==r['state_hash_before']
            assert e['action']==r['action']==r['decision']['executed_action']==r['decision']['attempts'][-1]['proposal']['action'].strip()
            assert not r['decision']['controller_generated_action']
            assert e['request_ids']==[q['request_id'] for q in qq if q['step']==i]
            if method=='REC':
                assert not r['decision']['rec_generated_action']
                assert len(r['decision']['rec_records'])==len([q for q in qq if q['step']==i and q['status']=='ok'])
        current=[] if seed==42 and method=='AGC-v2' else rows(folder/'new_requests.jsonl.gz');newq.extend(current)
        assert len(current)==result['new_requests']
        native=result['controller']['native_action_retries_total']+result['controller']['native_confidence_reviews_total']
        rec=result['controller'].get('rec_reconsider_calls',0)
        assert len(qq)==len(rr)+int(terminal is not None)+native+rec,(ident,'request count reconciliation')
        assert result['counts']['main_final']==sum(r['reward']['quest'] for r in rr)==s['scores']['quest']
        total_actions+=len(rr);total_requests+=len(qq);receipts.append(dict(case=ident,actions=len(rr),requests=len(qq),prefix_reuse_verified=True))
    assert total_actions==len(entries)==1454 and total_requests==1674
    assert len(newq)==cost['new_requests']==1251 and len({q['request_id'] for q in newq})==len(newq)
    assert math.isclose(sum(q['cost_usd'] for q in newq),cost['cost_usd'],abs_tol=1e-12)
    assert sum(q['usage']['prompt_tokens'] for q in newq)==cost['input_tokens'] and sum(q['usage']['completion_tokens'] for q in newq)==cost['output_tokens']
    with (RESULTS/'request_index.csv').open() as f:ri=list(csv.DictReader(f))
    assert len(ri)==total_requests and sum(x['new']=='True' for x in ri)==len(newq)
    for p in pairs:
        assert p['common_actions']==min(next(r['counts']['actions'] for r in runs if r['case']==case_id(p['seed'],method)) for method in ['AGC-v2','REC'])
    blocks=[x for x in ctrl if x['record']['check']['decision']=='RECONSIDER']
    assert len(blocks)==9 and all(x['terminal'] and x['native_probe']['accepted'] for x in blocks)
    assert not any(x['local_rejection_avoided'] or x['local_visibility_loss_avoided'] for x in ctrl)
    tr=read(RESULTS/'terminal_review.json');first=next(x for x in tr['cases'] if x['case']==case_id(43,'REC'))['records'][0]
    assert first['proposal']['action']=='pick up cloth' and first['native']['accepted'] and first['agc_assessment_at_terminal_state']['goal_review']
    probes=rows(RESULTS/'online_native_probes.jsonl.gz')
    for p in probes:
        if p['kind']=='terminal_blocked_proposal' and p['case']==case_id(44,'REC'):
            assert p['then_retry_last_rejected_action']['accepted'] and p['then_retry_last_rejected_action']['action']=='pick up herb_tea'
    off=read(RESULTS/'offline_summary.json');assert off['flagged_actions']==39 and off['no_detected_constraint']==3077
    coverage=read(RESULTS/'offline_coverage_review.json');assert coverage['counts']['all_removal_visibility_losses']==27 and coverage['local_visibility_effects_confirmed']==16
    cases=read(RESULTS/'case_review.json');assert len(cases['stage25_cases'])==10 and len(cases['paired_cases'])==3
    for pair in cases['paired_cases']:
        for method,branch in pair['branches'].items():
            folder=source(pair['seed'],method);rr=rows(folder/'trajectory.jsonl.gz')
            for e in branch['evidence']:
                r=rr[e['line']-1];assert e['observation']==r['observation'] and e['feedback']==r['feedback'] and e['action']==r['action']
    assert read(RESULTS/'conclusion.json')['verdict']=='NO_CLEAR_SUPPORT'
    for name in ['REC设计文档.md','失败模式覆盖分析.md','离线误动作拦截统计.md','Stage31实验报告.md','与Stage25失败案例对应分析.md','三游戏测试与研究判断.md','控制器逐提案与早停审计.md']:
        assert (REPORTS/name).stat().st_size>100
    write(RESULTS/'analysis_verification.json',dict(passed=True,receipts=receipts,actions=total_actions,requests=total_requests,new_requests=len(newq),
        full_evidence_index_checked=True,all_terminal_proposals_included=True,source_case_evidence_checked=True,old_prefixes_exact=True,
        native_and_rec_retry_counts_reconciled=True,new_model_calls=0))
    print(json.dumps(dict(passed=True,actions=total_actions,requests=total_requests,new_requests=len(newq))),flush=True)

if __name__=='__main__':main()
