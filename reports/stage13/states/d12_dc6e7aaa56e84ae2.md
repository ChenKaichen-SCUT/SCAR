# 冻结状态 d12_dc6e7aaa56e84ae2

目标：`craft 1 padded_tunic`。来源 Stage 10 / S1 / `sequence-f5bbe8ac06891a7d-S1-c3876e4fe87c`，零基行号 5，剩余 35 动作。

[原始冻结状态](../../../results/stage12/diagnostic/states.json)、[原始原生分支](../../../results/stage12/diagnostic/native_branches.jsonl.gz)、[本轮公开输入与历史](../../../results/stage13/public_inputs.json)。状态/候选 ID 精确对应这些文件；当前页所有引擎反馈均原样保存。

## 决策时公开证据

```json
{
  "objective": "Obtain at least 2 padded_tunic in your possession in total. You already hold one. The previous craft failed. Any valid route is allowed.",
  "target_action": "craft 1 padded_tunic",
  "current": {
    "location": "cellar",
    "hands": {
      "padded_tunic": 1.0
    },
    "ground": {
      "salvage_cloth": 2.0
    },
    "equipment": {
      "scout_satchel_0": 1.0
    },
    "neighbors": [
      "barracks",
      "courtyard"
    ]
  },
  "confirmed_recipe_relations": {
    "padded_tunic": {
      "ingredients": [
        "padded_lining",
        "sinew_cord"
      ],
      "stations": [
        "war_bench"
      ]
    },
    "stitched_panel": {
      "ingredients": [
        "bandage_roll",
        "sinew_cord"
      ],
      "stations": "UNKNOWN"
    },
    "ruin_maul": {
      "ingredients": [
        "ruin_blade",
        "wooden_rod",
        "bandage_roll"
      ],
      "stations": "UNKNOWN"
    },
    "war_strap": {
      "ingredients": [
        "sinew_cord",
        "bandage_roll"
      ],
      "stations": "UNKNOWN"
    },
    "timber_sword": {
      "ingredients": [
        "scorched_plank",
        "wood_strip",
        "sinew_cord"
      ],
      "stations": "UNKNOWN"
    },
    "spiked_club": {
      "ingredients": [
        "charred_timber",
        "rubble_chunk",
        "sinew_cord"
      ],
      "stations": "UNKNOWN"
    },
    "war_codex": {
      "ingredients": [
        "field_journal",
        "sinew_cord",
        "fiend_strip"
      ],
      "stations": "UNKNOWN"
    },
    "cog_crossbow": {
      "ingredients": [
        "gearwork_frame",
        "iron_bar",
        "sinew_cord"
      ],
      "stations": "UNKNOWN"
    },
    "ruin_spear": {
      "ingredients": [
        "knapped_edge",
        "wooden_rod",
        "sinew_cord"
      ],
      "stations": "UNKNOWN"
    },
    "hunter_gauntlets": {
      "ingredients": [
        "iron_bar",
        "war_strap",
        "sinew_cord"
      ],
      "stations": "UNKNOWN"
    },
    "fiend_scale_bundle": {
      "ingredients": [
        "fiend_alloy_scale",
        "sinew_cord"
      ],
      "stations": "UNKNOWN"
    },
    "scale_bundle": {
      "ingredients": [
        "iron_scale",
        "sinew_cord"
      ],
      "stations": "UNKNOWN"
    },
    "siege_crate": {
      "ingredients": [
        "scorched_plank",
        "iron_bar",
        "sinew_cord"
      ],
      "stations": "UNKNOWN"
    },
    "fiend_gauntlets": {
      "ingredients": [
        "fiend_alloy",
        "war_strap",
        "sinew_cord"
      ],
      "stations": "UNKNOWN"
    },
    "bandage_roll": {
      "ingredients": [
        "salvage_cloth",
        "sinew_cord"
      ],
      "stations": "UNKNOWN"
    },
    "scrap_buckler": {
      "ingredients": [
        "scrap_iron",
        "sinew_cord"
      ],
      "stations": "UNKNOWN"
    },
    "repair_kit": {
      "ingredients": [
        "scrap_iron",
        "sinew_cord",
        "oil_flask"
      ],
      "stations": "UNKNOWN"
    },
    "scout_satchel": {
      "ingredients": [
        "salvage_cloth",
        "sinew_cord"
      ],
      "stations": "UNKNOWN"
    },
    "warding_charm": {
      "ingredients": [
        "demon_core_shard",
        "sinew_cord",
        "hellcoal_concentrate"
      ],
      "stations": "UNKNOWN"
    },
    "field_journal": {
      "ingredients": [
        "war_parchment",
        "sinew_cord"
      ],
      "stations": "UNKNOWN"
    },
    "chain_net": {
      "ingredients": [
        "iron_bar",
        "sinew_cord"
      ],
      "stations": "UNKNOWN"
    },
    "oil_bomb": {
      "ingredients": [
        "oil_flask",
        "charcoal_brick",
        "salvage_cloth"
      ],
      "stations": "UNKNOWN"
    },
    "war_parchment": {
      "ingredients": [
        "salvage_cloth"
      ],
      "stations": "UNKNOWN"
    },
    "sinew_cord": {
      "ingredients": [
        "salvage_cloth"
      ],
      "stations": "UNKNOWN"
    },
    "war_banner": {
      "ingredients": [
        "salvage_cloth",
        "wooden_rod"
      ],
      "stations": "UNKNOWN"
    },
    "padded_lining": {
      "ingredients": [
        "stitched_panel",
        "salvage_cloth"
      ],
      "stations": "UNKNOWN"
    },
    "scrap_helm": {
      "ingredients": [
        "scrap_iron",
        "salvage_cloth"
      ],
      "stations": "UNKNOWN"
    },
    "ruin_gauntlets": {
      "ingredients": [
        "rubble_chunk",
        "war_strap",
        "salvage_cloth"
      ],
      "stations": "UNKNOWN"
    },
    "scrap_lantern": {
      "ingredients": [
        "scrap_iron",
        "devil_oil",
        "salvage_cloth"
      ],
      "stations": "UNKNOWN"
    }
  },
  "containers": {
    "scout_satchel_0": {
      "counts": {},
      "load": 0.0,
      "capacity": 20.0,
      "location": "cellar",
      "step": 2,
      "source": "public_container_inspection"
    }
  },
  "known_locations": {
    "barracks": {
      "objects": {
        "bandage_roll": 1.0,
        "sinew_cord": 1.0
      },
      "step": 13,
      "source": "public_ground_observation"
    },
    "cellar": {
      "objects": {
        "salvage_cloth": 2.0
      },
      "step": 15,
      "source": "public_ground_observation"
    },
    "courtyard": {
      "objects": {
        "war_bench": 1.0
      },
      "step": 7,
      "source": "public_ground_observation"
    }
  },
  "inspected": [
    "scout_satchel_0",
    "padded_tunic",
    "bandage_roll",
    "sinew_cord",
    "salvage_cloth"
  ],
  "produced": {},
  "recent_attempts": [
    {
      "action": "inspect padded_tunic",
      "target": "padded_tunic",
      "context": {
        "location": "barracks",
        "stations": {
          "war_bench": false
        },
        "materials": {},
        "visible": true
      },
      "feedback": "I inspected padded_tunic: A padded tunic that absorbs the shock of machine strikes.\nIt can be used to craft: None.\nIt has nothing written on it.",
      "state": "SUCCESS",
      "meaningful_trial": true,
      "failure_type": null,
      "retry_condition": null,
      "actual_action_cost": 1,
      "observed_resource_consumption": null,
      "resource_status": "UNKNOWN until independently audited; failed attempt cost retained",
      "was_forward_trial": false,
      "step": 11,
      "retry_after_block": false
    },
    {
      "action": "inspect bandage_roll",
      "target": "bandage_roll",
      "context": {
        "location": "barracks",
        "stations": {},
        "materials": {},
        "visible": true
      },
      "feedback": "I inspected bandage_roll: A rolled bolt of salvage cloth prepared for binding wounds or crafting gear.\nIt can be used to craft: stitched_panel (made of bandage_roll, sinew_cord), ruin_maul (made of ruin_blade, wooden_rod, bandage_roll), war_strap (made of sinew_cord, bandage_roll).\nIt has nothing written on it.",
      "state": "SUCCESS",
      "meaningful_trial": true,
      "failure_type": null,
      "retry_condition": null,
      "actual_action_cost": 1,
      "observed_resource_consumption": null,
      "resource_status": "UNKNOWN until independently audited; failed attempt cost retained",
      "was_forward_trial": false,
      "step": 12,
      "retry_after_block": false
    },
    {
      "action": "inspect sinew_cord",
      "target": "sinew_cord",
      "context": {
        "location": "barracks",
        "stations": {},
        "materials": {},
        "visible": true
      },
      "feedback": "I inspected sinew_cord: Twisted cord braided from salvaged fibers and dried sinew, surprisingly tough.\nIt can be used to craft: stitched_panel (made of bandage_roll, sinew_cord), timber_sword (made of scorched_plank, wood_strip, sinew_cord), spiked_club (made of charred_timber, rubble_chunk, sinew_cord), war_strap (made of sinew_cord, bandage_roll), war_codex (made of field_journal, sinew_cord, fiend_strip), cog_crossbow (made of gearwork_frame, iron_bar, sinew_cord), ruin_spear (made of knapped_edge, wooden_rod, sinew_cord), hunter_gauntlets (made of iron_bar, war_strap, sinew_cord), fiend_scale_bundle (made of fiend_alloy_scale, sinew_cord), scale_bundle (made of iron_scale, sinew_cord), siege_crate (made of scorched_plank, iron_bar, sinew_cord), fiend_gauntlets (made of fiend_alloy, war_strap, sinew_cord), bandage_roll (made of salvage_cloth, sinew_cord), padded_tunic (made of padded_lining, sinew_cord), scrap_buckler (made of scrap_iron, sinew_cord), repair_kit (made of scrap_iron, sinew_cord, oil_flask), scout_satchel (made of salvage_cloth, sinew_cord), warding_charm (made of demon_core_shard, sinew_cord, hellcoal_concentrate), field_journal (made of war_parchment, sinew_cord), chain_net (made of iron_bar, sinew_cord).\nIt has nothing written on it.",
      "state": "SUCCESS",
      "meaningful_trial": true,
      "failure_type": null,
      "retry_condition": null,
      "actual_action_cost": 1,
      "observed_resource_consumption": null,
      "resource_status": "UNKNOWN until independently audited; failed attempt cost retained",
      "was_forward_trial": false,
      "step": 13,
      "retry_after_block": false
    },
    {
      "action": "inspect salvage_cloth",
      "target": "salvage_cloth",
      "context": {
        "location": "cellar",
        "stations": {},
        "materials": {},
        "visible": true
      },
      "feedback": "I inspected salvage_cloth: Tattered fabric pulled from ruined banners and bedrolls, still serviceable.\nIt can be used to craft: bandage_roll (made of salvage_cloth, sinew_cord), oil_bomb (made of oil_flask, charcoal_brick, salvage_cloth), scout_satchel (made of salvage_cloth, sinew_cord), war_parchment (made of salvage_cloth), sinew_cord (made of salvage_cloth), war_banner (made of salvage_cloth, wooden_rod), padded_lining (made of stitched_panel, salvage_cloth), scrap_helm (made of scrap_iron, salvage_cloth), ruin_gauntlets (made of rubble_chunk, war_strap, salvage_cloth), scrap_lantern (made of scrap_iron, devil_oil, salvage_cloth).\nIt has nothing written on it.",
      "state": "SUCCESS",
      "meaningful_trial": true,
      "failure_type": null,
      "retry_condition": null,
      "actual_action_cost": 1,
      "observed_resource_consumption": null,
      "resource_status": "UNKNOWN until independently audited; failed attempt cost retained",
      "was_forward_trial": false,
      "step": 15,
      "retry_after_block": false
    }
  ],
  "unresolved_public_nodes": [
    "salvage_cloth"
  ],
  "uncertainty": "Missing relations are UNKNOWN, not impossible. Production history is not possession. No semantic hypothesis is a confirmed recipe."
}
```

公开持有量下界与是否精确（地面数量另见 current.ground；UNKNOWN 不补成 0）：

```json
{
  "bandage_roll": {
    "lower_bound": 0,
    "exact": true
  },
  "chain_net": {
    "lower_bound": 0,
    "exact": true
  },
  "charcoal_brick": {
    "lower_bound": 0,
    "exact": true
  },
  "charred_timber": {
    "lower_bound": 0,
    "exact": true
  },
  "cog_crossbow": {
    "lower_bound": 0,
    "exact": true
  },
  "demon_core_shard": {
    "lower_bound": 0,
    "exact": true
  },
  "devil_oil": {
    "lower_bound": 0,
    "exact": true
  },
  "field_journal": {
    "lower_bound": 0,
    "exact": true
  },
  "fiend_alloy": {
    "lower_bound": 0,
    "exact": true
  },
  "fiend_alloy_scale": {
    "lower_bound": 0,
    "exact": true
  },
  "fiend_gauntlets": {
    "lower_bound": 0,
    "exact": true
  },
  "fiend_scale_bundle": {
    "lower_bound": 0,
    "exact": true
  },
  "fiend_strip": {
    "lower_bound": 0,
    "exact": true
  },
  "gearwork_frame": {
    "lower_bound": 0,
    "exact": true
  },
  "hellcoal_concentrate": {
    "lower_bound": 0,
    "exact": true
  },
  "hunter_gauntlets": {
    "lower_bound": 0,
    "exact": true
  },
  "iron_bar": {
    "lower_bound": 0,
    "exact": true
  },
  "iron_scale": {
    "lower_bound": 0,
    "exact": true
  },
  "knapped_edge": {
    "lower_bound": 0,
    "exact": true
  },
  "oil_bomb": {
    "lower_bound": 0,
    "exact": true
  },
  "oil_flask": {
    "lower_bound": 0,
    "exact": true
  },
  "padded_lining": {
    "lower_bound": 0,
    "exact": true
  },
  "padded_tunic": {
    "lower_bound": 1.0,
    "exact": true
  },
  "repair_kit": {
    "lower_bound": 0,
    "exact": true
  },
  "rubble_chunk": {
    "lower_bound": 0,
    "exact": true
  },
  "ruin_blade": {
    "lower_bound": 0,
    "exact": true
  },
  "ruin_gauntlets": {
    "lower_bound": 0,
    "exact": true
  },
  "ruin_maul": {
    "lower_bound": 0,
    "exact": true
  },
  "ruin_spear": {
    "lower_bound": 0,
    "exact": true
  },
  "salvage_cloth": {
    "lower_bound": 0,
    "exact": true
  },
  "scale_bundle": {
    "lower_bound": 0,
    "exact": true
  },
  "scorched_plank": {
    "lower_bound": 0,
    "exact": true
  },
  "scout_satchel": {
    "lower_bound": 0,
    "exact": true
  },
  "scout_satchel_0": {
    "lower_bound": 1.0,
    "exact": true
  },
  "scrap_buckler": {
    "lower_bound": 0,
    "exact": true
  },
  "scrap_helm": {
    "lower_bound": 0,
    "exact": true
  },
  "scrap_iron": {
    "lower_bound": 0,
    "exact": true
  },
  "scrap_lantern": {
    "lower_bound": 0,
    "exact": true
  },
  "siege_crate": {
    "lower_bound": 0,
    "exact": true
  },
  "sinew_cord": {
    "lower_bound": 0,
    "exact": true
  },
  "spiked_club": {
    "lower_bound": 0,
    "exact": true
  },
  "stitched_panel": {
    "lower_bound": 0,
    "exact": true
  },
  "timber_sword": {
    "lower_bound": 0,
    "exact": true
  },
  "war_banner": {
    "lower_bound": 0,
    "exact": true
  },
  "war_codex": {
    "lower_bound": 0,
    "exact": true
  },
  "war_parchment": {
    "lower_bound": 0,
    "exact": true
  },
  "war_strap": {
    "lower_bound": 0,
    "exact": true
  },
  "warding_charm": {
    "lower_bound": 0,
    "exact": true
  },
  "wood_strip": {
    "lower_bound": 0,
    "exact": true
  },
  "wooden_rod": {
    "lower_bound": 0,
    "exact": true
  }
}
```

原始观察：

```text

Current Time: 0001-01-01 10:30:00
Current Location: Ashen Bastion, cellar

I inspected salvage_cloth: Tattered fabric pulled from ruined banners and bedrolls, still serviceable.
It can be used to craft: bandage_roll (made of salvage_cloth, sinew_cord), oil_bomb (made of oil_flask, charcoal_brick, salvage_cloth), scout_satchel (made of salvage_cloth, sinew_cord), war_parchment (made of salvage_cloth), sinew_cord (made of salvage_cloth), war_banner (made of salvage_cloth, wooden_rod), padded_lining (made of stitched_panel, salvage_cloth), scrap_helm (made of scrap_iron, salvage_cloth), ruin_gauntlets (made of rubble_chunk, war_strap, salvage_cloth), scrap_lantern (made of scrap_iron, devil_oil, salvage_cloth).
It has nothing written on it.

I am holding 1 padded_tunic.
I have equipped 1 scout_satchel_0.
I see 2 salvage_cloth near me.
I see no one nearby.

My level is 1.
My attack is at 10.
My defense is at 0.
My health is at 100.
My experience is at 10.

Neighboring areas: barracks, courtyard.

```

已知地点可见或历史观察到、尚未检查的对象（历史存在需重确认）：

```json
[
  "war_bench"
]
```

基础提案、FIFO 和实际 S1 选择：

```json
{
  "base_proposal": "enter courtyard",
  "FIFO": "enter barracks",
  "actual_S1": "enter barracks",
  "reason": "retain_F0",
  "mechanisms": {},
  "queue": [
    "sinew_cord",
    "padded_tunic",
    "stitched_panel",
    "salvage_cloth",
    "padded_lining"
  ],
  "graph": {}
}
```

公开特征、覆盖选择、分层入口账本：

```json
{
  "state_id": "d12_dc6e7aaa56e84ae2",
  "choices": {
    "C0": "c_f4bbfd0ebbe8",
    "C1": "c_f4bbfd0ebbe8",
    "C2": "c_f4bbfd0ebbe8",
    "C3": "c_f4bbfd0ebbe8",
    "L": "c_f4bbfd0ebbe8"
  },
  "features": {
    "incomplete_public_dependencies": false,
    "unknown_goal_recipe": false,
    "public_necessary_knowledge_drought": 0,
    "no_public_progress_streak": 0,
    "same_known_component_last3": false,
    "recent_unconnected_inspection_last4": true,
    "uninspected_independent_entry_intents": 0,
    "fresh_uninspected_product": false,
    "j3_previously_attempted": false,
    "j3_repeat_inspection_or_station": true,
    "j3_public_recipe_support": false,
    "j3_estimated_actions": 2,
    "s1_estimated_actions": null,
    "s1_public_execution_protected": false,
    "C1_trigger": false,
    "C2_trigger": false,
    "L_trigger": false,
    "remaining_actions": 35
  },
  "entry_ledger": [
    {
      "candidate_id": "c_973aea1af0e4",
      "intent": [
        "craft_then_inspect",
        "scout_satchel"
      ],
      "target": "scout_satchel",
      "entry_states": [
        "other_public_direction"
      ],
      "last_attempt_index": null,
      "last_feedback": null,
      "attempts": 0,
      "inspected": false,
      "produced": false,
      "unconnected_entry": false,
      "confirmed_necessary": false,
      "public_recipe_support": true,
      "station": false,
      "container": false,
      "first_action": "store 2 salvage_cloth inventory",
      "condition": "UNKNOWN",
      "estimated_actions": null,
      "estimate_is_not_native_cost_or_guaranteed_upper_bound": true,
      "menu_order": 0
    },
    {
      "candidate_id": "c_334ffca58064",
      "intent": [
        "craft_then_inspect",
        "war_parchment"
      ],
      "target": "war_parchment",
      "entry_states": [
        "other_public_direction"
      ],
      "last_attempt_index": null,
      "last_feedback": null,
      "attempts": 0,
      "inspected": false,
      "produced": false,
      "unconnected_entry": false,
      "confirmed_necessary": false,
      "public_recipe_support": true,
      "station": false,
      "container": false,
      "first_action": "store 2 salvage_cloth inventory",
      "condition": "UNKNOWN",
      "estimated_actions": null,
      "estimate_is_not_native_cost_or_guaranteed_upper_bound": true,
      "menu_order": 1
    },
    {
      "candidate_id": "c_3005d7648aa4",
      "intent": [
        "craft_then_inspect",
        "war_strap"
      ],
      "target": "war_strap",
      "entry_states": [
        "other_public_direction"
      ],
      "last_attempt_index": null,
      "last_feedback": null,
      "attempts": 0,
      "inspected": false,
      "produced": false,
      "unconnected_entry": false,
      "confirmed_necessary": false,
      "public_recipe_support": true,
      "station": false,
      "container": false,
      "first_action": "enter barracks",
      "condition": "UNKNOWN",
      "estimated_actions": null,
      "estimate_is_not_native_cost_or_guaranteed_upper_bound": true,
      "menu_order": 2
    },
    {
      "candidate_id": "c_f4bbfd0ebbe8",
      "intent": [
        "primitive",
        "enter barracks"
      ],
      "target": "barracks",
      "entry_states": [
        "other_public_direction"
      ],
      "last_attempt_index": null,
      "last_feedback": null,
      "attempts": 0,
      "inspected": false,
      "produced": false,
      "unconnected_entry": false,
      "confirmed_necessary": false,
      "public_recipe_support": false,
      "station": false,
      "container": false,
      "first_action": "enter barracks",
      "condition": "UNKNOWN",
      "estimated_actions": null,
      "estimate_is_not_native_cost_or_guaranteed_upper_bound": true,
      "menu_order": 3
    },
    {
      "candidate_id": "c_d6a4a748f3ca",
      "intent": [
        "craft_then_inspect",
        "stitched_panel"
      ],
      "target": "stitched_panel",
      "entry_states": [
        "public_necessary_node"
      ],
      "last_attempt_index": null,
      "last_feedback": null,
      "attempts": 0,
      "inspected": false,
      "produced": false,
      "unconnected_entry": false,
      "confirmed_necessary": true,
      "public_recipe_support": true,
      "station": false,
      "container": false,
      "first_action": "enter barracks",
      "condition": "UNKNOWN",
      "estimated_actions": null,
      "estimate_is_not_native_cost_or_guaranteed_upper_bound": true,
      "menu_order": 4
    },
    {
      "candidate_id": "c_8ecb614a6055",
      "intent": [
        "inspect",
        "salvage_cloth"
      ],
      "target": "salvage_cloth",
      "entry_states": [
        "inspected_with_public_information",
        "public_necessary_node"
      ],
      "last_attempt_index": 4,
      "last_feedback": "I inspected salvage_cloth: Tattered fabric pulled from ruined banners and bedrolls, still serviceable.\nIt can be used to craft: bandage_roll (made of salvage_cloth, sinew_cord), oil_bomb (made of oil_flask, charcoal_brick, salvage_cloth), scout_satchel (made of salvage_cloth, sinew_cord), war_parchment (made of salvage_cloth), sinew_cord (made of salvage_cloth), war_banner (made of salvage_cloth, wooden_rod), padded_lining (made of stitched_panel, salvage_cloth), scrap_helm (made of scrap_iron, salvage_cloth), ruin_gauntlets (made of rubble_chunk, war_strap, salvage_cloth), scrap_lantern (made of scrap_iron, devil_oil, salvage_cloth).\nIt has nothing written on it.",
      "attempts": 1,
      "inspected": true,
      "produced": false,
      "unconnected_entry": false,
      "confirmed_necessary": true,
      "public_recipe_support": false,
      "station": false,
      "container": false,
      "first_action": "inspect salvage_cloth",
      "condition": "UNKNOWN",
      "estimated_actions": 1,
      "estimate_is_not_native_cost_or_guaranteed_upper_bound": true,
      "menu_order": 5
    },
    {
      "candidate_id": "c_51d20e64a67f",
      "intent": [
        "craft_then_inspect",
        "sinew_cord"
      ],
      "target": "sinew_cord",
      "entry_states": [
        "inspected_with_public_information",
        "public_necessary_node"
      ],
      "last_attempt_index": 2,
      "last_feedback": "I inspected sinew_cord: Twisted cord braided from salvaged fibers and dried sinew, surprisingly tough.\nIt can be used to craft: stitched_panel (made of bandage_roll, sinew_cord), timber_sword (made of scorched_plank, wood_strip, sinew_cord), spiked_club (made of charred_timber, rubble_chunk, sinew_cord), war_strap (made of sinew_cord, bandage_roll), war_codex (made of field_journal, sinew_cord, fiend_strip), cog_crossbow (made of gearwork_frame, iron_bar, sinew_cord), ruin_spear (made of knapped_edge, wooden_rod, sinew_cord), hunter_gauntlets (made of iron_bar, war_strap, sinew_cord), fiend_scale_bundle (made of fiend_alloy_scale, sinew_cord), scale_bundle (made of iron_scale, sinew_cord), siege_crate (made of scorched_plank, iron_bar, sinew_cord), fiend_gauntlets (made of fiend_alloy, war_strap, sinew_cord), bandage_roll (made of salvage_cloth, sinew_cord), padded_tunic (made of padded_lining, sinew_cord), scrap_buckler (made of scrap_iron, sinew_cord), repair_kit (made of scrap_iron, sinew_cord, oil_flask), scout_satchel (made of salvage_cloth, sinew_cord), warding_charm (made of demon_core_shard, sinew_cord, hellcoal_concentrate), field_journal (made of war_parchment, sinew_cord), chain_net (made of iron_bar, sinew_cord).\nIt has nothing written on it.",
      "attempts": 1,
      "inspected": true,
      "produced": false,
      "unconnected_entry": false,
      "confirmed_necessary": true,
      "public_recipe_support": true,
      "station": false,
      "container": false,
      "first_action": "store 2 salvage_cloth inventory",
      "condition": "UNKNOWN",
      "estimated_actions": null,
      "estimate_is_not_native_cost_or_guaranteed_upper_bound": true,
      "menu_order": 6
    },
    {
      "candidate_id": "c_3f33cf002d85",
      "intent": [
        "inspect",
        "war_bench"
      ],
      "target": "war_bench",
      "entry_states": [
        "other_public_direction"
      ],
      "last_attempt_index": null,
      "last_feedback": null,
      "attempts": 0,
      "inspected": false,
      "produced": false,
      "unconnected_entry": false,
      "confirmed_necessary": false,
      "public_recipe_support": false,
      "station": true,
      "container": false,
      "first_action": "enter courtyard",
      "condition": "UNKNOWN",
      "estimated_actions": 2,
      "estimate_is_not_native_cost_or_guaranteed_upper_bound": true,
      "menu_order": 7
    },
    {
      "candidate_id": "c_a31e0c0dfecd",
      "intent": [
        "craft_then_inspect",
        "bandage_roll"
      ],
      "target": "bandage_roll",
      "entry_states": [
        "inspected_with_public_information",
        "public_necessary_node"
      ],
      "last_attempt_index": 1,
      "last_feedback": "I inspected bandage_roll: A rolled bolt of salvage cloth prepared for binding wounds or crafting gear.\nIt can be used to craft: stitched_panel (made of bandage_roll, sinew_cord), ruin_maul (made of ruin_blade, wooden_rod, bandage_roll), war_strap (made of sinew_cord, bandage_roll).\nIt has nothing written on it.",
      "attempts": 1,
      "inspected": true,
      "produced": false,
      "unconnected_entry": false,
      "confirmed_necessary": true,
      "public_recipe_support": true,
      "station": false,
      "container": false,
      "first_action": "store 2 salvage_cloth inventory",
      "condition": "UNKNOWN",
      "estimated_actions": null,
      "estimate_is_not_native_cost_or_guaranteed_upper_bound": true,
      "menu_order": 8
    }
  ],
  "public_input_digest": "76f265e9e8e0771c31f896ed3f42419c6e3b3c341da2cedc3856bf785dba5cd4",
  "single_supplement_max_actions": 4
}
```

## 历史进展依据

仅用当前决策之前的实际执行行；没有未来反馈。完整前后观察见公开输入文件。


|行号|执行动作|公开新配方|持有量增加/制作/新地点|进展|未关联入口检查|
|---|---|---|---|---|---|
|0|inspect padded_tunic||False/False/False|False|False|
|1|inspect bandage_roll|ruin_maul,stitched_panel,war_strap|False/False/False|True|True|
|2|inspect sinew_cord|bandage_roll,chain_net,cog_crossbow,field_journal,fiend_gauntlets,fiend_scale_bundle,hunter_gauntlets,padded_tunic,repair_kit,ruin_spear,scale_bundle,scout_satchel,scrap_buckler,siege_crate,spiked_club,timber_sword,war_codex,warding_charm|False/False/False|True|True|
|3|enter cellar||False/False/False|False|False|
|4|inspect salvage_cloth|oil_bomb,padded_lining,ruin_gauntlets,scrap_helm,scrap_lantern,sinew_cord,war_banner,war_parchment|False/False/False|True|True|

## 完整候选及公开依据

```json
[
  {
    "kind": "craft",
    "target": "scout_satchel",
    "category": "known_craft",
    "ingredients": [
      "salvage_cloth",
      "sinew_cord"
    ],
    "stations": "UNKNOWN",
    "evidence": "observed recipe and potentially accessible inputs; downstream connection may be unknown",
    "id": "c_973aea1af0e4",
    "confirmed_connection": false,
    "next_action": "store 2 salvage_cloth inventory",
    "public_condition": "UNKNOWN"
  },
  {
    "kind": "craft",
    "target": "war_parchment",
    "category": "known_craft",
    "ingredients": [
      "salvage_cloth"
    ],
    "stations": "UNKNOWN",
    "evidence": "observed recipe and potentially accessible inputs; downstream connection may be unknown",
    "id": "c_334ffca58064",
    "confirmed_connection": false,
    "next_action": "store 2 salvage_cloth inventory",
    "public_condition": "UNKNOWN"
  },
  {
    "kind": "craft",
    "target": "war_strap",
    "category": "known_craft",
    "ingredients": [
      "sinew_cord",
      "bandage_roll"
    ],
    "stations": "UNKNOWN",
    "evidence": "observed recipe and potentially accessible inputs; downstream connection may be unknown",
    "id": "c_3005d7648aa4",
    "confirmed_connection": false,
    "next_action": "enter barracks",
    "public_condition": "UNKNOWN"
  },
  {
    "kind": "primitive",
    "target": "barracks",
    "category": "primitive",
    "evidence": "public method proposal; exact first action retained",
    "first_action": "enter barracks",
    "id": "c_f4bbfd0ebbe8",
    "confirmed_connection": false,
    "next_action": "enter barracks",
    "public_condition": "UNKNOWN"
  },
  {
    "kind": "craft",
    "target": "stitched_panel",
    "category": "known_craft",
    "ingredients": [
      "bandage_roll",
      "sinew_cord"
    ],
    "stations": "UNKNOWN",
    "evidence": "observed recipe and potentially accessible inputs; downstream connection may be unknown",
    "id": "c_d6a4a748f3ca",
    "confirmed_connection": true,
    "next_action": "enter barracks",
    "public_condition": "UNKNOWN"
  },
  {
    "kind": "inspect",
    "target": "salvage_cloth",
    "category": "other_inspect",
    "evidence": "visible unresolved public prerequisite; repeat",
    "id": "c_8ecb614a6055",
    "confirmed_connection": true,
    "next_action": "inspect salvage_cloth",
    "public_condition": "UNKNOWN"
  },
  {
    "kind": "craft",
    "target": "sinew_cord",
    "category": "known_craft",
    "ingredients": [
      "salvage_cloth"
    ],
    "stations": "UNKNOWN",
    "evidence": "observed recipe and potentially accessible inputs; downstream connection may be unknown",
    "id": "c_51d20e64a67f",
    "confirmed_connection": true,
    "next_action": "store 2 salvage_cloth inventory",
    "public_condition": "UNKNOWN"
  },
  {
    "kind": "visit",
    "target": "war_bench",
    "category": "known_location",
    "location": "courtyard",
    "evidence": "historically seen object; current presence requires reconfirmation",
    "id": "c_3f33cf002d85",
    "confirmed_connection": false,
    "next_action": "enter courtyard",
    "public_condition": "UNKNOWN"
  },
  {
    "kind": "craft",
    "target": "bandage_roll",
    "category": "known_craft",
    "ingredients": [
      "salvage_cloth",
      "sinew_cord"
    ],
    "stations": "UNKNOWN",
    "evidence": "observed recipe and potentially accessible inputs; downstream connection may be unknown",
    "id": "c_a31e0c0dfecd",
    "confirmed_connection": true,
    "next_action": "store 2 salvage_cloth inventory",
    "public_condition": "UNKNOWN"
  }
]
```

## J0 与 J3 配对及去重排名

```json
{
  "state_id": "d12_dc6e7aaa56e84ae2",
  "family": "padded_tunic",
  "pair_class": "both_no_necessary_information",
  "same_exploration_intent": false,
  "J0": {
    "actions": 1,
    "new_key_recipes": [],
    "useful": false,
    "one_step_useful": false,
    "rejections": 0,
    "unrelated_craft": false,
    "unrelated_key_input_consumption": false,
    "environment_key_loss": false,
    "goal": false,
    "stop": "public_plan_complete_or_blocked",
    "candidate_id": "c_f4bbfd0ebbe8",
    "intent": [
      "primitive",
      "enter barracks"
    ],
    "actions_trace": [
      "enter barracks"
    ],
    "feedback_trace": [
      "I entered barracks."
    ],
    "native_new_necessary_rule_count": 0,
    "preparation_actions_until_first_necessary_recipe": null,
    "craft_actions": 0,
    "inspect_actions": 0,
    "consumption": {},
    "production": {},
    "environment_loss_quantities": {},
    "unrelated_key_consumption_quantities": {},
    "repeated_inspect_without_new_public_recipe": 0,
    "craft_without_output_or_new_recipe": 0,
    "public_known_necessary_executions": [],
    "raw_entry_useful": false,
    "native_trace_digest": "f419d8b6b8041481315722a048434f89a29c45603933326236efecd808e43ea3"
  },
  "J3": {
    "actions": 2,
    "new_key_recipes": [],
    "useful": false,
    "one_step_useful": false,
    "rejections": 0,
    "unrelated_craft": false,
    "unrelated_key_input_consumption": false,
    "environment_key_loss": false,
    "goal": false,
    "stop": "inspection_attempt_completed",
    "candidate_id": "c_3f33cf002d85",
    "intent": [
      "inspect",
      "war_bench"
    ],
    "actions_trace": [
      "enter courtyard",
      "inspect war_bench"
    ],
    "feedback_trace": [
      "I entered courtyard.",
      "I inspected war_bench: A reinforced workbench built by allied smiths for field assembly of anti-machine weapons.\nIt can be used to craft: None.\nIt has nothing written on it."
    ],
    "native_new_necessary_rule_count": 0,
    "preparation_actions_until_first_necessary_recipe": null,
    "craft_actions": 0,
    "inspect_actions": 1,
    "consumption": {},
    "production": {},
    "environment_loss_quantities": {},
    "unrelated_key_consumption_quantities": {},
    "repeated_inspect_without_new_public_recipe": 0,
    "craft_without_output_or_new_recipe": 0,
    "public_known_necessary_executions": [],
    "raw_entry_useful": false,
    "native_trace_digest": "b0909788cd3e9605ae18e750ebb7c28e039f47f5505791bec80ed7e4a950cd2b"
  },
  "J3_raw_judgment": {
    "type": "json_object",
    "selected_candidate_id": "c_3f33cf002d85",
    "ranked_candidate_ids": [
      "c_3f33cf002d85",
      "c_d6a4a748f3ca",
      "c_51d20e64a67f"
    ],
    "reason": "padded_tunic needs war_bench; previous craft failed only due to missing station. Reconfirm war_bench in courtyard.",
    "hypothesized_connection": "war_bench in courtyard enables crafting padded_tunic from padded_lining and sinew_cord.",
    "confidence": 0.6,
    "expected_information": "Whether war_bench currently exists in courtyard, enabling final craft.",
    "alternative_if_failed": "c_d6a4a748f3ca"
  },
  "public_features": {
    "incomplete_public_dependencies": false,
    "unknown_goal_recipe": false,
    "public_necessary_knowledge_drought": 0,
    "no_public_progress_streak": 0,
    "same_known_component_last3": false,
    "recent_unconnected_inspection_last4": true,
    "uninspected_independent_entry_intents": 0,
    "fresh_uninspected_product": false,
    "j3_previously_attempted": false,
    "j3_repeat_inspection_or_station": true,
    "j3_public_recipe_support": false,
    "j3_estimated_actions": 2,
    "s1_estimated_actions": null,
    "s1_public_execution_protected": false,
    "C1_trigger": false,
    "C2_trigger": false,
    "L_trigger": false,
    "remaining_actions": 35
  },
  "J3_top3_original_ids": [
    "c_3f33cf002d85",
    "c_d6a4a748f3ca",
    "c_51d20e64a67f"
  ],
  "J3_distinct_ranked_ids": [
    "c_3f33cf002d85",
    "c_d6a4a748f3ca",
    "c_51d20e64a67f"
  ],
  "removed_alias_ids": [],
  "alias_groups": [],
  "distinct_top3_useful": false,
  "distinct_top2_useful": false,
  "effective_lower_rank_ids": [],
  "no_effective_direction_in_returned_distinct_ranks": false,
  "candidate_pool_has_opportunity": false,
  "new_connection_direction_relative_to_S1": true,
  "new_connection_useful_native_supported": false,
  "public_evidence_class": "disclosed_recipe_or_dependency_direction",
  "co_mentioned_public_recipe_edges": [
    {
      "product": "padded_tunic",
      "ingredient": "padded_lining"
    },
    {
      "product": "padded_tunic",
      "ingredient": "sinew_cord"
    }
  ],
  "co_mention_is_not_entailment_or_proof_of_reasoning": true,
  "mentioned_public_goal_station_requirements": [
    "war_bench"
  ],
  "unconnected_recipe_names_mentioned": [],
  "name_association_causality": "not identifiable from generated explanation alone; hypothesized downstream links remain hypotheses",
  "raw_entry_selected": false,
  "raw_entry_effective_top3": [],
  "actual_native_costs_diagnostic_only": {
    "J0": 1,
    "J3": 2,
    "difference": 1
  }
}
```

## 主窗口全部原生分支

含原菜单及 Stage12 的自由提案补充分支；没有删除失败。new_key_recipes 是截至该步的累计新增集合，不能跨步相加。goal 仅为本短分支末局部持有目标，绝不表示本轮完成正式长程闭环。

### c_973aea1af0e4

```json
{
  "actions": 4,
  "new_key_recipes": [],
  "useful": false,
  "one_step_useful": false,
  "rejections": 1,
  "unrelated_craft": false,
  "unrelated_key_input_consumption": false,
  "environment_key_loss": false,
  "goal": false,
  "stop": "action_limit",
  "candidate_id": "c_973aea1af0e4",
  "intent": [
    "craft_then_inspect",
    "scout_satchel"
  ],
  "actions_trace": [
    "store 2 salvage_cloth inventory",
    "enter barracks",
    "store 1 sinew_cord inventory",
    "craft 2 scout_satchel"
  ],
  "feedback_trace": [
    "I stored 2 salvage_cloth in my inventory.\njames_owen enters the area.\n\nSide quest completed: collect 1 salvage_cloth\nYou earned 1 coins!\nTalk to james_owen to see your updated tasks.\nI have acquired a new item: salvage_cloth. It can be used to craft: bandage_roll (1 salvage_cloth, 2 sinew_cord), oil_bomb (1 oil_flask, 1 charcoal_brick, 1 salvage_cloth), scout_satchel (3 salvage_cloth, 1 sinew_cord), war_parchment (0.25 salvage_cloth), sinew_cord (0.5 salvage_cloth), war_banner (2 salvage_cloth, 1 wooden_rod), padded_lining (1 stitched_panel, 1 salvage_cloth), scrap_helm (2 scrap_iron, 1 salvage_cloth), ruin_gauntlets (2 rubble_chunk, 2 war_strap, 1 salvage_cloth), scrap_lantern (1 scrap_iron, 1 devil_oil, 1 salvage_cloth)",
    "I entered barracks.",
    "I stored 1 sinew_cord in my inventory.\nI have acquired a new item: sinew_cord. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), timber_sword (1 scorched_plank, 1 wood_strip, 1 sinew_cord), spiked_club (2 charred_timber, 2 rubble_chunk, 1 sinew_cord), war_strap (1 sinew_cord, 0.25 bandage_roll), war_codex (2 field_journal, 2 sinew_cord, 1 fiend_strip), cog_crossbow (1 gearwork_frame, 2 iron_bar, 3 sinew_cord), ruin_spear (1 knapped_edge, 1 wooden_rod, 1 sinew_cord), hunter_gauntlets (1 iron_bar, 1 war_strap, 1 sinew_cord), fiend_scale_bundle (6 fiend_alloy_scale, 3 sinew_cord), scale_bundle (6 iron_scale, 2 sinew_cord), siege_crate (4 scorched_plank, 2 iron_bar, 2 sinew_cord), fiend_gauntlets (1 fiend_alloy, 1 war_strap, 2 sinew_cord), bandage_roll (1 salvage_cloth, 2 sinew_cord), padded_tunic (1 padded_lining, 1 sinew_cord), scrap_buckler (2 scrap_iron, 1 sinew_cord), repair_kit (2 scrap_iron, 2 sinew_cord, 1 oil_flask), scout_satchel (3 salvage_cloth, 1 sinew_cord), warding_charm (1 demon_core_shard, 3 sinew_cord, 1 hellcoal_concentrate), field_journal (5 war_parchment, 1 sinew_cord), chain_net (3 iron_bar, 2 sinew_cord)",
    "Cannot craft scout_satchel. Missing necessary war_bench in the current area."
  ],
  "native_new_necessary_rule_count": 0,
  "preparation_actions_until_first_necessary_recipe": null,
  "craft_actions": 1,
  "inspect_actions": 0,
  "consumption": {},
  "production": {},
  "environment_loss_quantities": {},
  "unrelated_key_consumption_quantities": {},
  "repeated_inspect_without_new_public_recipe": 0,
  "craft_without_output_or_new_recipe": 1,
  "public_known_necessary_executions": [
    "store 2 salvage_cloth inventory",
    "store 1 sinew_cord inventory"
  ],
  "raw_entry_useful": false,
  "native_trace_digest": "f32c43c7b614aa891135ad13853c949e2c3afd08533de9e35e7aa76bd0fef190"
}
```

第 1 步：`store 2 salvage_cloth inventory`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I stored 2 salvage_cloth in my inventory.
james_owen enters the area.

Side quest completed: collect 1 salvage_cloth
You earned 1 coins!
Talk to james_owen to see your updated tasks.
I have acquired a new item: salvage_cloth. It can be used to craft: bandage_roll (1 salvage_cloth, 2 sinew_cord), oil_bomb (1 oil_flask, 1 charcoal_brick, 1 salvage_cloth), scout_satchel (3 salvage_cloth, 1 sinew_cord), war_parchment (0.25 salvage_cloth), sinew_cord (0.5 salvage_cloth), war_banner (2 salvage_cloth, 1 wooden_rod), padded_lining (1 stitched_panel, 1 salvage_cloth), scrap_helm (2 scrap_iron, 1 salvage_cloth), ruin_gauntlets (2 rubble_chunk, 2 war_strap, 1 salvage_cloth), scrap_lantern (1 scrap_iron, 1 devil_oil, 1 salvage_cloth)
```

第 2 步：`enter barracks`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I entered barracks.
```

第 3 步：`store 1 sinew_cord inventory`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I stored 1 sinew_cord in my inventory.
I have acquired a new item: sinew_cord. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), timber_sword (1 scorched_plank, 1 wood_strip, 1 sinew_cord), spiked_club (2 charred_timber, 2 rubble_chunk, 1 sinew_cord), war_strap (1 sinew_cord, 0.25 bandage_roll), war_codex (2 field_journal, 2 sinew_cord, 1 fiend_strip), cog_crossbow (1 gearwork_frame, 2 iron_bar, 3 sinew_cord), ruin_spear (1 knapped_edge, 1 wooden_rod, 1 sinew_cord), hunter_gauntlets (1 iron_bar, 1 war_strap, 1 sinew_cord), fiend_scale_bundle (6 fiend_alloy_scale, 3 sinew_cord), scale_bundle (6 iron_scale, 2 sinew_cord), siege_crate (4 scorched_plank, 2 iron_bar, 2 sinew_cord), fiend_gauntlets (1 fiend_alloy, 1 war_strap, 2 sinew_cord), bandage_roll (1 salvage_cloth, 2 sinew_cord), padded_tunic (1 padded_lining, 1 sinew_cord), scrap_buckler (2 scrap_iron, 1 sinew_cord), repair_kit (2 scrap_iron, 2 sinew_cord, 1 oil_flask), scout_satchel (3 salvage_cloth, 1 sinew_cord), warding_charm (1 demon_core_shard, 3 sinew_cord, 1 hellcoal_concentrate), field_journal (5 war_parchment, 1 sinew_cord), chain_net (3 iron_bar, 2 sinew_cord)
```

第 4 步：`craft 2 scout_satchel`；拒绝=True；累计必要配方=[]；消耗={}；环境损失={}。

```text
Cannot craft scout_satchel. Missing necessary war_bench in the current area.
```
### c_334ffca58064

```json
{
  "actions": 2,
  "new_key_recipes": [],
  "useful": false,
  "one_step_useful": false,
  "rejections": 1,
  "unrelated_craft": false,
  "unrelated_key_input_consumption": false,
  "environment_key_loss": false,
  "goal": false,
  "stop": "public_plan_complete_or_blocked",
  "candidate_id": "c_334ffca58064",
  "intent": [
    "craft_then_inspect",
    "war_parchment"
  ],
  "actions_trace": [
    "store 2 salvage_cloth inventory",
    "craft 2 war_parchment"
  ],
  "feedback_trace": [
    "I stored 2 salvage_cloth in my inventory.\njames_owen enters the area.\n\nSide quest completed: collect 1 salvage_cloth\nYou earned 1 coins!\nTalk to james_owen to see your updated tasks.\nI have acquired a new item: salvage_cloth. It can be used to craft: bandage_roll (1 salvage_cloth, 2 sinew_cord), oil_bomb (1 oil_flask, 1 charcoal_brick, 1 salvage_cloth), scout_satchel (3 salvage_cloth, 1 sinew_cord), war_parchment (0.25 salvage_cloth), sinew_cord (0.5 salvage_cloth), war_banner (2 salvage_cloth, 1 wooden_rod), padded_lining (1 stitched_panel, 1 salvage_cloth), scrap_helm (2 scrap_iron, 1 salvage_cloth), ruin_gauntlets (2 rubble_chunk, 2 war_strap, 1 salvage_cloth), scrap_lantern (1 scrap_iron, 1 devil_oil, 1 salvage_cloth)",
    "Cannot craft a single war_parchment. Do not have sufficient amount of necessary ingredients."
  ],
  "native_new_necessary_rule_count": 0,
  "preparation_actions_until_first_necessary_recipe": null,
  "craft_actions": 1,
  "inspect_actions": 0,
  "consumption": {},
  "production": {},
  "environment_loss_quantities": {},
  "unrelated_key_consumption_quantities": {},
  "repeated_inspect_without_new_public_recipe": 0,
  "craft_without_output_or_new_recipe": 1,
  "public_known_necessary_executions": [
    "store 2 salvage_cloth inventory"
  ],
  "raw_entry_useful": false,
  "native_trace_digest": "ce679b8e499279cb3bea35bbcc37277b112eb66e92ec898717e964a27d84c503"
}
```

第 1 步：`store 2 salvage_cloth inventory`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I stored 2 salvage_cloth in my inventory.
james_owen enters the area.

Side quest completed: collect 1 salvage_cloth
You earned 1 coins!
Talk to james_owen to see your updated tasks.
I have acquired a new item: salvage_cloth. It can be used to craft: bandage_roll (1 salvage_cloth, 2 sinew_cord), oil_bomb (1 oil_flask, 1 charcoal_brick, 1 salvage_cloth), scout_satchel (3 salvage_cloth, 1 sinew_cord), war_parchment (0.25 salvage_cloth), sinew_cord (0.5 salvage_cloth), war_banner (2 salvage_cloth, 1 wooden_rod), padded_lining (1 stitched_panel, 1 salvage_cloth), scrap_helm (2 scrap_iron, 1 salvage_cloth), ruin_gauntlets (2 rubble_chunk, 2 war_strap, 1 salvage_cloth), scrap_lantern (1 scrap_iron, 1 devil_oil, 1 salvage_cloth)
```

第 2 步：`craft 2 war_parchment`；拒绝=True；累计必要配方=[]；消耗={}；环境损失={}。

```text
Cannot craft a single war_parchment. Do not have sufficient amount of necessary ingredients.
```
### c_3005d7648aa4

```json
{
  "actions": 4,
  "new_key_recipes": [],
  "useful": false,
  "one_step_useful": false,
  "rejections": 1,
  "unrelated_craft": false,
  "unrelated_key_input_consumption": false,
  "environment_key_loss": false,
  "goal": false,
  "stop": "action_limit",
  "candidate_id": "c_3005d7648aa4",
  "intent": [
    "craft_then_inspect",
    "war_strap"
  ],
  "actions_trace": [
    "enter barracks",
    "store 1 sinew_cord inventory",
    "store 1 bandage_roll inventory",
    "craft 2 war_strap"
  ],
  "feedback_trace": [
    "I entered barracks.",
    "I stored 1 sinew_cord in my inventory.\nI have acquired a new item: sinew_cord. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), timber_sword (1 scorched_plank, 1 wood_strip, 1 sinew_cord), spiked_club (2 charred_timber, 2 rubble_chunk, 1 sinew_cord), war_strap (1 sinew_cord, 0.25 bandage_roll), war_codex (2 field_journal, 2 sinew_cord, 1 fiend_strip), cog_crossbow (1 gearwork_frame, 2 iron_bar, 3 sinew_cord), ruin_spear (1 knapped_edge, 1 wooden_rod, 1 sinew_cord), hunter_gauntlets (1 iron_bar, 1 war_strap, 1 sinew_cord), fiend_scale_bundle (6 fiend_alloy_scale, 3 sinew_cord), scale_bundle (6 iron_scale, 2 sinew_cord), siege_crate (4 scorched_plank, 2 iron_bar, 2 sinew_cord), fiend_gauntlets (1 fiend_alloy, 1 war_strap, 2 sinew_cord), bandage_roll (1 salvage_cloth, 2 sinew_cord), padded_tunic (1 padded_lining, 1 sinew_cord), scrap_buckler (2 scrap_iron, 1 sinew_cord), repair_kit (2 scrap_iron, 2 sinew_cord, 1 oil_flask), scout_satchel (3 salvage_cloth, 1 sinew_cord), warding_charm (1 demon_core_shard, 3 sinew_cord, 1 hellcoal_concentrate), field_journal (5 war_parchment, 1 sinew_cord), chain_net (3 iron_bar, 2 sinew_cord)",
    "I stored 1 bandage_roll in my inventory.\nI have acquired a new item: bandage_roll. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), ruin_maul (1 ruin_blade, 1 wooden_rod, 1 bandage_roll), war_strap (1 sinew_cord, 0.25 bandage_roll)",
    "Cannot craft war_strap. Missing necessary war_bench in the current area."
  ],
  "native_new_necessary_rule_count": 0,
  "preparation_actions_until_first_necessary_recipe": null,
  "craft_actions": 1,
  "inspect_actions": 0,
  "consumption": {},
  "production": {},
  "environment_loss_quantities": {},
  "unrelated_key_consumption_quantities": {},
  "repeated_inspect_without_new_public_recipe": 0,
  "craft_without_output_or_new_recipe": 1,
  "public_known_necessary_executions": [
    "store 1 sinew_cord inventory",
    "store 1 bandage_roll inventory"
  ],
  "raw_entry_useful": false,
  "native_trace_digest": "f0cbeca1dda97e6dce33bf13944c4edac9af2a77f47215b1eba89d8bc2abbe0b"
}
```

第 1 步：`enter barracks`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I entered barracks.
```

第 2 步：`store 1 sinew_cord inventory`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I stored 1 sinew_cord in my inventory.
I have acquired a new item: sinew_cord. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), timber_sword (1 scorched_plank, 1 wood_strip, 1 sinew_cord), spiked_club (2 charred_timber, 2 rubble_chunk, 1 sinew_cord), war_strap (1 sinew_cord, 0.25 bandage_roll), war_codex (2 field_journal, 2 sinew_cord, 1 fiend_strip), cog_crossbow (1 gearwork_frame, 2 iron_bar, 3 sinew_cord), ruin_spear (1 knapped_edge, 1 wooden_rod, 1 sinew_cord), hunter_gauntlets (1 iron_bar, 1 war_strap, 1 sinew_cord), fiend_scale_bundle (6 fiend_alloy_scale, 3 sinew_cord), scale_bundle (6 iron_scale, 2 sinew_cord), siege_crate (4 scorched_plank, 2 iron_bar, 2 sinew_cord), fiend_gauntlets (1 fiend_alloy, 1 war_strap, 2 sinew_cord), bandage_roll (1 salvage_cloth, 2 sinew_cord), padded_tunic (1 padded_lining, 1 sinew_cord), scrap_buckler (2 scrap_iron, 1 sinew_cord), repair_kit (2 scrap_iron, 2 sinew_cord, 1 oil_flask), scout_satchel (3 salvage_cloth, 1 sinew_cord), warding_charm (1 demon_core_shard, 3 sinew_cord, 1 hellcoal_concentrate), field_journal (5 war_parchment, 1 sinew_cord), chain_net (3 iron_bar, 2 sinew_cord)
```

第 3 步：`store 1 bandage_roll inventory`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I stored 1 bandage_roll in my inventory.
I have acquired a new item: bandage_roll. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), ruin_maul (1 ruin_blade, 1 wooden_rod, 1 bandage_roll), war_strap (1 sinew_cord, 0.25 bandage_roll)
```

第 4 步：`craft 2 war_strap`；拒绝=True；累计必要配方=[]；消耗={}；环境损失={}。

```text
Cannot craft war_strap. Missing necessary war_bench in the current area.
```
### c_f4bbfd0ebbe8

```json
{
  "actions": 1,
  "new_key_recipes": [],
  "useful": false,
  "one_step_useful": false,
  "rejections": 0,
  "unrelated_craft": false,
  "unrelated_key_input_consumption": false,
  "environment_key_loss": false,
  "goal": false,
  "stop": "public_plan_complete_or_blocked",
  "candidate_id": "c_f4bbfd0ebbe8",
  "intent": [
    "primitive",
    "enter barracks"
  ],
  "actions_trace": [
    "enter barracks"
  ],
  "feedback_trace": [
    "I entered barracks."
  ],
  "native_new_necessary_rule_count": 0,
  "preparation_actions_until_first_necessary_recipe": null,
  "craft_actions": 0,
  "inspect_actions": 0,
  "consumption": {},
  "production": {},
  "environment_loss_quantities": {},
  "unrelated_key_consumption_quantities": {},
  "repeated_inspect_without_new_public_recipe": 0,
  "craft_without_output_or_new_recipe": 0,
  "public_known_necessary_executions": [],
  "raw_entry_useful": false,
  "native_trace_digest": "f419d8b6b8041481315722a048434f89a29c45603933326236efecd808e43ea3"
}
```

第 1 步：`enter barracks`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I entered barracks.
```
### c_d6a4a748f3ca

```json
{
  "actions": 4,
  "new_key_recipes": [],
  "useful": false,
  "one_step_useful": false,
  "rejections": 1,
  "unrelated_craft": false,
  "unrelated_key_input_consumption": false,
  "environment_key_loss": false,
  "goal": false,
  "stop": "action_limit",
  "candidate_id": "c_d6a4a748f3ca",
  "intent": [
    "craft_then_inspect",
    "stitched_panel"
  ],
  "actions_trace": [
    "enter barracks",
    "store 1 bandage_roll inventory",
    "store 1 sinew_cord inventory",
    "craft 2 stitched_panel"
  ],
  "feedback_trace": [
    "I entered barracks.",
    "I stored 1 bandage_roll in my inventory.\nI have acquired a new item: bandage_roll. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), ruin_maul (1 ruin_blade, 1 wooden_rod, 1 bandage_roll), war_strap (1 sinew_cord, 0.25 bandage_roll)",
    "I stored 1 sinew_cord in my inventory.\nI have acquired a new item: sinew_cord. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), timber_sword (1 scorched_plank, 1 wood_strip, 1 sinew_cord), spiked_club (2 charred_timber, 2 rubble_chunk, 1 sinew_cord), war_strap (1 sinew_cord, 0.25 bandage_roll), war_codex (2 field_journal, 2 sinew_cord, 1 fiend_strip), cog_crossbow (1 gearwork_frame, 2 iron_bar, 3 sinew_cord), ruin_spear (1 knapped_edge, 1 wooden_rod, 1 sinew_cord), hunter_gauntlets (1 iron_bar, 1 war_strap, 1 sinew_cord), fiend_scale_bundle (6 fiend_alloy_scale, 3 sinew_cord), scale_bundle (6 iron_scale, 2 sinew_cord), siege_crate (4 scorched_plank, 2 iron_bar, 2 sinew_cord), fiend_gauntlets (1 fiend_alloy, 1 war_strap, 2 sinew_cord), bandage_roll (1 salvage_cloth, 2 sinew_cord), padded_tunic (1 padded_lining, 1 sinew_cord), scrap_buckler (2 scrap_iron, 1 sinew_cord), repair_kit (2 scrap_iron, 2 sinew_cord, 1 oil_flask), scout_satchel (3 salvage_cloth, 1 sinew_cord), warding_charm (1 demon_core_shard, 3 sinew_cord, 1 hellcoal_concentrate), field_journal (5 war_parchment, 1 sinew_cord), chain_net (3 iron_bar, 2 sinew_cord)",
    "Cannot craft stitched_panel. Missing necessary war_bench in the current area."
  ],
  "native_new_necessary_rule_count": 0,
  "preparation_actions_until_first_necessary_recipe": null,
  "craft_actions": 1,
  "inspect_actions": 0,
  "consumption": {},
  "production": {},
  "environment_loss_quantities": {},
  "unrelated_key_consumption_quantities": {},
  "repeated_inspect_without_new_public_recipe": 0,
  "craft_without_output_or_new_recipe": 1,
  "public_known_necessary_executions": [
    "store 1 bandage_roll inventory",
    "store 1 sinew_cord inventory"
  ],
  "raw_entry_useful": false,
  "native_trace_digest": "24db82791734fe8d51acf46d30976530201a0bf3768a6fe0b23e4fee808dcbdb"
}
```

第 1 步：`enter barracks`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I entered barracks.
```

第 2 步：`store 1 bandage_roll inventory`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I stored 1 bandage_roll in my inventory.
I have acquired a new item: bandage_roll. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), ruin_maul (1 ruin_blade, 1 wooden_rod, 1 bandage_roll), war_strap (1 sinew_cord, 0.25 bandage_roll)
```

第 3 步：`store 1 sinew_cord inventory`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I stored 1 sinew_cord in my inventory.
I have acquired a new item: sinew_cord. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), timber_sword (1 scorched_plank, 1 wood_strip, 1 sinew_cord), spiked_club (2 charred_timber, 2 rubble_chunk, 1 sinew_cord), war_strap (1 sinew_cord, 0.25 bandage_roll), war_codex (2 field_journal, 2 sinew_cord, 1 fiend_strip), cog_crossbow (1 gearwork_frame, 2 iron_bar, 3 sinew_cord), ruin_spear (1 knapped_edge, 1 wooden_rod, 1 sinew_cord), hunter_gauntlets (1 iron_bar, 1 war_strap, 1 sinew_cord), fiend_scale_bundle (6 fiend_alloy_scale, 3 sinew_cord), scale_bundle (6 iron_scale, 2 sinew_cord), siege_crate (4 scorched_plank, 2 iron_bar, 2 sinew_cord), fiend_gauntlets (1 fiend_alloy, 1 war_strap, 2 sinew_cord), bandage_roll (1 salvage_cloth, 2 sinew_cord), padded_tunic (1 padded_lining, 1 sinew_cord), scrap_buckler (2 scrap_iron, 1 sinew_cord), repair_kit (2 scrap_iron, 2 sinew_cord, 1 oil_flask), scout_satchel (3 salvage_cloth, 1 sinew_cord), warding_charm (1 demon_core_shard, 3 sinew_cord, 1 hellcoal_concentrate), field_journal (5 war_parchment, 1 sinew_cord), chain_net (3 iron_bar, 2 sinew_cord)
```

第 4 步：`craft 2 stitched_panel`；拒绝=True；累计必要配方=[]；消耗={}；环境损失={}。

```text
Cannot craft stitched_panel. Missing necessary war_bench in the current area.
```
### c_8ecb614a6055

```json
{
  "actions": 1,
  "new_key_recipes": [],
  "useful": false,
  "one_step_useful": false,
  "rejections": 0,
  "unrelated_craft": false,
  "unrelated_key_input_consumption": false,
  "environment_key_loss": false,
  "goal": false,
  "stop": "inspection_attempt_completed",
  "candidate_id": "c_8ecb614a6055",
  "intent": [
    "inspect",
    "salvage_cloth"
  ],
  "actions_trace": [
    "inspect salvage_cloth"
  ],
  "feedback_trace": [
    "I inspected salvage_cloth: Tattered fabric pulled from ruined banners and bedrolls, still serviceable.\nIt can be used to craft: bandage_roll (made of salvage_cloth, sinew_cord), oil_bomb (made of oil_flask, charcoal_brick, salvage_cloth), scout_satchel (made of salvage_cloth, sinew_cord), war_parchment (made of salvage_cloth), sinew_cord (made of salvage_cloth), war_banner (made of salvage_cloth, wooden_rod), padded_lining (made of stitched_panel, salvage_cloth), scrap_helm (made of scrap_iron, salvage_cloth), ruin_gauntlets (made of rubble_chunk, war_strap, salvage_cloth), scrap_lantern (made of scrap_iron, devil_oil, salvage_cloth).\nIt has nothing written on it."
  ],
  "native_new_necessary_rule_count": 0,
  "preparation_actions_until_first_necessary_recipe": null,
  "craft_actions": 0,
  "inspect_actions": 1,
  "consumption": {},
  "production": {},
  "environment_loss_quantities": {},
  "unrelated_key_consumption_quantities": {},
  "repeated_inspect_without_new_public_recipe": 1,
  "craft_without_output_or_new_recipe": 0,
  "public_known_necessary_executions": [],
  "raw_entry_useful": false,
  "native_trace_digest": "5284a7984990e2d1098519483de98abd0500990e46b66bc0baf4be2b275b22a5"
}
```

第 1 步：`inspect salvage_cloth`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I inspected salvage_cloth: Tattered fabric pulled from ruined banners and bedrolls, still serviceable.
It can be used to craft: bandage_roll (made of salvage_cloth, sinew_cord), oil_bomb (made of oil_flask, charcoal_brick, salvage_cloth), scout_satchel (made of salvage_cloth, sinew_cord), war_parchment (made of salvage_cloth), sinew_cord (made of salvage_cloth), war_banner (made of salvage_cloth, wooden_rod), padded_lining (made of stitched_panel, salvage_cloth), scrap_helm (made of scrap_iron, salvage_cloth), ruin_gauntlets (made of rubble_chunk, war_strap, salvage_cloth), scrap_lantern (made of scrap_iron, devil_oil, salvage_cloth).
It has nothing written on it.
```
### c_51d20e64a67f

```json
{
  "actions": 4,
  "new_key_recipes": [],
  "useful": false,
  "one_step_useful": false,
  "rejections": 1,
  "unrelated_craft": false,
  "unrelated_key_input_consumption": false,
  "environment_key_loss": false,
  "goal": false,
  "stop": "action_limit",
  "candidate_id": "c_51d20e64a67f",
  "intent": [
    "craft_then_inspect",
    "sinew_cord"
  ],
  "actions_trace": [
    "store 2 salvage_cloth inventory",
    "craft 2 sinew_cord",
    "enter courtyard",
    "craft 2 sinew_cord"
  ],
  "feedback_trace": [
    "I stored 2 salvage_cloth in my inventory.\njames_owen enters the area.\n\nSide quest completed: collect 1 salvage_cloth\nYou earned 1 coins!\nTalk to james_owen to see your updated tasks.\nI have acquired a new item: salvage_cloth. It can be used to craft: bandage_roll (1 salvage_cloth, 2 sinew_cord), oil_bomb (1 oil_flask, 1 charcoal_brick, 1 salvage_cloth), scout_satchel (3 salvage_cloth, 1 sinew_cord), war_parchment (0.25 salvage_cloth), sinew_cord (0.5 salvage_cloth), war_banner (2 salvage_cloth, 1 wooden_rod), padded_lining (1 stitched_panel, 1 salvage_cloth), scrap_helm (2 scrap_iron, 1 salvage_cloth), ruin_gauntlets (2 rubble_chunk, 2 war_strap, 1 salvage_cloth), scrap_lantern (1 scrap_iron, 1 devil_oil, 1 salvage_cloth)",
    "Cannot craft sinew_cord. Missing necessary war_bench in the current area.",
    "I entered courtyard.",
    "I successfully crafted 2 sinew_cord. It is now on the ground.\njames_owen enters the area.\n\nSide quest completed: craft a sinew_cord\nYou earned 3 coins!\nTalk to james_owen to see your updated tasks."
  ],
  "native_new_necessary_rule_count": 0,
  "preparation_actions_until_first_necessary_recipe": null,
  "craft_actions": 2,
  "inspect_actions": 0,
  "consumption": {
    "salvage_cloth": 1
  },
  "production": {
    "sinew_cord": 2
  },
  "environment_loss_quantities": {},
  "unrelated_key_consumption_quantities": {},
  "repeated_inspect_without_new_public_recipe": 0,
  "craft_without_output_or_new_recipe": 1,
  "public_known_necessary_executions": [
    "store 2 salvage_cloth inventory",
    "craft 2 sinew_cord"
  ],
  "raw_entry_useful": false,
  "native_trace_digest": "84cb65715a29eb4af1635281556ce5cdd7e05fca3f9ab84be2c10a4f859437a8"
}
```

第 1 步：`store 2 salvage_cloth inventory`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I stored 2 salvage_cloth in my inventory.
james_owen enters the area.

Side quest completed: collect 1 salvage_cloth
You earned 1 coins!
Talk to james_owen to see your updated tasks.
I have acquired a new item: salvage_cloth. It can be used to craft: bandage_roll (1 salvage_cloth, 2 sinew_cord), oil_bomb (1 oil_flask, 1 charcoal_brick, 1 salvage_cloth), scout_satchel (3 salvage_cloth, 1 sinew_cord), war_parchment (0.25 salvage_cloth), sinew_cord (0.5 salvage_cloth), war_banner (2 salvage_cloth, 1 wooden_rod), padded_lining (1 stitched_panel, 1 salvage_cloth), scrap_helm (2 scrap_iron, 1 salvage_cloth), ruin_gauntlets (2 rubble_chunk, 2 war_strap, 1 salvage_cloth), scrap_lantern (1 scrap_iron, 1 devil_oil, 1 salvage_cloth)
```

第 2 步：`craft 2 sinew_cord`；拒绝=True；累计必要配方=[]；消耗={}；环境损失={}。

```text
Cannot craft sinew_cord. Missing necessary war_bench in the current area.
```

第 3 步：`enter courtyard`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I entered courtyard.
```

第 4 步：`craft 2 sinew_cord`；拒绝=False；累计必要配方=[]；消耗={"salvage_cloth": 1}；环境损失={}。

```text
I successfully crafted 2 sinew_cord. It is now on the ground.
james_owen enters the area.

Side quest completed: craft a sinew_cord
You earned 3 coins!
Talk to james_owen to see your updated tasks.
```
### c_3f33cf002d85

```json
{
  "actions": 2,
  "new_key_recipes": [],
  "useful": false,
  "one_step_useful": false,
  "rejections": 0,
  "unrelated_craft": false,
  "unrelated_key_input_consumption": false,
  "environment_key_loss": false,
  "goal": false,
  "stop": "inspection_attempt_completed",
  "candidate_id": "c_3f33cf002d85",
  "intent": [
    "inspect",
    "war_bench"
  ],
  "actions_trace": [
    "enter courtyard",
    "inspect war_bench"
  ],
  "feedback_trace": [
    "I entered courtyard.",
    "I inspected war_bench: A reinforced workbench built by allied smiths for field assembly of anti-machine weapons.\nIt can be used to craft: None.\nIt has nothing written on it."
  ],
  "native_new_necessary_rule_count": 0,
  "preparation_actions_until_first_necessary_recipe": null,
  "craft_actions": 0,
  "inspect_actions": 1,
  "consumption": {},
  "production": {},
  "environment_loss_quantities": {},
  "unrelated_key_consumption_quantities": {},
  "repeated_inspect_without_new_public_recipe": 0,
  "craft_without_output_or_new_recipe": 0,
  "public_known_necessary_executions": [],
  "raw_entry_useful": false,
  "native_trace_digest": "b0909788cd3e9605ae18e750ebb7c28e039f47f5505791bec80ed7e4a950cd2b"
}
```

第 1 步：`enter courtyard`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I entered courtyard.
```

第 2 步：`inspect war_bench`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I inspected war_bench: A reinforced workbench built by allied smiths for field assembly of anti-machine weapons.
It can be used to craft: None.
It has nothing written on it.
```
### c_a31e0c0dfecd

```json
{
  "actions": 2,
  "new_key_recipes": [],
  "useful": false,
  "one_step_useful": false,
  "rejections": 0,
  "unrelated_craft": false,
  "unrelated_key_input_consumption": false,
  "environment_key_loss": false,
  "goal": false,
  "stop": "public_plan_complete_or_blocked",
  "candidate_id": "c_a31e0c0dfecd",
  "intent": [
    "craft_then_inspect",
    "bandage_roll"
  ],
  "actions_trace": [
    "store 2 salvage_cloth inventory",
    "enter barracks"
  ],
  "feedback_trace": [
    "I stored 2 salvage_cloth in my inventory.\njames_owen enters the area.\n\nSide quest completed: collect 1 salvage_cloth\nYou earned 1 coins!\nTalk to james_owen to see your updated tasks.\nI have acquired a new item: salvage_cloth. It can be used to craft: bandage_roll (1 salvage_cloth, 2 sinew_cord), oil_bomb (1 oil_flask, 1 charcoal_brick, 1 salvage_cloth), scout_satchel (3 salvage_cloth, 1 sinew_cord), war_parchment (0.25 salvage_cloth), sinew_cord (0.5 salvage_cloth), war_banner (2 salvage_cloth, 1 wooden_rod), padded_lining (1 stitched_panel, 1 salvage_cloth), scrap_helm (2 scrap_iron, 1 salvage_cloth), ruin_gauntlets (2 rubble_chunk, 2 war_strap, 1 salvage_cloth), scrap_lantern (1 scrap_iron, 1 devil_oil, 1 salvage_cloth)",
    "I entered barracks."
  ],
  "native_new_necessary_rule_count": 0,
  "preparation_actions_until_first_necessary_recipe": null,
  "craft_actions": 0,
  "inspect_actions": 0,
  "consumption": {},
  "production": {},
  "environment_loss_quantities": {},
  "unrelated_key_consumption_quantities": {},
  "repeated_inspect_without_new_public_recipe": 0,
  "craft_without_output_or_new_recipe": 0,
  "public_known_necessary_executions": [
    "store 2 salvage_cloth inventory"
  ],
  "raw_entry_useful": false,
  "native_trace_digest": "7abc353f0616ca819386881f2d06721e8c4726353dc33f0b49bcdbd5dd734835"
}
```

第 1 步：`store 2 salvage_cloth inventory`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I stored 2 salvage_cloth in my inventory.
james_owen enters the area.

Side quest completed: collect 1 salvage_cloth
You earned 1 coins!
Talk to james_owen to see your updated tasks.
I have acquired a new item: salvage_cloth. It can be used to craft: bandage_roll (1 salvage_cloth, 2 sinew_cord), oil_bomb (1 oil_flask, 1 charcoal_brick, 1 salvage_cloth), scout_satchel (3 salvage_cloth, 1 sinew_cord), war_parchment (0.25 salvage_cloth), sinew_cord (0.5 salvage_cloth), war_banner (2 salvage_cloth, 1 wooden_rod), padded_lining (1 stitched_panel, 1 salvage_cloth), scrap_helm (2 scrap_iron, 1 salvage_cloth), ruin_gauntlets (2 rubble_chunk, 2 war_strap, 1 salvage_cloth), scrap_lantern (1 scrap_iron, 1 devil_oil, 1 salvage_cloth)
```

第 2 步：`enter barracks`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I entered barracks.
```
### c_c53ac1f74f40

```json
{
  "actions": 1,
  "new_key_recipes": [],
  "useful": false,
  "one_step_useful": false,
  "rejections": 0,
  "unrelated_craft": false,
  "unrelated_key_input_consumption": false,
  "environment_key_loss": false,
  "goal": false,
  "stop": "public_plan_complete_or_blocked",
  "candidate_id": "c_c53ac1f74f40",
  "intent": [
    "primitive",
    "enter courtyard"
  ],
  "actions_trace": [
    "enter courtyard"
  ],
  "feedback_trace": [
    "I entered courtyard."
  ],
  "native_new_necessary_rule_count": 0,
  "preparation_actions_until_first_necessary_recipe": null,
  "craft_actions": 0,
  "inspect_actions": 0,
  "consumption": {},
  "production": {},
  "environment_loss_quantities": {},
  "unrelated_key_consumption_quantities": {},
  "repeated_inspect_without_new_public_recipe": 0,
  "craft_without_output_or_new_recipe": 0,
  "public_known_necessary_executions": [],
  "raw_entry_useful": false,
  "native_trace_digest": "12d606c36f5ac3cdbea713ab171906e831a696b217cdc0ca18e2e365304644c2"
}
```

第 1 步：`enter courtyard`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I entered courtyard.
```

## 本轮零 API 补充

[完整补充分支](../../../results/stage13/native_supplements.jsonl.gz)。base_proposal 仍为最多四步；truncation_sensitivity 为独立八步敏感性，前四步逐字段相同。

### truncation_sensitivity / c_973aea1af0e4

```json
{
  "actions": 7,
  "new_key_recipes": [],
  "useful": false,
  "one_step_useful": false,
  "rejections": 2,
  "unrelated_craft": false,
  "unrelated_key_input_consumption": false,
  "environment_key_loss": false,
  "goal": false,
  "stop": "public_plan_complete_or_blocked",
  "candidate_id": "c_973aea1af0e4",
  "intent": [
    "craft_then_inspect",
    "scout_satchel"
  ],
  "actions_trace": [
    "store 2 salvage_cloth inventory",
    "enter barracks",
    "store 1 sinew_cord inventory",
    "craft 2 scout_satchel",
    "enter cellar",
    "enter courtyard",
    "craft 2 scout_satchel"
  ],
  "feedback_trace": [
    "I stored 2 salvage_cloth in my inventory.\njames_owen enters the area.\n\nSide quest completed: collect 1 salvage_cloth\nYou earned 1 coins!\nTalk to james_owen to see your updated tasks.\nI have acquired a new item: salvage_cloth. It can be used to craft: bandage_roll (1 salvage_cloth, 2 sinew_cord), oil_bomb (1 oil_flask, 1 charcoal_brick, 1 salvage_cloth), scout_satchel (3 salvage_cloth, 1 sinew_cord), war_parchment (0.25 salvage_cloth), sinew_cord (0.5 salvage_cloth), war_banner (2 salvage_cloth, 1 wooden_rod), padded_lining (1 stitched_panel, 1 salvage_cloth), scrap_helm (2 scrap_iron, 1 salvage_cloth), ruin_gauntlets (2 rubble_chunk, 2 war_strap, 1 salvage_cloth), scrap_lantern (1 scrap_iron, 1 devil_oil, 1 salvage_cloth)",
    "I entered barracks.",
    "I stored 1 sinew_cord in my inventory.\nI have acquired a new item: sinew_cord. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), timber_sword (1 scorched_plank, 1 wood_strip, 1 sinew_cord), spiked_club (2 charred_timber, 2 rubble_chunk, 1 sinew_cord), war_strap (1 sinew_cord, 0.25 bandage_roll), war_codex (2 field_journal, 2 sinew_cord, 1 fiend_strip), cog_crossbow (1 gearwork_frame, 2 iron_bar, 3 sinew_cord), ruin_spear (1 knapped_edge, 1 wooden_rod, 1 sinew_cord), hunter_gauntlets (1 iron_bar, 1 war_strap, 1 sinew_cord), fiend_scale_bundle (6 fiend_alloy_scale, 3 sinew_cord), scale_bundle (6 iron_scale, 2 sinew_cord), siege_crate (4 scorched_plank, 2 iron_bar, 2 sinew_cord), fiend_gauntlets (1 fiend_alloy, 1 war_strap, 2 sinew_cord), bandage_roll (1 salvage_cloth, 2 sinew_cord), padded_tunic (1 padded_lining, 1 sinew_cord), scrap_buckler (2 scrap_iron, 1 sinew_cord), repair_kit (2 scrap_iron, 2 sinew_cord, 1 oil_flask), scout_satchel (3 salvage_cloth, 1 sinew_cord), warding_charm (1 demon_core_shard, 3 sinew_cord, 1 hellcoal_concentrate), field_journal (5 war_parchment, 1 sinew_cord), chain_net (3 iron_bar, 2 sinew_cord)",
    "Cannot craft scout_satchel. Missing necessary war_bench in the current area.",
    "I entered cellar.",
    "I entered courtyard.",
    "Cannot craft a single scout_satchel. Do not have sufficient amount of necessary ingredients."
  ],
  "native_new_necessary_rule_count": 0,
  "preparation_actions_until_first_necessary_recipe": null,
  "craft_actions": 2,
  "inspect_actions": 0,
  "consumption": {},
  "production": {},
  "environment_loss_quantities": {},
  "unrelated_key_consumption_quantities": {},
  "repeated_inspect_without_new_public_recipe": 0,
  "craft_without_output_or_new_recipe": 2,
  "public_known_necessary_executions": [
    "store 2 salvage_cloth inventory",
    "store 1 sinew_cord inventory"
  ],
  "raw_entry_useful": false,
  "native_trace_digest": "d1e6631007382c27dea79ea4c4a746da04ef4f88b3e43ea70f9cbb0970589496"
}
```
### truncation_sensitivity / c_3005d7648aa4

```json
{
  "actions": 8,
  "new_key_recipes": [],
  "useful": false,
  "one_step_useful": false,
  "rejections": 1,
  "unrelated_craft": true,
  "unrelated_key_input_consumption": true,
  "environment_key_loss": false,
  "goal": false,
  "stop": "inspection_attempt_completed",
  "candidate_id": "c_3005d7648aa4",
  "intent": [
    "craft_then_inspect",
    "war_strap"
  ],
  "actions_trace": [
    "enter barracks",
    "store 1 sinew_cord inventory",
    "store 1 bandage_roll inventory",
    "craft 2 war_strap",
    "enter cellar",
    "enter courtyard",
    "craft 2 war_strap",
    "inspect war_strap"
  ],
  "feedback_trace": [
    "I entered barracks.",
    "I stored 1 sinew_cord in my inventory.\nI have acquired a new item: sinew_cord. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), timber_sword (1 scorched_plank, 1 wood_strip, 1 sinew_cord), spiked_club (2 charred_timber, 2 rubble_chunk, 1 sinew_cord), war_strap (1 sinew_cord, 0.25 bandage_roll), war_codex (2 field_journal, 2 sinew_cord, 1 fiend_strip), cog_crossbow (1 gearwork_frame, 2 iron_bar, 3 sinew_cord), ruin_spear (1 knapped_edge, 1 wooden_rod, 1 sinew_cord), hunter_gauntlets (1 iron_bar, 1 war_strap, 1 sinew_cord), fiend_scale_bundle (6 fiend_alloy_scale, 3 sinew_cord), scale_bundle (6 iron_scale, 2 sinew_cord), siege_crate (4 scorched_plank, 2 iron_bar, 2 sinew_cord), fiend_gauntlets (1 fiend_alloy, 1 war_strap, 2 sinew_cord), bandage_roll (1 salvage_cloth, 2 sinew_cord), padded_tunic (1 padded_lining, 1 sinew_cord), scrap_buckler (2 scrap_iron, 1 sinew_cord), repair_kit (2 scrap_iron, 2 sinew_cord, 1 oil_flask), scout_satchel (3 salvage_cloth, 1 sinew_cord), warding_charm (1 demon_core_shard, 3 sinew_cord, 1 hellcoal_concentrate), field_journal (5 war_parchment, 1 sinew_cord), chain_net (3 iron_bar, 2 sinew_cord)",
    "I stored 1 bandage_roll in my inventory.\nI have acquired a new item: bandage_roll. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), ruin_maul (1 ruin_blade, 1 wooden_rod, 1 bandage_roll), war_strap (1 sinew_cord, 0.25 bandage_roll)",
    "Cannot craft war_strap. Missing necessary war_bench in the current area.",
    "I entered cellar.",
    "I entered courtyard.",
    "Only enough ingredients to craft 1 war_strap.\nI successfully crafted 1 war_strap. It is now on the ground.",
    "I inspected war_strap: A tough strap for securing armor plates and weapon grips.\nIt can be used to craft: timber_vest (made of timber_plate, wood_rivet, padded_lining, war_strap), fiend_cuirass (made of fiend_plate, fiend_rivet, padded_lining, war_strap), ruin_cuirass (made of ruin_plate, war_strap, padded_lining), demonhide_armor (made of fiend_scale_bundle, padded_lining, war_strap, war_engine_heart), timber_shield (made of timber_plate, wood_rivet, war_strap), fiend_halberd (made of fiend_alloy, iron_bar, wooden_rod, war_strap), fiend_shield (made of fiend_alloy_sheet, timber_plate, war_strap, fiend_rivet), hunter_shield (made of iron_sheet, timber_plate, war_strap), hunter_gauntlets (made of iron_bar, war_strap, sinew_cord), demonslayer (made of fiend_alloy, brimite_blade, war_engine_heart, war_strap), brimite_sword (made of brimite_blade, wooden_rod, war_strap), hunter_sword (made of honed_blade, wooden_rod, war_strap), iron_mace (made of iron_bar, wooden_rod, war_strap), war_pack (made of stitched_panel, war_strap, iron_bar), fiend_gauntlets (made of fiend_alloy, war_strap, sinew_cord), ruin_gauntlets (made of rubble_chunk, war_strap, salvage_cloth), hunter_scale (made of scale_bundle, padded_lining, war_strap), ruin_plate (made of ruin_slab, war_strap).\nIt has nothing written on it."
  ],
  "native_new_necessary_rule_count": 0,
  "preparation_actions_until_first_necessary_recipe": null,
  "craft_actions": 2,
  "inspect_actions": 1,
  "consumption": {
    "sinew_cord": 1,
    "bandage_roll": 1
  },
  "production": {
    "war_strap": 1
  },
  "environment_loss_quantities": {},
  "unrelated_key_consumption_quantities": {
    "sinew_cord": 1,
    "bandage_roll": 1
  },
  "repeated_inspect_without_new_public_recipe": 0,
  "craft_without_output_or_new_recipe": 1,
  "public_known_necessary_executions": [
    "store 1 sinew_cord inventory",
    "store 1 bandage_roll inventory"
  ],
  "raw_entry_useful": false,
  "native_trace_digest": "8068f739ebcdedea0283d25c7d64025b256bc9e314678064ff46fa008c81e4e1"
}
```
### truncation_sensitivity / c_d6a4a748f3ca

```json
{
  "actions": 8,
  "new_key_recipes": [],
  "useful": false,
  "one_step_useful": false,
  "rejections": 1,
  "unrelated_craft": false,
  "unrelated_key_input_consumption": false,
  "environment_key_loss": false,
  "goal": false,
  "stop": "inspection_attempt_completed",
  "candidate_id": "c_d6a4a748f3ca",
  "intent": [
    "craft_then_inspect",
    "stitched_panel"
  ],
  "actions_trace": [
    "enter barracks",
    "store 1 bandage_roll inventory",
    "store 1 sinew_cord inventory",
    "craft 2 stitched_panel",
    "enter cellar",
    "enter courtyard",
    "craft 2 stitched_panel",
    "inspect stitched_panel"
  ],
  "feedback_trace": [
    "I entered barracks.",
    "I stored 1 bandage_roll in my inventory.\nI have acquired a new item: bandage_roll. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), ruin_maul (1 ruin_blade, 1 wooden_rod, 1 bandage_roll), war_strap (1 sinew_cord, 0.25 bandage_roll)",
    "I stored 1 sinew_cord in my inventory.\nI have acquired a new item: sinew_cord. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), timber_sword (1 scorched_plank, 1 wood_strip, 1 sinew_cord), spiked_club (2 charred_timber, 2 rubble_chunk, 1 sinew_cord), war_strap (1 sinew_cord, 0.25 bandage_roll), war_codex (2 field_journal, 2 sinew_cord, 1 fiend_strip), cog_crossbow (1 gearwork_frame, 2 iron_bar, 3 sinew_cord), ruin_spear (1 knapped_edge, 1 wooden_rod, 1 sinew_cord), hunter_gauntlets (1 iron_bar, 1 war_strap, 1 sinew_cord), fiend_scale_bundle (6 fiend_alloy_scale, 3 sinew_cord), scale_bundle (6 iron_scale, 2 sinew_cord), siege_crate (4 scorched_plank, 2 iron_bar, 2 sinew_cord), fiend_gauntlets (1 fiend_alloy, 1 war_strap, 2 sinew_cord), bandage_roll (1 salvage_cloth, 2 sinew_cord), padded_tunic (1 padded_lining, 1 sinew_cord), scrap_buckler (2 scrap_iron, 1 sinew_cord), repair_kit (2 scrap_iron, 2 sinew_cord, 1 oil_flask), scout_satchel (3 salvage_cloth, 1 sinew_cord), warding_charm (1 demon_core_shard, 3 sinew_cord, 1 hellcoal_concentrate), field_journal (5 war_parchment, 1 sinew_cord), chain_net (3 iron_bar, 2 sinew_cord)",
    "Cannot craft stitched_panel. Missing necessary war_bench in the current area.",
    "I entered cellar.",
    "I entered courtyard.",
    "Only enough ingredients to craft 1 stitched_panel.\nI successfully crafted 1 stitched_panel. It is now on the ground.",
    "I inspected stitched_panel: A reinforced cloth panel stitched for field armor assembly.\nIt can be used to craft: war_pack (made of stitched_panel, war_strap, iron_bar), padded_lining (made of stitched_panel, salvage_cloth).\nIt has nothing written on it."
  ],
  "native_new_necessary_rule_count": 0,
  "preparation_actions_until_first_necessary_recipe": null,
  "craft_actions": 2,
  "inspect_actions": 1,
  "consumption": {
    "sinew_cord": 1,
    "bandage_roll": 1
  },
  "production": {
    "stitched_panel": 1
  },
  "environment_loss_quantities": {},
  "unrelated_key_consumption_quantities": {},
  "repeated_inspect_without_new_public_recipe": 0,
  "craft_without_output_or_new_recipe": 1,
  "public_known_necessary_executions": [
    "store 1 bandage_roll inventory",
    "store 1 sinew_cord inventory",
    "craft 2 stitched_panel"
  ],
  "raw_entry_useful": false,
  "native_trace_digest": "7c729be48be34b48a40f864f0de40e210599d5b9e00781663755bf43b4d945d6"
}
```
### truncation_sensitivity / c_51d20e64a67f

```json
{
  "actions": 4,
  "new_key_recipes": [],
  "useful": false,
  "one_step_useful": false,
  "rejections": 1,
  "unrelated_craft": false,
  "unrelated_key_input_consumption": false,
  "environment_key_loss": false,
  "goal": false,
  "stop": "public_plan_complete_or_blocked",
  "candidate_id": "c_51d20e64a67f",
  "intent": [
    "craft_then_inspect",
    "sinew_cord"
  ],
  "actions_trace": [
    "store 2 salvage_cloth inventory",
    "craft 2 sinew_cord",
    "enter courtyard",
    "craft 2 sinew_cord"
  ],
  "feedback_trace": [
    "I stored 2 salvage_cloth in my inventory.\njames_owen enters the area.\n\nSide quest completed: collect 1 salvage_cloth\nYou earned 1 coins!\nTalk to james_owen to see your updated tasks.\nI have acquired a new item: salvage_cloth. It can be used to craft: bandage_roll (1 salvage_cloth, 2 sinew_cord), oil_bomb (1 oil_flask, 1 charcoal_brick, 1 salvage_cloth), scout_satchel (3 salvage_cloth, 1 sinew_cord), war_parchment (0.25 salvage_cloth), sinew_cord (0.5 salvage_cloth), war_banner (2 salvage_cloth, 1 wooden_rod), padded_lining (1 stitched_panel, 1 salvage_cloth), scrap_helm (2 scrap_iron, 1 salvage_cloth), ruin_gauntlets (2 rubble_chunk, 2 war_strap, 1 salvage_cloth), scrap_lantern (1 scrap_iron, 1 devil_oil, 1 salvage_cloth)",
    "Cannot craft sinew_cord. Missing necessary war_bench in the current area.",
    "I entered courtyard.",
    "I successfully crafted 2 sinew_cord. It is now on the ground.\njames_owen enters the area.\n\nSide quest completed: craft a sinew_cord\nYou earned 3 coins!\nTalk to james_owen to see your updated tasks."
  ],
  "native_new_necessary_rule_count": 0,
  "preparation_actions_until_first_necessary_recipe": null,
  "craft_actions": 2,
  "inspect_actions": 0,
  "consumption": {
    "salvage_cloth": 1
  },
  "production": {
    "sinew_cord": 2
  },
  "environment_loss_quantities": {},
  "unrelated_key_consumption_quantities": {},
  "repeated_inspect_without_new_public_recipe": 0,
  "craft_without_output_or_new_recipe": 1,
  "public_known_necessary_executions": [
    "store 2 salvage_cloth inventory",
    "craft 2 sinew_cord"
  ],
  "raw_entry_useful": false,
  "native_trace_digest": "84cb65715a29eb4af1635281556ce5cdd7e05fca3f9ab84be2c10a4f859437a8"
}
```

## 公开文本新颖性独立审计

将原反馈中的带数量配方也计为公开信息；不修改策略、Stage12 或主分数。

```json
{
  "initial_public_text_necessary_recipes": [
    "padded_lining",
    "padded_tunic",
    "sinew_cord",
    "stitched_panel"
  ],
  "selected": {
    "C0": {
      "new_native_necessary_public_text_recipes": [],
      "useful": false,
      "stage12_parser_useful": false,
      "new_vs_initial_public_text": true
    },
    "C1": {
      "new_native_necessary_public_text_recipes": [],
      "useful": false,
      "stage12_parser_useful": false,
      "new_vs_initial_public_text": true
    },
    "C2": {
      "new_native_necessary_public_text_recipes": [],
      "useful": false,
      "stage12_parser_useful": false,
      "new_vs_initial_public_text": true
    },
    "C3": {
      "new_native_necessary_public_text_recipes": [],
      "useful": false,
      "stage12_parser_useful": false,
      "new_vs_initial_public_text": true
    },
    "L": {
      "new_native_necessary_public_text_recipes": [],
      "useful": false,
      "stage12_parser_useful": false,
      "new_vs_initial_public_text": true
    },
    "J3": {
      "new_native_necessary_public_text_recipes": [],
      "useful": false,
      "stage12_parser_useful": false,
      "new_vs_initial_public_text": true
    }
  }
}
```
