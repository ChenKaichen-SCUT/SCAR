"""Freeze the 16 development/regression families and four internal conditions."""
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
from scar_stage9.controller import METHODS, RepairController

OUT = Path('results/stage9')
BASE = '74a819beb7f44cb77b3875e09038204b48c1c586'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def configure():
    assert not (OUT/'freeze.json').exists(), 'Do not overwrite a frozen experiment'
    OUT.mkdir(parents=True, exist_ok=True)
    prior = {p: sha(p) for p in subprocess.check_output(['git', 'ls-files', '-z']).decode().split('\0') if p}
    atomic_json(OUT/'prior_manifest.json', prior)
    cases = []
    (OUT/'initial_states').mkdir(exist_ok=True)
    for old in json.loads(Path('results/stage8/cases.json').read_text()):
        if old['game'] != 'robot_kingdom':
            continue
        case = copy.deepcopy(old)
        case.update(cohort='development_old10' if old['cohort'] == 'regression' else 'development_stage8_6',
                    stage9_scope='Previously analyzed development/regression task, NOT independent generalization', max_steps=40)
        cases.append(case)
        shutil.copyfile(Path('results/stage8/initial_states')/(case['id']+'.pkl.gz'), OUT/'initial_states'/(case['id']+'.pkl.gz'))
    assert len(cases) == 16
    atomic_json(OUT/'cases.json', cases)
    cfg = json.loads(Path('configs/protocol_stage8.json').read_text())
    cfg.update(protocol_cohort='stage9_v1', algorithms=METHODS, games=['robot_kingdom'],
               max_steps=40, diagnostic_max_steps=40, total_budget_usd=4, episode_budget_usd=.20,
               budget_authorization='User waived historical20USD cap; Guide9 finite64episode batch with new4USD automatic hardstop',
               switches={'F0': 'frozen Stage8 P1', 'F-Old': 'frozen Stage8 P3', 'F1': 'three public-condition repairs', 'F2': 'F1 plus bounded persistent GPAR'},
               predeclared_outcomes={'primary': 'R10/20/40 on all16 development families; old10 and Stage8six strata',
                   'comparisons': ['F1 vs F-Old', 'F2 vs F1', 'F2 vs F0'],
                   'uncertainty': 'paired family bootstrap; small, repeatedly developed sample; no confirmatory significance',
                   'new_confirmation_set': False,
                   'selection': 'all16 existing Robot tasks; no outcome selection or replacement; optional expansion deferred',
                   'abort': 'model-format or method abort retained as failure, no paid rerun',
                   'seed': 'one unchanged physical seed per family; stochastic LLM trajectories not coupled',
                   'same_state_audit': 'all F1/F2 saved decisions replayed with same proposal under opposite active_recovery flag',
                   'physical_effects': 'independent engine only; no evaluator fields are policy inputs',
                   'stop_after_results': 'no policy modification, extra steps, new seeds or output resampling'},
               mechanisms={'base': 'same STM5, PublicFacts48/6000, FIFO and DeepSeek Flash proposal in all methods',
                   'condition_values': ['SUPPORTED', 'REJECT', 'UNKNOWN'],
                   'recovery_actual_actions': RepairController.RECOVERY_ACTIONS,
                   'recovery_depth': RepairController.RECOVERY_DEPTH,
                   'solver_same_condition_visits': 2, 'plan_same_context_rebuilds': 2,
                   'consecutive_no_progress_recovery_actions': 2,
                   'candidate_checks_per_step': RepairController.MAX_CANDIDATES,
                   'forward_success_trials_per_product_without_unfilled_parent': 2,
                   'extra_model_calls': 0})
    atomic_json('configs/protocol_stage9.json', cfg)
    rows = json.loads(Path('results/stage8/episode_metrics.json').read_text())
    ids = {c['id'] for c in cases}
    rows = [r for r in rows if r['case_id'] in ids]
    rate = sum(r['cost_usd'] for r in rows)/sum(r['steps'] for r in rows)
    atomic_json(OUT/'budget_estimate.json', {'based_on': 'all Stage8 Robot16 episodes', 'source_episodes': len(rows),
        'cost_per_action_usd': rate, 'episodes': 64, 'max_actions': 2560,
        'full40_estimate_usd': rate*2560, 'hard_cap_usd': 4,
        'previous_cumulative_usd': 33.493288512, 'price_basis': cfg['pricing_basis'], 'api_calls_before_freeze': 0})
    print(json.dumps({'families': 16, 'episodes': 64, 'estimated_full40_usd': rate*2560, 'hard_cap': 4}))


def integration(root):
    from scar_stage9.run import episode
    from scar_stage9.agent import make_agent
    from scar_sequence.prepare import NoAPIProvider
    from scar.environment import restore, AGENT_ID
    root = Path(root); root.mkdir(parents=True, exist_ok=True)
    case = json.loads((OUT/'cases.json').read_text())[0]
    raw = gzip.decompress((OUT/'initial_states'/(case['id']+'.pkl.gz')).read_bytes())
    initial = root/'initial.pkl'; initial.write_bytes(raw)
    cfg = json.loads(Path('configs/protocol_stage9.json').read_text())
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
    for name in ['offline_checks', 'integration_checks']:
        assert json.loads((OUT/(name+'.json')).read_text())['passed'], name
    prior = json.loads((OUT/'prior_manifest.json').read_text())
    assert all(sha(p) == h for p, h in prior.items())
    cases = json.loads((OUT/'cases.json').read_text())
    paths = [str(p) for base in ['scar', 'scar_v2', 'scar_v3', 'scar_sequence', 'scar_unknown17', 'scar_unknown17_stage7', 'scar_stage8'] for p in Path(base).rglob('*.py')]
    paths += ['scar_stage9/'+n+'.py' for n in ['__init__', 'controller', 'agent', 'run', 'prepare', 'offline']]
    paths += ['configs/protocol_stage9.json', 'tests/test_stage9.py']
    data = [str(p) for p in (OUT/'initial_states').glob('*.gz')] + [str(OUT/'cases.json'), str(OUT/'evaluation_protocol.json')]
    f = {'base_commit': BASE, 'time_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'code_hashes': {p: sha(p) for p in paths}, 'data_hashes': {p: sha(p) for p in data},
         'prior_file_hashes': prior, 'dataset_digest': digest(cases), 'families': 16, 'episodes': 64,
         'api_calls_before_freeze': 0, 'only_game': 'robot_kingdom', 'independent_generalization': False}
    root = Path(runtime); (root/'initials').mkdir(parents=True, exist_ok=True)
    for c in cases:
        raw = gzip.decompress((OUT/'initial_states'/(c['id']+'.pkl.gz')).read_bytes())
        assert hashlib.sha256(raw).hexdigest() == c['snapshot_sha256']
        (root/'initials'/(c['id']+'.pkl')).write_bytes(raw)
    atomic_json(OUT/'freeze.json', f)
    print('Stage9 policy, data and budget frozen; zero API calls')


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('action', choices=['configure', 'integration', 'freeze']); p.add_argument('--runtime')
    a = p.parse_args()
    if a.action == 'configure': configure()
    elif a.action == 'integration': integration(a.runtime)
    else: freeze(a.runtime)
