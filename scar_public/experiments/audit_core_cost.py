"""Count actual and shared-response workload, including the invalid first batch."""
import argparse
from collections import defaultdict
import json
from pathlib import Path

from scar_public.provider import peak_cost, usage_summary


def lines(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line] if path.exists() else []


def audit(root, invalid):
    assert (root/'analysis.json').exists(), 'Costs are finalized after evaluation'
    workloads = defaultdict(lambda: dict(responses=0,input_tokens=0,output_tokens=0,
                                         estimate_usd_without_local_sharing=0))
    for block in (root/'evaluation').iterdir():
        if not block.is_dir(): continue
        completed = [r for r in lines(block/'api'/'attempts.jsonl') if r['event']=='completed']
        lookup = {(r['step'],r['request_hash']):r for r in completed}
        delivered = [(r['arm'],r) for r in completed]
        for reuse in lines(block/'api'/'reuse.jsonl'):
            delivered.append((reuse['arm'],lookup[(reuse['step'],reuse['request_hash'])]))
        for arm, row in delivered:
            purpose = 'sentry_auxiliary' if row['repair']==100 else 'actor_including_format_repairs'
            entry = workloads[arm+'/'+purpose];usage=row['usage']
            entry['responses'] += 1
            entry['input_tokens'] += usage.get('prompt_tokens',0)
            entry['output_tokens'] += usage.get('completion_tokens',0)
            entry['estimate_usd_without_local_sharing'] += peak_cost(usage)
    groups = dict(valid_formal=usage_summary(root/'evaluation'),
                  valid_smoke=usage_summary(root/'smoke_final'),
                  invalid_formal=usage_summary(invalid/'evaluation'),
                  invalid_root_all_smokes_and_evaluation=usage_summary(invalid))
    total = usage_summary(root)
    previous = usage_summary(invalid)
    for key,value in previous.items():
        if isinstance(value,(int,float)): total[key]+=value
    total['actual_models']=sorted(set(total['actual_models']+previous['actual_models']))
    result = dict(groups=groups,all_work_this_study=total,
        valid_logical_workload_by_arm_and_purpose=dict(workloads),
        pricing_basis_usd_per_million=dict(input_cache_hit=.006,input_cache_miss=.30,output=1.20),
        qualification='Frozen token-based estimate, not an invoice or a verified current price. Unknown-charge attempts are excluded from the numeric cost, not assigned zero cost. Local shared-response reuse differs from provider-side input caching. Invalid outcomes never enter the effect estimate.')
    (root/'cost_audit.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(dict(groups=groups,all_work_this_study=total),indent=2))


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--invalid-root',type=Path,required=True);args=p.parse_args()
    audit(args.root,args.invalid_root)
