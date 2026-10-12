from scar_stage13.text_audit import extract


def test_acquisition_and_inspection_same_disclosed_recipe():
    assert extract('hellfire_bomb (1 hellcoal_concentrate, 1 oil_flask, 0.5 iron_bar)')==extract('hellfire_bomb (made of hellcoal_concentrate, oil_flask, iron_bar)')


def test_capacity_and_prose_not_recipes():
    assert not extract('inventory (capacity: 1/20), (90 HP remaining), None. forge (maybe iron)')
    assert extract('a (made of b, c), d (2 e)')=={'a':['b','c'],'d':['e']}
