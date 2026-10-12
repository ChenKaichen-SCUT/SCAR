import copy
import json

from scar_stage10.controller import ResourceController, make_controller, restore_controller, REJECT, UNKNOWN
from scar_unknown17_stage7.controller import Stage7Controller, CONFIGS


def obs(feedback='', location='room', hands='no objects', equipment='1 bag', ground='no objects', step=0):
    return {'step': step, 'text': f'Current Location: Test, {location}\n\n{feedback}\n\nI am holding {hands}.\nI have equipped {equipment}.\nI see {ground} near me.\nI see no one nearby.\nNeighboring areas: hall.\n'}


def controller(method='S1'):
    c = make_controller(method); c.set_goal('craft 1 final', 'Obtain at least 2 final')
    c.table.observe(obs())
    c.table.inventory = 'bag'
    c.table.containers = {'bag': {'counts': {}, 'load': 0, 'capacity': 20, 'location': 'room', 'step': 0}}
    return c


def test_s0_is_exact_frozen_class():
    c = make_controller('S0')
    assert type(c) is Stage7Controller and c.flags == CONFIGS['C1']


def test_only_f0_is_backbone():
    assert ResourceController.__bases__ == (Stage7Controller,)
    assert ResourceController._batch_action is Stage7Controller._batch_action
    assert ResourceController._fifo is Stage7Controller._fifo
    assert not hasattr(controller('S3'), 'recovery')


def test_unknown_counts_and_volume_never_imply_rejection():
    c = controller(); c.table.containers['bag'].update(counts=None, load=None)
    c.table.recipes['part'] = {'ingredients': ['raw']}
    c.table.observe(obs(ground='2 raw'))
    assert c.assess('craft 2 part')['status'] == UNKNOWN
    assert c.assess('store 2 raw inventory')['status'] == UNKNOWN


def test_known_hand_block_has_batch_transfer_alternative():
    c = controller(); c.table.observe(obs(hands='1 final, 1 raw', ground='1 raw'))
    assert c.assess('pick up raw')['status'] == REJECT
    assert 'store 2 raw inventory' in c.alternatives('pick up raw')


def test_crafting_batch_remains_f0_two_not_f1_one():
    c = controller(); c.table.recipes['final'] = {'ingredients': ['part']}
    c.queue_needs['part'] = 1
    assert c._batch_action('craft 1 part') == 'craft 2 part'


def test_owned_lower_bound_does_not_ban_more_production():
    c = controller(); c.table.observe(obs(hands='1 raw, 1 part'))
    c.table.recipes['part'] = {'ingredients': ['raw']}
    assert c.assess('craft 2 part')['status'] != REJECT


def test_time_or_unrelated_travel_cannot_release_material_failure():
    c = controller(); c.table.recipes['part'] = {'ingredients': ['raw']}
    before = obs(hands='1 raw')
    c.observe(before, 'craft 2 part', obs('Cannot craft a single part.', hands='1 raw', step=1))
    c.table.observe(obs(hands='1 raw', location='hall', step=90))
    assert c.assess('craft 2 part')['status'] == REJECT
    c.table.observe(obs(hands='2 raw', location='hall', step=91))
    assert c.assess('craft 2 part')['status'] != REJECT


def test_new_station_allows_retry():
    c = controller(); c.table.recipes['part'] = {'ingredients': ['raw']}
    c.observe(obs(hands='1 raw'), 'craft 2 part', obs('Cannot craft part. Missing necessary bench in the current area.', hands='1 raw', step=1))
    c.table.observe(obs(hands='1 raw', ground='1 bench', location='hall', step=2))
    assert c.assess('craft 2 part')['status'] != REJECT


def test_legal_direct_base_goal_collection_preserved():
    c = controller()
    assert c.choose(obs(ground='2 final'), 'store 2 final inventory') == 'store 2 final inventory'


def test_s2_collects_all_two_visible_materials():
    c = controller('S2'); c.table.recipes['final'] = {'ingredients': ['raw']}
    c.table.observe(obs(ground='2 raw'))
    a, meta = c.opportunity('store 1 raw inventory')
    assert a == 'store 2 raw inventory' and meta['kind'] == 'bulk_collection'


def test_held_copy_included_before_ground_batch():
    c = controller('S2'); c.table.recipes['final'] = {'ingredients': ['raw']}
    c.table.observe(obs(hands='1 raw', ground='2 raw'))
    assert c.collection('raw', True) == 'store 3 raw inventory'


def test_s2_does_not_collect_unrelated_objects_before_leaving():
    c = controller('S2'); c.table.observe(obs(ground='9 unrelated'))
    assert c.opportunity('enter hall') == (None, None)


def test_opportunity_limit_counts_extra_actions_only():
    c = controller('S2'); c.table.recipes['final'] = {'ingredients': ['raw']}
    c.table.observe(obs(ground='2 raw')); c.opportunity_spent = c.OPPORTUNITY_LIMIT
    assert c.opportunity('enter hall') == (None, None)
    assert c.opportunity('store 1 raw inventory')[0] == 'store 2 raw inventory'


def test_full_bag_stashes_unrelated_held_item_into_current_container():
    c = controller('S3'); c.table.observe(obs(hands='1 spare, 1 final', ground='1 cache, 2 raw'))
    c.table.containers['bag'].update(load=20)
    c.table.containers['cache'] = {'counts': {}, 'load': 0, 'capacity': 10, 'location': 'room', 'step': 0}
    a, meta = c.stash_option('pick up raw')
    assert a == 'store 1 spare cache' and meta['kind'] == 'stash'


def test_full_bag_single_transfer_intent_survives_checkpoint():
    c = controller('S3'); c.table.containers['bag'].update(counts={'spare': 1}, load=20)
    c.table.observe(obs(ground='1 cache, 1 raw'))
    c.table.containers['cache'] = {'counts': {}, 'load': 0, 'capacity': 10, 'location': 'room', 'step': 0}
    a, meta = c.stash_option('store 1 raw inventory')
    assert a == 'take out spare inventory'
    c.storage_intent = meta
    clone = restore_controller(json.loads(json.dumps(c.to_dict())))
    assert clone.to_dict() == c.to_dict()


def test_stash_record_return_and_reconfirmation():
    c = controller('S3'); before = obs(hands='1 spare', ground='1 cache')
    c.table.containers['cache'] = {'counts': {}, 'load': 0, 'capacity': 10, 'location': 'room', 'step': 0}
    c.observe(before, 'store 1 spare cache', obs('I stored 1 spare in cache.', ground='1 cache', step=1))
    assert len(c.stashes) == 1
    c.table.observe(obs(location='hall', step=2)); c.table.links['hall'] = ['room']; c.refresh_stashes()
    assert c.retrieve('spare')[0] == 'enter room'
    c.table.observe(obs(ground='1 cache', step=3)); c.refresh_stashes()
    assert c.retrieve('spare')[0] == 'inspect cache'
    c.observe(obs(ground='1 cache', step=3), 'inspect cache', obs('I inspected cache. It contains: 1 spare (capacity: 1/10).', ground='1 cache', step=4))
    assert c.retrieve('spare')[0] == 'take out spare cache'


def test_disappeared_stash_does_not_generate_phantom_takeout():
    c = controller('S3'); c.table.containers['cache'] = {'counts': {}, 'load': 0, 'capacity': 10, 'location': 'room', 'step': 0}
    c.observe(obs(hands='1 spare', ground='1 cache'), 'store 1 spare cache', obs('I stored 1 spare in cache.', ground='1 cache', step=1))
    c.observe(obs(ground='1 cache', step=2), 'inspect cache', obs('I inspected cache. It contains: no objects (capacity: 0/10).', ground='1 cache', step=3))
    assert c.retrieve('spare') == (None, None)
    assert next(iter(c.stashes.values()))['status'] == 'missing'


def test_no_discard_of_key_intermediate_or_final_goal():
    c = controller('S3'); c.table.recipes['final'] = {'ingredients': ['part']}
    c.table.observe(obs(hands='1 part, 1 final', ground='1 final'))
    assert c.assess('drop part')['status'] == REJECT
    assert c.assess('drop final')['status'] == REJECT


def test_recipe_cycles_are_finite():
    c = controller(); c.table.recipes = {'final': {'ingredients': ['a']}, 'a': {'ingredients': ['final']}}
    assert c._all_needed('final') == {'final', 'a'}
    c.choose(obs(), 'wait')
    assert len(c.condition_log) <= c.MAX_CANDIDATES


def test_json_restore_repeats_same_decision():
    for method in ['S1', 'S2', 'S3']:
        c = controller(method); c.table.recipes['final'] = {'ingredients': ['raw']}
        clone = restore_controller(json.loads(json.dumps(c.to_dict())))
        observation = obs(ground='2 raw')
        assert c.choose(observation, 'wait') == clone.choose(observation, 'wait')
        assert c.to_dict() == clone.to_dict()


def test_wait_fallback_can_collect_extra_input_after_ambiguous_quota():
    c = controller(); c.exploration_spent = c.EXPLORATION_LIMIT
    c.table.recipes = {'final': {'ingredients': ['raw', 'part'], 'stations': ['bench']}}
    c.table.containers['bag']['counts'] = {'raw': 1}
    c.quotas['final'] = 2; c.queue = ['raw', 'part', 'final']; c.queue_needs = {'raw': 2, 'part': 2}
    assert c.choose(obs(hands='1 final, 1 part', ground='1 part, 1 bench'), 'wait') == 'store 2 part inventory'


def test_inspected_station_and_unrelated_currency_not_collection_relevance():
    c = controller('S2'); c.table.recipes['final'] = {'ingredients': ['raw'], 'stations': ['bench']}
    c.attempt_log = [{'state': 'SUCCESS', 'target': 'coin', 'action': 'inspect coin'},
                     {'state': 'SUCCESS', 'target': 'bench', 'action': 'inspect bench'}]
    assert 'bench' not in c.relevant() and 'coin' not in c.relevant()
