"""Recomputable paired metrics; all episodes and terminal proposals retained."""
import csv
import subprocess
import sys
from collections import Counter
from .common import *
from .metrics import source,audit,totals,goal
from agents.rec_v1.state import visible

def csvwrite(path,records):
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(records[0]),lineterminator='\n');w.writeheader();w.writerows(records)

def main():
    offline();assert read(RESULTS/'verification.json')['passed'];runs=[];by={};decisions=[];anomalies=[];requests=[];index=[];timelines={}
    probes=rows(RESULTS/'online_native_probes.jsonl.gz');probe_lookup={(p['case'],p['step'],p['kind'],(p.get('evidence') or {}).get('record_index')):p for p in probes}
    terminal_review={x['case']:x for x in read(RESULTS/'terminal_review.json')['cases']}
    for seed,method in CASES:
        ident=case_id(seed,method);folder=source(seed,method);rr=rows(folder/'trajectory.jsonl.gz');qq=rows(folder/'requests.jsonl.gz');s=read(folder/'summary.json')
        aa,recoveries=audit(rr);gzwrite(RESULTS/'action_metrics'/f'{ident}.jsonl.gz',aa);timelines[ident]=aa;tt=totals(aa);by[ident]=rr
        terminal=read(folder/'decision_exhausted.json') if (folder/'decision_exhausted.json').exists() else None
        dds=[dict(step=r['step'],decision=r['decision'],actual=r) for r in rr]
        if terminal:dds.append(dict(step=terminal['step'],decision=terminal['decision'],actual=None))
        counts=Counter()
        for entry in dds:
            n=entry['step'];d=entry['decision'];actual=entry['actual'];records=d.get('rec_records',[])
            counts['rec_reconsider_calls']+=d.get('rec_reconsider_calls',0);counts['rec_blocked_proposals']+=sum(x['check']['decision']=='RECONSIDER' for x in records)
            counts['decisions_triggering_rec']+=any(x['check']['decision']=='RECONSIDER' for x in records)
            counts['native_action_retries_recorded']+=d.get('action_retry_calls',0);counts['native_confidence_reviews_recorded']+=d.get('confidence_review_calls',0)
            counts['controller_generated_actions']+=bool(d.get('controller_generated_action') or d.get('rec_generated_action'))
            for i,record in enumerate(records,1):
                kind='blocked_proposal' if actual else 'terminal_blocked_proposal';p=probe_lookup.get((ident,n,kind,i))
                candidate=record.get('proposal');candidate_action=candidate.get('action') if isinstance(candidate,dict) else None
                actual_good=not aa[n-1]['public_rejected'] if actual else None
                # These are strictly one-step counterfactual findings, not reward effects.
                avoided_rejection=bool(p and not p['accepted'] and actual_good)
                prevented_visibility_loss=bool(p and actual and visible(actual['observation']) and not p['visible'] and 'too dark to see' in p['feedback']['text'].lower() and visible(actual['feedback']))
                decisions.append(dict(case=ident,step=n,proposal_index=i,record=record,executed_action=actual['action'] if actual else None,
                    actual_goal=goal(actual) if actual else None,proposal_executed=bool(actual and i==len(records) and record['passed_to_agc'] and candidate_action.strip()==actual['action']),
                    native_probe=p,local_rejection_avoided=avoided_rejection,local_visibility_loss_avoided=prevented_visibility_loss,
                    candidate_accepted_by_native=p['accepted'] if p else None,terminal=actual is None,
                    goal_changed_after_reconsider=bool(actual and candidate and record['check']['decision']=='RECONSIDER' and candidate.get('goal_description')!=goal(actual))))
                counts['local_rejection_avoided_proposals']+=avoided_rejection;counts['local_visibility_loss_avoided_proposals']+=prevented_visibility_loss
                if p:counts['blocked_but_native_accepted_proposals']+=p['accepted']
        for q in qq:
            issues=[];raw=q.get('raw_response',{});parsed=q.get('parsed_json')
            if q['status']!='ok':issues.append(q['status'])
            if q.get('parse_exception'):issues.append(q['parse_exception'])
            if raw and raw['choices'][0]['finish_reason']!='stop':issues.append('finish_reason:'+raw['choices'][0]['finish_reason'])
            if q['status']=='ok' and not q.get('parse_exception'):
                issues+=['missing_'+k for k in ['action','reasoning','goal_description','goal_evidence'] if not isinstance(parsed,dict) or not isinstance(parsed.get(k),str)]
            new=not(method=='AGC-v2' and (seed==42 or q['step']<=47))
            if issues:anomalies.append(dict(case=ident,step=q['step'],ordinal=q['ordinal'],request_id=q['request_id'],issues=issues,new=new,source=str((folder/'requests.jsonl.gz').relative_to(ROOT))))
            requests.append(dict(case=ident,step=q['step'],ordinal=q['ordinal'],request_id=q['request_id'],status=q['status'],new=new,
                input_tokens=q.get('usage',{}).get('prompt_tokens',0),output_tokens=q.get('usage',{}).get('completion_tokens',0),cost_usd=q.get('cost_usd',0),peak_reference_usd=q.get('peak_rate_reference_cost_usd',0)))
        # A REC exception interrupts the inherited _act before its decision
        # object is finalized. Recover the two terminal native review counts
        # from saved proposals, original prompts and replayed AGC assessments.
        tr=terminal_review.get(ident)
        reached=[x for x in tr['records'] if x['passed_to_agc']] if tr else []
        counts['native_action_retries_terminal_reconstructed']=sum(x['agc_assessment_at_terminal_state']['hard'] for x in reached)
        counts['native_confidence_reviews_terminal_reconstructed']=sum(not x['agc_assessment_at_terminal_state']['hard'] and x['agc_assessment_at_terminal_state']['goal_review'] for x in reached)
        counts['native_action_retries_total']=counts['native_action_retries_recorded']+counts['native_action_retries_terminal_reconstructed']
        counts['native_confidence_reviews_total']=counts['native_confidence_reviews_recorded']+counts['native_confidence_reviews_terminal_reconstructed']
        native_condition_cases=[]
        for p in probes:
            if p['case']!=ident or p['kind']!='before_actual_risk':continue
            after=probe_lookup[ident,p['step'],'after_actual_risk',None]
            native_condition_cases.append(dict(step=p['step'],craft_before=p['craft_success'],craft_after=after['craft_success'],
                condition_lost=p['craft_success'] and not after['craft_success']))
        result=dict(case=ident,seed=seed,method=method,status=s['status'],counts=tt,controller=counts,terminal=terminal,
            recoveries=recoveries,native_condition_cases=native_condition_cases,verified_immediate_craft_condition_losses=sum(x['condition_lost'] for x in native_condition_cases),
            requests=len(qq),new_requests=sum(x['new'] for x in requests if x['case']==ident),
            input_tokens=sum(q.get('usage',{}).get('prompt_tokens',0) for q in qq),output_tokens=sum(q.get('usage',{}).get('completion_tokens',0) for q in qq),
            max_prompt_tokens=max((q.get('usage',{}).get('prompt_tokens',0) for q in qq),default=0),
            cost_usd=sum(q.get('cost_usd',0) for q in qq),new_cost_usd=sum(x['cost_usd'] for x in requests if x['case']==ident and x['new']),
            peak_reference_cost_usd=sum(q.get('peak_rate_reference_cost_usd',0) for q in qq),
            rates_per100={k:100*tt.get(k,0)/max(1,len(rr)) for k in ['public_rejected','repeated_failure','repeated_missing_conditions','wait','reacquisition_cycles','visibility_lost','removal_visibility_lost']},
            scores=s['scores'],main_quest_progress=s['main_quest_progress'],source=str(folder.relative_to(ROOT)))
        runs.append(result)
        for i,(r,a) in enumerate(zip(rr,aa),1):
            index.append(dict(case=ident,step=r['step'],source=str((folder/'trajectory.jsonl.gz').relative_to(ROOT)),line=i,
                action=r['action'],state_hash_before=r['state_hash_before'],state_hash=r['state_hash'],
                request_ids=[q['request_id'] for q in qq if q['step']==r['step']],metrics=a))
    pairs=[]
    for seed in SEEDS:
        a=next(x for x in runs if x['case']==case_id(seed,'AGC-v2'));b=next(x for x in runs if x['case']==case_id(seed,'REC'));n=min(a['counts']['actions'],b['counts']['actions'])
        ar=by[a['case']];br=by[b['case']];div=next((i+1 for i,(x,y) in enumerate(zip(ar,br)) if x['action']!=y['action']),None)
        pairs.append(dict(seed=seed,common_actions=n,AGC_v2=totals(timelines[a['case']][:n]),REC=totals(timelines[b['case']][:n]),
            main_delta=b['counts']['main_final']-a['counts']['main_final'],chapter_delta=b['counts']['chapter1']-a['counts']['chapter1'],
            first_action_divergence=div,divergence_A=ar[div-1]['action'] if div else None,divergence_B=br[div-1]['action'] if div else None,
            rec_early_termination=b['status']=='agent_decision_exhausted',no_extra_rec_early_stop=b['status']=='native_done' or b['counts']['actions']>=a['counts']['actions']))
    progress_better=sum(p['main_delta']>0 or p['chapter_delta']>0 for p in pairs);worse=any(p['main_delta']<0 or p['chapter_delta']<0 for p in pairs)
    no_early=all(not p['rec_early_termination'] and p['no_extra_rec_early_stop'] for p in pairs)
    error_pairs=sum(p['REC']['public_rejected']<p['AGC_v2']['public_rejected'] for p in pairs)
    errors_a=sum(p['AGC_v2']['public_rejected'] for p in pairs);errors_b=sum(p['REC']['public_rejected'] for p in pairs)
    verdict='PROGRESS_SUPPORT' if progress_better>=2 and not worse and no_early else 'ERROR_REDUCTION_ONLY' if no_early and not worse and error_pairs>=2 and errors_a>0 and errors_b<=.9*errors_a else 'NO_CLEAR_SUPPORT'
    write(RESULTS/'metrics.json',runs);write(RESULTS/'paired_comparison.json',pairs);gzwrite(RESULTS/'evidence_index.jsonl.gz',index);gzwrite(RESULTS/'controller_audit.jsonl.gz',decisions)
    write(RESULTS/'response_anomalies.json',anomalies);csvwrite(RESULTS/'request_index.csv',requests)
    write(RESULTS/'conclusion.json',dict(verdict=verdict,progress_better_pairs=progress_better,any_progress_regression=worse,no_extra_rec_early_stop=no_early,
        error_reduction_pairs=error_pairs,common_window_rejections_AGC_v2=errors_a,common_window_rejections_REC=errors_b,
        independent_environment_seeds=3,model_samples_per_method_seed=1,strict_causal_module_effect_established=False,new_analysis_model_calls=0))
    flat=[dict(case=x['case'],status=x['status'],**x['counts'],requests=x['requests'],input_tokens=x['input_tokens'],output_tokens=x['output_tokens'],
        new_requests=x['new_requests'],cost_usd=x['cost_usd'],new_cost_usd=x['new_cost_usd'],peak_reference_cost_usd=x['peak_reference_cost_usd']) for x in runs]
    keys=sorted({k for x in flat for k in x});csvwrite(RESULTS/'comparison.csv',[{k:x.get(k,0) for k in keys} for x in flat])
    official=[]
    for method in ['AGC-v2','REC']:
        args=[sys.executable,str(ENGINE/'challenge_eval.py'),'--remnant',*[str(source(seed,method)) for seed in SEEDS],'--json']
        result=json.loads(subprocess.run(args,capture_output=True,text=True,check=True).stdout)
        assert result['games']['remnant']['main_quest']==sum(x['scores']['quest'] for x in runs if x['method']==method)/3
        official.append(dict(method=method,args=args,result=result,scorer_sha256=sha(ENGINE/'challenge_eval.py')))
    write(RESULTS/'official_scores.json',official)
    print(json.dumps(read(RESULTS/'conclusion.json')),flush=True)

if __name__=='__main__':main()
