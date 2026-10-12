import ast
import copy
import json
from pathlib import Path

import pytest

from scar_stage10.controller import ResourceController
from scar_stage11.controller import GoalController, METHODS, PROMPT_REMINDER, adapted, make_controller, restore_controller
from tests.test_stage10 import obs


def controller(method='E4'):
    c = make_controller(method); c.set_goal('craft 1 final', 'Obtain at least 2 final')
    c.table.observe(obs(hands='1 final', ground='1 bench, 1 unrelated'))
    c.table.inventory = 'bag'
    c.table.inspected = ['final', 'bag']
    c.table.containers = {'bag': {'counts': {'raw': 4}, 'load': 4, 'capacity': 20, 'location': 'room', 'step': 0}}
    return c


def test_reference_and_prompt_only_are_exact_s1_class():
    assert type(make_controller('E0')) is ResourceController
    assert type(make_controller('E1')) is ResourceController
    assert make_controller('E0').to_dict() == make_controller('E1').to_dict()


def test_s1_batch_fifo_and_only_two_switches():
    assert GoalController.__bases__ == (ResourceController,)
    assert GoalController._batch_action is ResourceController._batch_action
    assert GoalController._fifo is ResourceController._fifo
    for method in METHODS:
        c = make_controller(method)
        assert not c.opportunistic and not c.storage and not hasattr(c, 'recovery')


def test_prompt_is_short_fixed_and_contains_no_case_answers():
    assert len(PROMPT_REMINDER.split()) < 90
    assert not any(n in PROMPT_REMINDER for n in ['wood_strip', 'fiend', 'robot', 'family'])


def test_unknown_bridge_is_not_a_goal_dependency():
    c = controller('E2'); c.table.recipes['bridge'] = {'ingredients': ['raw'], 'stations': ['bench']}
    candidates = c.exploration_candidates({'final'})
    bridge = next(r for r in candidates if r['target'] == 'bridge')
    assert bridge['basis']['unknown_downstream_connection']
    assert c.goal_view['known_dependency_nodes'] == ['final']
    assert 'bridge' not in c.goal_view['edges']['final']


def test_public_new_edge_immediately_updates_fifo():
    c = controller(); c.queue = ['final']
    before = obs(hands='1 final', ground='1 part')
    c.observe(before, 'inspect part', obs('I inspected part. It can be used to craft: final (made of part).', hands='1 final', ground='1 part', step=1))
    assert 'part' in c.goal_view['known_dependency_nodes'] and 'part' in c.queue
    assert c.queue[0] == 'final'


def test_known_complete_parent_does_not_activate_its_inputs():
    c = controller(); c.table.containers['bag']['counts']['part'] = 1
    c.table.recipes.update(final={'ingredients': ['part']}, part={'ingredients': ['raw']})
    view = c.public_goal_view(synchronize=True)
    assert view['nodes']['part']['status'] == 'COMPLETE'
    assert 'raw' not in view['active_nodes'] and 'part' not in c.queue


def test_required_unknown_object_outranks_new_product_and_unrelated():
    c = controller('E2'); c.table.recipes['final'] = {'ingredients': ['missing']}
    c.table.observe(obs(hands='1 final', ground='1 missing, 1 new_part, 1 unrelated'))
    c.produced11['new_part'] = 0
    assert c.exploration_candidates({'final'})[0]['action'] == 'inspect missing'


def test_known_forward_trial_precedes_unrelated_inspection():
    c = controller('E2'); c.table.recipes['bridge'] = {'ingredients': ['raw'], 'stations': ['bench']}
    assert c._explore({'final'}) == 'craft 1 bridge'


def test_new_successful_product_can_be_inspected():
    c = controller('E2'); c.table.recipes['bridge'] = {'ingredients': ['raw'], 'stations': ['bench']}
    before = obs(hands='1 final', ground='1 bench, 1 unrelated')
    c.observe(before, 'craft 2 bridge', obs('I successfully crafted 2 bridge.', hands='1 final', ground='1 bench, 2 bridge, 1 unrelated', step=1))
    assert 'bridge' in c.produced11
    assert c._explore({'final'}) == 'inspect bridge'


def test_speculation_cannot_consume_retained_goal():
    c = controller('E2'); c.table.recipes['downstream'] = {'ingredients': ['final'], 'stations': ['bench']}
    assert not any(r['target'] == 'downstream' for r in c.exploration_candidates({'final'}))


def test_no_repeated_forward_product_if_owned_or_previously_made():
    c = controller('E2'); c.table.recipes['bridge'] = {'ingredients': ['raw'], 'stations': ['bench']}
    c.produced11['bridge'] = 0
    assert not any(r['kind'] == 'known_forward_bridge' for r in c.exploration_candidates({'final'}))


def test_ready_necessary_craft_before_unrelated_exploration():
    c = controller('E3'); c.table.recipes.update(final={'ingredients': ['part'], 'stations': ['bench']}, part={'ingredients': ['raw'], 'stations': ['bench']})
    action = c.choose(obs(hands='1 final', ground='1 bench, 1 unrelated'), 'inspect unrelated')
    assert action == 'craft 2 part'
    assert c.goal_view['nodes']['part']['status'] == 'READY'


def test_missing_station_is_blocked_and_never_called_ready():
    c = controller('E3'); c.table.recipes.update(final={'ingredients': ['part']}, part={'ingredients': ['raw'], 'stations': ['elsewhere']})
    view = c.public_goal_view(synchronize=True)
    assert view['nodes']['part']['status'] == 'BLOCKED'
    assert not any(r['action'] == 'craft 1 part' and r['eligible'] for r in c.execution_candidates(view))


def test_unknown_station_is_bounded_trial_not_false_ready():
    c = controller('E3'); c.table.recipes.update(final={'ingredients': ['part']}, part={'ingredients': ['raw']})
    view = c.public_goal_view(synchronize=True)
    assert view['nodes']['part']['status'] == 'UNKNOWN'
    assert any(r['action'] == 'craft 1 part' and r['eligible'] for r in c.execution_candidates(view))


def test_acquire_existing_product_before_duplicate_craft():
    c = controller('E3'); c.table.recipes.update(final={'ingredients': ['part']}, part={'ingredients': ['raw'], 'stations': ['bench']})
    o = obs(hands='1 final', ground='1 bench, 1 part')
    assert c.choose(o, 'inspect unrelated') == 'store 1 part inventory'


def test_known_sufficient_copy_excluded_from_execution_candidates():
    c = controller('E3'); c.table.containers['bag']['counts']['part'] = 1
    c.table.recipes.update(final={'ingredients': ['part']}, part={'ingredients': ['raw'], 'stations': ['bench']})
    assert not any(r['action'] == 'craft 1 part' for r in c.execution_candidates(c.public_goal_view()))


@pytest.mark.parametrize('method', ['E2', 'E3', 'E4'])
def test_direct_final_base_collection_preserved(method):
    c = controller(method)
    assert c.choose(obs(hands='1 final', ground='1 final'), 'pick up final') == 'pick up final'


def test_unchanged_failed_craft_not_retried_due_to_time():
    c = controller('E3'); c.table.recipes.update(final={'ingredients': ['part']}, part={'ingredients': ['raw'], 'stations': ['bench']})
    before = obs(hands='1 final', ground='1 bench')
    c.observe(before, 'craft 2 part', obs('Cannot craft a single part.', hands='1 final', ground='1 bench', step=1))
    assert not c.allowed11('craft 2 part')
    c.table.observe(obs(hands='1 final', ground='1 bench', step=80))
    assert not c.allowed11('craft 2 part')


@pytest.mark.parametrize('method', METHODS)
def test_public_state_json_roundtrip_has_same_next_action(method):
    c = controller(method); c.table.recipes['bridge'] = {'ingredients': ['raw'], 'stations': ['bench']}
    state = json.loads(json.dumps(c.to_dict())); restored = restore_controller(state)
    assert c.to_dict() == restored.to_dict()
    o = obs(hands='1 final', ground='1 bench, 1 unrelated')
    assert c.choose(o, 'wait') == restored.choose(o, 'wait')


def test_historical_adapter_disables_s2_s3_and_preserves_s1():
    c = controller('E0'); state = c.to_dict()
    assert adapted(state, 'E0').to_dict() == state
    state.update(opportunistic=True, storage=True)
    assert not adapted(state, 'E4').opportunistic and not adapted(state, 'E4').storage


def test_historical_adapter_cannot_reenable_older_stage7_mechanisms():
    state = controller('E0').to_dict()
    state['flags'] = {k: True for k in state['flags']}
    state['quantity_facts']['produced'] = {'historically_made': 2}
    for method in METHODS:
        c = adapted(state, method)
        assert c.flags == make_controller('E0').flags
    assert 'historically_made' in adapted(state, 'E4').produced11


def test_import_boundary_and_no_task_specific_literals():
    source = Path('scar_stage11/controller.py').read_text(); tree = ast.parse(source)
    imports = [n.module or '' for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
    assert not any(any(s in name for s in ['environment', 'evaluate', 'audit', 'diagnostics', 'pathlib']) for name in imports)
    forbidden = ['wood_strip', 'wooden_rod', 'fiend_helm', 'hellfire_bomb', 'hunter_gauntlets', 'brimite', 'family_id', 'recipe_graph']
    assert not any(value in source for value in forbidden)


def test_cyclic_public_recipe_graph_is_bounded():
    c = controller(); c.table.recipes.update(final={'ingredients': ['loop']}, loop={'ingredients': ['final']})
    view = c.public_goal_view(synchronize=True)
    assert len(view['nodes']) == 2 and len(c.queue) == 2


def test_probe_is_not_charged_to_overriding_final_base():
    c = controller('E2'); c.table.recipes['bridge'] = {'ingredients': ['raw'], 'stations': ['bench']}
    action = c.choose(obs(hands='1 final', ground='1 final, 1 bench'), 'pick up final')
    assert action == 'pick up final' and not c.trials.get('final')
