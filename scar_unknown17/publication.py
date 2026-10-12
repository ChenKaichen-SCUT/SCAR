"""Frozen source, raw accounting, delivery hashes and credential-pattern scan."""
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import re
from scar.io import atomic_json,digest


def main():
    out=Path('results/unknown17');freeze=json.loads((out/'freeze.json').read_text())
    prior={p:h for p,h in freeze['prior_file_hashes'].items()}
    old_errors=[p for p,h in prior.items() if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h]
    code_errors=[p for p,h in freeze['code_hashes'].items() if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h]
    cases=json.loads((out/'cases.json').read_text());complete=json.loads((out/'completion.json').read_text());ver=json.loads((out/'verification.json').read_text())
    totals={};stats_errors=[];requests={};metrics=json.loads((out/'method_metrics.json').read_text())['all']
    for path in sorted(out.glob('trajectories_*.jsonl.gz')):
        rows=[json.loads(l) for l in gzip.open(path,'rt')];method=rows[0]['summary']['algorithm']
        count=Counter();cost=0
        for e in rows:
            rs=e['rows'];count['episodes']+=1;count['steps']+=len(rs);count['successes']+=any(r['diagnostic_goal_reached'] for r in rs)
            cost+=sum(r['api_delta']['cost_usd'] for r in rs)
            assert len(rs)<=40
            assert all(r['initial_state_hash']==next(c['state_hash'] for c in cases if c['id']==e['case_id']) for r in rs)
        totals[method]=dict(count,cost_usd=cost)
        expected=metrics[method]
        if count['episodes']!=17 or count['steps']!=expected['steps'] or count['successes']!=expected['successes'] or abs(cost-expected['cost_usd'])>1e-8:stats_errors.append(method)
        req=[json.loads(l) for l in gzip.open(out/f'requests_{method}.jsonl.gz','rt')]
        requests[method]={'count':len(req),'cost_usd':sum(r['request'].get('charged_or_reserved_usd',0) for r in req),
            'tokens':sum((r['request'].get('usage') or {}).get('prompt_tokens',0)+(r['request'].get('usage') or {}).get('completion_tokens',0) for r in req)}
        if abs(requests[method]['cost_usd']-cost)>1e-8:stats_errors.append(method+':ledger')
    newfiles=sorted([p for d in ['scar_unknown17','results/unknown17','reports/unknown17'] for p in Path(d).rglob('*')
        if p.is_file() and '__pycache__' not in p.parts and p.name not in {'publication_checks.json','artifact_manifest.json'}]+
        [Path('configs/protocol_unknown17.json'),Path('tests/test_unknown17.py')])
    leaked=[];patterns=[rb'sk-[A-Za-z0-9_-]{20,}',rb'gh[pousr]_[A-Za-z0-9]{20,}',rb'-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----']
    for p in newfiles:
        data=p.read_bytes()
        if p.suffix=='.gz':data=gzip.decompress(data)
        if any(re.search(pattern,data) for pattern in patterns):leaked.append(str(p))
    target=json.loads((out/'targeted_checks_summary.json').read_text());conflict=json.loads((out/'overproduction_counterfactual.json').read_text())
    summary={'old_file_mismatches':old_errors,'frozen_code_mismatches':code_errors,
        'dataset_digest_matches':digest(cases)==freeze['dataset_digest'],'complete':complete['fully_complete'],
        'full_physical_replay_passed':ver['passed'],'raw_statistic_mismatches':stats_errors,
        'raw_counts':totals,'requests':requests,'new_cost_usd':sum(x['cost_usd'] for x in requests.values()),
        'credential_pattern_files':leaked,'productive_batch_local_goal_changes':len(target['local_goal_changes']),
        'overproduction_goal_pair':[r['goal'] for r in conflict['variants']],
        'delivery_file_count':len(newfiles)+2}
    summary['passed']=not old_errors and not code_errors and summary['dataset_digest_matches'] and summary['complete'] and ver['passed'] and not stats_errors and not leaked and summary['overproduction_goal_pair']==[True,False]
    atomic_json(out/'publication_checks.json',summary)
    assert summary['passed'],summary
    newfiles.append(out/'publication_checks.json')
    atomic_json(out/'artifact_manifest.json',{'files':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in newfiles},
        'scope':'new implementation and generated experimental results only; excludes this self-manifest, downloaded engine/models, keys and runtime ledgers'})
    print(json.dumps({'passed':True,'files':len(newfiles),'episodes':153,'cost_usd':summary['new_cost_usd']}))

if __name__=='__main__':main()
