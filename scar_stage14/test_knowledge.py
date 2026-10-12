import copy
import pytest
from scar_stage14.knowledge import Knowledge,extract
from scar_stage14.common import load,ROOT


def native(text,step=1):return {'step':step,'text':'Current Location: room\n\n'+text+'\n\nI am holding nothing.\n'}
def names(step=1):return native('I inspected ore: Some metal.\nIt can be used to craft: bar (made of ore, fuel).\nIt has nothing written on it.',step)
def quantities(step=2):return native('I picked up ore.\nI have acquired a new item: ore. It can be used to craft: bar (0.5 ore, 2 fuel)',step)

@pytest.mark.parametrize('row',load(ROOT/'parser_gold.json')['rows'],ids=lambda r:r['id'])
def test_independent_native_gold(row):
    facts,bad=extract(row['observation'],row['action']);gold=row['expected']
    assert not bad
    got={f['product']:set(f['ingredients']) for f in facts if f['ingredients']}
    assert got=={n:set(v) for n,v in gold['recipes'].items()}
    assert {f['product']:f['quantities'] for f in facts if f['quantities']}==gold['quantities']
    assert {f['product']:f['stations'] for f in facts if f['stations']}==gold['stations']


def test_names_unknown_quantities_and_enrichment():
    k=Knowledge();d=k.observe(names(),'inspect ore');assert d['new_relations']==['bar']
    assert k.facts['bar']['quantities'] is None
    d=k.observe(quantities(),'pick up ore');assert not d['new_relations'] and d['quantity_updates']==['bar']
    assert k.facts['bar']['quantities']=={'ore':.5,'fuel':2} and k.facts['bar']['first_relation_step']==1
    k.observe(names(3),'inspect ore');assert k.facts['bar']['quantities']=={'ore':.5,'fuel':2}
    assert len(k.relations())==1 and len(k.events)==3


def test_duplicate_observation_and_later_repeat_separate():
    k=Knowledge();k.observe(names(),'inspect ore');assert k.observe(names(),'inspect ore')['duplicate_observation']
    d=k.observe(names(2),'inspect ore');assert d['repeated_relations']==['bar'] and len(k.events)==2


def test_station_requirement_partial_preserves_names():
    k=Knowledge();k.observe(names(),'inspect ore')
    k.observe(native('Cannot craft bar. Missing necessary furnace in the current area.',2),'craft 1 bar')
    f=k.facts['bar'];assert f['ingredients']==['fuel','ore'] and f['stations']==['furnace']
    assert f['station_completeness']=='known_required_subset' and f['quantities'] is None


def test_future_prohibited_and_prior_state_immutable():
    k=Knowledge();k.observe(names(),'inspect ore');old=k.to_dict()
    with pytest.raises(ValueError):k.observe(quantities(9),'pick up ore',cutoff=8)
    assert k.to_dict()==old


def test_model_guess_not_fact_even_with_native_like_words():
    k=Knowledge();k.observe(quantities(),'pick up ore',source_kind='model_response')
    assert not k.facts

@pytest.mark.parametrize('text',[
    'I inspected a_note: It says sword (made of ore, fuel), possibly useful.',
    'A storyteller says bar (2 ore).',
    'It can be used to craft: bar (made of ore).',
    'I inspected bag: A sack.\nIt contains: 2 ore (capacity: 2/20).',
    'I successfully crafted 2 bar. It is now on the ground. (90 HP remaining)',
    'NPC: Cannot craft bar. Missing necessary furnace in the current area.',
    'I inspected ore: A rock.\nIt can be used to craft: maybe bar (made of ore).'
])
def test_description_inventory_narrative_not_recipe(text):
    assert not extract(native(text),'inspect ore')[0]


def test_ambiguous_quantities_no_default_one():
    f,bad=extract(native('I have acquired a new item: ore. It can be used to craft: bar (some ore)'),'pick up ore')
    assert not f and bad


def test_conflicts_preserved_but_not_promoted():
    k=Knowledge();k.observe(names(),'inspect ore')
    k.observe(native('I inspected ore: Rock.\nIt can be used to craft: bar (made of ore, wood).',2),'inspect ore')
    assert k.facts['bar']['certainty']=='AMBIGUOUS_CONFLICT' and not k.relations()
    assert k.events[-1]['conflict']
