"""Read-only reconciliation of evidence, then write publication checks/manifest."""
import collections
import gzip
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from scar.io import atomic_json,digest

ROOT=Path('results/stage12')
OUT=ROOT/'diagnostic'


def main():
    def load(name):return json.loads((OUT/(name+'.json')).read_text())
    freeze=load('freeze');states=load('states');judgments=load('judgments')
    protected=freeze['prior_file_hashes'];frozen=freeze['code_hashes']|freeze['data_hashes']
    bad_prior=[p for p,h in protected.items() if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h]
    bad_frozen=[p for p,h in frozen.items() if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h]
    req=[json.loads(line) for line in (OUT/'requests.jsonl').read_text().splitlines()]
    native=[json.loads(line) for line in gzip.open(OUT/'native_branches.jsonl.gz','rt')]
    branches={r['state_id']:r['branches'] for r in native};metrics=load('state_metrics');methods=load('method_metrics')
    errors=[]
    for row in metrics:
        b=branches[row['state_id']].get(row['selected_id'])
        if row['useful']!=bool(b and b['new_key_recipes']) or row['actions']!=(b['actions'] if b else 0):
            errors.append({'state_id':row['state_id'],'method':row['method'],'kind':'raw_metric_mismatch'})
    for method in ['J0','J1','J2','J3']:
        rows=[r for r in metrics if r['method']==method]
        if len(rows)!=50 or any(methods[method][k]!=sum(r[k] for r in rows) for k in ['useful','actions','one_step_useful']):
            errors.append({'method':method,'kind':'aggregate_mismatch'})
    cost=sum(r['request'].get('cost_usd',0) for r in req)
    charged=sum(r['request'].get('charged_or_reserved_usd',0) for r in req)
    completion=load('completion');local=load('local_portable_replay');native_check=load('native_verification')
    nbranch=sum(len(r['branches']) for r in native)
    nactions=sum(b['actions'] for r in native for b in r['branches'].values())
    gate=load('gate');closed=json.loads((ROOT/'closed_loop/status.json').read_text())
    cases=json.loads(Path('results/stage11/cases.json').read_text());case_ids={c['id'] for c in cases}
    suite=list(ET.parse(OUT/'unit_tests.xml').getroot().iter('testsuite'))
    unit={k:sum(int(s.attrib.get(k,0)) for s in suite) for k in ['tests','errors','failures','skipped']}
    judgment=json.loads((ROOT/'research_judgment.json').read_text())
    seen_queries={(j['state_id'],j['method'],j['replicate']) for j in judgments}
    expected_queries={(q['state_id'],q['method'],q['replicate']) for q in load('frozen_queries')}
    checks={
        'protected_history':not bad_prior,'frozen_code_and_data':not bad_frozen,
        'state_digest':digest(states)==freeze['states_digest'],
        'original_ten_only':len(states)==50 and set(s['case_id'] for s in states)==case_ids
            and all(c['game']=='robot_kingdom' for c in cases)
            and all(sum(s['case_id']==cid for s in states)==5 for cid in case_ids),
        'unique_states':len({s['state_id'] for s in states})==50,
        'bounded_candidates':all(2<=len(s['candidates'])<=16 for s in states),
        'source_replay':load('state_replay_checks')['passed'],
        'zero_api_preflight':load('preflight')['passed'] and load('preflight')['api_calls']==0,
        'unit_tests':unit['tests']==freeze['unit_tests']==140 and not any(unit[k] for k in ['errors','failures','skipped']),
        'exact_query_set':len(judgments)==120 and seen_queries==expected_queries,
        'completed_judgments':completion['judgments']==120 and completion['completed']==120 and completion['requests']==len(req),
        'no_request_id_reuse':len({r['request']['request_id'] for r in req})==len(req),
        'model_and_prompt':load('model_audit')['passed'],
        'cost_accounting':abs(cost-completion['ledger_usd'])<1e-9 and abs(charged-cost)<1e-9 and completion['pending']==0,
        'native_replay':native_check['passed'] and native_check['branches']==nbranch and native_check['actions']==nactions
             and all(b['replayed_twice'] and b['actions']<=4 for r in native for b in r['branches'].values()),
        'independent_local_replay':local['passed'] and local['states']==50 and local['branches']==nbranch
             and local['actions_per_replay']==nactions and local['api_calls']==0,
        'raw_metrics':not errors,
        'gate_and_stop_consistent':gate['decision']=='NO-GO' and not gate['passed'] and closed['actual_episodes']==0
             and closed['api_calls']==0 and all(r['status']=='not_run' and r['recovery_at_40'] is None for r in closed['methods'].values()),
        'judgment_consistent':judgment['primary_useful_top1']=={m:v['useful'] for m,v in methods.items()}
             and judgment['decision']==gate['decision'] and abs(judgment['new_cost_usd']-cost)<1e-9,
        'no_post_freeze_tuning_or_paid_resampling':completion['no_paid_resampling'] and not judgment['post_freeze_policy_changes']
             and judgment['paid_resampling']==0,
    }
    files=sorted(p for base in ['scar_stage12','results/stage12','reports/stage12'] for p in Path(base).rglob('*')
                 if p.is_file() and '__pycache__' not in p.parts and p.name not in {'publication_checks.json','artifact_manifest.json'})
    files += [Path('configs/protocol_stage12_diagnostic.json'),Path('tests/test_stage12.py')]
    patterns=[rb'sk-[A-Za-z0-9_-]{20,}',rb'gh[pousr]_[A-Za-z0-9]{20,}',rb'-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----']
    secrets=[]
    for path in [Path('/root/.scar-deepseek-key'),Path('/mnt/Space0/AINative/miyao.txt')]:
        if path.exists():secrets.extend(v.strip().encode() for v in path.read_text().splitlines() if len(v.strip())>12)
    leaks=[];large=[];unexpected=[];broken=[]
    for p in files:
        raw=p.read_bytes()
        if len(raw)>=100_000_000:large.append(str(p))
        if p.suffix not in {'.py','.json','.jsonl','.md','.xml','.gz'} or p.is_symlink():unexpected.append(str(p))
        data=gzip.decompress(raw) if p.suffix=='.gz' else raw
        if any(re.search(pattern,data) for pattern in patterns) or any(s in data for s in secrets):leaks.append(str(p))
        if p.suffix=='.md':
            for link in re.findall(r'\]\(([^)]+)\)',p.read_text()):
                if not link.startswith(('https://','http://','#')) and not (p.parent/link.split('#')[0]).exists():broken.append([str(p),link])
    checks.update(credential_scan=not leaks,file_scope=not unexpected,github_file_sizes=not large,report_links=not broken,
        required_reports=all((Path('reports/stage12')/n).exists() for n in ['LLM探索判断能力报告.md','短程工作流验证报告.md','实验总报告.md','复现指南.md']),
        all_state_evidence=len(list(Path('reports/stage12/states').glob('*.md')))==50)
    result={'checks':checks,'passed':all(checks.values()),'protected_prior_files':len(protected),
        'prior_mismatches':bad_prior,'frozen_mismatches':bad_frozen,'metric_errors':errors,
        'credential_pattern_files':leaks,'unexpected_files':unexpected,'oversize_files':large,'broken_links':broken,
        'unit_tests':unit,'states':50,'branches':nbranch,'actions_per_replay':nactions,'judgments':120,'requests':len(req),
        'new_cost_usd':cost,'project_total_usd':36.796477182+cost,'stageB':'not_run','files':len(files)+2,
        'scope':'our Stage12 code and generated experimental materials; no downloaded engine/model or private credentials/ledger',
        'api_calls_in_publication_check':0}
    atomic_json(ROOT/'publication_checks.json',result)
    assert result['passed'],result
    files.append(ROOT/'publication_checks.json')
    atomic_json(ROOT/'artifact_manifest.json',{'files':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
        'scope':result['scope']+'; manifest excludes itself'})
    print(json.dumps({k:result[k] for k in ['passed','states','branches','requests','new_cost_usd','files']}))


if __name__=='__main__':main()
