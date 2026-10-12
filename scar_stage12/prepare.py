"""Select50 public diagnostic states, materialize snapshots, freeze before API."""
import argparse
import contextlib
import copy
import datetime
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import xml.etree.ElementTree as ET

from scar.io import atomic_json, digest
from scar_stage11.controller import adapted
from scar_unknown17.facts import PublicFacts
from scar_stage12.public import candidate_set, controller, public_view, confirmed
from scar_stage12.prompts import messages

OUT = Path('results/stage12/diagnostic')
BASE = '1bdf87212f7877dcd91874038dc1459c162493d8'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sources():
    for stage, methods in [(10, ['S1']), (11, ['E0', 'E1'])]:
        for method in methods:
            path = Path(f'results/stage{stage}/trajectories_{method}.jsonl.gz')
            for ep in map(json.loads, gzip.open(path, 'rt')):
                yield stage, method, ep


def configure():
    assert not (OUT/'freeze.json').exists()
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip() == BASE
    OUT.mkdir(parents=True, exist_ok=True)
    prior = {p: sha(p) for p in subprocess.check_output(['git', 'ls-files', '-z']).decode().split('\0') if p}
    atomic_json('results/stage12/prior_manifest.json', prior)
    cfg = json.loads(Path('configs/protocol_stage11.json').read_text())
    cfg = {k: cfg[k] for k in ['upstream_commit', 'python_hash_seed', 'model', 'base_url', 'thinking', 'temperature',
                                'max_tokens', 'short_term_memory_size', 'pricing_usd_per_million', 'pricing_basis']}
    cfg.update(protocol_cohort='stage12_diagnostic_v1', total_budget_usd=.75, episode_budget_usd=.04,
               states=50, families=10, candidates=16, max_branch_actions=4, primary_judgments=100,
               stability_judgments=20, judgment_methods=['J0','J1','J2','J3'], api_workers=8,
               comparisons=['J2-J0','J2-J1','J3-J0','J3-J1','J3-J2'], bootstrap_samples=10000, bootstrap_seed=314159,
               sampling={'sources':['Stage10 S1','Stage11 E0','Stage11 E1'], 'per_family':5,
                         'slots':['early_unknown','multiple_uninspected','new_relation','fresh_product','late_execution'],
                         'preferred_stage':[10,11,10,11,11], 'target_index':[2,9,16,24,32],
                         'eligibility':'index<=36, at least2 public candidates; public signature deduplication',
                         'ordering':'predicate match then source match then distance from target index then stable digest; no outcome labels',
                         'fallback':'if desired predicate absent use other publicly eligible states; retain full sampling audit'},
               common_executor='4 actions or remaining40; reuse S1 acquire/station/batch; inspect actual produced object; no oracle suffix',
               cropping='two exact rule-action anchors then round-robin8 public types, hash within type; cap16; hash presentation order',
               J2='same public view, STM5, summary, reminder; free primitive action, no menu or forced ranking',
               J3='same common inputs plus full retained menu and structured hypothesis/ranking fields',
               rule_mapping='exact original first action; craft may continue to inspect; no inferred intent for transport; common executor for every descriptor',
               stability='first selected state per family, one extra J2 and J3 response each; primary response never replaced',
               malformed='provider<=3 format/transport attempts; semantic/schema invalid answer recorded, no resampling or best-of selection',
               gate={'net_useful_top1_vs_each_rule_at_least':5, 'positive_net_families_vs_each_rule_at_least':3,
                     'retained_effective_state_coverage_at_least':.85,
                     'raw_entry_useful_count_at_least_best_rule_minus':1,
                     'rejection_state_count_at_most_worst_rule_plus':5,
                     'unrelated_craft_state_count_at_most_worst_rule_plus':2,
                     'environment_key_loss_state_count_at_most_worst_rule_plus':2,
                     'unrelated_key_input_consumption_state_count_at_most_worst_rule_plus':2,
                     'valid_primary_answers_at_least':48,
                     'minimum_informative_families':5, 'raw_entry_success_fraction_at_least':.25,
                     'one_step_net_gain_vs_each_rule_at_least':0,
                     'interpretation':'exploratory screen, not significance; at least one LLM method must satisfy every condition'},
               if_gate_fails='NO-GO; no paid StageB; no B3 failure score', policy_changes_after_freeze=False,
               budget_authorization='Guide12 StageA; existing waived historical cap; separate0.75USD hard guard',
               no_independent_generalization=True)
    atomic_json('configs/protocol_stage12_diagnostic.json', cfg)
    atomic_json(OUT/'evaluation_protocol.json', {
        'primary':'same-state top1 branch yields at least1 NEW native-necessary public recipe relation within4 actions',
        'secondary':['one-step new-key gain','J3 top3 includes useful candidate','environment actions per useful selected branch',
                     'newly disclosed rule count','candidate coverage before/after crop','unconnected raw entry selection',
                     'native rejections','unrelated production','key material consumption','exogenous key material loss',
                     'hypothesis support/mistakes','predeclared duplicate-query stability'],
        'no_opportunity':'separate no-positive-candidate states; zero yield is not automatically a wrong choice',
        'truth_firewall':'recipe_graph and native physical quantities only after actions chosen; never planning input',
        'candidate_counterfactuals':'evaluate retained AND cropped public pool twice; same executor for all methods',
        'paired_uncertainty':'resample10 developed families with replacement10000 times; all states within family stay together',
        'comparison_caveat':'J3 has explicit menu and multi-action intentions; J2 free action; not pure semantic-reasoning ablation; report one-step sensitivity',
        'gate':cfg['gate'], 'screening_not_significance':True})
    print(json.dumps({'configured':True,'states':50,'planned_judgments':120,'cap_usd':.75}))


def select():
    assert not (OUT/'freeze.json').exists()
    cases = {c['id']:c for c in json.loads(Path('results/stage11/cases.json').read_text())}
    base_system = {}
    for record in map(json.loads, gzip.open('results/stage11/requests_E0.jsonl.gz','rt')):
        cid = next(c for c in cases if record['task_id'].startswith(c))
        base_system.setdefault(cid, record['request']['messages'][0]['content'].split('\nPersistent public facts.')[0])
    pool = {c:[] for c in cases}; eligible_audit=[]
    for stage, method, ep in sources():
        case=cases[ep['case_id']]; facts=PublicFacts(); history=[]
        for h in case['history']:
            facts.observe(h['before'],h['action'],h['after'])
            history.append(f"{h['before']['text']}\nAction: {h['action']}\n{h['after']['text']}")
        facts.set_goal(case['target_action'],case['public_goal'])
        history.append('Recovery objective: '+case['public_goal'])
        previous_known=set()
        for row in ep['rows']:
            state=copy.deepcopy(row['stage7_state_before']);obs=row['observation']
            ctrl=controller(state,obs)
            text,summary=facts.render(obs)
            # References use the exact same frozen historical base proposal.
            j0=adapted(state,'E0');a0=j0.choose(obs,row['proposed_action'])
            assert a0==row['executed_action'],(stage,method,row['index'])
            j1=adapted(state,'E2');a1=j1.choose(obs,row['proposed_action'])
            menu,drop=candidate_set(state,obs,[a0,a1]);known={n for n,r in ctrl.table.recipes.items() if r.get('ingredients')}
            unknown=public_view(ctrl)['unresolved_public_nodes']
            unseen=ctrl.visible()-set(ctrl.table.inspected)
            predicates={'early_unknown':bool(unknown), 'multiple_uninspected':len(unseen)>=2,
                        'new_relation':bool(known-previous_known),
                        'fresh_product':bool(unseen & set(ctrl.quantity_facts.produced)),
                        'late_execution':row['index']>=20 and bool(ctrl.table.recipes.get(parse_target(ctrl),{}).get('ingredients'))}
            signature=digest([ctrl.table.state.get('location'),ctrl.table.state.get('hands'),ctrl.table.state.get('ground'),
                              ctrl.table.containers,ctrl.table.recipes,ctrl.table.inspected])
            eligible=row['index']<=36 and len(menu)>=2
            eligible_audit.append({'stage':stage,'task_id':ep['task_id'],'case_id':case['id'],'index':row['index'],
                                   'public_predicates':predicates,'candidate_count':len(menu),'eligible':eligible,'public_signature':signature})
            if eligible:
                pool[case['id']].append({'source_stage':stage,'source_method':method,'source_task':ep['task_id'],
                    'case_id':case['id'],'source_index':row['index'],'public_predicates':predicates,'public_signature':signature,
                    'public_controller':state,'observation':obs,'memory':history[-5:],'facts_text':text,'facts_summary':summary,
                    'public_view':public_view(ctrl),'base_system':base_system[case['id']],
                    'frozen_base_proposal':row['proposed_action'],'rule_actions':{'J0':a0,'J1':a1},
                    'rule_decisions':{'J0':j0.last_choice,'J1':j1.last_choice},'candidates':menu,'cropped_candidates':drop})
            previous_known=known
            facts.observe(obs,row['executed_action'],row['next_observation'])
            history.append(f"{obs['text']}\nProposed: {row['proposed_action']}\nExecuted action: {row['executed_action']}")
    cfg=json.loads(Path('configs/protocol_stage12_diagnostic.json').read_text());s=cfg['sampling'];selected=[]
    for cid,items in sorted(pool.items()):
        used=set()
        for slot,preferred,target in zip(s['slots'],s['preferred_stage'],s['target_index'],strict=True):
            possible=[x for x in items if x['public_signature'] not in used]
            assert possible,cid
            chosen=min(possible,key=lambda x:(not x['public_predicates'][slot],x['source_stage']!=preferred,
                abs(x['source_index']-target),digest([x['source_task'],x['source_index']])))
            chosen=copy.deepcopy(chosen);chosen['sampling_slot']=slot;chosen['slot_predicate_matched']=chosen['public_predicates'][slot]
            chosen['state_id']='d12_'+digest([chosen['source_task'],chosen['source_index']])[:16]
            chosen['remaining_actions']=40-chosen['source_index'];used.add(chosen['public_signature']);selected.append(chosen)
    assert len(selected)==50
    atomic_json(OUT/'sampling_audit.json',{'selection_uses_native_labels':False,'eligible_states':eligible_audit,
        'selected':[{'state_id':s['state_id'],'case_id':s['case_id'],'source':s['source_task'],'index':s['source_index'],
                     'slot':s['sampling_slot'],'predicate_matched':s['slot_predicate_matched']} for s in selected]})
    atomic_json(OUT/'states.json',selected)
    print(json.dumps({'selected':len(selected),'families':len(pool),'slot_matches':sum(s['slot_predicate_matched'] for s in selected),
                      'retained_candidates':sum(len(s['candidates']) for s in selected),'cropped':sum(len(s['cropped_candidates']) for s in selected)}))


def parse_target(ctrl):
    from scar_v3.state import parse_action
    return parse_action(ctrl.target).target


def snapshots(runtime):
    from scar.environment import restore,snapshot,state_digest
    from scar.diagnostics.build import transition
    assert not (OUT/'freeze.json').exists()
    root=Path(runtime);root.mkdir(parents=True,exist_ok=True);(OUT/'states').mkdir(exist_ok=True)
    states=json.loads((OUT/'states.json').read_text());by_source={}
    for s in states:by_source.setdefault(s['source_task'],{})[s['source_index']]=s
    checks=[]
    with (root/'prepare.log').open('w') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        for stage,method,ep in sources():
            if ep['task_id'] not in by_source:continue
            selected=by_source[ep['task_id']]
            raw=gzip.decompress(Path('results/stage11/initial_states',ep['case_id']+'.pkl.gz').read_bytes())
            with tempfile.TemporaryDirectory() as tmp:
                env=restore(raw,tmp)
                for row in ep['rows']:
                    i=row['index']
                    if i in selected:
                        s=selected[i];assert env.obs['agent_adam_davis']==row['observation']
                        data=snapshot(env);path=OUT/'states'/(s['state_id']+'.pkl.gz')
                        with gzip.GzipFile(filename=str(path),mode='wb',mtime=0) as f:f.write(data)
                        s['snapshot_path']=str(path);s['snapshot_sha256']=hashlib.sha256(data).hexdigest();s['physical_hash']=state_digest(env)
                        checks.append({'state_id':s['state_id'],'source_public_observation_matches':True,'physical_hash':s['physical_hash']})
                    if i>=max(selected):break
                    got=transition(env,row['executed_action']);assert got['after']==row['next_observation']
    assert len(checks)==50
    atomic_json(OUT/'states.json',states);atomic_json(OUT/'state_replay_checks.json',{'checks':checks,'passed':True,'api_calls':0})
    print(json.dumps({'snapshots':50,'source_replays_passed':True,'api_calls':0}))


def freeze():
    assert not (OUT/'freeze.json').exists()
    states=json.loads((OUT/'states.json').read_text());assert len(states)==50
    tests=list(ET.parse(OUT/'unit_tests.xml').getroot().iter('testsuite'))
    assert tests and not any(int(s.attrib.get(k,0)) for s in tests for k in ['errors','failures','skipped'])
    assert json.loads((OUT/'state_replay_checks.json').read_text())['passed']
    assert json.loads((OUT/'preflight.json').read_text())['passed']
    prior=json.loads(Path('results/stage12/prior_manifest.json').read_text());assert all(sha(p)==h for p,h in prior.items())
    cfg=json.loads(Path('configs/protocol_stage12_diagnostic.json').read_text())
    requests=[]
    for i,s in enumerate(states):
        for m in ['J2','J3']:
            system,user=messages(s,m)
            requests.append({'state_id':s['state_id'],'method':m,'replicate':0,'system':system,'user':user})
            if i%5==0:requests.append({'state_id':s['state_id'],'method':m,'replicate':1,'system':system,'user':user})
    atomic_json(OUT/'frozen_queries.json',requests)
    price=cfg['pricing_usd_per_million'];chars=sum(len(r['system'])+len(r['user']) for r in requests)
    conservative=sum((len(json.dumps([r['system'],r['user']]).encode())+1024)*price['cache_miss']/1e6+768*price['output']/1e6 for r in requests)
    atomic_json(OUT/'budget_estimate.json',{'queries':len(requests),'input_token_proxy_char_div4':chars/4,
        'no_cache_estimate_usd':chars/4*price['cache_miss']/1e6+len(requests)*400*price['output']/1e6,
        'one_attempt_conservative_reservations_usd':conservative,'hard_cap_usd':cfg['total_budget_usd'],
        'per_query_cap_usd':cfg['episode_budget_usd'],'max_format_attempts':3,'api_calls_before_freeze':0})
    code=[p for p in prior if p.endswith('.py')]+[str(p) for p in Path('scar_stage12').glob('*.py')]
    code+=['configs/protocol_stage12_diagnostic.json','tests/test_stage12.py']
    data=[str(p) for p in (OUT/'states').glob('*.gz')]+[str(OUT/n) for n in ['states.json','frozen_queries.json','evaluation_protocol.json','sampling_audit.json']]
    atomic_json(OUT/'freeze.json',{'base_commit':BASE,'time_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'code_hashes':{p:sha(p) for p in code},'data_hashes':{p:sha(p) for p in data},
        'prior_file_hashes':prior,'states_digest':digest(states),'states':50,'planned_judgments':120,
        'api_calls_before_freeze':0,'unit_tests':sum(int(t.attrib['tests']) for t in tests),'stageB_authorized_only_if_gate_passes':True})
    print(json.dumps({'frozen':True,'queries':len(requests),'one_attempt_reservation_usd':conservative,'hard_cap_usd':.75}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['configure','select','snapshots','freeze']);p.add_argument('--runtime');a=p.parse_args()
    if a.action=='snapshots':snapshots(a.runtime)
    else:globals()[a.action]()
