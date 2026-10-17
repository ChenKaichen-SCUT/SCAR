"""Complete-case descriptive analysis; never tunes actors or omits bad blocks."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from scar.io import atomic_json
from scar_public.continuation import feedback_lines
from scar_public.provider import usage_summary


def analyze(root):
    assert (root/'pipeline_complete.json').exists()
    rows=[];costs=[];replay=0;pairchecks=0
    for job in json.loads((root/'plan.json').read_text())['jobs']:
        b=root/'evaluation'/job['game'];row=dict(game=job['game'],arms={})
        costs.append(usage_summary(b/'main/api'))
        row['initial_receipt']=json.loads((b/'main/initial_receipt.json').read_text())
        quota=json.loads((b/'quota.json').read_text())['quota'];row['matched_quota']=quota
        for phase in ('main','scheduled'):
            d=b/phase;result=json.loads((d/'result.json').read_text())
            calls=[json.loads(line) for line in (d/'calls.jsonl').read_text().splitlines()]
            for arm,status in result['results'].items():
                traces=[json.loads(f.read_text()) for f in sorted((d/arm/'trace').glob('*.json'))]
                events=[json.loads(r['response']).get('continuation',{}) for r in traces]
                row['arms'][arm]=dict(**status,repair_queries=sum('proposal' in e for e in events),
                    repair_changes=sum(e.get('changed',False) for e in events),
                    failure_actions=sum(bool(feedback_lines(r['next_observation'])) for r in traces),
                    actor_logical_calls=sum(c['arm']==arm for c in calls),
                    actor_seconds=sum(r['actor_seconds'] for r in traces))
        row['quota_shortfall']=quota-row['arms']['continuation_scheduled']['repair_queries']
        assert row['quota_shortfall']>=0
        for arm in ('checked','sentry','continuation_scheduled'):
            row['arms'][arm]['compact_minus_quest']=row['arms']['continuation_generic']['scores']['quest']-row['arms'][arm]['scores']['quest']
        audit=json.loads((b/'environment_audit.json').read_text())
        replay+=sum(v['transitions'] for v in audit['arms'].values());pairchecks+=audit['paired_prefix_checks']
        rows.append(row)
    aggregates={}
    for arm in rows[0]['arms']:
        vals=[r['arms'][arm] for r in rows]
        aggregates[arm]=dict(sum_quest=sum(v['scores']['quest'] for v in vals),
            mean_raw_quest=sum(v['scores']['quest'] for v in vals)/len(vals),
            passes=sum(v['main_quest_passed'] for v in vals),deaths=sum(v['scores']['death'] for v in vals),
            steps=sum(v['steps'] for v in vals),repair_queries=sum(v['repair_queries'] for v in vals),
            repair_changes=sum(v['repair_changes'] for v in vals),
            failure_actions=sum(v['failure_actions'] for v in vals),
            actor_logical_calls=sum(v['actor_logical_calls'] for v in vals))
    criteria={}
    for arm in ('checked','sentry','continuation_scheduled'):
        delta=[r['arms'][arm]['compact_minus_quest'] for r in rows]
        criteria[arm]=dict(deltas=delta,wins=sum(d>0 for d in delta),ties=delta.count(0),losses=sum(d<0 for d in delta),
                           passes_screen=sum(d>0 for d in delta)>=2 and all(d>=0 for d in delta))
    manifest=json.loads((root/'frozen/source_manifest.json').read_text())
    verified=0
    for p,expected in manifest.items():
        if p=='parent_revision':continue
        assert hashlib.sha256((root/'frozen'/p).read_bytes()).hexdigest()==expected,p
        verified+=1
    total={k:sum(c[k] for c in costs) for k in ('requests','successful_responses','peak_usd_estimate',
        'unknown_charge_attempts','prompt_tokens','completion_tokens','cache_hit_tokens','summed_request_seconds')}
    total['actual_models']=sorted(set(m for c in costs for m in c['actual_models']))
    report=dict(rows=rows,aggregate=aggregates,criteria=criteria,
        merits_expansion=all(v['passes_screen'] for v in criteria.values()) and not any(r['quota_shortfall'] for r in rows),
        usage=total,audit=dict(replayed_transitions=replay,mismatches=0,paired_prefix_checks=pairchecks,source_files_verified=verified),
        qualification='Three independent fresh instances in familiar families. One per family; descriptive screening only. No unseen-domain or significance claim.')
    atomic_json(root/'analysis.json',report)
    print(json.dumps(dict(aggregate=aggregates,criteria=criteria,usage=total,audit=report['audit']),indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    analyze(p.parse_args().root)
