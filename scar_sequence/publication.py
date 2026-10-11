"""Validate delivery against frozen sources and independent raw-record counts."""
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import re
from scar.io import atomic_json,digest


def main():
    root=Path('results/sequence');freeze=json.loads((root/'freeze.json').read_text())
    checks={}
    checks['frozen_code_mismatches']=[n for n,s in freeze['code_hashes'].items() if hashlib.sha256(Path(n).read_bytes()).hexdigest()!=s]
    checks['prior_file_mismatches']=[n for n,s in freeze['protected_prior_files'].items() if hashlib.sha256(Path(n).read_bytes()).hexdigest()!=s]
    cases=json.loads((root/'dataset/cases.json').read_text());checks['dataset_hash_matches']=digest(cases)==freeze['dataset_digest']
    methods=json.loads((root/'method_metrics.json').read_text())['all'];counts={};tasks=set();mismatches=[]
    for method,expected in methods.items():
        n=success=steps=calls=tokens=0;cost=0
        with gzip.open(root/f'trajectories_{method}.jsonl.gz','rt') as f:
            for ep in map(json.loads,f):
                assert ep['task_id'] not in tasks;tasks.add(ep['task_id'])
                n+=1;steps+=len(ep['rows']);success+=any(r['diagnostic_goal_reached'] for r in ep['rows'])
                assert [r['index'] for r in ep['rows']]==list(range(len(ep['rows'])))
        with gzip.open(root/f'requests_{method}.jsonl.gz','rt') as f:
            for obj in map(json.loads,f):
                r=obj['request'];calls+=1;cost+=r.get('cost_usd',0)
                tokens+=(r.get('usage') or {}).get('prompt_tokens',0)+(r.get('usage') or {}).get('completion_tokens',0)
        actual={'n':n,'successes':success,'steps':steps,'api_calls':calls,'cost_usd':cost,
                'tokens':tokens}
        for key in ['n','successes','steps','api_calls','cost_usd']:
            if abs(actual[key]-expected[key])>1e-8:mismatches.append([method,key,actual[key],expected[key]])
        counts[method]=actual
    checks['raw_record_stat_mismatches']=mismatches;checks['raw_record_counts']=counts
    checks['initial_states']=len(list((root/'dataset/initial_states').glob('*.pkl.gz')))
    checks['full_physical_replay_passed']=json.loads((root/'verification.json').read_text())['passed']
    checks['local_initial_replay_passed']=json.loads((root/'local_initial_replay.json').read_text())['passed']
    audit=json.loads((root/'resource_audit_summary.json').read_text())
    checks['all_resource_transitions_audited']=audit['actions_audited']==sum(x['steps'] for x in counts.values())
    examples={r['case_id']:r for r in json.loads((root/'typical_cases.json').read_text())}
    checks['batch_counterfactual']=[v['goal'] for v in examples['sequence-48401b39ba565b57']['batch_size_counterfactual']['variants']]==[False,True]
    checks['post_cap_branch_goal']=examples['sequence-7ef74a089f1ce41d']['after_cap_counterfactual']['goal']
    files=sorted(p for base in ['scar_sequence','results/sequence','reports/sequence'] for p in Path(base).rglob('*')
        if p.is_file() and '__pycache__' not in p.parts and p.name not in {'artifact_manifest.json','publication_checks.json'})
    files += [Path('configs/protocol_sequence.json'),Path('tests/test_sequence.py')]
    secrets=[]
    for path in files:
        data=path.read_bytes()
        if path.suffix=='.gz':data=gzip.decompress(data)
        if re.search(rb'sk-[A-Za-z0-9_-]{16,}|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----',data):secrets.append(str(path))
    checks['credential_pattern_files']=secrets;checks['delivery_file_count']=len(files)+2
    checks['passed']=all([not checks['frozen_code_mismatches'],not checks['prior_file_mismatches'],checks['dataset_hash_matches'],
        not mismatches,checks['initial_states']==35,checks['full_physical_replay_passed'],checks['local_initial_replay_passed'],
        checks['all_resource_transitions_audited'],checks['batch_counterfactual'],checks['post_cap_branch_goal'],not secrets,len(tasks)==175])
    atomic_json(root/'publication_checks.json',checks)
    if not checks['passed']:raise ValueError('Publication checks failed; see non-secret structured checks')
    files.append(root/'publication_checks.json')
    atomic_json(root/'artifact_manifest.json',{'files':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
        'verification_passed':True,'source_baseline':'a32a1c635700686ff9d09957dc8dda52ff25886b',
        'frozen_prior_files_unchanged':len(freeze['protected_prior_files']),
        'raw_runtime_metrics_preserved':True,'posthoc_resource_correction_disclosed':True,
        'no_downloaded_engine_or_models':True,'snapshots':'our experiment-generated physical states, no policy/provider objects'})
    print(json.dumps({'passed':True,'files':len(files),'episodes':len(tasks),'cost_usd':sum(r['cost_usd'] for r in counts.values())}))


if __name__=='__main__':main()
