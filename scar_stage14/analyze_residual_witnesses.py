"""Score the exhaustive unfinished-commitment supplement, with strict gates."""
import re
from collections import Counter,defaultdict
from scar.io import atomic_json,digest
from scar_stage14.common import ROOT,load,records,episodes,save_records
from scar_stage14.analyze_intents import annotate,score
from scar_stage12.public import controller
from scar_v3.state import parse_action


def main():
    plan=load(ROOT/'residual_replay_plan.json');jobs={j['state_id']:j for j in plan['jobs']}
    states={s['state_id']:s for s in load(ROOT/'residual_checkpoint_manifest.json')}
    eps={ep['task_id']:(ep,c) for _,_,ep,c,_ in episodes()}
    tl=defaultdict(list)
    for r in records(ROOT/'episode_timeline.jsonl.gz'):tl[r['task_id']].append(r)
    out=[];timelines=[]
    for rec in records(ROOT/'residual_native_branches.jsonl.gz'):
        j=jobs[rec['state_id']];b=rec['branch'];ep,case=eps[j['source_task']];start=j['source_index']
        keys={case['object_names'][oid] for oid in case['recipe_graph']}
        relevant={case['object_names'][oid] for oid in set(case['materials'])|set(case['products'])}
        ann=annotate({'knowledge':j['knowledge'],'native_necessary_keys_offline_only':list(keys)},b)
        timelines.append({'state_id':j['state_id'],'source_task':j['source_task'],'rows':ann})
        common=0
        for a,r in zip(b['trace'],ep['rows'][start:]):
            if a['action']!=r['executed_action']:break
            assert a['after']==r['next_observation'];common+=1
        divergence=start+common if common<len(b['trace']) and start+common<len(ep['rows']) else None
        prefix=tl[j['source_task']][start:divergence] if divergence is not None else []
        updates=[{'index':r['index'],'delta':{k:r['K1_delta'][k] for k in ['new_relations','quantity_updates','station_updates']}}
            for r in prefix if any(r['K1_delta'][k] for k in ['new_relations','quantity_updates','station_updates'])]
        losses=[r for r in ep['summary'].get('resource_destruction',[]) if divergence is not None and start<=r['index']<divergence]
        risks=[{'index':r['index'],'feedback':r['feedback']} for r in ep['rows'][start:divergence] if re.search(r'attacked|lost \d+ HP|Missing necessary|sufficient amount',r['feedback'])] if divergence is not None else []
        direct=False
        if divergence is not None:
            row=ep['rows'][divergence];p=parse_action(row['executed_action']);goal=parse_action(case['target_action']).target
            # Inspecting the goal is not a direct completion opportunity.
            if p.target==goal and p.verb in {'craft','pick up','store','take out'}:
                c=controller(row['stage7_state_before'],row['observation'])
                direct=c.assess(row['executed_action'])['status']!='REJECT'
        gates={'explicit_recorded_exploration':True,'actual_first_action_accepted':True,
            'actual_chain_unfinished':not j['actual_commitment']['actual_closure']['complete'],
            'native_fixed_continuation_completes':b['intent_complete'],
            'different_actual_next_action':divergence is not None,
            'next_action_native_supported':common<len(b['trace']) and not b['trace'][common]['rejected'],
            'no_new_information_resource_or_risk':not (updates or losses or risks),
            'no_direct_goal_completion_opportunity':not direct}
        confirmed=all(gates.values())
        windows={str(w):score(b,ann,w,True,j['public']['remaining_actions'],j['intent'],j['public'],relevant) for w in [4,6,8]}
        e=j['actual_commitment']['public_evidence'];cap=e.get('spent') is not None and e.get('limit') is not None and e['spent']>=e['limit']
        label='F4_policy_quota_boundary' if confirmed and cap else 'F4' if confirmed else 'completion_with_intervening_information_or_constraints' if b['intent_complete'] else 'F5_window' if b['stop']=='action_budget' else 'F5_public_precondition_or_material'
        out.append({'state_id':j['state_id'],'task_id':j['source_task'],'family':j['family'],'method':j['method'],
            'start_index':start,'target':j['intent']['target'],'source_public_evidence':e,
            'physical_hash':states[j['state_id']]['physical_hash'],'gates':gates,'confirmed_F4':confirmed,'classification':label,
            'internal_exploration_quota_reached':cap,'quota_is_policy_bound_not_original40_environment_budget':True,
            'common_prefix':common,'divergence_index':divergence,
            'actual_at_divergence':ep['rows'][divergence]['executed_action'] if divergence is not None else None,
            'fixed_at_divergence':b['trace'][common]['action'] if common<len(b['trace']) else None,
            'new_public_information_before_switch':updates,'resource_changes_before_switch':losses,'public_risk_or_precondition_feedback':risks,
            'windows':windows,'new_necessary_quantity_information':sorted(keys&{n for a in ann for n in a['K1_delta']['quantity_updates']}),
            'native_actions':[r['action'] for r in b['trace']],'native_stop':b['stop'],'native_intent_complete':b['intent_complete']})
    confirmed=[r for r in out if r['confirmed_F4']]
    summary={'native_branches':len(out),'native_completed_by8':sum(r['native_intent_complete'] for r in out),
        'classification':dict(Counter(r['classification'] for r in out)),
        'confirmed_F4_episode_records':len(confirmed),'confirmed_F4_families':sorted({r['family'] for r in confirmed}),
        'confirmed_F4_unique_physical_states':len({r['physical_hash'] for r in confirmed}),
        'confirmed_F4_new_necessary_names':sum(bool(r['windows']['8']['new_necessary']) for r in confirmed),
        'confirmed_F4_new_necessary_quantities':sum(bool(r['new_necessary_quantity_information']) for r in confirmed),
        'confirmed_F4_main4_completed':sum(r['windows']['4']['intent_complete'] for r in confirmed),
        'confirmed_F4_simple_fixed_continuation_suffices':all(r['native_intent_complete'] for r in confirmed),
        'stale_goal_not_accepted':len(plan['excluded']),
        'interpretation':'one family/one physical prefix repeated in S1 E0 E1; explicit internal18 exploration cap, not an unexplained latent workflow failure',
        'decision':'NO-GO','RQ3_beyond_deterministic_continuation':'not established','new_api_calls':0}
    atomic_json(ROOT/'residual_witness_audit.json',out);atomic_json(ROOT/'residual_witness_summary.json',summary)
    save_records(ROOT/'residual_witness_knowledge_timeline.jsonl.gz',timelines)
    final=[]
    for c in load(ROOT/'full_reference_commitments.json'):
        witness=next((r for r in out if (r['task_id'],r['start_index'],r['target'])==(c['task_id'],c['start_index'],c['target'])),None)
        excluded=any((r['task_id'],r['start_index'],r['target'])==(c['task_id'],c['start_index'],c['target']) for r in plan['excluded'])
        final.append(dict(c,pre_supplement_classification=c['classification'],
            classification=witness['classification'] if witness else 'stale_goal_not_accepted' if excluded else c['classification'],
            residual_witness_id=witness['state_id'] if witness else None,confirmed_F4=bool(witness and witness['confirmed_F4'])))
    atomic_json(ROOT/'full_reference_commitments_final.json',final)
    summary['all69_final_classification']=dict(Counter(r['classification'] for r in final))
    atomic_json(ROOT/'residual_witness_summary.json',summary)
    base=load(ROOT/'residual_summary.json');base['supplement']=summary
    base['confirmed_F4_all_episode_records']=base['confirmed_F4_frozen_states']+len(confirmed)
    base['reason']='one quota-induced interruption family, fully handled by fixed continuation; no evidence for a new workflow mechanism beyond the deterministic baseline'
    atomic_json(ROOT/'residual_summary.json',base);print(summary)

if __name__=='__main__':main()
