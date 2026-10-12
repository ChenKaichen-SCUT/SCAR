"""Final delivery: immutable-source checks, raw statistics and credential scan."""
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import re
from scar.io import atomic_json,digest


def main():
    out=Path('results/stage7');freeze=json.loads((out/'freeze.json').read_text());load=lambda n:json.loads((out/(n+'.json')).read_text())
    old_errors=[p for p,h in freeze['prior_file_hashes'].items() if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h]
    code_errors=[p for p,h in freeze['code_hashes'].items() if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h]
    cases=load('cases');expected=load('method_metrics')['all'];ver=load('verification');totals={};requests={};errors=[]
    summaries={(r['id'],r['algorithm']):r for r in load('all_summaries')}
    for path in sorted(out.glob('trajectories_C*.jsonl.gz')):
        episodes=list(map(json.loads,gzip.open(path,'rt')));method=episodes[0]['summary']['algorithm'];count=Counter();rowcost=fullcost=0
        for ep in episodes:
            rows=ep['rows'];count['episodes']+=1;count['actions']+=len(rows);count['successes']+=any(r['diagnostic_goal_reached'] for r in rows)
            rowcost+=sum(r['api_delta']['cost_usd'] for r in rows);fullcost+=ep['summary']['cost_usd']
            assert len(rows)<=40
            assert all(r['initial_state_hash']==next(c['state_hash'] for c in cases if c['id']==ep['case_id']) for r in rows)
            assert all(r['stage7_flags']==json.loads(Path('configs/protocol_stage7.json').read_text())['switches'][method] for r in rows)
        req=list(map(json.loads,gzip.open(out/f'requests_{method}.jsonl.gz','rt')))
        requests[method]={'count':len(req),'charged_usd':sum(r['request'].get('charged_or_reserved_usd',0) for r in req),
            'cost_usd':sum(r['request'].get('cost_usd',0) for r in req),
            'tokens':sum((r['request'].get('usage') or {}).get('prompt_tokens',0)+(r['request'].get('usage') or {}).get('completion_tokens',0) for r in req)}
        e=expected[method]
        if count['episodes']!=17 or count['actions']!=e['steps'] or count['successes']!=e['successes'] or abs(fullcost-e['cost_usd'])>1e-8 or abs(fullcost-requests[method]['cost_usd'])>1e-8:errors.append(method)
        totals[method]=dict(count,all_request_cost_usd=fullcost,committed_action_cost_usd=rowcost,
            request_cost_outside_committed_actions_usd=fullcost-rowcost)
    files=sorted([p for d in ['scar_unknown17_stage7','results/stage7','reports/stage7'] for p in Path(d).rglob('*') if p.is_file()
        and '__pycache__' not in p.parts and p.name not in {'publication_checks.json','artifact_manifest.json'}]+
        [Path('configs/protocol_stage7.json'),Path('tests/test_stage7.py')])
    patterns=[rb'sk-[A-Za-z0-9_-]{20,}',rb'gh[pousr]_[A-Za-z0-9]{20,}',rb'-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----']
    leaks=[]
    for p in files:
        data=p.read_bytes()
        if p.suffix=='.gz':data=gzip.decompress(data)
        if any(re.search(x,data) for x in patterns):leaks.append(str(p))
    result={'complete':load('completion')['fully_complete'],'code_mismatches':code_errors,'prior_file_mismatches':old_errors,
        'protected_prior_files':len(freeze['prior_file_hashes']),'dataset_digest_matches':digest(cases)==freeze['dataset_digest'],
        'physical_replay_passed':ver['passed'],'decision_audit_passed':load('decision_audit_summary')['passed'],
        'full_prompt_parity_passed':load('full_prompt_parity')['passed'],'offline_gate_passed':load('offline_checks')['passed'],
        'raw_counts':totals,'requests':requests,'statistic_mismatches':errors,'credential_pattern_files':leaks,
        'new_cost_usd':sum(r['charged_usd'] for r in requests.values()),'delivery_file_count':len(files)+2}
    result['passed']=all([result['complete'],not code_errors,not old_errors,result['dataset_digest_matches'],
        ver['passed'],result['decision_audit_passed'],result['full_prompt_parity_passed'],result['offline_gate_passed'],not errors,not leaks,
        set(totals)=={'C0','C1','C2','C3','C4','C5'},abs(result['new_cost_usd']-ver['new_ledger_usd'])<1e-8])
    atomic_json(out/'publication_checks.json',result);assert result['passed'],result
    files.append(out/'publication_checks.json')
    atomic_json(out/'artifact_manifest.json',{'files':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
        'scope':'our Stage7 implementation and generated experimental results only; excludes downloaded engine/models, credentials, runtime ledgers and this self manifest'})
    print(json.dumps({'passed':True,'files':len(files)+1,'episodes':102,'new_cost_usd':result['new_cost_usd']}))

if __name__=='__main__':main()
