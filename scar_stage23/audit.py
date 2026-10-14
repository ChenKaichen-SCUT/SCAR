"""Offline evidence indices, response/cost reconciliation and paired contrasts."""
from collections import Counter
from .common import *
from .analyze import csvwrite


def main():
    from scar_stage22b.common import forbid_network
    from scar.io import digest
    forbid_network();check_freeze()
    metrics=read(RESULTS/'metrics.json');original=rows(SOURCE/'trajectory.jsonl.gz')
    source_requests={r['step']:r for r in rows(SOURCE/'requests.jsonl.gz')}
    contrasts=[];index=[];cost_rows=[];anomalies=[];evidence=[];milestones=[]
    unique_paid=set();all_cost=0.;all_tokens=[0,0];all_calls=0
    for start in CASES:
        case=case_id(start);traces={};requests={}
        for variant in VARIANTS:
            folder=RESULTS/'runs'/case/variant
            traces[variant]=rows(folder/'trajectory.jsonl.gz')
            req=[source_requests[n] for n in range(start,301)] if variant==VARIANTS[0] else rows(folder/'requests.jsonl.gz')
            requests[variant]=req
            paid=[] if variant==VARIANTS[0] else rows(folder/'paid_requests.jsonl.gz')
            summary=read(folder/'summary.json');counts=Counter();total=0.;finish=Counter()
            for p in paid:
                assert p['request_id'] not in unique_paid
                unique_paid.add(p['request_id']);assert p['status']=='ok' and p['attempt']==0
                u=p['usage'];prices=p['unit_prices']
                expected=(u['prompt_cache_hit_tokens']*prices['cache_hit']+u['prompt_cache_miss_tokens']*prices['cache_miss']+u['completion_tokens']*prices['output'])/1e6
                assert abs(expected-p['cost_usd'])<1e-10
                assert abs(p['charged_or_reserved_usd']-p['cost_usd'])<1e-10
                total+=expected
                for key in ['prompt_tokens','completion_tokens','prompt_cache_hit_tokens','prompt_cache_miss_tokens']:counts[key]+=u[key]
            assert len(paid)==summary['new_model_requests'] and abs(total-summary['new_model_cost_usd'])<1e-9
            all_cost+=total;all_calls+=len(paid);all_tokens[0]+=counts['prompt_tokens'];all_tokens[1]+=counts['completion_tokens']
            for q in req:
                choice=q['raw_response']['choices'][0];finish[choice.get('finish_reason')]+=1
                j=q.get('parsed_json');bad=not isinstance(j,dict) or not isinstance(j.get('action'),str) or not isinstance(j.get('reasoning'),str)
                if bad or choice.get('finish_reason')!='stop':
                    anomalies.append(dict(case=case,variant=variant,step=q['step'],request_id=q['request_id'],
                        sample_origin=q.get('sample_origin','Stage22-original'),finish_reason=choice.get('finish_reason'),
                        bad_schema=bad,raw_content=choice['message'].get('content'),handling='Frozen agent JSON parsing/fallback; no resampling.'))
            cost_rows.append(dict(case=case,variant=variant,new_requests=len(paid),cost_usd=total,
                **dict(counts),logical_requests=len(req),logical_input_tokens=sum(q['usage']['prompt_tokens'] for q in req),
                logical_output_tokens=sum(q['usage']['completion_tokens'] for q in req),
                minimum_input_tokens=min(q['usage']['prompt_tokens'] for q in req),maximum_input_tokens=max(q['usage']['prompt_tokens'] for q in req),
                first_input_tokens=req[0]['usage']['prompt_tokens'],last_input_tokens=req[-1]['usage']['prompt_tokens'],finish_reasons=dict(finish)))
            m=next(m for m in metrics if m['case']==case and m['variant']==variant)
            selected={start,300,m['first_reset'],m['first_effective_release'],m['first_quest_gain'],m['chapter1_step'],m['first_new_fact_after_reset']}
            selected|={x['step'] for x in m['quest_events']}
            if m['wait_runs']:
                longest=max(m['wait_runs'],key=lambda x:x['length']);selected|={longest['start'],longest['end']}
            for row in traces[variant]:
                n=row['step'];decision=row.get('decision') or original[n-1]['decision']
                ref=f'results/stage23/runs/{case}/{variant}/trajectory.jsonl.gz:{n-start+1}'
                index.append(dict(case=case,variant=variant,step=n,trace=ref,
                    full_decision=ref if variant!=VARIANTS[0] else f'results/stage22/runs/mark__Stage18-Fixed/trajectory.jsonl.gz:{n}',
                    model_request=f'results/stage23/runs/{case}/{variant}/requests.jsonl.gz:{n-start+1}' if variant!=VARIANTS[0] else f'results/stage22/runs/mark__Stage18-Fixed/requests.jsonl.gz:{n}',
                    pre_state_sha256=row['state_hash_before'],post_state_sha256=row['state_hash']))
                if row['reward']['quest']:
                    milestones.append(dict(case=case,variant=variant,step=n,action=row['action'],quest_gain=row['reward']['quest'],
                        quest_score=row['scores']['quest'],quest_state=row['main_quest_progress'],feedback=row['feedback'],trace=ref))
                if n in selected:
                    evidence.append(dict(case=case,variant=variant,step=n,trace=ref,observation=row['observation'],
                        action=row['action'],proposal=decision['proposed_action'],feedback=row['feedback'],
                        reset=row.get('reset'),decision=decision,quest_gain=row['reward']['quest'],quest_score=row['scores']['quest']))
        b,c=(traces[v] for v in VARIANTS[1:])
        for other in VARIANTS[1:]:
            a=traces[VARIANTS[0]];d=traces[other]
            k=next((i for i,(x,y) in enumerate(zip(a,d)) if x['action']!=y['action']),None)
            same_first=req_equal=requests[other][0]['messages']==requests[VARIANTS[0]][0]['messages']
            q=dict(case=case,comparison=f'Stage18-Origin vs {other}',first_action_divergence=None if k is None else start+k,
                initial_context_exact=same_first,initial_raw_response_exact=requests[other][0]['raw_response']==requests[VARIANTS[0]][0]['raw_response'])
            if k is not None:
                q.update(origin_action=a[k]['action'],variant_action=d[k]['action'],
                    same_state_at_divergence=a[k]['state_hash_before']==d[k]['state_hash_before'],
                    same_context_at_divergence=requests[VARIANTS[0]][k]['messages']==requests[other][k]['messages'],
                    same_raw_response_at_divergence=requests[VARIANTS[0]][k]['raw_response']==requests[other][k]['raw_response'],
                    origin_feedback=a[k]['feedback'],variant_feedback=d[k]['feedback'])
            contrasts.append(q)
        contrasts.append(dict(case=case,comparison='Stage18-Reset vs Oracle-Reset',
            identical_action_and_state_path=all(x['action']==y['action'] and x['state_hash']==y['state_hash'] for x,y in zip(b,c)) and len(b)==len(c),
            first_action_divergence=next((x['step'] for x,y in zip(b,c) if x['action']!=y['action']),None),
            identical_model_messages=sum(x['messages']==y['messages'] for x,y in zip(requests[VARIANTS[1]],requests[VARIANTS[2]]))))
    expected=read(RESULTS/'costs.json')
    assert all_calls==expected['new_model_requests'] and abs(all_cost-expected['usage_priced_usd'])<1e-8
    assert all_tokens==[expected['input_tokens'],expected['output_tokens']]
    groups=[]
    for name,starts in [('primary_early',[33,35]),('other_checkpoints',[52,64,70,100,179,193,244,271]),
                         ('remaining_ge200',[33,35,52,64,70,100]),('remaining_100_to199',[179,193]),('remaining_lt100',[244,271])]:
        for variant in VARIANTS:
            mm=[r for r in metrics if r['start'] in starts and r['variant']==variant]
            groups.append(dict(group=name,variant=variant,checkpoints=len(mm),gained_main_reward=sum(r['main_reward_gain']>0 for r in mm),
                chapter1_completed=sum(r['chapter1_completed'] for r in mm),reward_sum=sum(r['main_reward_gain'] for r in mm),
                actions=sum(r['actual_actions'] for r in mm),waits=sum(r['wait_count'] for r in mm)))
    write(RESULTS/'paired_contrasts.json',contrasts);write(RESULTS/'cost_reconciliation.json',dict(passed=True,new_requests=all_calls,
        usage_priced_usd=all_cost,input_tokens=all_tokens[0],output_tokens=all_tokens[1],all_requests_ok=True,retries=0,
        unresolved_reservations=0,variants=cost_rows,anomaly_references=anomalies,
        unique_new_anomalies=len({r['request_id'] for r in anomalies if r['sample_origin']=='new-model-request'})))
    write(RESULTS/'stratified.json',groups);write(RESULTS/'quest_milestones.json',milestones)
    gzwrite(RESULTS/'key_evidence.jsonl.gz',evidence);csvwrite(RESULTS/'evidence_index.csv',index)
    print(json.dumps(dict(all_trace_rows=len(index),new_requests=all_calls,cost=all_cost,anomaly_references=len(anomalies),paired_contrasts=len(contrasts))))


if __name__=='__main__':main()
