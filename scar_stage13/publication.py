"""Reconcile all sources, frozen policies, numerical reports and publication scope."""
import ast
import collections
import gzip
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from scar.io import atomic_json,digest
from scar_stage13.analyze import load,brief,aggregate,OUT,OLD
from scar_stage13.native import verify_freeze
from scar_stage13.policy import decide,intent,entries
from scar_stage13.prepare import public_history
from scar_stage12.public import controller,primitive_candidate


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    verify_freeze();freeze=load(OUT/'freeze.json');prior=load(OUT/'prior_manifest.json')
    states=load(OLD/'states.json');by={s['state_id']:s for s in states}
    inputs={r['state_id']:r['public'] for r in load(OUT/'public_inputs.json')}
    ds={r['state_id']:r for r in load(OUT/'decisions.json')}
    native={r['state_id']:r['branches'] for r in map(json.loads,gzip.open(OLD/'native_branches.jsonl.gz','rt'))}
    extras=list(map(json.loads,gzip.open(OUT/'native_supplements.jsonl.gz','rt')))
    extra={(r['state_id'],r['candidate']['id']):r['branch'] for r in extras if r['kind']=='base_proposal'}
    episodes={}
    for stage,methods in [(10,['S1']),(11,['E0','E1'])]:
        for m in methods:
            for ep in map(json.loads,gzip.open(f'results/stage{stage}/trajectories_{m}.jsonl.gz','rt')):episodes[ep['task_id']]=ep
    judgments={(r['state_id'],r['method'],r['replicate']):r for r in load(OLD/'judgments.json')}
    source_checks=[];policy_checks=[]
    for s in states:
        sid=s['state_id'];p=inputs[sid];row=episodes[s['source_task']]['rows'][s['source_index']]
        h=public_history(episodes[s['source_task']],s['source_index'])
        source_checks.append({'state_id':sid,'passed':h==p['history'] and row['observation']==s['observation']
            and row['stage7_state_before']==s['public_controller']==p['controller']
            and row['executed_action']==s['rule_actions']['J0']==p['s1_action']
            and row['proposed_action']==s['frozen_base_proposal']==p['base_proposal']
            and p['candidates']==s['candidates'] and p['remaining_actions']==s['remaining_actions']
            and p['j3_selected']==judgments[sid,'J3',0]['parsed']['selected_candidate_id']
            and set(p)=={'controller','observation','candidates','history','base_proposal','s1_action','remaining_actions','j3_selected'}})
        got=decide(p);same=got=={k:ds[sid][k] for k in got}
        c=controller(p['controller'],p['observation']);before=c.to_dict();entries(c,p['candidates'],p['history'])
        unchanged=before==c.to_dict()
        policy_checks.append({'state_id':sid,'choices_reproduced':same,'preview_read_only':unchanged,
            'all_selected_ids_in_frozen_menu':all(k in {x['id'] for x in s['candidates']} for k in got['choices'].values())})
    rows=load(OUT/'state_metrics.json');metrics=load(OUT/'method_metrics.json');errors=[]
    for r in rows:
        b=native[r['state_id']][r['candidate_id']];expected=brief(by[r['state_id']],b)
        if any(r[k]!=v for k,v in expected.items()):errors.append([r['state_id'],r['method'],'branch_mismatch'])
    baseline=[r for r in rows if r['method']=='C0']
    for m in metrics:
        if aggregate([r for r in rows if r['method']==m],baseline)!=metrics[m]:errors.append([m,'aggregate'])
    opportunity={s['state_id'] for s in states if any(native[s['state_id']][c['id']]['useful'] for c in s['candidates'])}
    expected_misses={r['state_id'] for r in baseline if r['state_id'] in opportunity and not r['useful']}
    misses=load(OUT/'misses.json')
    for r in misses:
        sid=r['state_id'];s=by[sid]
        if r['all_public_candidates']!=s['candidates'] or r['public_view']!=s['public_view']:errors.append([sid,'miss_public_source'])
        good=[brief(s,native[sid][c['id']]) for c in s['candidates'] if native[sid][c['id']]['useful']]
        if r['useful_candidates']!=good:errors.append([sid,'miss_counterfactual'])
        pc=primitive_candidate(s['frozen_base_proposal']);b=native[sid].get(pc['id']) or extra[sid,pc['id']]
        if r['base_proposal_branch']!=brief(s,b):errors.append([sid,'base_counterfactual'])
    llm=load(OUT/'llm_pairs.json');ls=load(OUT/'llm_summary.json')
    for r in llm:
        if r['J3_raw_judgment']!=judgments[r['state_id'],'J3',0]['parsed']:errors.append([r['state_id'],'J3_raw'])
        menu={c['id']:c for c in by[r['state_id']]['candidates']};seen=set();unique=[]
        for cid in r['J3_top3_original_ids']:
            k=intent(menu[cid])
            if k not in seen:unique.append(cid);seen.add(k)
        if unique!=r['J3_distinct_ranked_ids']:errors.append([r['state_id'],'intent_dedup'])
    plan=load(OUT/'supplement_plan.json');server=load(OUT/'native_supplements.jsonl.gz.verification.json');local=load(OUT/'local_replay.verification.json')
    expected_jobs=[{k:r[k] for k in ['state_id','candidate','limit','kind']} for r in extras]
    first4=all(r['branch']['trace'][:4]==native[r['state_id']][r['candidate']['id']]['trace'] for r in extras if r['kind']=='truncation_sensitivity')
    # Reconcile rendered native actions and feedback with exact source strings.
    pages=[]
    for s in states:
        sid=s['state_id'];body=(Path('reports/stage13/states')/(sid+'.md')).read_text()
        ok=s['observation']['text'] in body
        for cid,b in native[sid].items():
            ok=ok and f'### {cid}' in body
            for tr in b['trace']:ok=ok and tr['feedback'] in body and f"`{tr['action']}`" in body
        pages.append({'state_id':sid,'passed':bool(ok)})
    suites=[]
    for path in [OUT/'unit_tests.xml',OUT/'dependency_tests.xml']:suites+=list(ET.parse(path).getroot().iter('testsuite'))
    tests={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ['tests','failures','errors','skipped']}
    policy_tree=ast.parse(Path('scar_stage13/policy.py').read_text())
    imports=[n.module for n in ast.walk(policy_tree) if isinstance(n,ast.ImportFrom)]
    forbidden={'scar.environment','scar_stage13.native','scar_stage13.analyze','scar_stage12.evaluate','openai','socket','requests'}
    checks={'prior_2094_files_unchanged':len(prior)==2094 and all(sha(p)==h for p,h in prior.items()),
        'freeze_manifest_hash':sha(OUT/'prior_manifest.json')==freeze['prior_manifest_sha256'],
        'frozen_code_inputs_choices_unchanged':all(sha(p)==h for p,h in freeze['frozen_hashes'].items()),
        'original50_original10':len(states)==50 and len({s['case_id'] for s in states})==10 and len(opportunity)==27,
        'public_source_prefixes':all(r['passed'] for r in source_checks),
        'public_policy_only':not (set(imports)&forbidden),
        'all_frozen_choices_reproduced':all(r['choices_reproduced'] and r['preview_read_only'] and r['all_selected_ids_in_frozen_menu'] for r in policy_checks),
        'main_window4':all(native[r['state_id']][r['candidate_id']]['actions']<=min(4,by[r['state_id']]['remaining_actions']) for r in rows),
        'all_metrics_match_native_sources':not errors,
        'all17_misses':len(misses)==17 and {r['state_id'] for r in misses}==expected_misses,
        'all50_llm_pairs_and12_differences':len(llm)==50 and len(ls['gains'])==4 and len(ls['losses'])==8 and len(ls['other38'])==38,
        'all_changed_pairs_retained':len(load(OUT/'changed_pairs.json'))==sum(r['changed'] for r in rows if r['method'] in {'C1','C2','C3','L'}),
        'native_supplement_plan_exact':expected_jobs==plan['jobs'] and len(extras)==70,
        'base_proposals_all50':len(plan['reused_base_proposals'])+len(extra)==50,
        'server_and_local_double_replay':server['passed'] and local['passed'] and local['independent_replay'] and server['branches']==local['branches']==70 and server['actions_per_replay']==local['actions_per_replay']==347,
        'all_extended_first4_unchanged':first4,
        'native_zero_api_network_disabled':server['api_calls']==local['api_calls']==0 and server['network_disabled_in_workers'] and local['network_disabled_in_workers'],
        'state_report_sources':all(p['passed'] for p in pages),
        'tests':tests['tests']==149 and not any(tests[k] for k in ['failures','errors','skipped']),
        'text_audit_separate':load(OUT/'public_text_novelty_audit.json')['policy_unchanged'] and load(OUT/'public_text_novelty_audit.json')['stage12_primary_metric_unchanged'],
        'no_go_and_no_closed_loop':load(OUT/'research_judgment.json')['decision']=='NO-GO' and load(OUT/'research_judgment.json')['closed_loop_success'] is None}
    exclusions={'publication_checks.json','artifact_manifest.json'}
    files=sorted(p for root in ['scar_stage13','results/stage13','reports/stage13'] for p in Path(root).rglob('*')
        if p.is_file() and '__pycache__' not in p.parts and p.name not in exclusions)
    secrets=[]
    for path in [Path('/mnt/Space0/AINative/miyao.txt'),Path('/root/.scar-deepseek-key')]:
        if path.exists():secrets.extend(v.strip().encode() for v in path.read_text().splitlines() if len(v.strip())>12)
    patterns=[rb'sk-[A-Za-z0-9_-]{20,}',rb'gh[pousr]_[A-Za-z0-9]{20,}',rb'-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----']
    leaks=[];large=[];scope=[];links=[]
    for p in files:
        raw=p.read_bytes();data=gzip.decompress(raw) if p.suffix=='.gz' else raw
        if any(re.search(x,data) for x in patterns) or any(k in data for k in secrets):leaks.append(str(p))
        if len(raw)>=100_000_000:large.append(str(p))
        if p.is_symlink() or p.suffix not in {'.py','.md','.json','.jsonl','.xml','.gz'}:scope.append(str(p))
        if p.suffix=='.md':
            for target in re.findall(r'\]\(([^)]+)\)',p.read_text()):
                if not target.startswith(('https://','http://','#')):
                    dest=p.parent/target.split('#')[0]
                    if dest.name=='publication_checks.json' and dest.parent.resolve()==OUT.resolve():continue
                    if not dest.exists():links.append([str(p),target])
    checks.update(no_credentials=not leaks,github_sizes=not large,only_own_artifacts=not scope,report_links=not links)
    result={'passed':all(checks.values()),'checks':checks,'errors':errors,'source_checks':source_checks,'policy_checks':policy_checks,
        'report_checks':pages,'tests':tests,'protected_prior_files':len(prior),'files_excluding_self_and_manifest':len(files),
        'leaks':leaks,'unexpected':scope,'broken_links':links,'api_calls':0,'new_cost_usd':0,
        'project_total_usd':36.888925758,'closed_loop_episodes':0,'closed_loop_success':None,
        'scope':'our Stage13 code, generated evidence and Chinese reports only; no downloaded engine, secrets, dependencies or binaries'}
    atomic_json(OUT/'publication_checks.json',result)
    assert result['passed'],{k:v for k,v in checks.items() if not v}
    files.append(OUT/'publication_checks.json')
    atomic_json(OUT/'artifact_manifest.json',{'files':{str(p):sha(p) for p in files},'scope':result['scope'],'self_excluded':True})
    print(json.dumps({'passed':True,'tests':tests,'prior_files':len(prior),'files':len(files)+1,'api_calls':0}))

if __name__=='__main__':main()
