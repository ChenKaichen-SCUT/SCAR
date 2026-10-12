"""Predeclared paired screen; no dataset filtering or policy modifications."""
import collections
import gzip
import json
from pathlib import Path

import numpy as np
from scar.io import atomic_json
from scar_stage12.public import primitive_candidate, controller, confirmed

OUT=Path('results/stage12/diagnostic')
METHODS=['J0','J1','J2','J3']


def raw_entry(state, candidate):
    ctrl=controller(state['public_controller'],state['observation'])
    return (candidate['kind'] in {'inspect','visit'} and candidate['target'] not in confirmed(ctrl)
            and candidate['target'] not in ctrl.quantity_facts.produced
            and not ctrl.table.recipes.get(candidate['target'],{}).get('ingredients')
            and candidate['target'] not in ctrl.table.containers
            and candidate['target'] not in {x for r in ctrl.table.recipes.values() for x in r.get('stations',[])})


def chosen(state, method, judgments):
    if method in {'J0','J1'}:
        return primitive_candidate(state['rule_actions'][method])['id'],None
    j=judgments.get((state['state_id'],method,0))
    if not j or j['status']!='completed':return None,j
    return (primitive_candidate(j['parsed']['action'])['id'] if method=='J2'
            else j['parsed']['selected_candidate_id']),j


def main():
    states=json.loads((OUT/'states.json').read_text());native={r['state_id']:r for r in map(json.loads,gzip.open(OUT/'native_branches.jsonl.gz','rt'))}
    judgments={(r['state_id'],r['method'],r['replicate']):r for r in json.loads((OUT/'judgments.json').read_text())}
    cfg=json.loads(Path('configs/protocol_stage12_diagnostic.json').read_text());rows=[];coverage=[];stability=[]
    for s in states:
        n=native[s['state_id']];bs=n['branches'];pool=set(n['retained_ids']+n['cropped_ids']);ret=set(n['retained_ids'])
        useful={k for k,b in bs.items() if b['useful']};raw={k for k in useful if raw_entry(s,bs[k]['candidate'])}
        coverage.append({'state_id':s['state_id'],'case_id':s['case_id'],
            'full_public_pool_has_useful':bool(useful&pool),'retained_has_useful':bool(useful&ret),
            'any_observed_candidate_has_useful':bool(useful),'raw_entry_has_useful':bool(raw),
            'retained_useful_ids':sorted(useful&ret),'cropped_useful_ids':sorted(useful&(pool-ret)),
            'free_proposal_only_useful_ids':sorted(useful-pool),'raw_entry_useful_ids':sorted(raw)})
        for method in METHODS:
            cid,j=chosen(s,method,judgments);b=bs.get(cid);top3=None
            if method=='J3' and j and j['status']=='completed':
                top3=bool(set(j['parsed']['ranked_candidate_ids'])&useful)
            rows.append({'state_id':s['state_id'],'case_id':s['case_id'],'method':method,
                'selected_id':cid,'valid':b is not None,'useful':bool(b and b['useful']),
                'one_step_useful':bool(b and b['one_step_useful']), 'new_key_recipes':b['new_key_recipes'] if b else [],
                'top3_useful':top3,'actions':b['actions'] if b else 0,
                'raw_entry_useful':bool(cid in raw),'no_public_pool_opportunity':not bool(useful&pool),
                'rejected':bool(b and b['rejections']),'rejections':b['rejections'] if b else 0,
                'unrelated_craft':bool(b and b['unrelated_craft']),
                'environment_key_loss':bool(b and b['environment_key_loss']),
                'unrelated_key_input_consumption':bool(b and b['unrelated_key_input_consumption'])})
        for method in ['J2','J3']:
            j=judgments.get((s['state_id'],method,1))
            if not j:continue
            cid,primary=chosen(s,method,judgments)
            other=(primitive_candidate(j['parsed']['action'])['id'] if method=='J2' else j['parsed']['selected_candidate_id']) if j['status']=='completed' else None
            stability.append({'state_id':s['state_id'],'case_id':s['case_id'],'method':method,
                'both_valid':cid in bs and other in bs,'same_selection':cid==other and cid is not None,
                'primary_useful':bool(cid in useful),'replicate_useful':bool(other in useful),
                'same_information_outcome':(cid in useful)==(other in useful) if cid and other else None,
                'primary_id':cid,'replicate_id':other,'used_for_primary_result':False})
    sums={}
    for method in METHODS:
        subset=[r for r in rows if r['method']==method]
        values={k:sum(r[k] for r in subset) for k in ['valid','useful','one_step_useful','actions','raw_entry_useful','rejected',
            'rejections','unrelated_craft','environment_key_loss','unrelated_key_input_consumption']}
        values['n']=len(subset);values['top1_rate']=values['useful']/len(subset)
        values['useful_on_public_informative_states']=sum(r['useful'] and not r['no_public_pool_opportunity'] for r in subset)
        values['public_informative_states']=sum(not r['no_public_pool_opportunity'] for r in subset)
        values['actions_per_useful_selection']=values['actions']/values['useful'] if values['useful'] else None
        values['mean_actions_successful_branches']=sum(r['actions'] for r in subset if r['useful'])/values['useful'] if values['useful'] else None
        values['top3_useful']=sum(r['top3_useful'] is True for r in subset) if method=='J3' else None
        sums[method]=values
    families=sorted({s['case_id'] for s in states});by={(r['state_id'],r['method']):r for r in rows};pairs=[]
    rng=np.random.default_rng(cfg['bootstrap_seed']);samples=rng.integers(0,len(families),(cfg['bootstrap_samples'],len(families)))
    for comparison in cfg['comparisons']:
        new,old=comparison.split('-');gains=[];losses=[];family=[]
        for f in families:
            members=[s for s in states if s['case_id']==f]
            delta=sum(int(by[s['state_id'],new]['useful'])-int(by[s['state_id'],old]['useful']) for s in members)
            family.append({'case_id':f,'n':len(members),'net_useful':delta,'rate_difference':delta/len(members)})
        for s in states:
            a,b=by[s['state_id'],new]['useful'],by[s['state_id'],old]['useful']
            if a and not b:gains.append(s['state_id'])
            if b and not a:losses.append(s['state_id'])
        rates=np.array([f['rate_difference'] for f in family]);distribution=rates[samples].mean(axis=1)
        pairs.append({'comparison':comparison,'net_useful':len(gains)-len(losses),'gains':gains,'losses':losses,
            'positive_net_families':sum(f['net_useful']>0 for f in family),'family_details':family,
            'rate_difference':float(rates.mean()),'family_bootstrap_ci95':np.quantile(distribution,[.025,.975]).tolist()})
    effective=sum(c['any_observed_candidate_has_useful'] for c in coverage)
    retained=sum(c['retained_has_useful'] for c in coverage)
    raw_states=sum(c['raw_entry_has_useful'] for c in coverage)
    informative_families=len({c['case_id'] for c in coverage if c['any_observed_candidate_has_useful']})
    gates={};threshold=cfg['gate']
    for method in ['J2','J3']:
        selected=[p for p in pairs if p['comparison'] in {method+'-J0',method+'-J1'}]
        checks={'net_gain_over_both_rules':all(p['net_useful']>=threshold['net_useful_top1_vs_each_rule_at_least'] for p in selected),
            'gains_across_families_over_both_rules':all(p['positive_net_families']>=threshold['positive_net_families_vs_each_rule_at_least'] for p in selected),
            'candidate_coverage':effective>0 and retained/effective>=threshold['retained_effective_state_coverage_at_least'],
            'informative_families':informative_families>=threshold['minimum_informative_families'],
            'raw_entry_vs_reference':sums[method]['raw_entry_useful']>=max(sums[m]['raw_entry_useful'] for m in ['J0','J1'])-threshold['raw_entry_useful_count_at_least_best_rule_minus'],
            'raw_entry_not_systematically_ignored':raw_states>0 and sums[method]['raw_entry_useful']/raw_states>=threshold['raw_entry_success_fraction_at_least'],
            'valid_answers':sums[method]['valid']>=threshold['valid_primary_answers_at_least'],
            'one_step_sensitivity':sums[method]['one_step_useful']>=max(sums[m]['one_step_useful'] for m in ['J0','J1'])+threshold['one_step_net_gain_vs_each_rule_at_least']}
        for metric,key in [('rejected','rejection_state_count_at_most_worst_rule_plus'),('unrelated_craft','unrelated_craft_state_count_at_most_worst_rule_plus'),
                           ('environment_key_loss','environment_key_loss_state_count_at_most_worst_rule_plus'),
                           ('unrelated_key_input_consumption','unrelated_key_input_consumption_state_count_at_most_worst_rule_plus')]:
            checks[metric+'_bounded']=sums[method][metric]<=max(sums[m][metric] for m in ['J0','J1'])+threshold[key]
        gates[method]={'checks':checks,'passed':all(checks.values())}
    gate={'methods':gates,'passed':any(g['passed'] for g in gates.values()),
          'decision':'GO' if any(g['passed'] for g in gates.values()) else 'NO-GO',
          'stageB_run':False,'screening_not_significance':True,'thresholds':threshold}
    atomic_json(OUT/'state_metrics.json',rows);atomic_json(OUT/'method_metrics.json',sums)
    atomic_json(OUT/'candidate_coverage.json',{'states':coverage,'observed_informative_states':effective,
        'retained_informative_states':retained,'retained_effective_state_coverage':retained/effective if effective else None,
        'informative_families':informative_families,'useful_raw_entry_states':raw_states,
        'scope':'public pre-crop pool plus actually observed free proposals; not an exhaustive oracle action set'})
    atomic_json(OUT/'paired_comparisons.json',pairs);atomic_json(OUT/'stability.json',stability);atomic_json(OUT/'gate.json',gate)
    print(json.dumps({'methods':sums,'gate':gate},ensure_ascii=False))


if __name__=='__main__':main()
