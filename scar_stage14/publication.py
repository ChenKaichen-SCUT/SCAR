"""Reconcile source integrity, actual native witnesses, reports and upload scope."""
import argparse
import ast
import gzip
import re
from pathlib import Path
import xml.etree.ElementTree as ET
from scar.io import atomic_json
from scar_stage14.common import ROOT,OLD,sha,load,records
from scar_stage14.replay import verify_freezes


def checks():
    verify_freezes();prior=load(ROOT/'prior_manifest.json')
    for f in ['replay_freeze.json','residual_replay_freeze.json']:
        for p,h in load(ROOT/f)['hashes'].items():assert sha(p)==h,p
    suites=list(ET.parse(ROOT/'full_regression_tests.xml').getroot().iter('testsuite'))
    test={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ['tests','failures','errors','skipped']}
    states={s['state_id']:s for s in load(OLD/'states.json')};pubs=load(ROOT/'intent_public_inputs.json')
    intents={(r['state_id'],r['intent']['id']):r['intent'] for r in load(ROOT/'candidate_intents.json')}
    refs=load(ROOT/'intent_references.json');raw=[r for p in ['reused_intent_branches.jsonl.gz','native_intent_branches.jsonl.gz'] for r in records(ROOT/p)]
    first=[];bounds=[]
    for r in raw:
        i=intents[r['state_id'],r['intent_id']];b=r['branch']
        first.append(bool(b['trace']) and b['trace'][0]['action']==i['first_action'])
        bounds.append(len(b['trace'])<=min(8,pubs[r['state_id']]['remaining_actions']))
    residual=list(records(ROOT/'residual_native_branches.jsonl.gz'));jobs={j['state_id']:j for j in load(ROOT/'residual_replay_plan.json')['jobs']}
    for r in residual:
        j=jobs[r['state_id']];first.append(r['branch']['trace'][0]['action']==j['intent']['first_action'])
        bounds.append(r['branch']['actions']<=min(8,j['public']['remaining_actions']))
    certificates=[load(ROOT/p) for p in ['native_intent_branches.jsonl.gz.verification.json','local_native.verification.json',
        'residual_native_branches.jsonl.gz.verification.json','local_residual.verification.json']]
    native_ok=all(c['passed'] and c['each_replayed_twice'] and c['network_disabled'] and c['api_calls']==0 for c in certificates)
    native_ok=native_ok and certificates[1]['independent_local_replay'] and certificates[3]['independent_local_replay']
    native_ok=native_ok and [c['branches'] for c in certificates]==[47,47,22,22] and [c['actions_per_replay'] for c in certificates]==[169,169,86,86]
    stats=load(ROOT/'knowledge_statistics.json');rr=load(ROOT/'residual_summary.json');rows=load(ROOT/'calibrated_state_metrics.json')
    summaries=load(ROOT/'calibrated_method_metrics.json');arith=[]
    for s in summaries:
        selected=[r for r in rows if (r['panel'],r['window'],r['method'])==(s['panel'],s['window'],s['method'])]
        arith.append(len(selected)==50 and all(sum(r[k] for r in selected)==s[k] for k in ['actions','useful','rejections','environment_key_loss']))
    main={r['method']:r['useful'] for r in summaries if r['panel']=='both' and r['window']==4}
    forbidden={'scar.environment','scar_stage14.native','scar_stage12.evaluate','openai','requests','socket'}
    public_imports=[]
    for file in ['intents.py','executor.py','knowledge.py']:
        tree=ast.parse((Path('scar_stage14')/file).read_text())
        public_imports += [n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
    ok={'prior_2185_files_unchanged':len(prior)==2185 and all(sha(p)==h for p,h in prior.items()),
        'all_four_freezes_intact':True,'all_formal_data_audited':stats['formal_episodes']==90 and stats['formal_actions']==2837,
        'all_requests_aligned':stats['matched_primary_requests']==2837,
        'no_history_time_leak':load(ROOT/'history_time_audit.json')['passed'],
        'parser_gold_passed':load(ROOT/'parser_validation.json')['passed'],
        'original50_original10':len(states)==50 and len({s['case_id'] for s in states.values()})==10,
        'all_historical_branches_audited':stats['stage12_branches']==363 and stats['stage13_branches']==70,
        'public_only_modules':not(set(public_imports)&forbidden),
        'public_input_whitelist':all(set(p)=={'controller','observation','remaining_actions'} for p in pubs.values()),
        'all_first_actions_preserved':all(first),'all_original_remaining_budgets_respected':all(bounds),
        'all377_intents_evaluated':len(raw)==len(intents)==377,
        'both_sites_both_repeats_exact':native_ok,
        'all_panels_metrics_reconcile':len(rows)==2400 and all(arith),
        'original_metrics_reproduced':load(ROOT/'intent_interpretation_summary.json')['historical_metrics_exact'],
        'main_scores':main=={'J0':14,'J1':17,'J2':4,'J3':6},
        'old17_complete':rr['original_misses']==17 and rr['original17_total_recovered4']==4 and rr['original17_remaining4']==13,
        'all90_full_tasks_including_success':len(load(ROOT/'full_episode_failure_audit.json'))==90 and rr['full_successes']==39,
        'all69_reference_commitments':len(load(ROOT/'full_reference_commitments_final.json'))==69,
        'all22_unfinished_accepted_witnesses':len(residual)==22,
        'no_cross_family_workflow_claim':rr['supplement']['confirmed_F4_families']==['fiend_helm'] and rr['supplement']['confirmed_F4_unique_physical_states']==1,
        'inventory_completion_amendment_disclosed':load(ROOT/'completion_scoring_amendment.json')['native_actions_feedback_state_hashes_unchanged'],
        'tests_passed':test['tests']==215 and not any(test[k] for k in ['failures','errors','skipped']),
        'server_independent_analysis_matches':load(ROOT/'server_verification.json')['passed'],
        'NO_GO_no_new_API':rr['decision']=='NO-GO' and rr['new_api_calls']==0 and rr['new_model_cost_usd']==0}
    pages=list(Path('reports/stage14/states').glob('*.md'));epages=list(Path('reports/stage14/episodes').glob('*.md'))
    ok['complete_reports']=len(pages)==50 and len(epages)==90
    ok['state_report_original_observations']=all(s['observation']['text'] in (Path('reports/stage14/states')/(sid+'.md')).read_text() for sid,s in states.items())
    exclusions={'publication_checks.json','artifact_manifest.json'}
    files=sorted(p for root in ['scar_stage14','results/stage14','reports/stage14'] for p in Path(root).rglob('*')
        if p.is_file() and '__pycache__' not in p.parts and p.name not in exclusions and not p.name.endswith('.progress.json'))
    patterns=[rb'sk-[A-Za-z0-9_-]{20,}',rb'gh[pousr]_[A-Za-z0-9]{20,}',rb'-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----']
    secrets=[]
    for p in [Path('/mnt/Space0/AINative/miyao.txt'),Path('/root/.scar-deepseek-key')]:
        if p.exists():secrets += [v.strip().encode() for v in p.read_text().splitlines() if len(v.strip())>12]
    leaks=[];scope=[];links=[]
    for p in files:
        data=p.read_bytes();data=gzip.decompress(data) if p.suffix=='.gz' else data
        if any(re.search(x,data) for x in patterns) or any(s in data for s in secrets):leaks.append(str(p))
        if p.is_symlink() or p.suffix not in {'.py','.md','.json','.xml','.gz'} or p.stat().st_size>=100_000_000:scope.append(str(p))
        if p.suffix=='.md':
            for target in re.findall(r'\]\(([^)]+)\)',p.read_text()):
                if not target.startswith(('https://','http://','#')) and not (p.parent/target.split('#')[0]).exists():links.append([str(p),target])
    ok.update(no_credentials=not leaks,only_own_code_evidence_reports=not scope,report_links_resolve=not links)
    result={'passed':all(ok.values()),'checks':ok,'tests':test,'protected_prior_files':len(prior),
        'new_native_branches':69,'actions_per_replay':255,'native_double_replay_sites':['server','local'],
        'api_calls':0,'new_model_cost_usd':0,'cumulative_model_cost_usd':36.888925758,'new_closed_loop_episodes':0,
        'all_files_count_excluding_self_manifest':len(files),'leaks':leaks,'unexpected_scope':scope,'broken_links':links}
    assert result['passed'],{k:v for k,v in ok.items() if not v}
    return result,files


def main(verify=False):
    result,files=checks()
    if verify:
        for p,h in load(ROOT/'artifact_manifest.json')['files'].items():assert sha(p)==h,p
        assert load(ROOT/'publication_checks.json')==result
    else:
        atomic_json(ROOT/'publication_checks.json',result);files.append(ROOT/'publication_checks.json')
        atomic_json(ROOT/'artifact_manifest.json',{'files':{str(p):sha(p) for p in files},'self_excluded':True,
            'scope':'Stage14 self-written code, generated evidence/checkpoints, Chinese analysis reports only'})
    print({'passed':True,'tests':result['tests']['tests'],'prior_files':2185,'artifacts':len(files)+1,'verify':verify})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');a=p.parse_args();main(a.verify)
