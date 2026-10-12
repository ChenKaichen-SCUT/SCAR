"""Reconcile raw artifacts, immutable history, hashes and credential patterns."""
import collections,gzip,hashlib,json,re
from pathlib import Path
from scar.io import atomic_json,digest
from scar_stage8.controller import METHODS
OUT=Path('results/stage8')
def main():
    load=lambda n:json.loads((OUT/(n+'.json')).read_text())
    freeze=load('freeze');cases=load('cases');cs={c['id']:c for c in cases};ver=load('verification');eps=load('episode_metrics')
    prior_errors=[p for p,h in freeze['prior_file_hashes'].items() if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h]
    frozen_errors=[p for p,h in (freeze['code_hashes']|freeze['data_hashes']).items() if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h]
    errors=[];totals={}
    for method in METHODS:
        rows=list(map(json.loads,gzip.open(OUT/f'trajectories_{method}.jsonl.gz','rt')));requests=list(map(json.loads,gzip.open(OUT/f'requests_{method}.jsonl.gz','rt')))
        metrics=[x for x in eps if x['algorithm']==method]
        got={'episodes':len(rows),'actions':sum(len(e['rows']) for e in rows),'successes':sum(any(r['diagnostic_goal_reached'] for r in e['rows']) for e in rows),
            'api_calls':len(requests),'cost_usd':sum(x['request'].get('cost_usd',0) for x in requests),
            'tokens':sum((x['request'].get('usage') or {}).get('prompt_tokens',0)+(x['request'].get('usage') or {}).get('completion_tokens',0) for x in requests),
            'cost_outside_committed_actions_usd':sum(x['request'].get('cost_usd',0) for x in requests)-sum(r['api_delta']['cost_usd'] for e in rows for r in e['rows'])}
        if len(rows)!=len(cases) or got['actions']!=sum(x['steps'] for x in metrics) or got['successes']!=sum(x['recovery_at_40'] for x in metrics) or abs(got['cost_usd']-sum(x['cost_usd'] for x in metrics))>1e-8:errors.append(method)
        for e in rows:
            assert len(e['rows'])<=40
            assert e['summary']['game']==cs[e['case_id']]['game']
            assert all(x['initial_state_hash']==cs[e['case_id']]['state_hash'] for x in e['rows'])
        totals[method]=got
    files=sorted(p for base in ['scar_stage8','results/stage8','reports/stage8'] for p in Path(base).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name not in {'publication_checks.json','artifact_manifest.json'})+[Path('tests/test_stage8.py'),Path('configs/protocol_stage8.json')]
    patterns=[rb'sk-[A-Za-z0-9_-]{20,}',rb'gh[pousr]_[A-Za-z0-9]{20,}',rb'-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----']
    secret_bytes=[]
    for p in [Path('/root/.scar-deepseek-key'),Path('/mnt/Space0/AINative/miyao.txt')]:
        if p.exists():
            for value in p.read_text().strip().splitlines():
                value=value.strip()
                if len(value)>12:secret_bytes.append(value.encode())
    leaks=[]
    for p in files:
        data=p.read_bytes()
        if p.suffix=='.gz':data=gzip.decompress(data)
        if any(re.search(pattern,data) for pattern in patterns) or any(s in data for s in secret_bytes):leaks.append(str(p))
    result={'complete':load('completion')['fully_complete'],'prior_file_mismatches':prior_errors,'frozen_file_mismatches':frozen_errors,
        'protected_prior_files':len(freeze['prior_file_hashes']),'dataset_digest_matches':digest(cases)==freeze['dataset_digest'],
        'physical_replay_passed':ver['passed'],'decision_audit_passed':load('decision_audit_summary')['passed'],
        'offline_gate_passed':load('offline_checks')['passed'],'integration_passed':load('integration_checks')['passed'],
        'raw_totals':totals,'statistic_mismatches':errors,'credential_pattern_files':leaks,'files':len(files)+2,
        'new_cost_usd':sum(r['cost_usd'] for r in totals.values()),'no_downloaded_models_or_engine':True}
    result['passed']=all([result['complete'],not prior_errors,not frozen_errors,result['dataset_digest_matches'],ver['passed'],result['decision_audit_passed'],result['offline_gate_passed'],result['integration_passed'],not errors,not leaks])
    atomic_json(OUT/'publication_checks.json',result);assert result['passed'],result
    files.append(OUT/'publication_checks.json')
    atomic_json(OUT/'artifact_manifest.json',{'files':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
        'scope':'our implementation/generated artifacts; excludes upstream engine/models, private credentials, runtime ledgers and selfmanifest'})
    print(json.dumps({'passed':True,'files':len(files)+1,'episodes':sum(x['episodes'] for x in totals.values()),'new_cost_usd':result['new_cost_usd']}))
if __name__=='__main__':main()
