import copy
import json
from scar_stage9.controller import RepairController, restore_controller, SUPPORTED, REJECT, UNKNOWN


def obs(feedback='', location='room', hands='no objects', equipment='1 bag', ground='no objects', step=0):
    return {'step': step, 'text': f'Current Location: Test, {location}\n\n{feedback}\n\nI am holding {hands}.\nI have equipped {equipment}.\nI see {ground} near me.\nI see no one nearby.\nNeighboring areas: hall.\n'}


def controller(active=False):
    c = RepairController(active)
    c.set_goal('craft 1 final', 'Obtain at least 2 final')
    c.table.observe(obs())
    c.table.inventory = 'bag'
    c.table.containers = {'bag': {'counts': {}, 'load': 0, 'capacity': 20, 'location': 'room', 'step': 0}}
    return c


def test_unknown_capacity_is_not_rejection():
    c = controller(); c.table.observe(obs(hands='1 raw')); c.table.containers['bag']['load'] = None
    assert c.assess('store 1 raw inventory')['status'] == UNKNOWN
    assert c.admissible('store 1 raw inventory')


def test_unknown_counts_are_not_absence():
    c = controller(); c.table.containers['bag']['counts'] = None
    c.table.recipes['part'] = {'ingredients': ['raw'], 'stations': []}
    assert c.assess('craft 1 part')['status'] == UNKNOWN
    assert c.ownership('raw')['exact'] is False


def test_known_full_hands_and_repair():
    c = controller(); c.table.observe(obs(hands='1 final, 1 cord', ground='1 cord'))
    assert c.assess('pick up cord')['status'] == REJECT
    assert c.collection('cord', 2) == 'store 2 cord inventory'
    assert 'store 2 cord inventory' in c.repairs('pick up cord')


def test_goal_batch_not_replaced_by_partial_pickup():
    c = controller(); o = obs(ground='2 final')
    assert c.choose(o, 'store 2 final inventory') == 'store 2 final inventory'


def test_history_not_current_presence():
    c = controller(); c.table.places['hall'] = {'objects': {'raw': 3}, 'step': 1}
    assert c.assess('pick up raw')['status'] == REJECT
    assert c.acquire_options('raw', 1) == ['enter hall']


def test_lower_bound_not_upper_bound():
    c = controller(); c.table.observe(obs(hands='1 part, 1 raw', ground='1 bench'))
    c.table.recipes['part'] = {'ingredients': ['raw'], 'stations': ['bench']}
    assert c.public_demand('part') == 1
    assert c.protect_craft('craft 1 part', 'craft 1 part') == 'craft 1 part'
    assert c.assess('craft 1 part')['status'] != REJECT


def test_goal_consumption_rejected():
    c = controller(); c.table.observe(obs(hands='1 final'))
    c.table.recipes['detour'] = {'ingredients': ['final']}
    assert c.assess('craft 1 detour')['status'] == REJECT


def test_ambiguous_failure_does_not_increase_all_quotas():
    c = controller(); o = obs(hands='1 raw')
    c.table.recipes['part'] = {'ingredients': ['raw']}
    c.observe(o, 'craft 1 part', obs('Cannot craft a single part.', hands='1 raw', step=1))
    assert c.quotas == {}
    assert c.assess('craft 1 part')['status'] == REJECT


def test_changed_station_releases_failure():
    c = controller(); o = obs(hands='1 raw')
    c.table.recipes['part'] = {'ingredients': ['raw'], 'stations': ['bench']}
    c.observe(o, 'craft 1 part', obs('Cannot craft part. Missing necessary bench in the current area.', hands='1 raw', step=1))
    c.table.observe(obs(hands='1 raw', location='hall', ground='1 bench', step=2))
    assert c.assess('craft 1 part')['status'] != REJECT


def test_time_does_not_release_failure():
    c = controller(); o = obs(hands='1 raw')
    c.table.recipes['part'] = {'ingredients': ['raw']}
    c.observe(o, 'craft 1 part', obs('Cannot craft a single part.', hands='1 raw', step=1))
    c.table.observe(obs(hands='1 raw', step=99))
    assert c.assess('craft 1 part')['status'] == REJECT


def test_no_hidden_recipe_inference():
    c = controller(True); o = obs()
    c.observe(o, 'craft 1 unknown', obs('Cannot craft a single unknown.', step=1))
    assert c.table.recipes.get('unknown', {}).get('ingredients', []) == []
    assert c.recovery['blocked_action'] == 'craft 1 unknown'
    assert c.target == 'craft 1 final'


def test_checkpoint_preserves_recovery_identity_and_goal():
    c = controller(True); o = obs(hands='2 raw', ground='1 cord')
    c.observe(o, 'pick up cord', obs('Cannot pick up cord. No space in hand.', hands='2 raw', ground='1 cord', step=1))
    clone = restore_controller(json.loads(json.dumps(c.to_dict())))
    assert clone.to_dict() == c.to_dict()
    assert clone.recovery is clone.recovery_records[-1]
    assert clone.choose(o, 'wait') == c.choose(o, 'wait')


def test_recovery_budget_and_solver_cycles_bounded():
    c = controller(True); a = 'pick up absent'; assessment = c.assess(a)
    c.start_recovery(a, assessment, 'unit')
    c.recovery['remaining_actions'] = 0
    assert c.plan_action() is None and c.recovery is None
    for _ in range(10):
        c.start_recovery(a, assessment, 'unit'); c.cancel_recovery('unit_cancel')
    assert len(c.recovery_records) == c.MAX_PLAN_REBUILDS


def test_f1_has_no_persistent_plan():
    c = controller(); o = obs()
    c.observe(o, 'craft 1 unknown', obs('Cannot craft a single unknown.', step=1))
    assert c.recovery is None and c.recovery_records == []


def test_numeric_requirements_do_not_inherit_ambiguous_quota():
    c = controller(); c.quotas = {'final': 4}
    c.table.recipes['final'] = {'ingredients': ['cloth', 'cord']}
    c.public_quantity_rules['final'] = {'quantities': {'cloth': 1, 'cord': 2}}
    assert c.requirements('final') == {'cloth': 1, 'cord': 2}


def test_speculation_bounded_without_permanent_material_ban():
    c = controller(); c.table.observe(obs(hands='1 part, 1 raw'))
    c.table.recipes['part'] = {'ingredients': ['raw']}; c.actual_trials['part'] = 2
    assert c.assess('craft 1 part')['status'] == REJECT
    c.table.recipes['next'] = {'ingredients': ['part']}
    c.public_quantity_rules['next'] = {'quantities': {'part': 2}}
    assert c.assess('craft 1 part')['status'] != REJECT
