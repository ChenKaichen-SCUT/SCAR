"""Small public-state/unit checks. No environment steps or network calls."""
import ast
import copy
import json
from pathlib import Path
import pytest
from scar.io import digest
from scar_stage10.controller import ResourceController
from scar_stage14.knowledge import Knowledge
from scar_stage14.test_knowledge import native, names, quantities
from scar_stage16.config import BaselineConfig, VARIANTS
from scar_stage16.controller import make_controller, dump_controller, restore_controller
from scar_stage16.knowledge import PublicTable, PublicFacts16
from scar_stage16.migration import migrate_state
from scar_stage16.state import PublicRuleState
from scar_stage16.replay import load_fixtures, prepared_agent


def obs(feedback='', location='room', hands='no objects', equipment='1 bag', ground='no objects', step=0):
    return {'step': step, 'text': f'Current Location: Test, {location}\n\n{feedback}\n\nI am holding {hands}.\nI have equipped {equipment}.\nI see {ground} near me.\nI see no one nearby.\nNeighboring areas: hall.\n'}


def controller(variant='S1_P1_P3'):
    c = make_controller(variant)
    c.set_goal('craft 1 final', 'Obtain at least 2 final')
    c.table.observe(obs(hands='1 final'))
    c.table.inventory = 'bag'
    c.table.containers = {'bag': {'counts': {}, 'load': 0, 'capacity': 20, 'location': 'room', 'step': 0}}
    return c


def rule(c, text='final (1 ore)', step=1, **kwargs):
    o = obs('I have acquired a new item: ore. It can be used to craft: '+text, step=step, **kwargs)
    c.table.observe(o, 'pick up ore')
    return o


GOLD = json.loads(Path('results/stage14/parser_gold.json').read_text())['rows']

@pytest.mark.parametrize('row', GOLD, ids=lambda row: row['id'])
def test_native_parser_gold(row):
    t = PublicTable().observe(row['observation'], row['action'])
    gold = row['expected']
    assert {n: set(r['ingredients']) for n, r in t.recipes.items() if r['ingredients']} == {n: set(v) for n, v in gold['recipes'].items()}
    assert {n: r['quantities'] for n, r in t.recipes.items() if r['quantities']} == gold['quantities']
    assert {n: r['stations'] for n, r in t.recipes.items() if r.get('stations')} == gold['stations']


def test_unknown_quantities_decimal_first_times_and_dedup():
    t = PublicTable().observe(names(), 'inspect ore')
    assert t.recipes['bar']['quantities'] is None
    t.observe(quantities(), 'pick up ore')
    saved = copy.deepcopy(t.knowledge.to_dict())
    t.observe(quantities(), 'pick up ore')
    assert t.knowledge.to_dict() == saved
    t.observe(names(3), 'inspect ore')
    c = controller(); c.table = t
    r = PublicRuleState(c).get_recipe('bar')
    assert r['quantities'] == {'status': 'KNOWN', 'value': {'ore': .5, 'fuel': 2}}
    assert (r['first_relation_step'], r['first_quantity_step']) == (1, 2)
    assert r['stations']['status'] == 'UNKNOWN' and not r['complete']
    assert len(PublicRuleState(c).get_rule_evidence('bar')['events']) == 3


def test_conflict_not_actionable_or_silently_resolved():
    c = controller(); c.table.observe(names(), 'inspect ore')
    c.table.observe(native('I inspected ore: Rock.\nIt can be used to craft: bar (made of ore, wood).', 2), 'inspect ore')
    v = PublicRuleState(c)
    assert v.get_recipe('bar')['status'] == 'CONFLICTED'
    assert v.get_known_dependencies('bar')['dependencies'] == []
    assert 'bar' not in c.table.recipes
    assert len(v.get_rule_evidence('bar')['events']) == 2
    c.table.observe(names(3), 'inspect ore')
    assert PublicRuleState(c).get_recipe('bar')['status'] == 'CONFLICTED'


def test_future_disclosure_rejected_without_mutation_and_model_untrusted():
    k = Knowledge(); k.observe(names(), 'inspect ore'); before = k.to_dict()
    with pytest.raises(ValueError):
        k.observe(quantities(9), 'pick up ore', cutoff=8)
    assert k.to_dict() == before
    k.observe(quantities(), 'pick up ore', source_kind='model_response')
    assert k.to_dict() == before


def test_station_subset_never_exhaustive_rule():
    c = controller(); rule(c)
    c.table.observe(obs('Cannot craft final. Missing necessary bench in the current area.', step=2), 'craft 1 final')
    r = PublicRuleState(c).get_recipe('final')
    assert r['stations'] == {'status': 'KNOWN', 'value': ['bench']}
    assert r['station_completeness']['status'] == 'UNKNOWN' and not r['complete']
    assert PublicRuleState(c).get_execution_status('final')['s1_assessment']['status'] == 'REJECT'


def test_summary_matches_quantity_source_not_consumption_average():
    f = PublicFacts16(); f.observe(names(), 'pick up ore', quantities())
    text, summary = f.render(quantities())
    recipe = next(r for r in summary['records'] if r['kind'] == 'recipe')
    assert recipe['value']['quantities'] == {'ore': .5, 'fuel': 2}
    assert 'batch consumption UNKNOWN' in text


@pytest.mark.parametrize('variant', VARIANTS)
def test_material_retry_changes_only_on_relevant_feedback(variant):
    c = controller(variant); rule(c, 'part (1 ore)', hands='1 ore')
    before = obs(hands='1 ore')
    c.observe(before, 'craft 2 part', obs('Cannot craft a single part.', hands='1 ore', step=1))
    c.table.observe(obs(hands='1 ore', location='hall', step=90))
    assert c.assess('craft 2 part')['status'] == 'REJECT'
    c.table.observe(obs(hands='2 ore', location='hall', step=91))
    assert c.assess('craft 2 part')['status'] != 'REJECT'


@pytest.mark.parametrize('variant', VARIANTS)
def test_station_change_releases_retry(variant):
    c = controller(variant); rule(c, 'part (1 ore)', hands='1 ore')
    c.observe(obs(hands='1 ore'), 'craft 2 part', obs('Cannot craft part. Missing necessary bench in the current area.', hands='1 ore', step=1))
    assert not c.retry_allowed('craft 2 part')
    c.table.observe(obs(hands='1 ore', ground='1 bench', location='hall', step=2))
    assert c.retry_allowed('craft 2 part')


def test_necessary_base_action_preserved_and_repeated_invalid_blocked():
    c = controller('S1_P1')
    assert c.choose(obs(ground='2 final'), 'store 2 final inventory') == 'store 2 final inventory'
    c = controller(); rule(c, 'part (1 ore)')
    assert c.assess('craft 2 part')['status'] == 'REJECT'
    c.table.observe(obs(hands='1 ore'))
    assert c.assess('craft 2 part')['status'] == 'UNKNOWN'  # station not disclosed
    action = 'inspect ore'
    c.actual_visits[digest([action, c.context(action)])] = 2
    assert not c.admissible(action, True)


@pytest.mark.parametrize('variant', VARIANTS)
def test_original_batch_rules_and_observed_sample(variant):
    c = controller(variant)
    c.table.observe(obs(hands='2 ore'))
    c.quantity_facts.table.observe(obs(hands='2 ore'))
    c.quantity_facts.table.inventory = 'bag'
    c.quantity_facts.table.containers = copy.deepcopy(c.table.containers)
    c.queue_needs['part'] = 1
    assert c._batch_action('craft 1 part') == 'craft 2 part'
    c.queue_needs['part'] = 3
    assert c._batch_action('craft 1 part') == 'craft 3 part'
    c.quantity_facts.effects = [{'target': 'part', 'before_counts': {'ore': 2, 'bag': 1},
        'actual': 3, 'requested': 4, 'consumed': {'ore': 1}, 'source_step': 1}]
    assert c._batch_action('craft 1 part') == 'craft 4 part'
    assert c.mechanism_decision['batch']['rule'] == 'exact_public_context_sample'
    assert type(c)._batch_action is ResourceController._batch_action


def test_ground_production_not_completion_and_direct_finish():
    c = controller(); c.table.observe(obs(hands='1 final', ground='1 final'))
    v = PublicRuleState(c)
    assert not v.get_goal_status()['complete']
    assert v.get_goal_status()['direct_acquisition_actions'] == ['pick up final']
    assert c.direct_finish('enter hall')[0] == 'pick up final'
    assert c.choose(obs(ground='2 final'), 'store 2 final inventory') == 'pick up final'
    c.table.observe(obs(hands='2 final'))
    assert PublicRuleState(c).get_goal_status()['complete']
    assert c.direct_finish('wait')[0] is None


def test_final_craft_then_collect_respects_original_action_reserve():
    c = controller(); rule(c, hands='1 ore, 1 final')
    assert c.finish('wait')[0] == 'craft 1 final'
    c.step16 = 39
    assert c.finish('wait')[0] is None
    c.step16 = 0; c.risk16 = True
    assert c.finish('wait')[1]['reason'] == 'public_health_or_combat_risk'


def test_chain_net_historical_bulk_transfer():
    f = next(f for f in load_fixtures() if f['id'] == 'P3-chain_net-36')
    c = migrate_state(f['stage7_state_before'], f['variant'])
    assert c.choose(f['observation'], f['proposed_action']) == 'store 2 iron_bar inventory'
    assert c.audit16['checks'][0]['conditions']['reason'] == 'single_local_final_dependency'


def test_p3_off_never_invokes_finish(monkeypatch):
    c = controller('S1_P1')
    def forbidden(*args): raise AssertionError('P3 ran in P1 config')
    monkeypatch.setattr(c, 'finish', forbidden)
    c.choose(obs(ground='1 final'), 'enter hall')
    assert c.audit16['modules'] == [] and c.audit16['selected_module'] is None


def test_p1_off_uses_legacy_parser_and_summary():
    from scar_unknown17.facts import PublicFacts
    c = controller('S1'); c.table.observe(quantities(), 'pick up ore')
    assert type(c) is ResourceController and not hasattr(c.table, 'knowledge')
    assert not c.table.recipes.get('bar', {}).get('quantities')
    f = PublicFacts(); f.observe(names(), 'pick up ore', quantities())
    assert 'UNKNOWN unless an observed sample below' in f.render(quantities())[0]
    assert PublicRuleState(c).get_recipe('bar')['source_mode'] == 'S1_legacy_record'


@pytest.mark.parametrize('variant', ['P2', 'P4', 'P5', 'P6', 'S1_P3', 'S2', 'S3'])
def test_experimental_config_not_exposed(variant):
    with pytest.raises(ValueError): BaselineConfig(variant)


def test_mismatched_history_and_corrupt_schema_rejected():
    f = next(f for f in load_fixtures() if f['id'] == 'P3-chain_net-36')
    with pytest.raises(ValueError): migrate_state(f['stage7_state_before'], 'S1_P1')
    with pytest.raises(ValueError): migrate_state(f['stage7_state_before'], 'S1')
    c = migrate_state(f['stage7_state_before'], f['variant'])
    with pytest.raises(ValueError): restore_controller(dump_controller(c), 'S1')
    data = dump_controller(c); data['schema_version'] = 99
    with pytest.raises(ValueError): restore_controller(data)


def test_all_queries_are_detached_and_snapshot_time_does_not_advance():
    from scar_stage16.replay import query_readonly
    c = controller(); rule(c, 'final (1 ore), part (1 final)', hands='1 ore')
    view = PublicRuleState(c); first = view.get_recipe('final')
    before = copy.deepcopy(c.to_dict()); query_readonly(c)
    assert c.to_dict() == before
    first['quantities']['value']['ore'] = 999
    assert view.get_recipe('final')['quantities']['value']['ore'] == 1
    rule(c, 'unseen (1 ore)', step=99)
    assert view.get_recipe('unseen')['status'] == 'UNKNOWN'
    assert PublicRuleState(c).get_recipe('unseen')['status'] == 'KNOWN'


def test_unknown_material_counts_and_container_staleness():
    c = controller(); c.table.containers['bag']['counts'] = None
    rule(c, hands='1 final')
    status = PublicRuleState(c).get_execution_status('final')
    assert status['nominal_material_conditions'][0]['status'] == 'UNKNOWN'
    available = PublicRuleState(c).get_available_materials()
    assert available['accessible_containers'][0]['current_contents_certainty'] == 'UNKNOWN'
    assert available['accessible_containers'][0]['last_observed_counts']['status'] == 'UNKNOWN'


def test_missing_graph_is_public_only_bounded_and_unranked_objects():
    c = controller(); rule(c, 'final (1 part), part (1 final)', ground='1 zzz, 1 aaa')
    c.table.inspected = ['zzz']
    v = PublicRuleState(c)
    assert {g['product'] for g in v.get_missing_knowledge()['gaps']} == {'final', 'part'}
    assert v.get_recipe('secret')['status'] == 'UNKNOWN'
    assert all(g['missing_conditions'] == ['stations', 'station_completeness', 'batch_consumption'] for g in v.get_missing_knowledge()['gaps'])
    objects = v.get_uninspected_objects()
    assert 'zzz' not in [x['object'] for x in objects] and 'aaa' in [x['object'] for x in objects]
    assert all('score' not in x and 'relevance' not in x for x in objects)


@pytest.mark.parametrize('variant', VARIANTS)
def test_agent_json_checkpoint_next_action_prompt_and_feedback(tmp_path, variant):
    f = next(f for f in load_fixtures() if f['variant'] == variant and f['source_row'] > 0)
    agent, p = prepared_agent(f)
    agent.save_memory(tmp_path)
    clone, q = prepared_agent(f); clone.load_memory(tmp_path)
    assert clone._act(f['observation'])[0] == agent._act(f['observation'])[0] == f['executed_action']
    assert q.messages == p.messages == f['messages']
    for a in (agent, clone): a.observe_transition(f['observation'], f['executed_action'], f['next_observation'])
    assert dump_controller(clone.controller) == dump_controller(agent.controller)
    assert clone.facts.to_dict() == agent.facts.to_dict()
    assert clone.short_term_memory == agent.short_term_memory


def test_production_has_no_stage15_dispatch_or_task_catalogue_import():
    for name in ('agent', 'controller', 'knowledge', 'state', 'config'):
        tree = ast.parse(Path('scar_stage16', name+'.py').read_text())
        modules = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        assert not any(m and (m.startswith('scar_stage15') or 'witness' in m or 'cases' in m) for m in modules)


@pytest.mark.parametrize('key,value', [('opportunistic', True), ('storage', True), ('batch', 'none')])
def test_checkpoint_cannot_enable_unfrozen_strategy(key, value):
    state = dump_controller(controller()); state['state'][key] = value
    with pytest.raises(ValueError): restore_controller(state)


def test_public_container_objects_are_included_without_ranking():
    c = controller(); c.table.containers['bag']['counts'] = {'uninspected_material': 2}
    items = PublicRuleState(c).get_uninspected_objects()
    item = next(x for x in items if x['object'] == 'uninspected_material')
    assert item['observations'][0]['container'] == 'bag'


@pytest.mark.parametrize('variant', VARIANTS)
def test_model_stm_config_matches_original_factory(variant):
    from scar_stage16 import config
    f = next(f for f in load_fixtures() if f['variant'] == variant)
    agent, _ = prepared_agent(f); old, _ = prepared_agent(f, old=True)
    for key in ('llm_name', 'llm_provider', 'embed_name', 'max_new_tokens', 'temperature', 'torch_seed', 'short_term_memory_size'):
        assert getattr(agent.cfg, key) == getattr(old.cfg, key)
    assert agent.cfg.llm_name == config.MODEL
    assert agent.cfg.system_prompt == old.cfg.system_prompt
    assert agent.cfg.action_prompt == old.cfg.action_prompt


@pytest.mark.parametrize('variant', VARIANTS)
def test_direct_entry_initializes_only_saved_public_prefix(variant):
    import gzip
    from scar_stage16.agent import make_agent
    from scar_stage16.replay import RecordedProvider, expected_state, reference
    f = next(f for f in load_fixtures() if f['variant'] == variant and f['source_row'] == 0)
    with gzip.open(f['source_file'], 'rt') as stream:
        episode = next(e for e in map(json.loads, stream) if e['task_id'] == f['task_id'])
    provider = RecordedProvider(f['response'])
    agent = make_agent(provider, game=f['game'], config=BaselineConfig(variant, f['seed']))
    agent.initialize_episode(episode['summary']['history'], f['target_action'], f['public_goal'])
    assert dump_controller(agent.controller) == expected_state(reference(f['stage7_state_before'], variant), variant)
    assert agent._act(f['observation'])[0] == f['executed_action']
    assert provider.messages == f['messages']
    with pytest.raises(ValueError): agent.initialize_episode([], f['target_action'], f['public_goal'])
