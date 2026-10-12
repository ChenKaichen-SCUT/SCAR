"""Four measurement panels; identical historical method choices, no sampling."""
from collections import defaultdict,Counter
from scar.io import atomic_json,digest
from scar_stage14.common import ROOT,OLD,load,records,save_records
from scar_stage14.knowledge import Knowledge
from scar_stage14.executor import Executor
from scar_stage14.replay import verify_freezes
from scar_v3.state import parse_action

PANELS={'original':('old',False),'parser_only':('old',True),'executor_only':('unified',False),'both':('unified',True)}


def annotate(kstate,branch):
    k=Knowledge.from_dict(kstate['knowledge']);keys=set(kstate['native_necessary_keys_offline_only']);initial=set(k.relations())
    out=[]
    for r in branch['trace']:
        d=k.observe(r['after'],r['action'],cutoff=r['after']['step'],source={'kind':'native_branch','index':r['index']})
        new=set(k.relations())-initial
        out.append({'index':r['index'],'action':r['action'],'feedback':r['feedback'],'observation_digest':digest(r['after']),
            'K1_delta':d,'K1_new_relations':sorted(new),'K1_new_necessary':sorted(new&keys),
            'K2_new_relations':r['new_public_recipes'],'K2_new_necessary':r['new_key_recipes']})
    return out


def score(branch,ann,window,parser,remaining,intent,pub,relevant):
    trace=branch['trace'][:min(window,remaining)];a=ann[:len(trace)]
    prefix='K1' if parser else 'K2'
    new=sorted({n for r in a for n in r[prefix+'_new_necessary']})
    relations=sorted({n for r in a for n in r[prefix+'_new_relations']})
    complete=None;completion=None;stop=branch.get('stop')
    if intent is not None:
        e=Executor(pub,intent)
        # Completion audit of actual evidence, never used to rewrite the branch.
        for r in trace:e.observe(r['action'],r['before'],r['after'])
        complete=e.completed;completion=e.completion_step
        if not complete and len(trace)>=min(window,remaining):stop='window_or_original_budget'
        # Measurement-only correction: native inventory inspection uses "my
        # inventory", unlike object inspection headers. The frozen executor
        # already stops after this one action; no actions or scores of recipe
        # novelty change. Preserve its raw stop in the native artifact.
        if (intent['operation']=='inspect' and intent['target']=='inventory' and trace
            and not trace[0]['rejected'] and trace[0]['feedback'].startswith('I inspected my inventory.')):
            complete=True;completion=1;stop='intent_complete_inventory_feedback'
    return {'actions':len(trace),'useful':bool(new),'new_necessary':new,'new_public_relations':relations,
        'one_step_useful':bool(a and a[0][prefix+'_new_necessary']),
        'first_action_legal':not trace[0]['rejected'] if trace else False,
        'intent_complete':complete,'completion_step':completion,'stop':stop,
        'explicit_intent':bool(intent and intent['clarity']=='explicit'),
        'incomplete_exploration_intent':bool(intent and intent['clarity']=='incomplete'),
        'rejections':sum(r['rejected'] for r in trace),'rejected':any(r['rejected'] for r in trace),
        'critical_consumption':any(set(r['action_consumption'])&relevant for r in trace),
        'unrelated_craft':any(r['unrelated_craft'] for r in trace),
        'unrelated_key_input_consumption':any(r['unrelated_key_input_consumption'] for r in trace),
        'environment_key_loss':any(r['environment_key_loss'] for r in trace),
        'repeated_public_relations':sorted({n for r in a for n in r['K1_delta']['repeated_relations']}),
        'quantity_updates':sorted({n for r in a for n in r['K1_delta']['quantity_updates']}),
        'station_updates':sorted({n for r in a for n in r['K1_delta']['station_updates']}),
        'goal':trace[-1]['goal'] if trace else False}


def totals(rows):
    fields=['actions','useful','one_step_useful','rejected','rejections','critical_consumption',
        'unrelated_craft','unrelated_key_input_consumption','environment_key_loss','explicit_intent','incomplete_exploration_intent']
    out={k:sum(r[k] for r in rows) for k in fields};out['n']=len(rows)
    out['intent_complete']=sum(r['intent_complete'] is True for r in rows)
    out['useful_explicit']=sum(r['useful'] and r['explicit_intent'] for r in rows)
    out['public_pool_opportunities']=sum(r.get('public_pool_opportunity',False) for r in rows)
    out['all_observed_opportunities']=sum(r.get('any_opportunity',False) for r in rows)
    out['actions_per_useful']=out['actions']/out['useful'] if out['useful'] else None
    return out


def main():
    verify_freezes()
    ss={s['state_id']:s for s in load(OLD/'states.json')}
    ks={r['state_id']:r for r in load(ROOT/'frozen_state_knowledge.json')}
    pubs=load(ROOT/'intent_public_inputs.json');refs=load(ROOT/'intent_references.json')
    cases={c['id']:c for c in load('results/stage11/cases.json')}
    intents={(r['state_id'],r['intent']['id']):r['intent'] for r in load(ROOT/'candidate_intents.json')}
    old={r['state_id']:r for r in records(OLD/'native_branches.jsonl.gz')}
    oldbranches={(sid,cid):b for sid,r in old.items() for cid,b in r['branches'].items()}
    for r in records('results/stage13/native_supplements.jsonl.gz'):
        if r['kind']=='truncation_sensitivity':oldbranches[r['state_id'],r['candidate']['id']]=r['branch']
    unified={(r['state_id'],r['intent_id']):r['branch'] for path in ['reused_intent_branches.jsonl.gz','native_intent_branches.jsonl.gz'] for r in records(ROOT/path)}
    assert len(unified)==len(intents)==377
    annotations={};all_timeline=[];scores={};candidate_scores=[]
    for mode,bs in [('old',oldbranches),('unified',unified)]:
        for (sid,cid),b in bs.items():
            ann=annotate(ks[sid],b);annotations[mode,sid,cid]=ann
            all_timeline.append({'mode':mode,'state_id':sid,'branch_id':cid,'trace_digest':digest(b['trace']),'rows':ann})
            for window in [4,6,8]:
                for parser in [False,True]:
                    intent=intents[sid,cid] if mode=='unified' else None
                    case=cases[ss[sid]['case_id']]
                    relevant={case['object_names'][oid] for oid in set(case['materials'])|set(case['products'])}
                    m=score(b,ann,window,parser,ss[sid]['remaining_actions'],intent,pubs[sid],relevant)
                    scores[mode,sid,cid,window,parser]=m
                    candidate_scores.append({'mode':mode,'state_id':sid,'branch_id':cid,'window':window,'parser':'K1' if parser else 'K2',**m})
    rows=[];coverage=[]
    for panel,(mode,parser) in PANELS.items():
        for window in [4,6,8]:
            for sid,s in ss.items():
                family=parse_action(s['public_controller']['target']).target
                pool=set(old[sid]['retained_ids']+old[sid]['cropped_ids'])
                rpool=[r for r in refs if r['state_id']==sid and r['role']=='pool']
                def lookup(r):return scores[mode,sid,r['candidate_id'] if mode=='old' else r['intent_id'],window,parser]
                pooluse=any(lookup(r)['useful'] for r in rpool if r['candidate_id'] in pool)
                anyuse=any(lookup(r)['useful'] for r in refs if r['state_id']==sid)
                coverage.append({'panel':panel,'window':window,'state_id':sid,'family':family,
                    'public_pool_opportunity':pooluse,'any_opportunity':anyuse})
                for method in ['J0','J1','J2','J3']:
                    r=next(r for r in refs if r['state_id']==sid and r['role']==method and r.get('replicate')==0)
                    m=lookup(r)
                    rows.append({'panel':panel,'window':window,'state_id':sid,'family':family,'method':method,
                        'candidate_id':r['candidate_id'],'intent_id':r['intent_id'],**m,
                        'public_pool_opportunity':pooluse,'any_opportunity':anyuse})
    # Exact historic score reproduction is mandatory before interpreting deltas.
    for r in load(OLD/'state_metrics.json'):
        now=next(x for x in rows if x['panel']=='original' and x['window']==4 and x['state_id']==r['state_id'] and x['method']==r['method'])
        for k in ['actions','useful','one_step_useful','rejected','rejections','unrelated_craft','environment_key_loss','unrelated_key_input_consumption']:assert now[k]==r[k],(r['state_id'],r['method'],k)
    summaries=[];family=[];pairs=[]
    for panel in PANELS:
        for window in [4,6,8]:
            for method in ['J0','J1','J2','J3']:
                group=[r for r in rows if r['panel']==panel and r['window']==window and r['method']==method]
                summaries.append({'panel':panel,'window':window,'method':method,**totals(group)})
                for f in sorted({r['family'] for r in group}):family.append({'panel':panel,'window':window,'method':method,'family':f,**totals([r for r in group if r['family']==f])})
            for new,oldm in [('J1','J0'),('J2','J0'),('J3','J0')]:
                subset={(r['state_id'],r['method']):r for r in rows if r['panel']==panel and r['window']==window};d=[]
                for f in sorted({r['family'] for r in subset.values()}):
                    ids=[sid for sid in ss if subset[sid,new]['family']==f]
                    d.append({'family':f,'states':len(ids),'gain':sum(subset[sid,new]['useful'] and not subset[sid,oldm]['useful'] for sid in ids),
                        'loss':sum(subset[sid,oldm]['useful'] and not subset[sid,new]['useful'] for sid in ids)})
                pairs.append({'panel':panel,'window':window,'comparison':new+'-'+oldm,'families':d,
                    'gain':sum(x['gain'] for x in d),'loss':sum(x['loss'] for x in d),
                    'positive_families':sum(x['gain']>x['loss'] for x in d),'negative_families':sum(x['gain']<x['loss'] for x in d)})
    save_records(ROOT/'intent_knowledge_timeline.jsonl.gz',all_timeline)
    save_records(ROOT/'candidate_window_metrics.jsonl.gz',candidate_scores)
    atomic_json(ROOT/'calibrated_state_metrics.json',rows);atomic_json(ROOT/'calibrated_method_metrics.json',summaries)
    atomic_json(ROOT/'family_metrics.json',family);atomic_json(ROOT/'paired_family_comparisons.json',pairs)
    atomic_json(ROOT/'calibrated_coverage.json',coverage)
    strata=[]
    for window in [4,6,8]:
        sub=[r for r in rows if r['panel']=='both' and r['window']==window]
        common=[sid for sid in ss if all(r['explicit_intent'] for r in sub if r['state_id']==sid)]
        for method in ['J0','J1','J2','J3']:
            strata.append({'window':window,'method':method,'stratum':'all_four_methods_explicit',
                'state_ids':common,**totals([r for r in sub if r['method']==method and r['state_id'] in common])})
    atomic_json(ROOT/'comparison_strata.json',strata)
    atomic_json(ROOT/'intent_interpretation_summary.json',{'intent_types':dict(Counter(i['type'] for i in intents.values())),
        'clarity':dict(Counter(i['clarity'] for i in intents.values())),'new_calls':0,'historical_metrics_exact':True})
    print([{k:r[k] for k in ['panel','window','method','useful','actions','all_observed_opportunities']} for r in summaries if r['window']==4])

if __name__=='__main__':main()
