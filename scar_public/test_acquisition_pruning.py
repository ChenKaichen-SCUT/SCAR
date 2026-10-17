import copy
from scar_public.obligations import ExecutionModel


def world():
    m=ExecutionModel();m.observe('Current Location: hall\nI am holding no objects.\nI have equipped no objects.\nI see 5 wood, 5 thread, 1 bench near me.\nNeighboring areas: yard.')
    m.capacity_lower=m.capacity_upper=2
    m.recipes={'club':{'needs':{'wood':2,'thread':1},'quote':'club (2 wood, 1 thread)'},
               'dagger':{'needs':{'wood':1,'thread':1},'quote':'dagger (1 wood, 1 thread)'}}
    m.inspected=['bench'];m.stations={'club':{'name':'bench'},'dagger':{'name':'bench'}}
    return m


def test_capacity_rejection_preserves_feasible_simpler_alternative():
    m=world()
    assert m.acquisition('club',prune_impossible=True)['search_nodes']==0
    a=m.acquisition('dagger');b=m.acquisition('dagger',prune_impossible=True)
    assert a['plan']==b['plan'] and b['status']=='candidate'


def test_observed_container_prevents_unsound_hand_only_rejection():
    m=world();m.current['ground']['bag']=1;m.locations['hall']['objects']['bag']=1
    m.containers={'bag':{'items':{},'capacity':5,'used':0}}
    p=m.acquisition('club',prune_impossible=True)
    assert p['status']=='candidate' and any('bag' in a for a in p['plan'])


def test_existing_output_can_be_acquired_even_when_its_recipe_is_impossible():
    m=world();m.current['ground']['club']=1
    assert m.acquisition('club',prune_impossible=True)['plan']==['pick up club']


def test_upstream_capacity_obstruction_and_unknown_container_discovery():
    m=world();m.recipes['staff']={'needs':{'club':1},'quote':'staff (1 club)'}
    assert m.acquisition('staff',prune_impossible=True)['search_nodes']==0
    m.current['ground']['unknown_box']=1;m.locations['hall']['objects']['unknown_box']=1
    p=m.acquisition('club',prune_impossible=True)
    assert p['status']=='capacity_discovery' and p['plan']==['inspect unknown_box']


def test_small_inventory_grid_keeps_all_baseline_candidates():
    for wood in range(4):
        for thread in range(3):
            for capacity in (1,2,3):
                m=world();m.capacity_lower=m.capacity_upper=capacity;m.current['ground'].update(wood=wood,thread=thread)
                m.locations['hall']['objects'].update(wood=wood,thread=thread)
                for target in ('club','dagger'):
                    a=copy.deepcopy(m).acquisition(target);b=copy.deepcopy(m).acquisition(target,prune_impossible=True)
                    if a['status']=='candidate':assert b['status']=='candidate' and a['plan']==b['plan']


def test_overcapacity_initial_observation_is_not_discarded():
    m=world();m.current['holding']={'wood':2,'thread':1}
    p=m.acquisition('club',prune_impossible=True)
    assert p['status']=='candidate' and p['plan'][0]=='craft 1 club'


def test_zero_scaled_input_does_not_require_an_unreachable_type():
    m=world();m.recipes['dagger']['needs']['dust']=0.0001
    assert m.acquisition('dagger',prune_impossible=True)['status']=='candidate'


def test_new_agent_enables_pruning_after_checkpoint_restore_only_for_itself():
    from scar_public.intent_repair import IntentMemory
    from scar_public.evidence_repair import RepairMemory
    m=IntentMemory();m.load(m.state())
    assert m.model.acquisition_pruning
    assert not getattr(RepairMemory().model,'acquisition_pruning',False)
