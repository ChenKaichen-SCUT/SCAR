"""Freeze the original ten development/regression families and four internal conditions."""
import argparse
import contextlib
import copy
import datetime
import gzip
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from scar.io import atomic_json, digest
from scar_stage10.controller import METHODS, ResourceController

OUT = Path('results/stage10')
BASE = 'ce72e27bf2df83fe2794c6a94351098595c0abee'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def configure():
    assert not (OUT/'freeze.json').exists(), 'Do not overwrite a frozen experiment'
    OUT.mkdir(parents=True, exist_ok=True)
    prior = {p: sha(p) for p in subprocess.check_output(['git', 'ls-files', '-z']).decode().split('\0') if p}
    atomic_json(OUT/'prior_manifest.json', prior)
    cases = []
    (OUT/'initial_states').mkdir(exist_ok=True)
    for old in json.loads(Path('results/stage9/cases.json').read_text()):
        if old['cohort'] != 'development_old10': continue
        assert old['game'] == 'robot_kingdom'
        case = copy.deepcopy(old)
        case.update(stage10_scope='Original ten repeatedly analyzed unknown-craft families; development regression only')
        cases.append(case)
        shutil.copyfile(Path('results/stage9/initial_states')/(case['id']+'.pkl.gz'), OUT/'initial_states'/(case['id']+'.pkl.gz'))
    assert len(cases) == 10
    atomic_json(OUT/'cases.json', cases)
    cfg = json.loads(Path('configs/protocol_stage9.json').read_text())
    cfg.update(protocol_cohort='stage10_v1', algorithms=METHODS, games=['robot_kingdom'],
        max_steps=40, diagnostic_max_steps=40, total_budget_usd=3, episode_budget_usd=.20,
        budget_authorization='Guide10 finite40episode batch; historical20USD cap waived; new3USD guard',
        switches={'S0':'frozen F0 / Stage7 C1', 'S1':'F0 plus evidence-based reliability',
                  'S2':'S1 plus opportunistic collection', 'S3':'S2 plus remembered storage and reconfirmation'},
        predeclared_outcomes={'primary':'R10/20/40 on original10 development families',
            'comparisons':['S1-S0','S2-S1','S3-S2','S3-S0'],
            'uncertainty':'10000 paired family bootstrap, seed314159; no generalization or significance claim',
            'selection':'all original10; no Stage8six, no other game, no new dataset',
            'abort':'retain method and format abort as failure; no paid episode rerun',
            'seed':'one unchanged physical seed per family; subsequent LLM responses not coupled',
            'same_state_audit':'all saved new-method decisions toggle the adjacent added mechanism with the same proposal',
            'stop_after_results':'no policy modification, extra actions, seeds or resampling'},
        mechanisms={'backbone':'frozen F0 FIFO, exploration ranking and crafting batches',
            'extra_model_calls':0, 'GPAR':False, 'candidate_limit':32,
            'opportunistic_extra_actions':6,'stash_transfer_actions':4,
            'volume':'UNKNOWN, public capacity checks or bounded native trials; no hidden sizes',
            'storage':'public event records, single pending transfer, reobserve before retrieval',
            'prompt':'same STM5/PublicFacts48/6000 as F0'})
    atomic_json('configs/protocol_stage10.json', cfg)
    ids = {c['id'] for c in cases}
    rows = [r for r in json.loads(Path('results/stage9/episode_metrics.json').read_text()) if r['case_id'] in ids]
    rate = sum(r['cost_usd'] for r in rows)/sum(r['steps'] for r in rows)
    atomic_json(OUT/'budget_estimate.json', {'based_on':'Stage9 originalRobot10, all40 episodes',
        'source_episodes':len(rows),'cost_per_action_usd':rate,'episodes':40,'max_actions':1600,
        'full40_estimate_usd':rate*1600,'hard_cap_usd':3,'previous_cumulative_usd':35.002277412,
        'price_basis':cfg['pricing_basis'],'api_calls_before_freeze':0})
    atomic_json(OUT/'evaluation_protocol.json', {
        'frozen_before_formal':True,'primary':cfg['predeclared_outcomes'],
        'success':'native possess goal, no evaluator suffix; R10/20/40; paired same initial state',
        'resource_effects':'native evaluator separates action consumption from full-step losses; no hidden data to policy',
        'overrides':'save proposal, frozen-backbone candidate, public reason, selected candidate, real effects; local branches twice',
        'storage':'separate recorded, reconfirmed, retrieved, missing, harmful exposure and phantom attempts',
        'knowledge':'native key recipe names vs public history; discovery-to-execution, missing and unconverted rules',
        'residual_causes':['knowledge_discovery','known_knowledge_not_converted_to_plan','material_or_action_execution'],
        'causal_limits':'labels may overlap; counterfactuals are local; stochastic full trajectories are not strict causal tests',
        'historical_evaluation':'Stage7-9 originalRobot10 states only; critical bandage and fiend failures plus capacity fixtures',
        'fee':cfg['pricing_basis'],'policy_changes_after_results':False})
    print(json.dumps({'families':10,'episodes':40,'estimated_full40_usd':rate*1600,'hard_cap':3}))


def integration(root):
    from scar_stage10.run import episode
    from scar_stage10.agent import make_agent
    from scar_sequence.prepare import NoAPIProvider
    from scar.environment import restore, AGENT_ID
    root = Path(root); root.mkdir(parents=True, exist_ok=True)
    case = json.loads((OUT/'cases.json').read_text())[0]
    raw = gzip.decompress((OUT/'initial_states'/(case['id']+'.pkl.gz')).read_bytes())
    initial = root/'initial.pkl'; initial.write_bytes(raw)
    cfg = json.loads(Path('configs/protocol_stage10.json').read_text())
    records, prompts = [], []
    class Capture(NoAPIProvider):
        def generate(self, *args, **kwargs):
            self.last = copy.deepcopy([args, kwargs])
            return super().generate(*args, **kwargs)
    with (root/'integration.log').open('w') as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        for method in METHODS:
            task = dict(case, task_id='smoke-'+method, algorithm=method, diagnostic=True, max_steps=3,
                        stage='smoke', initial_snapshot=str(initial))
            result = episode(task, cfg, root/'integration', None, 1, provider_factory=NoAPIProvider)
            row = {k: result[k] for k in ['algorithm', 'status', 'steps', 'api_calls', 'cost_usd', 'error']}
            with tempfile.TemporaryDirectory() as tmp:
                provider = Capture(); agent = make_agent(method, case['game'], provider, cfg, Path(tmp)/'a')
                for h in case['history']:
                    agent.memorize(f"{h['before']['text']}\nAction: {h['action']}\n{h['after']['text']}")
                    agent.observe_transition(h['before'], h['action'], h['after'])
                agent.set_recovery_objective(case['target_action'], case['public_goal'])
                agent.act(restore(raw, tmp).obs[AGENT_ID]); prompts.append(provider.last)
                agent.save_memory(Path(tmp)/'saved')
                clone = make_agent(method, case['game'], Capture(), cfg, Path(tmp)/'b'); clone.load_memory(Path(tmp)/'saved')
                row['agent_roundtrip'] = agent.controller.to_dict() == clone.controller.to_dict() and agent.facts.to_dict() == clone.facts.to_dict() and agent.short_term_memory == clone.short_term_memory
            records.append(row)
    result = {'records': records, 'same_first_request_all4': all(p == prompts[0] for p in prompts),
              'passed': all(r['status'] == 'completed' and r['api_calls'] == 0 and r['agent_roundtrip'] for r in records) and all(p == prompts[0] for p in prompts)}
    atomic_json(OUT/'integration_checks.json', result); print(json.dumps(result)); assert result['passed']


def freeze(runtime):
    assert not (OUT/'freeze.json').exists()
    for name in ['offline_checks', 'integration_checks', 'storage_checks']:
        assert json.loads((OUT/(name+'.json')).read_text())['passed'], name
    critical = json.loads((OUT/'critical_autonomous.json').read_text())
    assert len(critical) == 24 and all(r['autonomous_goal'] for r in critical if r['method'] != 'S0')
    import xml.etree.ElementTree as ET
    suites = list(ET.parse(OUT/'unit_tests.xml').getroot().iter('testsuite'))
    assert sum(int(s.attrib.get('tests', 0)) for s in suites) == 88
    assert not any(int(s.attrib.get(k, 0)) for s in suites for k in ['failures', 'errors', 'skipped'])
    prior = json.loads((OUT/'prior_manifest.json').read_text())
    assert all(sha(p) == h for p, h in prior.items())
    cases = json.loads((OUT/'cases.json').read_text())
    paths = [str(p) for base in ['scar', 'scar_v2', 'scar_v3', 'scar_sequence', 'scar_unknown17', 'scar_unknown17_stage7', 'scar_stage8', 'scar_stage9'] for p in Path(base).rglob('*.py')]
    paths += ['scar_stage10/'+n+'.py' for n in ['__init__', 'controller', 'agent', 'run', 'prepare', 'offline', 'storage_checks']]
    paths += ['configs/protocol_stage10.json', 'tests/test_stage10.py']
    data = [str(p) for p in (OUT/'initial_states').glob('*.gz')] + [str(OUT/'cases.json'), str(OUT/'evaluation_protocol.json')]
    f = {'base_commit': BASE, 'time_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'code_hashes': {p: sha(p) for p in paths}, 'data_hashes': {p: sha(p) for p in data},
         'prior_file_hashes': prior, 'dataset_digest': digest(cases), 'families': 10, 'episodes': 40,
         'api_calls_before_freeze': 0, 'only_game': 'robot_kingdom', 'independent_generalization': False}
    root = Path(runtime); (root/'initials').mkdir(parents=True, exist_ok=True)
    for c in cases:
        raw = gzip.decompress((OUT/'initial_states'/(c['id']+'.pkl.gz')).read_bytes())
        assert hashlib.sha256(raw).hexdigest() == c['snapshot_sha256']
        (root/'initials'/(c['id']+'.pkl')).write_bytes(raw)
    atomic_json(OUT/'freeze.json', f)
    print('Stage10 policy, data and budget frozen; zero API calls')


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('action', choices=['configure', 'integration', 'freeze']); p.add_argument('--runtime')
    a = p.parse_args()
    if a.action == 'configure': configure()
    elif a.action == 'integration': integration(a.runtime)
    else: freeze(a.runtime)
