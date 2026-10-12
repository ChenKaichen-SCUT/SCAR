"""Actual overhead, repeated equal-feedback probes and trial resource costs."""
from collections import Counter,defaultdict
import gzip
import json
from pathlib import Path
from scar.io import atomic_json
from scar_v3.state import parse_action


def main():
    out=Path('results/unknown17');batches={}
    for b in map(json.loads,gzip.open(out/'batch_audit.jsonl.gz','rt')):batches[b['task_id'],b['index']]=b
    result={};by_family=[]
    for path in sorted(out.glob('trajectories_*.jsonl.gz')):
        method=path.name.removeprefix('trajectories_').removesuffix('.jsonl.gz');totals=Counter();consumed=Counter()
        for ep in map(json.loads,gzip.open(path,'rt')):
            counts=Counter();cost=Counter();resources=Counter();seen={};repeated=[]
            for r in ep['rows']:
                p=parse_action(r['executed_action']);mechs=r.get('structured',{}).get('mechanisms',{});explore=mechs.get('exploration')
                if explore:
                    counts['directed_actions']+=1;cost['directed_action_api_cost_usd']+=r['api_delta']['cost_usd']
                    counts['directed_action_input_tokens']+=r['api_delta']['input_tokens']
                    counts['directed_action_output_tokens']+=r['api_delta']['output_tokens']
                    if explore['reason']=='bounded forward recipe trial':
                        counts['forward_trial_actions']+=1
                        resources.update(batches[(ep['task_id'],r['index'])]['actual']['consumed'])
                        cost['forward_trial_api_cost_usd']+=r['api_delta']['cost_usd']
                if p.verb=='inspect':
                    key=(r['physical_before']['resource_hash'],r['executed_action'],r['action_rule_feedback'])
                    if key in seen:repeated.append({'previous_index':seen[key],'index':r['index'],'action':r['executed_action'],
                        'feedback':r['action_rule_feedback'],'resource_hash':r['physical_before']['resource_hash']})
                    seen[key]=r['index']
                if mechs.get('batch'):
                    b=batches.get((ep['task_id'],r['index']))
                    if b and b['predicted_consumption'] is None:counts['batch_choices_without_empirical_prediction']+=1
            counts['same_resource_same_feedback_reinspections']=len(repeated);totals.update(counts);totals.update(cost);consumed.update(resources)
            by_family.append({'case_id':ep['case_id'],'method':method,**counts,**cost,
                'forward_trial_actual_consumption_by_name':dict(resources),'repeated_inspection_evidence':repeated})
        result[method]={**totals,'forward_trial_actual_consumption_by_name':dict(consumed)}
    atomic_json(out/'mechanism_overhead.json',{'methods':result,'episodes':by_family,
        'scope':'Real API cost of the selected action, not a counterfactual incremental billing estimate. Trial input consumption uses original action dispatch, not nominal recipe arithmetic. Reinspection count is same physical resource configuration, same object and same feedback; does not prove confirmation has zero decision value.',
        'extra_summary_model_calls':0})

if __name__=='__main__':main()
