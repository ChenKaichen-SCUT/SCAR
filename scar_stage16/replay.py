"""Bounded offline checkpoint regression. Never constructs a game environment.

Each checkpoint is restored independently. Saved feedback is ingested exactly
once, after matching the saved action; there are no complete episode rollouts.
Stage15 imports below belong solely to this historical reference harness.
"""
import argparse
import contextlib
import copy
import gzip
import hashlib
import io
import json
from pathlib import Path
import socket
from unittest.mock import patch
from .controller import dump_controller, restore_controller
from .migration import migrate_state, migrate_facts
from .state import PublicRuleState

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT/'results/stage16/checkpoints.jsonl.gz'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def stable_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':')).encode()).hexdigest()


def load_fixtures():
    with gzip.open(FIXTURES, 'rt') as stream:
        return [json.loads(line) for line in stream]


def reference(data, variant):
    if variant == 'S1':
        from scar_stage10.controller import ResourceController
        return ResourceController.from_dict(copy.deepcopy(data))
    from scar_stage15.controller import Controller15
    return Controller15.from_dict(data)


def expected_state(old, variant):
    return dump_controller(migrate_state(old.to_dict(), variant))


def check_equal(left, right, label):
    if left != right:
        if isinstance(left, dict) and isinstance(right, dict):
            keys = [k for k in left.keys() | right.keys() if left.get(k) != right.get(k)]
            raise AssertionError(f'{label}: different keys {keys}')
        raise AssertionError(f'{label}: {str(left)[:160]} != {str(right)[:160]}')


def verify_fixture_sources(fixtures):
    for source in dict.fromkeys(f['source_file'] for f in fixtures):
        selected = [f for f in fixtures if f['source_file'] == source]
        assert all(sha(ROOT/source) == f['source_sha256'] for f in selected)
        with gzip.open(ROOT/source, 'rt') as stream:
            episodes = {e['task_id']: e for e in map(json.loads, stream)}
        for f in selected:
            row = episodes[f['task_id']]['rows'][f['source_row']]
            for key in ('observation', 'next_observation', 'proposed_action', 'executed_action',
                        'response', 'stage7_state_before', 'structured', 'fact_summary'):
                check_equal(f[key], row[key], f['id']+':source:'+key)
        method = selected[0]['source_method']
        with gzip.open(ROOT/f'results/stage15/requests_{method}.jsonl.gz', 'rt') as stream:
            requests = list(map(json.loads, stream))
        for f in selected:
            matching = [r['request'] for r in requests if r['task_id'] == f['task_id'] and
                r['request'].get('raw_response', {}).get('choices', [{}])[0].get('message', {}).get('content') == f['response']]
            assert len(matching) == 1
            check_equal(f['messages'], matching[0]['messages'], f['id']+':request')


def query_readonly(controller):
    before = dump_controller(controller)
    view = PublicRuleState(controller)
    goal = controller.target.split()[-1]
    outputs = [view.get_recipe(goal), view.get_known_dependencies(goal), view.get_missing_knowledge(),
               view.get_available_materials(), view.get_rule_evidence(goal), view.get_execution_status(goal),
               view.get_goal_status(), view.get_uninspected_objects()]
    snapshot = stable_hash(outputs)
    for out in outputs:
        out.clear()
    check_equal(before, dump_controller(controller), 'query mutated live state')
    return snapshot


class RecordedProvider:
    """Deterministic saved response, not an API client or model inference."""
    def __init__(self, response):
        self.response, self.messages, self.calls = response, None, 0

    def generate(self, user_prompt, system_prompt):
        self.calls += 1
        self.messages = [{'role': 'system', 'content': system_prompt},
                         {'role': 'user', 'content': user_prompt}]
        return {'response': self.response, 'num_input_tokens': 0, 'num_output_tokens': 0}


def prepared_agent(fixture, *, old=False):
    from .agent import make_agent
    from .config import BaselineConfig, OBJECTIVE_PREFIX
    provider = RecordedProvider(fixture['response'])
    with contextlib.redirect_stdout(io.StringIO()):
        if old:
            from scar_stage15.agent import make_agent as old_factory
            settings = json.loads((ROOT/'configs/protocol_stage15.json').read_text())
            settings['seed'] = fixture['seed']
            agent = old_factory(fixture['source_method'], fixture['game'], provider, settings, '/tmp/scar16_reference_memory')
            agent.controller = reference(fixture['stage7_state_before'], fixture['variant'])
            from scar_stage15.knowledge import PublicFacts15
            from scar_unknown17.facts import PublicFacts
            agent.facts = (PublicFacts if fixture['variant'] == 'S1' else PublicFacts15).from_dict(
                copy.deepcopy(fixture['agent_facts_before']))
        else:
            agent = make_agent(provider, game=fixture['game'], config=BaselineConfig(fixture['variant'], fixture['seed']))
            agent.controller = migrate_state(fixture['stage7_state_before'], fixture['variant'])
            agent.facts = migrate_facts(fixture['agent_facts_before'], fixture['variant'])
    agent.cfg.system_prompt += OBJECTIVE_PREFIX+fixture['public_goal']
    agent.short_term_memory = copy.deepcopy(fixture['stm_before'])
    return agent, provider


def replay_one(f):
    variant, obs, proposal = f['variant'], f['observation'], f['proposed_action']
    old = reference(f['stage7_state_before'], variant)
    new = migrate_state(f['stage7_state_before'], variant)
    for data in (f['stage7_state_before']['table'], f['agent_facts_before']['table']):
        events = data.get('knowledge15', {}).get('events', [])
        assert all(e['observed_step'] <= obs['step'] for e in events), f['id']+':future evidence'
    snapshot = query_readonly(new)
    restored = restore_controller(json.loads(json.dumps(dump_controller(new))), variant)
    old_action = old.choose(obs, proposal)
    new_action = new.choose(obs, proposal)
    check_equal(old_action, f['executed_action'], f['id']+':saved action')
    check_equal(new_action, old_action, f['id']+':new action')
    check_equal(restored.choose(obs, proposal), new_action, f['id']+':roundtrip action')
    check_equal(dump_controller(restored), dump_controller(new), f['id']+':roundtrip state')
    check_equal(old.last_choice, f['structured'], f['id']+':saved decision')
    check_equal(expected_state(old, variant), dump_controller(new), f['id']+':after choose')
    decision_hash = stable_hash(dump_controller(new))
    old.observe(obs, old_action, f['next_observation'])
    new.observe(obs, new_action, f['next_observation'])
    check_equal(expected_state(old, variant), dump_controller(new), f['id']+':after observe')
    agent, provider = prepared_agent(f)
    original, old_provider = prepared_agent(f, old=True)
    check_equal(agent._act(obs)[0], f['executed_action'], f['id']+':agent action')
    check_equal(original._act(obs)[0], f['executed_action'], f['id']+':original agent action')
    check_equal(provider.messages, f['messages'], f['id']+':archived model input')
    check_equal(provider.messages, old_provider.messages, f['id']+':old/new model input')
    check_equal(agent.decision['fact_summary'], f['fact_summary'], f['id']+':saved facts')
    check_equal(agent.short_term_memory, original.short_term_memory, f['id']+':STM')
    check_equal(expected_state(original.controller, variant), dump_controller(agent.controller), f['id']+':agent controller')
    agent.observe_transition(obs, new_action, f['next_observation'])
    original.observe_transition(obs, new_action, f['next_observation'])
    check_equal(expected_state(original.controller, variant), dump_controller(agent.controller), f['id']+':agent feedback')
    check_equal(migrate_facts(original.facts.to_dict(), variant).to_dict(), agent.facts.to_dict(), f['id']+':fact updates')
    assert provider.calls == old_provider.calls == 1
    return {'id': f['id'], 'variant': variant, 'task_id': f['task_id'], 'source_row': f['source_row'],
            'historic_success': f['historical_episode_success'], 'proposal': proposal, 'expected': old_action,
            'actual': new_action, 'action_equal': True, 'decision_and_state_equal': True,
            'feedback_and_knowledge_equal': True, 'prompt_and_stm_equal': True,
            'json_roundtrip_equal': True, 'readonly_snapshot_hash': snapshot,
            'decision_hash': decision_hash, 'after_observe_hash': stable_hash(dump_controller(new)),
            'messages_hash': stable_hash(provider.messages),
            'finish_checks': getattr(new, 'audit16', {}).get('checks', [])}


def replay_archived_branch():
    path = ROOT/'results/stage16/chain_net_branch.json'
    b = json.loads(path.read_text())
    with gzip.open(ROOT/b['source_job'], 'rt') as stream:
        source = next(row for row in map(json.loads, stream) if row['id'] == b['source_id'])
    check_equal(b['state'], source['variants']['P3']['state'], 'branch source checkpoint')
    with gzip.open(ROOT/b['source_trace'], 'rt') as stream:
        source = next(row for row in map(json.loads, stream) if row['state_id'] == b['source_id'])
    check_equal(b['trace'], [{k: row[k] for k in ('before', 'after', 'action', 'proposal', 'decision')}
                             for row in source['branches']['P3']['trace']], 'branch source trace')
    old, new = reference(b['state'], 'S1_P1_P3'), migrate_state(b['state'], 'S1_P1_P3')
    results = []
    for row in b['trace']:
        a, z = old.choose(row['before'], row['proposal']), new.choose(row['before'], row['proposal'])
        check_equal(a, row['action'], 'branch saved action')
        check_equal(z, a, 'branch new action')
        check_equal(old.audit15, row['decision'], 'branch saved decision')
        check_equal(expected_state(old, 'S1_P1_P3'), dump_controller(new), 'branch choice state')
        old.observe(row['before'], a, row['after'])
        new.observe(row['before'], z, row['after'])
        check_equal(expected_state(old, 'S1_P1_P3'), dump_controller(new), 'branch feedback state')
        results.append({'proposal': row['proposal'], 'actual': z, 'state_equal': True,
                        'after_state_hash': stable_hash(dump_controller(new))})
    return results


def deny_network(*args, **kwargs):
    raise AssertionError('Network forbidden during Stage16 offline acceptance')


def run():
    fixtures = load_fixtures()
    assert 20 <= sum(f['variant'] == 'S1_P1_P3' for f in fixtures) <= 40
    verify_fixture_sources(fixtures)
    with patch.object(socket.socket, 'connect', deny_network), patch.object(socket, 'create_connection', deny_network):
        rows = [replay_one(f) for f in fixtures]
        branch = replay_archived_branch()
    return {'passed': True, 'p3_checkpoints': sum(r['variant'] == 'S1_P1_P3' for r in rows),
            'ablation_checkpoints': sum(r['variant'] != 'S1_P1_P3' for r in rows),
            'strictly_recoverable': len(rows), 'unrecoverable_selected': 0,
            'new_api_calls': 0, 'new_native_actions': 0, 'full_episode_replays': 0,
            'network_blocked': True, 'rows': rows, 'archived_chain_net_branch': branch}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/scar_stage16_replay.json'))
    args = parser.parse_args()
    result = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('rows', 'archived_chain_net_branch')}))


if __name__ == '__main__':
    main()
