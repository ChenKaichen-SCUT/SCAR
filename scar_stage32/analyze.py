import csv,subprocess,sys,re
from collections import Counter
from agents.agc.state import extract
from scar_stage31.metrics import audit,totals
from .common import *

def csvwrite(path,records):
    keys=sorted({k for r in records for k in r})
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys,lineterminator='\n');w.writeheader();w.writerows(records)

def main():
    offline();assert read(RESULTS/'verification.json')['passed'];allmetrics=[];evidence=[];reflection=[];requests=[];anomalies=[];timelines={};allq=[];resource_events=[]
    probes={(x['seed'],x['step'],x['reflection_index']):x for x in rows(RESULTS/'online_native_probes.jsonl.gz')}
    for seed in SEEDS:
        for method,folder in [('AGC-v2',baseline(seed)),('SAER',RESULTS/'runs'/ident(seed))]:
            case=f'remnant__s{seed}__{method}';rr=rows(folder/'trajectory.jsonl.gz');qq=rows(folder/'requests.jsonl.gz');s=read(folder/'summary.json');aa,recoveries=audit(rr);timelines[case]=aa
            gzwrite(RESULTS/'action_metrics'/f'{case}.jsonl.gz',aa);c=totals(aa);terminal=read(folder/'decision_exhausted.json') if (folder/'decision_exhausted.json').exists() else None
            dds=[dict(step=r['step'],decision=r['decision'],actual=r) for r in rr]
            if terminal:dds.append(dict(step=terminal['step'],decision=terminal['decision'],actual=None))
            counters=Counter();phases={}
            for entry in dds:
                d=entry['decision'];n=entry['step'];actual=entry['actual']
                counters['native_action_retries']+=d.get('action_retry_calls',0);counters['native_confidence_reviews']+=d.get('confidence_review_calls',0)
                for ordinal,call in enumerate(d.get('saer_calls',[]),1):counters['calls_'+call['phase']]+=1;phases[n,ordinal]=call['phase']
                for i,r in enumerate(d.get('saer_records',[]),1):
                    if 'prediction' not in r:counters['invalid_candidate_skips']+=1;continue
                    p=probes[seed,n,i];a=p['pair']['candidate'];b=p['pair']['final'];changed=bool(a and b and a['action']!=b['action']);applied=p['final_applied'];warning=r['warning']
                    base_visible=extract(actual['observation'] if actual else terminal['observation'])['hands'] is not None
                    cand_dark=bool(a and base_visible and extract(a['feedback'])['hands'] is None and 'too dark to see' in a['feedback']['text'].lower())
                    final_dark=bool(b and base_visible and extract(b['feedback'])['hands'] is None and 'too dark to see' in b['feedback']['text'].lower())
                    x=dict(case=case,seed=seed,step=n,index=i,candidate=r['candidate'],final_proposal=r.get('final_proposal'),prediction=r['prediction'],warning=warning,
                        changed=changed,final_applied=applied,terminal=actual is None,candidate_native=a,final_native=b,
                        rejected_to_accepted=bool(a and not a['accepted'] and b and b['accepted']),accepted_to_rejected=bool(a and a['accepted'] and (not b or not b['accepted'])),
                        avoided_visibility_loss=cand_dark and not final_dark and bool(b),introduced_visibility_loss=not cand_dark and final_dark,
                        actual_new_state=aa[n-1]['new_public_signature'] if applied else None,actual_new_area=aa[n-1]['new_area'] if applied else None,
                        actual_quest_gain=actual['reward']['quest'] if applied else None,actual_wait=actual['action']=='wait' if applied else None,
                        candidate_quest_gain=a['reward']['quest'] if a else None,final_quest_gain=b['reward']['quest'] if b else None,
                        accepted_candidate_to_wait=bool(a and a['accepted'] and a['action']!='wait' and b and b['action']=='wait'),
                        request_ids=[q['request_id'] for q in qq if q['step']==n and r['first_call']<=q['ordinal']<=r['last_call']],risk_veto=False)
                    reflection.append(x)
                    for scope in ['all','applied'] if applied else ['all']:
                        counters[scope+'_reflections']+=1;counters[scope+'_warnings']+=warning;counters[scope+'_changes']+=changed;counters[scope+'_warning_changes']+=warning and changed
                        counters[scope+'_rejected_to_accepted']+=x['rejected_to_accepted'];counters[scope+'_accepted_to_rejected']+=x['accepted_to_rejected']
                        counters[scope+'_avoided_visibility_loss']+=x['avoided_visibility_loss'];counters[scope+'_introduced_visibility_loss']+=x['introduced_visibility_loss']
                    counters['prediction_format_unavailable']+=r['prediction'] is None
                    if applied and warning and changed:
                        counters['warning_changed_new_state']+=x['actual_new_state'];counters['warning_changed_new_area']+=x['actual_new_area'];counters['warning_changed_quest_gain']+=x['actual_quest_gain'];counters['warning_changed_wait']+=x['actual_wait']
            for i,(r,a) in enumerate(zip(rr,aa),1):
                evidence.append(dict(case=case,seed=seed,method=method,step=r['step'],source=str((folder/'trajectory.jsonl.gz').relative_to(ROOT)),line=i,
                    action=r['action'],state_hash_before=r['state_hash_before'],state_hash=r['state_hash'],metrics=a,request_ids=[q['request_id'] for q in qq if q['step']==r['step']]))
                if re.match(r'^(?:drop|discard|store|unequip|give|consume) ',r['action']):
                    before,after=extract(r['observation']),extract(r['feedback'])
                    resource_events.append(dict(case=case,seed=seed,method=method,step=i,action=r['action'],goal=a['goal'],accepted=not a['public_rejected'],
                        changes={k:dict(before=before[k],after=after[k]) for k in ['hands','equipment','observed_container_contents','ground'] if before[k]!=after[k]},
                        shadow_resource_risk=any(x['kind']=='required_resource_custody_risk' for x in a['shadow_assessment']['reasons']),
                        removal_visibility_lost=a['removal_visibility_lost'],feedback=r['feedback'],source=str((folder/'trajectory.jsonl.gz').relative_to(ROOT)),
                        irreversible_material_loss_established=False,critical_resource_truth='Not inferred from goal name or removal alone.'))
            for q in qq:
                phase=phases.get((q['step'],q['ordinal']),'native_decision')
                requests.append(dict(case=case,step=q['step'],ordinal=q['ordinal'],phase=phase,request_id=q['request_id'],new=method=='SAER',cost_usd=q.get('cost_usd',0),input_tokens=q.get('usage',{}).get('prompt_tokens',0),output_tokens=q.get('usage',{}).get('completion_tokens',0)))
                if method=='SAER':allq.append(q)
                issue=[];parsed=q.get('parsed_json')
                if q.get('parse_exception'):issue.append(q['parse_exception'])
                if q['status']!='ok':issue.append(q['status'])
                if q.get('raw_response') and q['raw_response']['choices'][0]['finish_reason']!='stop':issue.append('finish_reason:'+q['raw_response']['choices'][0]['finish_reason'])
                fields=['predicted_effect','goal_risk','reason'] if phase=='reflection' else ['action','reasoning','goal_description','goal_evidence']
                if q['status']=='ok':issue+=['missing_'+k for k in fields if not isinstance(parsed,dict) or not isinstance(parsed.get(k),str)]
                if issue:anomalies.append(dict(case=case,step=q['step'],ordinal=q['ordinal'],phase=phase,request_id=q['request_id'],issues=issue,new=method=='SAER'))
            allmetrics.append(dict(case=case,seed=seed,method=method,status=s['status'],counts=c,reflection_counts=dict(counters),recoveries=recoveries,terminal=terminal,
                scores=s['scores'],main_quest_progress=s['main_quest_progress'],requests=len(qq),input_tokens=sum(q.get('usage',{}).get('prompt_tokens',0) for q in qq),
                output_tokens=sum(q.get('usage',{}).get('completion_tokens',0) for q in qq),cost_usd=sum(q.get('cost_usd',0) for q in qq),
                peak_reference_cost_usd=sum(q.get('peak_rate_reference_cost_usd',0) for q in qq),max_prompt_tokens=max(q.get('usage',{}).get('prompt_tokens',0) for q in qq),
                rates_per100={k:100*c.get(k,0)/max(1,len(rr)) for k in ['public_rejected','repeated_failure','wait','reacquisition_cycles','removal_visibility_lost']},source=str(folder.relative_to(ROOT))))
    pairs=[]
    for seed in SEEDS:
        a,b=[next(r for r in allmetrics if r['seed']==seed and r['method']==method) for method in ['AGC-v2','SAER']];n=min(a['counts']['actions'],b['counts']['actions'])
        aa=timelines[a['case']];bb=timelines[b['case']];div=next((i+1 for i,(x,y) in enumerate(zip(aa,bb)) if x['action']!=y['action']),None)
        pairs.append(dict(seed=seed,common_actions=n,AGC_v2=totals(aa[:n]),SAER=totals(bb[:n]),main_delta=b['counts']['main_final']-a['counts']['main_final'],chapter_delta=b['counts']['chapter1']-a['counts']['chapter1'],
            extra_method_early_stop=b['status']=='agent_decision_exhausted',first_action_divergence=div))
    gain=sum(p['main_delta']>0 or p['chapter_delta']>0 for p in pairs);worse=any(p['main_delta']<0 or p['chapter_delta']<0 for p in pairs);early=any(p['extra_method_early_stop'] for p in pairs)
    ea=sum(p['AGC_v2']['public_rejected'] for p in pairs);eb=sum(p['SAER']['public_rejected'] for p in pairs);better=sum(p['SAER']['public_rejected']<p['AGC_v2']['public_rejected'] for p in pairs)
    local=better>=2 and ea>0 and eb<=.9*ea
    verdict='REGRESSION_OR_BLOCKING' if worse or early else 'PROGRESS_AND_RELIABILITY_SUPPORT' if gain>=2 and local else 'LOCAL_RELIABILITY_ONLY' if local else 'NO_CLEAR_SUPPORT'
    write(RESULTS/'metrics.json',allmetrics);write(RESULTS/'paired_comparison.json',pairs);gzwrite(RESULTS/'evidence_index.jsonl.gz',evidence);gzwrite(RESULTS/'reflection_audit.jsonl.gz',reflection)
    gzwrite(RESULTS/'resource_events.jsonl.gz',resource_events)
    write(RESULTS/'response_anomalies.json',anomalies);csvwrite(RESULTS/'request_index.csv',requests)
    write(RESULTS/'conclusion.json',dict(verdict=verdict,main_better_pairs=gain,any_main_regression=worse,extra_method_early_stop=early,error_reduction_pairs=better,
        common_rejections_baseline=ea,common_rejections_saer=eb,threshold_error_reduction=local,strict_causal_module_effect=False,new_analysis_model_calls=0))
    flat=[dict(case=r['case'],status=r['status'],**r['counts'],requests=r['requests'],cost_usd=r['cost_usd'],input_tokens=r['input_tokens'],output_tokens=r['output_tokens']) for r in allmetrics];csvwrite(RESULTS/'comparison.csv',flat)
    official=[]
    for method in ['AGC-v2','SAER']:
        folders=[baseline(seed) if method=='AGC-v2' else RESULTS/'runs'/ident(seed) for seed in SEEDS]
        args=[sys.executable,str(ENGINE/'challenge_eval.py'),'--remnant',*[str(p) for p in folders],'--json'];r=json.loads(subprocess.run(args,capture_output=True,text=True,check=True).stdout)
        assert r['games']['remnant']['main_quest']==sum(x['counts']['main_final'] for x in allmetrics if x['method']==method)/3
        official.append(dict(method=method,args=args,result=r,scorer_sha256=sha(ENGINE/'challenge_eval.py')))
    write(RESULTS/'official_scores.json',official);print(json.dumps(read(RESULTS/'conclusion.json')),flush=True)

if __name__=='__main__':main()
