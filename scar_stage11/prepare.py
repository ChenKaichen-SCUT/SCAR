"""Prepare, integrate and freeze the original ten-family, five-condition batch."""
import argparse
import contextlib
import copy
import datetime
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET

from scar.io import atomic_json, digest
from scar_stage11.controller import METHODS, PROMPT_REMINDER

OUT = Path('results/stage11')
BASE = 'c1cf74814abf84387723fe5e342b29a1b7042168'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def configure():
    assert not (OUT/'freeze.json').exists()
    OUT.mkdir(parents=True, exist_ok=True)
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip() == BASE
    prior = {p: sha(p) for p in subprocess.check_output(['git', 'ls-files', '-z']).decode().split('\0') if p}
    atomic_json(OUT/'prior_manifest.json', prior)
    cases = json.loads(Path('results/stage10/cases.json').read_text())
    assert len(cases) == 10 and all(c['game'] == 'robot_kingdom' and c['cohort'] == 'development_old10' for c in cases)
    atomic_json(OUT/'cases.json', cases)
    (OUT/'initial_states').mkdir(exist_ok=True)
    for c in cases:
        shutil.copyfile(Path('results/stage10/initial_states')/(c['id']+'.pkl.gz'), OUT/'initial_states'/(c['id']+'.pkl.gz'))
    cfg = json.loads(Path('configs/protocol_stage10.json').read_text())
    cfg.update(protocol_cohort='stage11_v1', algorithms=METHODS, total_budget_usd=4,
        budget_authorization='Guide11 finite50episode batch; prior20USD cap waived; new4USD guard',
        switches={'E0': 'frozen Stage10 S1', 'E1': 'S1 + fixed prompt reminder only',
                  'E2': 'S1 + public goal-related exploration priority', 'E3': 'S1 + timely necessary execution',
                  'E4': 'S1 + both priorities'},
        prompt_reminder_E1=PROMPT_REMINDER,
        predeclared_outcomes={'primary': 'R10/20/40 on original10 development families',
            'comparisons': ['E1-E0', 'E2-E0', 'E3-E0', 'E4-E0', 'E4-E2', 'E4-E3', 'E2-E1', 'E4-E1'],
            'uncertainty': '10000 paired family bootstrap seed314159, descriptive only; LLM sampling not paired',
            'scope': 'only original10 Robot families; no new dataset, games, seeds or steps',
            'abort': 'retain failed, method/format abort and budget termination; no paid episode reruns',
            'prompt': 'E0/E2/E3/E4 same prompt; E1 differs by exactly the frozen reminder',
            'same_state_audit': 'E2/E3 disable new controls to S1; E4 independently disable each and both; same proposal and public state',
            'policy_changes_after_results': False},
        mechanisms={'backbone': 'Stage10 S1; original FIFO and batch functions inherited',
            'extra_model_calls': 0, 'GPAR': False, 'S2_collection': False, 'S3_storage': False,
            'candidate_limit_per_list': 32, 'public_node_limit': 64,
            'speculative_production_trials': 4, 'exploration_actions': 18,
            'prompt': 'STM5/PublicFacts48/6000; same base except E1 fixed reminder',
            'final_base_priority': 'all explicit-priority conditions preserve a publicly supported final-goal base move',
            'unknown_links': 'possible bridge annotations never become dependency edges'})
    atomic_json('configs/protocol_stage11.json', cfg)
    rows = json.loads(Path('results/stage10/episode_metrics.json').read_text())
    rate = sum(r['cost_usd'] for r in rows)/sum(r['steps'] for r in rows)
    atomic_json(OUT/'budget_estimate.json', {'based_on': 'Stage10 all40 episodes, actual cost per action',
        'source_episodes': 40, 'cost_per_action_usd': rate, 'episodes': 50, 'max_actions': 2000,
        'full40_estimate_usd': rate*2000, 'hard_cap_usd': 4, 'episode_cap_usd': .20,
        'previous_cumulative_usd': 35.675010474, 'price_basis': cfg['pricing_basis'], 'api_calls_before_freeze': 0})
    atomic_json(OUT/'evaluation_protocol.json', {'frozen_before_formal': True, 'primary': cfg['predeclared_outcomes'],
        'goal': 'native possession amount, not merely successful crafting',
        'key_discovery': 'public ingredient names intersect independent native dependency recipe names; not exact quantity knowledge',
        'exploration': 'inspect/known forward-trial/associated preparation; goal relevance from public links or explicitly possible bridge',
        'unrelated_exploration': 'two counts: no public confirmed link vs evaluator non-key subject; neither proves action useless',
        'knowledge_gain': 'all new public recipe names and native key names separately; attribute after real action',
        'new_product_inspection': 'first real production per product; inspect within next3 actions and before termination; report censored last3 separately',
        'timely_execution': 'states with publicly confirmed necessary unmet subgoal and native-legal inherited-batch craft or current acquisition; execution now and within next3 when same goal context remains',
        'timely_limits': 'local opportunity, not globally optimal schedule; report public READY/UNKNOWN and native feasibility separately',
        'discovery_to_first_craft': 'first successful craft action index minus first public recipe discovery index; unconverted/censored retained',
        'overrides': 'model proposal, S1 reference, ranked public candidates, selected reason, actual recipe/material/goal gains, harmful native base overrides',
        'repeat': 'same action and same Stage10 public context; no new rule, material or condition progress',
        'health': 'public death events, curse warnings and native resource loss separately',
        'counterfactual': 'both local physical branches replayed twice, no oracle action sent online; no causal inference from unpaired model trajectories',
        'historical_tests': 'original10 Stage10 histories, existing Stage8/10 diagnostic states; no new allocation fixtures',
        'questions': ['Does goal exploration improve discovery/completion?', 'Does timely known execution improve completion?',
                      'Do explicit controls improve over prompt-only?'],
        'decision_rule': 'if prompt-only or S1 matches gains, added explicit value is not established; keep all regressions',
        'post_freeze_policy_changes': False})
    print(json.dumps({'families': 10, 'episodes': 50, 'estimated_usd': rate*2000, 'hard_cap_usd': 4}))


def integration(runtime):
    from scar_stage11.run import episode
    from scar_stage11.agent import make_agent
    from scar_sequence.prepare import NoAPIProvider
    from scar.environment import restore, AGENT_ID
    root = Path(runtime); root.mkdir(parents=True, exist_ok=True)
    case = json.loads((OUT/'cases.json').read_text())[0]
    raw = gzip.decompress((OUT/'initial_states'/(case['id']+'.pkl.gz')).read_bytes())
    initial = root/'initial.pkl'; initial.write_bytes(raw)
    cfg = json.loads(Path('configs/protocol_stage11.json').read_text())
    records, prompts = [], {}
    class Capture(NoAPIProvider):
        def generate(self, *args, **kwargs):
            self.last = copy.deepcopy([args, kwargs]); return super().generate(*args, **kwargs)
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
                agent.act(restore(raw, tmp).obs[AGENT_ID]); prompts[method] = provider.last
                agent.save_memory(Path(tmp)/'saved')
                clone = make_agent(method, case['game'], Capture(), cfg, Path(tmp)/'b'); clone.load_memory(Path(tmp)/'saved')
                row['agent_roundtrip'] = agent.controller.to_dict() == clone.controller.to_dict() and agent.facts.to_dict() == clone.facts.to_dict() and agent.short_term_memory == clone.short_term_memory
            records.append(row)
    plain = json.dumps(prompts['E0']); reminder = json.dumps(prompts['E1'])
    prompt_match = all(prompts[m] == prompts['E0'] for m in ['E2', 'E3', 'E4'])
    prompt_only = reminder.replace('\\n'+PROMPT_REMINDER, '') == plain and reminder != plain
    result = {'records': records, 'same_first_request_E0_E2_E3_E4': prompt_match,
              'E1_exactly_fixed_reminder': prompt_only, 'prompt_reminder': PROMPT_REMINDER,
              'passed': all(r['status'] == 'completed' and r['api_calls'] == 0 and r['agent_roundtrip'] for r in records) and prompt_match and prompt_only}
    atomic_json(OUT/'integration_checks.json', result); print(json.dumps(result)); assert result['passed']


def freeze(runtime):
    assert not (OUT/'freeze.json').exists()
    for name in ['offline_checks', 'integration_checks', 'analysis_smoke_checks']:
        assert json.loads((OUT/(name+'.json')).read_text())['passed'], name
    suites = list(ET.parse(OUT/'unit_tests.xml').getroot().iter('testsuite'))
    test_count = sum(int(s.attrib.get('tests', 0)) for s in suites)
    assert test_count >= 110 and not any(int(s.attrib.get(k, 0)) for s in suites for k in ['failures', 'errors', 'skipped'])
    prior = json.loads((OUT/'prior_manifest.json').read_text()); assert all(sha(p) == h for p, h in prior.items())
    paths = [p for p in prior if p.endswith('.py')]
    paths += ['scar_stage11/'+n+'.py' for n in ['__init__', 'controller', 'agent', 'run', 'prepare', 'offline']]
    paths += ['configs/protocol_stage11.json', 'tests/test_stage11.py']
    data = [str(p) for p in (OUT/'initial_states').glob('*.gz')]+[str(OUT/'cases.json'), str(OUT/'evaluation_protocol.json')]
    cases = json.loads((OUT/'cases.json').read_text())
    f = {'base_commit': BASE, 'time_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'code_hashes': {p: sha(p) for p in paths}, 'data_hashes': {p: sha(p) for p in data},
         'prior_file_hashes': prior, 'dataset_digest': digest(cases), 'families': 10, 'episodes': 50,
         'api_calls_before_freeze': 0, 'only_game': 'robot_kingdom', 'independent_generalization': False,
         'unit_tests': test_count, 'prompt_reminder_sha256': hashlib.sha256(PROMPT_REMINDER.encode()).hexdigest()}
    root = Path(runtime); (root/'initials').mkdir(parents=True, exist_ok=True)
    assert not (root/'runs').exists(), 'Fresh runtime required before freezing'
    for c in cases:
        raw = gzip.decompress((OUT/'initial_states'/(c['id']+'.pkl.gz')).read_bytes())
        assert hashlib.sha256(raw).hexdigest() == c['snapshot_sha256']
        (root/'initials'/(c['id']+'.pkl')).write_bytes(raw)
    atomic_json(OUT/'freeze.json', f)
    print('Stage11 policies, prompts, data and evaluation frozen; zero API calls')


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('action', choices=['configure', 'integration', 'freeze']); p.add_argument('--runtime')
    a = p.parse_args()
    if a.action == 'configure': configure()
    elif a.action == 'integration': integration(a.runtime)
    else: freeze(a.runtime)
