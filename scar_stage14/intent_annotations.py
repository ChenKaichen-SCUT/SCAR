"""Manual reading of saved J2 reasoning, before Stage14 native scoring.

Values identify the explicitly named next production target, not a true hidden
dependency. Missing entries have no unambiguous bounded exploration suffix.
The unmodified reasoning and its hash are saved alongside every annotation.
"""
GOALS={
('d12_4892e4fbb1fad417',0):'fiend_rivet',
('d12_1112504715d6d930',0):'fiend_alloy_scale',
('d12_1112504715d6d930',1):'fiend_alloy_scale',
('d12_17c5deb0c6ac6acf',0):'brimite_blade_blank',
('d12_17c5deb0c6ac6acf',1):'brimite_blade_blank',
('d12_2bd7c9c561fcf61b',0):'fiend_helm',
('d12_2bd7c9c561fcf61b',1):'fiend_helm',
('d12_a92f408263c9541e',0):'hellfire_bomb',
('d12_a92f408263c9541e',1):'hellfire_bomb',
('d12_8694b7913dc729f7',0):'chain_net',
('d12_8694b7913dc729f7',1):'chain_net',
('d12_7aba559853f3978b',0):'fiend_rivet',
('d12_7aba559853f3978b',1):'fiend_rivet',
('d12_61af4f652315aaae',0):'padded_lining',
('d12_db9cf8a8d4ddadac',0):'padded_tunic',
('d12_db9cf8a8d4ddadac',1):'padded_tunic',
('d12_508fa7a07ea3f787',0):'bandage_roll',
('d12_b5e67d08463a4c9c',0):'iron_nugget',
('d12_2b84d3d36487c9b2',1):'sinew_cord',
('d12_c22b3ec6c829109c',0):'hunter_gauntlets',
('d12_c22b3ec6c829109c',1):'hunter_gauntlets',
('d12_1cd1a634b22e2a0a',0):'forged_blade_blank',
('d12_8d93a9fe38ae0edb',0):'fiend_helm',
('d12_edea7c24b75cf3bb',0):'iron_bar',
('d12_44fff422fc987cfb',0):'padded_tunic',
('d12_84a8b7d14c832282',0):'bandage_roll',
('d12_b2926ff775c6769c',0):'forged_blade_blank',
('d12_b2926ff775c6769c',1):'forged_blade_blank',
('d12_01c83c35e4b3f13b',0):'hellfire_bomb',
}
# Explicit destination without a uniquely specified next component/object.
DESTINATIONS={('d12_dc6e7aaa56e84ae2',0):'courtyard'}
AMBIGUOUS={
('d12_2b84d3d36487c9b2',0):'mentions bandage_roll and sinew_cord but does not commit to one next craft',
('d12_2310e2d3684d6e00',0):'search for wooden_rod has no known location or concrete bounded suffix',
('d12_053962d91bc03253',0):'take-out is described as a contents probe; subsequent sufficient materials unknown',
('d12_2f6a0c1e72839f91',0):'search location for either cloth or scrap; no specified next exploration object',
('d12_437b4653a9a80655',0):'search location for rod or its ingredients; no known object-specific next action',
}
