# 冻结状态 d12_db9cf8a8d4ddadac

目标：`craft 1 padded_tunic`。来源 Stage 10 / S1 / `sequence-f5bbe8ac06891a7d-S1-c3876e4fe87c`，零基行号 2，剩余 38 动作。

[原始冻结状态](../../../results/stage12/diagnostic/states.json)、[原始原生分支](../../../results/stage12/diagnostic/native_branches.jsonl.gz)、[本轮公开输入与历史](../../../results/stage13/public_inputs.json)。状态/候选 ID 精确对应这些文件；当前页所有引擎反馈均原样保存。

## 决策时公开证据

```json
{
  "objective": "Obtain at least 2 padded_tunic in your possession in total. You already hold one. The previous craft failed. Any valid route is allowed.",
  "target_action": "craft 1 padded_tunic",
  "current": {
    "location": "barracks",
    "hands": {
      "padded_tunic": 1.0
    },
    "ground": {
      "bandage_roll": 1.0,
      "sinew_cord": 1.0
    },
    "equipment": {
      "scout_satchel_0": 1.0
    },
    "neighbors": [
      "cellar"
    ]
  },
  "confirmed_recipe_relations": {
    "padded_tunic": {
      "ingredients": "UNKNOWN",
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
    }
  },
  "containers": {
    "scout_satchel_0": {
      "counts": {},
      "load": 0.0,
      "capacity": 20.0,
      "location": "barracks",
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
      "step": 12,
      "source": "public_ground_observation"
    },
    "cellar": {
      "objects": {
        "salvage_cloth": 2.0
      },
      "step": 8,
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
    "bandage_roll"
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
    }
  ],
  "unresolved_public_nodes": [
    "padded_tunic"
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
  "padded_tunic": {
    "lower_bound": 1.0,
    "exact": true
  },
  "ruin_blade": {
    "lower_bound": 0,
    "exact": true
  },
  "ruin_maul": {
    "lower_bound": 0,
    "exact": true
  },
  "scout_satchel_0": {
    "lower_bound": 1.0,
    "exact": true
  },
  "sinew_cord": {
    "lower_bound": 0,
    "exact": true
  },
  "stitched_panel": {
    "lower_bound": 0,
    "exact": true
  },
  "war_strap": {
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

Current Time: 0001-01-01 10:00:00
Current Location: Ashen Bastion, barracks

I inspected bandage_roll: A rolled bolt of salvage cloth prepared for binding wounds or crafting gear.
It can be used to craft: stitched_panel (made of bandage_roll, sinew_cord), ruin_maul (made of ruin_blade, wooden_rod, bandage_roll), war_strap (made of sinew_cord, bandage_roll).
It has nothing written on it.

I am holding 1 padded_tunic.
I have equipped 1 scout_satchel_0.
I see 1 bandage_roll, 1 sinew_cord near me.
I see no one nearby.

My level is 1.
My attack is at 10.
My defense is at 0.
My health is at 100.
My experience is at 10.

Neighboring areas: cellar.

```

已知地点可见或历史观察到、尚未检查的对象（历史存在需重确认）：

```json
[
  "salvage_cloth",
  "sinew_cord",
  "war_bench"
]
```

基础提案、FIFO 和实际 S1 选择：

```json
{
  "base_proposal": "enter courtyard",
  "FIFO": "inspect sinew_cord",
  "actual_S1": "inspect sinew_cord",
  "reason": "retain_F0",
  "mechanisms": {
    "exploration": {
      "reason": "unknown recipe/material link",
      "source": {
        "public_entity": "sinew_cord",
        "missing_nodes": [
          "padded_tunic"
        ]
      },
      "spent": 3,
      "limit": 18
    }
  },
  "queue": [
    "padded_tunic"
  ],
  "graph": {}
}
```

公开特征、覆盖选择、分层入口账本：

```json
{
  "state_id": "d12_db9cf8a8d4ddadac",
  "choices": {
    "C0": "c_9336e1422f2b",
    "C1": "c_9336e1422f2b",
    "C2": "c_9336e1422f2b",
    "C3": "c_9336e1422f2b",
    "L": "c_9336e1422f2b"
  },
  "features": {
    "incomplete_public_dependencies": true,
    "unknown_goal_recipe": true,
    "public_necessary_knowledge_drought": 2,
    "no_public_progress_streak": 0,
    "same_known_component_last3": false,
    "recent_unconnected_inspection_last4": true,
    "uninspected_independent_entry_intents": 2,
    "fresh_uninspected_product": false,
    "j3_previously_attempted": false,
    "j3_repeat_inspection_or_station": true,
    "j3_public_recipe_support": false,
    "j3_estimated_actions": 3,
    "s1_estimated_actions": 1,
    "s1_public_execution_protected": false,
    "C1_trigger": false,
    "C2_trigger": false,
    "L_trigger": false,
    "remaining_actions": 38
  },
  "entry_ledger": [
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
      "first_action": "store 1 sinew_cord inventory",
      "condition": "UNKNOWN",
      "estimated_actions": null,
      "estimate_is_not_native_cost_or_guaranteed_upper_bound": true,
      "menu_order": 0
    },
    {
      "candidate_id": "c_e02a00b1c3e8",
      "intent": [
        "inspect",
        "salvage_cloth"
      ],
      "target": "salvage_cloth",
      "entry_states": [
        "unconnected_uninspected_entry"
      ],
      "last_attempt_index": null,
      "last_feedback": null,
      "attempts": 0,
      "inspected": false,
      "produced": false,
      "unconnected_entry": true,
      "confirmed_necessary": false,
      "public_recipe_support": false,
      "station": false,
      "container": false,
      "first_action": "enter cellar",
      "condition": "UNKNOWN",
      "estimated_actions": 2,
      "estimate_is_not_native_cost_or_guaranteed_upper_bound": true,
      "menu_order": 1
    },
    {
      "candidate_id": "c_0450ed6211e2",
      "intent": [
        "inspect",
        "padded_tunic"
      ],
      "target": "padded_tunic",
      "entry_states": [
        "inspected_no_new_public_recipe",
        "public_necessary_node"
      ],
      "last_attempt_index": 0,
      "last_feedback": "I inspected padded_tunic: A padded tunic that absorbs the shock of machine strikes.\nIt can be used to craft: None.\nIt has nothing written on it.",
      "attempts": 1,
      "inspected": true,
      "produced": false,
      "unconnected_entry": false,
      "confirmed_necessary": true,
      "public_recipe_support": false,
      "station": false,
      "container": false,
      "first_action": "inspect padded_tunic",
      "condition": "UNKNOWN",
      "estimated_actions": 1,
      "estimate_is_not_native_cost_or_guaranteed_upper_bound": true,
      "menu_order": 2
    },
    {
      "candidate_id": "c_d6a4a748f3ca",
      "intent": [
        "craft_then_inspect",
        "stitched_panel"
      ],
      "target": "stitched_panel",
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
      "first_action": "store 1 bandage_roll inventory",
      "condition": "UNKNOWN",
      "estimated_actions": null,
      "estimate_is_not_native_cost_or_guaranteed_upper_bound": true,
      "menu_order": 3
    },
    {
      "candidate_id": "c_9336e1422f2b",
      "intent": [
        "inspect",
        "sinew_cord"
      ],
      "target": "sinew_cord",
      "entry_states": [
        "unconnected_uninspected_entry"
      ],
      "last_attempt_index": null,
      "last_feedback": null,
      "attempts": 0,
      "inspected": false,
      "produced": false,
      "unconnected_entry": true,
      "confirmed_necessary": false,
      "public_recipe_support": false,
      "station": false,
      "container": false,
      "first_action": "inspect sinew_cord",
      "condition": "UNKNOWN",
      "estimated_actions": 1,
      "estimate_is_not_native_cost_or_guaranteed_upper_bound": true,
      "menu_order": 4
    },
    {
      "candidate_id": "c_e20aa056f29e",
      "intent": [
        "primitive",
        "store 1 bandage_roll inventory"
      ],
      "target": "bandage_roll",
      "entry_states": [
        "inspected_with_public_information"
      ],
      "last_attempt_index": 1,
      "last_feedback": "I inspected bandage_roll: A rolled bolt of salvage cloth prepared for binding wounds or crafting gear.\nIt can be used to craft: stitched_panel (made of bandage_roll, sinew_cord), ruin_maul (made of ruin_blade, wooden_rod, bandage_roll), war_strap (made of sinew_cord, bandage_roll).\nIt has nothing written on it.",
      "attempts": 1,
      "inspected": true,
      "produced": false,
      "unconnected_entry": false,
      "confirmed_necessary": false,
      "public_recipe_support": false,
      "station": false,
      "container": false,
      "first_action": "store 1 bandage_roll inventory",
      "condition": "UNKNOWN",
      "estimated_actions": null,
      "estimate_is_not_native_cost_or_guaranteed_upper_bound": true,
      "menu_order": 5
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
      "first_action": "enter cellar",
      "condition": "UNKNOWN",
      "estimated_actions": 3,
      "estimate_is_not_native_cost_or_guaranteed_upper_bound": true,
      "menu_order": 6
    },
    {
      "candidate_id": "c_ff3dc4ae7a9a",
      "intent": [
        "inspect",
        "sinew_cord"
      ],
      "target": "sinew_cord",
      "entry_states": [
        "unconnected_uninspected_entry"
      ],
      "last_attempt_index": null,
      "last_feedback": null,
      "attempts": 0,
      "inspected": false,
      "produced": false,
      "unconnected_entry": true,
      "confirmed_necessary": false,
      "public_recipe_support": false,
      "station": false,
      "container": false,
      "first_action": "inspect sinew_cord",
      "condition": "UNKNOWN",
      "estimated_actions": 1,
      "estimate_is_not_native_cost_or_guaranteed_upper_bound": true,
      "menu_order": 7
    }
  ],
  "public_input_digest": "341b25aae72dd3476e133c31aeb7205c1279866d3e3fbbfafe5ae5f47d765fe6",
  "single_supplement_max_actions": 4
}
```

## 历史进展依据

仅用当前决策之前的实际执行行；没有未来反馈。完整前后观察见公开输入文件。


|行号|执行动作|公开新配方|持有量增加/制作/新地点|进展|未关联入口检查|
|---|---|---|---|---|---|
|0|inspect padded_tunic||False/False/False|False|False|
|1|inspect bandage_roll|ruin_maul,stitched_panel,war_strap|False/False/False|True|True|

## 完整候选及公开依据

```json
[
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
    "next_action": "store 1 sinew_cord inventory",
    "public_condition": "UNKNOWN"
  },
  {
    "kind": "visit",
    "target": "salvage_cloth",
    "category": "known_location",
    "location": "cellar",
    "evidence": "historically seen object; current presence requires reconfirmation",
    "id": "c_e02a00b1c3e8",
    "confirmed_connection": false,
    "next_action": "enter cellar",
    "public_condition": "UNKNOWN"
  },
  {
    "kind": "inspect",
    "target": "padded_tunic",
    "category": "other_inspect",
    "evidence": "visible unresolved public prerequisite; repeat",
    "id": "c_0450ed6211e2",
    "confirmed_connection": true,
    "next_action": "inspect padded_tunic",
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
    "confirmed_connection": false,
    "next_action": "store 1 bandage_roll inventory",
    "public_condition": "UNKNOWN"
  },
  {
    "kind": "inspect",
    "target": "sinew_cord",
    "category": "primitive",
    "evidence": "public method proposal; exact first action retained",
    "first_action": "inspect sinew_cord",
    "id": "c_9336e1422f2b",
    "confirmed_connection": false,
    "next_action": "inspect sinew_cord",
    "public_condition": "UNKNOWN"
  },
  {
    "kind": "primitive",
    "target": "bandage_roll",
    "category": "primitive",
    "evidence": "public method proposal; exact first action retained",
    "first_action": "store 1 bandage_roll inventory",
    "id": "c_e20aa056f29e",
    "confirmed_connection": false,
    "next_action": "store 1 bandage_roll inventory",
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
    "next_action": "enter cellar",
    "public_condition": "UNKNOWN"
  },
  {
    "kind": "inspect",
    "target": "sinew_cord",
    "category": "unconnected_visible",
    "evidence": "currently observed, not previously inspected",
    "id": "c_ff3dc4ae7a9a",
    "confirmed_connection": false,
    "next_action": "inspect sinew_cord",
    "public_condition": "UNKNOWN"
  }
]
```

## J0 与 J3 配对及去重排名

```json
{
  "state_id": "d12_db9cf8a8d4ddadac",
  "family": "padded_tunic",
  "pair_class": "loss",
  "same_exploration_intent": false,
  "J0": {
    "actions": 1,
    "new_key_recipes": [
      "padded_tunic"
    ],
    "useful": true,
    "one_step_useful": true,
    "rejections": 0,
    "unrelated_craft": false,
    "unrelated_key_input_consumption": false,
    "environment_key_loss": false,
    "goal": false,
    "stop": "inspection_attempt_completed",
    "candidate_id": "c_9336e1422f2b",
    "intent": [
      "inspect",
      "sinew_cord"
    ],
    "actions_trace": [
      "inspect sinew_cord"
    ],
    "feedback_trace": [
      "I inspected sinew_cord: Twisted cord braided from salvaged fibers and dried sinew, surprisingly tough.\nIt can be used to craft: stitched_panel (made of bandage_roll, sinew_cord), timber_sword (made of scorched_plank, wood_strip, sinew_cord), spiked_club (made of charred_timber, rubble_chunk, sinew_cord), war_strap (made of sinew_cord, bandage_roll), war_codex (made of field_journal, sinew_cord, fiend_strip), cog_crossbow (made of gearwork_frame, iron_bar, sinew_cord), ruin_spear (made of knapped_edge, wooden_rod, sinew_cord), hunter_gauntlets (made of iron_bar, war_strap, sinew_cord), fiend_scale_bundle (made of fiend_alloy_scale, sinew_cord), scale_bundle (made of iron_scale, sinew_cord), siege_crate (made of scorched_plank, iron_bar, sinew_cord), fiend_gauntlets (made of fiend_alloy, war_strap, sinew_cord), bandage_roll (made of salvage_cloth, sinew_cord), padded_tunic (made of padded_lining, sinew_cord), scrap_buckler (made of scrap_iron, sinew_cord), repair_kit (made of scrap_iron, sinew_cord, oil_flask), scout_satchel (made of salvage_cloth, sinew_cord), warding_charm (made of demon_core_shard, sinew_cord, hellcoal_concentrate), field_journal (made of war_parchment, sinew_cord), chain_net (made of iron_bar, sinew_cord).\nIt has nothing written on it."
    ],
    "native_new_necessary_rule_count": 1,
    "preparation_actions_until_first_necessary_recipe": 0,
    "craft_actions": 0,
    "inspect_actions": 1,
    "consumption": {},
    "production": {},
    "environment_loss_quantities": {},
    "unrelated_key_consumption_quantities": {},
    "repeated_inspect_without_new_public_recipe": 0,
    "craft_without_output_or_new_recipe": 0,
    "public_known_necessary_executions": [],
    "raw_entry_useful": true,
    "native_trace_digest": "23983769fbde4dd45c69c3b1b2d50374b38059efc7e2c11e8211cc79aa19059b"
  },
  "J3": {
    "actions": 3,
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
      "enter cellar",
      "enter courtyard",
      "inspect war_bench"
    ],
    "feedback_trace": [
      "I entered cellar.",
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
    "native_trace_digest": "6ac01022234f8ffcb5816f388587508880bf385c4f1c1f70adc55f98df2faefd"
  },
  "J3_raw_judgment": {
    "selected_candidate_id": "c_3f33cf002d85",
    "ranked_candidate_ids": [
      "c_3f33cf002d85",
      "c_d6a4a748f3ca",
      "c_3005d7648aa4"
    ],
    "reason": "Need war_bench to craft padded_tunic; courtyard historically had one. Verify current presence before crafting intermediates.",
    "hypothesized_connection": "war_bench in courtyard enables padded_tunic craft, possibly via intermediate stitched_panel or war_strap.",
    "confidence": 0.5,
    "expected_information": "Whether war_bench currently exists in courtyard and what it enables.",
    "alternative_if_failed": "c_d6a4a748f3ca"
  },
  "public_features": {
    "incomplete_public_dependencies": true,
    "unknown_goal_recipe": true,
    "public_necessary_knowledge_drought": 2,
    "no_public_progress_streak": 0,
    "same_known_component_last3": false,
    "recent_unconnected_inspection_last4": true,
    "uninspected_independent_entry_intents": 2,
    "fresh_uninspected_product": false,
    "j3_previously_attempted": false,
    "j3_repeat_inspection_or_station": true,
    "j3_public_recipe_support": false,
    "j3_estimated_actions": 3,
    "s1_estimated_actions": 1,
    "s1_public_execution_protected": false,
    "C1_trigger": false,
    "C2_trigger": false,
    "L_trigger": false,
    "remaining_actions": 38
  },
  "J3_top3_original_ids": [
    "c_3f33cf002d85",
    "c_d6a4a748f3ca",
    "c_3005d7648aa4"
  ],
  "J3_distinct_ranked_ids": [
    "c_3f33cf002d85",
    "c_d6a4a748f3ca",
    "c_3005d7648aa4"
  ],
  "removed_alias_ids": [],
  "alias_groups": [
    {
      "intent": [
        "inspect",
        "sinew_cord"
      ],
      "ids": [
        "c_9336e1422f2b",
        "c_ff3dc4ae7a9a"
      ],
      "different_information_outcomes": false
    }
  ],
  "distinct_top3_useful": false,
  "distinct_top2_useful": false,
  "effective_lower_rank_ids": [],
  "no_effective_direction_in_returned_distinct_ranks": true,
  "candidate_pool_has_opportunity": true,
  "new_connection_direction_relative_to_S1": true,
  "new_connection_useful_native_supported": false,
  "public_evidence_class": "known_station_prerequisite_only",
  "co_mentioned_public_recipe_edges": [],
  "co_mention_is_not_entailment_or_proof_of_reasoning": true,
  "mentioned_public_goal_station_requirements": [
    "war_bench"
  ],
  "unconnected_recipe_names_mentioned": [
    "stitched_panel",
    "war_strap"
  ],
  "name_association_causality": "not identifiable from generated explanation alone; hypothesized downstream links remain hypotheses",
  "raw_entry_selected": false,
  "raw_entry_effective_top3": [],
  "actual_native_costs_diagnostic_only": {
    "J0": 1,
    "J3": 3,
    "difference": 2
  }
}
```

## 主窗口全部原生分支

含原菜单及 Stage12 的自由提案补充分支；没有删除失败。new_key_recipes 是截至该步的累计新增集合，不能跨步相加。goal 仅为本短分支末局部持有目标，绝不表示本轮完成正式长程闭环。

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
    "store 1 sinew_cord inventory",
    "store 1 bandage_roll inventory",
    "craft 2 war_strap",
    "enter cellar"
  ],
  "feedback_trace": [
    "I stored 1 sinew_cord in my inventory.\nI have acquired a new item: sinew_cord. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), timber_sword (1 scorched_plank, 1 wood_strip, 1 sinew_cord), spiked_club (2 charred_timber, 2 rubble_chunk, 1 sinew_cord), war_strap (1 sinew_cord, 0.25 bandage_roll), war_codex (2 field_journal, 2 sinew_cord, 1 fiend_strip), cog_crossbow (1 gearwork_frame, 2 iron_bar, 3 sinew_cord), ruin_spear (1 knapped_edge, 1 wooden_rod, 1 sinew_cord), hunter_gauntlets (1 iron_bar, 1 war_strap, 1 sinew_cord), fiend_scale_bundle (6 fiend_alloy_scale, 3 sinew_cord), scale_bundle (6 iron_scale, 2 sinew_cord), siege_crate (4 scorched_plank, 2 iron_bar, 2 sinew_cord), fiend_gauntlets (1 fiend_alloy, 1 war_strap, 2 sinew_cord), bandage_roll (1 salvage_cloth, 2 sinew_cord), padded_tunic (1 padded_lining, 1 sinew_cord), scrap_buckler (2 scrap_iron, 1 sinew_cord), repair_kit (2 scrap_iron, 2 sinew_cord, 1 oil_flask), scout_satchel (3 salvage_cloth, 1 sinew_cord), warding_charm (1 demon_core_shard, 3 sinew_cord, 1 hellcoal_concentrate), field_journal (5 war_parchment, 1 sinew_cord), chain_net (3 iron_bar, 2 sinew_cord)",
    "I stored 1 bandage_roll in my inventory.\nI have acquired a new item: bandage_roll. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), ruin_maul (1 ruin_blade, 1 wooden_rod, 1 bandage_roll), war_strap (1 sinew_cord, 0.25 bandage_roll)",
    "Cannot craft war_strap. Missing necessary war_bench in the current area.",
    "I entered cellar."
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
  "public_known_necessary_executions": [],
  "raw_entry_useful": false,
  "native_trace_digest": "10deee9f70643992c0651ab2781472e8ff81d54fa66d482b4bf16a1595646134"
}
```

第 1 步：`store 1 sinew_cord inventory`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I stored 1 sinew_cord in my inventory.
I have acquired a new item: sinew_cord. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), timber_sword (1 scorched_plank, 1 wood_strip, 1 sinew_cord), spiked_club (2 charred_timber, 2 rubble_chunk, 1 sinew_cord), war_strap (1 sinew_cord, 0.25 bandage_roll), war_codex (2 field_journal, 2 sinew_cord, 1 fiend_strip), cog_crossbow (1 gearwork_frame, 2 iron_bar, 3 sinew_cord), ruin_spear (1 knapped_edge, 1 wooden_rod, 1 sinew_cord), hunter_gauntlets (1 iron_bar, 1 war_strap, 1 sinew_cord), fiend_scale_bundle (6 fiend_alloy_scale, 3 sinew_cord), scale_bundle (6 iron_scale, 2 sinew_cord), siege_crate (4 scorched_plank, 2 iron_bar, 2 sinew_cord), fiend_gauntlets (1 fiend_alloy, 1 war_strap, 2 sinew_cord), bandage_roll (1 salvage_cloth, 2 sinew_cord), padded_tunic (1 padded_lining, 1 sinew_cord), scrap_buckler (2 scrap_iron, 1 sinew_cord), repair_kit (2 scrap_iron, 2 sinew_cord, 1 oil_flask), scout_satchel (3 salvage_cloth, 1 sinew_cord), warding_charm (1 demon_core_shard, 3 sinew_cord, 1 hellcoal_concentrate), field_journal (5 war_parchment, 1 sinew_cord), chain_net (3 iron_bar, 2 sinew_cord)
```

第 2 步：`store 1 bandage_roll inventory`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I stored 1 bandage_roll in my inventory.
I have acquired a new item: bandage_roll. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), ruin_maul (1 ruin_blade, 1 wooden_rod, 1 bandage_roll), war_strap (1 sinew_cord, 0.25 bandage_roll)
```

第 3 步：`craft 2 war_strap`；拒绝=True；累计必要配方=[]；消耗={}；环境损失={}。

```text
Cannot craft war_strap. Missing necessary war_bench in the current area.
```

第 4 步：`enter cellar`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I entered cellar.
```
### c_e02a00b1c3e8

```json
{
  "actions": 2,
  "new_key_recipes": [
    "padded_lining",
    "sinew_cord"
  ],
  "useful": true,
  "one_step_useful": false,
  "rejections": 0,
  "unrelated_craft": false,
  "unrelated_key_input_consumption": false,
  "environment_key_loss": false,
  "goal": false,
  "stop": "inspection_attempt_completed",
  "candidate_id": "c_e02a00b1c3e8",
  "intent": [
    "inspect",
    "salvage_cloth"
  ],
  "actions_trace": [
    "enter cellar",
    "inspect salvage_cloth"
  ],
  "feedback_trace": [
    "I entered cellar.",
    "I inspected salvage_cloth: Tattered fabric pulled from ruined banners and bedrolls, still serviceable.\nIt can be used to craft: bandage_roll (made of salvage_cloth, sinew_cord), oil_bomb (made of oil_flask, charcoal_brick, salvage_cloth), scout_satchel (made of salvage_cloth, sinew_cord), war_parchment (made of salvage_cloth), sinew_cord (made of salvage_cloth), war_banner (made of salvage_cloth, wooden_rod), padded_lining (made of stitched_panel, salvage_cloth), scrap_helm (made of scrap_iron, salvage_cloth), ruin_gauntlets (made of rubble_chunk, war_strap, salvage_cloth), scrap_lantern (made of scrap_iron, devil_oil, salvage_cloth).\nIt has nothing written on it."
  ],
  "native_new_necessary_rule_count": 2,
  "preparation_actions_until_first_necessary_recipe": 1,
  "craft_actions": 0,
  "inspect_actions": 1,
  "consumption": {},
  "production": {},
  "environment_loss_quantities": {},
  "unrelated_key_consumption_quantities": {},
  "repeated_inspect_without_new_public_recipe": 0,
  "craft_without_output_or_new_recipe": 0,
  "public_known_necessary_executions": [],
  "raw_entry_useful": true,
  "native_trace_digest": "987764a33594d1765951d8ea26cc98c252f3ca03965df9a6f5547391c69b3ef2"
}
```

第 1 步：`enter cellar`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I entered cellar.
```

第 2 步：`inspect salvage_cloth`；拒绝=False；累计必要配方=["padded_lining", "sinew_cord"]；消耗={}；环境损失={}。

```text
I inspected salvage_cloth: Tattered fabric pulled from ruined banners and bedrolls, still serviceable.
It can be used to craft: bandage_roll (made of salvage_cloth, sinew_cord), oil_bomb (made of oil_flask, charcoal_brick, salvage_cloth), scout_satchel (made of salvage_cloth, sinew_cord), war_parchment (made of salvage_cloth), sinew_cord (made of salvage_cloth), war_banner (made of salvage_cloth, wooden_rod), padded_lining (made of stitched_panel, salvage_cloth), scrap_helm (made of scrap_iron, salvage_cloth), ruin_gauntlets (made of rubble_chunk, war_strap, salvage_cloth), scrap_lantern (made of scrap_iron, devil_oil, salvage_cloth).
It has nothing written on it.
```
### c_0450ed6211e2

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
  "candidate_id": "c_0450ed6211e2",
  "intent": [
    "inspect",
    "padded_tunic"
  ],
  "actions_trace": [
    "inspect padded_tunic"
  ],
  "feedback_trace": [
    "I inspected padded_tunic: A padded tunic that absorbs the shock of machine strikes.\nIt can be used to craft: None.\nIt has nothing written on it."
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
  "native_trace_digest": "c9d3c04ab47109b6c391759f2186cfe5972ebfefc7edab73bf63935b6af0ff25"
}
```

第 1 步：`inspect padded_tunic`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I inspected padded_tunic: A padded tunic that absorbs the shock of machine strikes.
It can be used to craft: None.
It has nothing written on it.
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
    "store 1 bandage_roll inventory",
    "store 1 sinew_cord inventory",
    "craft 2 stitched_panel",
    "enter cellar"
  ],
  "feedback_trace": [
    "I stored 1 bandage_roll in my inventory.\nI have acquired a new item: bandage_roll. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), ruin_maul (1 ruin_blade, 1 wooden_rod, 1 bandage_roll), war_strap (1 sinew_cord, 0.25 bandage_roll)",
    "I stored 1 sinew_cord in my inventory.\nI have acquired a new item: sinew_cord. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), timber_sword (1 scorched_plank, 1 wood_strip, 1 sinew_cord), spiked_club (2 charred_timber, 2 rubble_chunk, 1 sinew_cord), war_strap (1 sinew_cord, 0.25 bandage_roll), war_codex (2 field_journal, 2 sinew_cord, 1 fiend_strip), cog_crossbow (1 gearwork_frame, 2 iron_bar, 3 sinew_cord), ruin_spear (1 knapped_edge, 1 wooden_rod, 1 sinew_cord), hunter_gauntlets (1 iron_bar, 1 war_strap, 1 sinew_cord), fiend_scale_bundle (6 fiend_alloy_scale, 3 sinew_cord), scale_bundle (6 iron_scale, 2 sinew_cord), siege_crate (4 scorched_plank, 2 iron_bar, 2 sinew_cord), fiend_gauntlets (1 fiend_alloy, 1 war_strap, 2 sinew_cord), bandage_roll (1 salvage_cloth, 2 sinew_cord), padded_tunic (1 padded_lining, 1 sinew_cord), scrap_buckler (2 scrap_iron, 1 sinew_cord), repair_kit (2 scrap_iron, 2 sinew_cord, 1 oil_flask), scout_satchel (3 salvage_cloth, 1 sinew_cord), warding_charm (1 demon_core_shard, 3 sinew_cord, 1 hellcoal_concentrate), field_journal (5 war_parchment, 1 sinew_cord), chain_net (3 iron_bar, 2 sinew_cord)",
    "Cannot craft stitched_panel. Missing necessary war_bench in the current area.",
    "I entered cellar."
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
  "public_known_necessary_executions": [],
  "raw_entry_useful": false,
  "native_trace_digest": "2fdb2336a0175773d178ecdf853c3025507603be1c870ec5d931b148abbc7585"
}
```

第 1 步：`store 1 bandage_roll inventory`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I stored 1 bandage_roll in my inventory.
I have acquired a new item: bandage_roll. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), ruin_maul (1 ruin_blade, 1 wooden_rod, 1 bandage_roll), war_strap (1 sinew_cord, 0.25 bandage_roll)
```

第 2 步：`store 1 sinew_cord inventory`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I stored 1 sinew_cord in my inventory.
I have acquired a new item: sinew_cord. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), timber_sword (1 scorched_plank, 1 wood_strip, 1 sinew_cord), spiked_club (2 charred_timber, 2 rubble_chunk, 1 sinew_cord), war_strap (1 sinew_cord, 0.25 bandage_roll), war_codex (2 field_journal, 2 sinew_cord, 1 fiend_strip), cog_crossbow (1 gearwork_frame, 2 iron_bar, 3 sinew_cord), ruin_spear (1 knapped_edge, 1 wooden_rod, 1 sinew_cord), hunter_gauntlets (1 iron_bar, 1 war_strap, 1 sinew_cord), fiend_scale_bundle (6 fiend_alloy_scale, 3 sinew_cord), scale_bundle (6 iron_scale, 2 sinew_cord), siege_crate (4 scorched_plank, 2 iron_bar, 2 sinew_cord), fiend_gauntlets (1 fiend_alloy, 1 war_strap, 2 sinew_cord), bandage_roll (1 salvage_cloth, 2 sinew_cord), padded_tunic (1 padded_lining, 1 sinew_cord), scrap_buckler (2 scrap_iron, 1 sinew_cord), repair_kit (2 scrap_iron, 2 sinew_cord, 1 oil_flask), scout_satchel (3 salvage_cloth, 1 sinew_cord), warding_charm (1 demon_core_shard, 3 sinew_cord, 1 hellcoal_concentrate), field_journal (5 war_parchment, 1 sinew_cord), chain_net (3 iron_bar, 2 sinew_cord)
```

第 3 步：`craft 2 stitched_panel`；拒绝=True；累计必要配方=[]；消耗={}；环境损失={}。

```text
Cannot craft stitched_panel. Missing necessary war_bench in the current area.
```

第 4 步：`enter cellar`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I entered cellar.
```
### c_9336e1422f2b

```json
{
  "actions": 1,
  "new_key_recipes": [
    "padded_tunic"
  ],
  "useful": true,
  "one_step_useful": true,
  "rejections": 0,
  "unrelated_craft": false,
  "unrelated_key_input_consumption": false,
  "environment_key_loss": false,
  "goal": false,
  "stop": "inspection_attempt_completed",
  "candidate_id": "c_9336e1422f2b",
  "intent": [
    "inspect",
    "sinew_cord"
  ],
  "actions_trace": [
    "inspect sinew_cord"
  ],
  "feedback_trace": [
    "I inspected sinew_cord: Twisted cord braided from salvaged fibers and dried sinew, surprisingly tough.\nIt can be used to craft: stitched_panel (made of bandage_roll, sinew_cord), timber_sword (made of scorched_plank, wood_strip, sinew_cord), spiked_club (made of charred_timber, rubble_chunk, sinew_cord), war_strap (made of sinew_cord, bandage_roll), war_codex (made of field_journal, sinew_cord, fiend_strip), cog_crossbow (made of gearwork_frame, iron_bar, sinew_cord), ruin_spear (made of knapped_edge, wooden_rod, sinew_cord), hunter_gauntlets (made of iron_bar, war_strap, sinew_cord), fiend_scale_bundle (made of fiend_alloy_scale, sinew_cord), scale_bundle (made of iron_scale, sinew_cord), siege_crate (made of scorched_plank, iron_bar, sinew_cord), fiend_gauntlets (made of fiend_alloy, war_strap, sinew_cord), bandage_roll (made of salvage_cloth, sinew_cord), padded_tunic (made of padded_lining, sinew_cord), scrap_buckler (made of scrap_iron, sinew_cord), repair_kit (made of scrap_iron, sinew_cord, oil_flask), scout_satchel (made of salvage_cloth, sinew_cord), warding_charm (made of demon_core_shard, sinew_cord, hellcoal_concentrate), field_journal (made of war_parchment, sinew_cord), chain_net (made of iron_bar, sinew_cord).\nIt has nothing written on it."
  ],
  "native_new_necessary_rule_count": 1,
  "preparation_actions_until_first_necessary_recipe": 0,
  "craft_actions": 0,
  "inspect_actions": 1,
  "consumption": {},
  "production": {},
  "environment_loss_quantities": {},
  "unrelated_key_consumption_quantities": {},
  "repeated_inspect_without_new_public_recipe": 0,
  "craft_without_output_or_new_recipe": 0,
  "public_known_necessary_executions": [],
  "raw_entry_useful": true,
  "native_trace_digest": "23983769fbde4dd45c69c3b1b2d50374b38059efc7e2c11e8211cc79aa19059b"
}
```

第 1 步：`inspect sinew_cord`；拒绝=False；累计必要配方=["padded_tunic"]；消耗={}；环境损失={}。

```text
I inspected sinew_cord: Twisted cord braided from salvaged fibers and dried sinew, surprisingly tough.
It can be used to craft: stitched_panel (made of bandage_roll, sinew_cord), timber_sword (made of scorched_plank, wood_strip, sinew_cord), spiked_club (made of charred_timber, rubble_chunk, sinew_cord), war_strap (made of sinew_cord, bandage_roll), war_codex (made of field_journal, sinew_cord, fiend_strip), cog_crossbow (made of gearwork_frame, iron_bar, sinew_cord), ruin_spear (made of knapped_edge, wooden_rod, sinew_cord), hunter_gauntlets (made of iron_bar, war_strap, sinew_cord), fiend_scale_bundle (made of fiend_alloy_scale, sinew_cord), scale_bundle (made of iron_scale, sinew_cord), siege_crate (made of scorched_plank, iron_bar, sinew_cord), fiend_gauntlets (made of fiend_alloy, war_strap, sinew_cord), bandage_roll (made of salvage_cloth, sinew_cord), padded_tunic (made of padded_lining, sinew_cord), scrap_buckler (made of scrap_iron, sinew_cord), repair_kit (made of scrap_iron, sinew_cord, oil_flask), scout_satchel (made of salvage_cloth, sinew_cord), warding_charm (made of demon_core_shard, sinew_cord, hellcoal_concentrate), field_journal (made of war_parchment, sinew_cord), chain_net (made of iron_bar, sinew_cord).
It has nothing written on it.
```
### c_e20aa056f29e

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
  "candidate_id": "c_e20aa056f29e",
  "intent": [
    "primitive",
    "store 1 bandage_roll inventory"
  ],
  "actions_trace": [
    "store 1 bandage_roll inventory"
  ],
  "feedback_trace": [
    "I stored 1 bandage_roll in my inventory.\nI have acquired a new item: bandage_roll. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), ruin_maul (1 ruin_blade, 1 wooden_rod, 1 bandage_roll), war_strap (1 sinew_cord, 0.25 bandage_roll)"
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
  "native_trace_digest": "3986550e2517cdf4583956d6cf166e9b3a6547db4339e3d93a0e0655e6124f44"
}
```

第 1 步：`store 1 bandage_roll inventory`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I stored 1 bandage_roll in my inventory.
I have acquired a new item: bandage_roll. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), ruin_maul (1 ruin_blade, 1 wooden_rod, 1 bandage_roll), war_strap (1 sinew_cord, 0.25 bandage_roll)
```
### c_3f33cf002d85

```json
{
  "actions": 3,
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
    "enter cellar",
    "enter courtyard",
    "inspect war_bench"
  ],
  "feedback_trace": [
    "I entered cellar.",
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
  "native_trace_digest": "6ac01022234f8ffcb5816f388587508880bf385c4f1c1f70adc55f98df2faefd"
}
```

第 1 步：`enter cellar`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I entered cellar.
```

第 2 步：`enter courtyard`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I entered courtyard.
```

第 3 步：`inspect war_bench`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I inspected war_bench: A reinforced workbench built by allied smiths for field assembly of anti-machine weapons.
It can be used to craft: None.
It has nothing written on it.
```
### c_ff3dc4ae7a9a

```json
{
  "actions": 1,
  "new_key_recipes": [
    "padded_tunic"
  ],
  "useful": true,
  "one_step_useful": true,
  "rejections": 0,
  "unrelated_craft": false,
  "unrelated_key_input_consumption": false,
  "environment_key_loss": false,
  "goal": false,
  "stop": "inspection_attempt_completed",
  "candidate_id": "c_ff3dc4ae7a9a",
  "intent": [
    "inspect",
    "sinew_cord"
  ],
  "actions_trace": [
    "inspect sinew_cord"
  ],
  "feedback_trace": [
    "I inspected sinew_cord: Twisted cord braided from salvaged fibers and dried sinew, surprisingly tough.\nIt can be used to craft: stitched_panel (made of bandage_roll, sinew_cord), timber_sword (made of scorched_plank, wood_strip, sinew_cord), spiked_club (made of charred_timber, rubble_chunk, sinew_cord), war_strap (made of sinew_cord, bandage_roll), war_codex (made of field_journal, sinew_cord, fiend_strip), cog_crossbow (made of gearwork_frame, iron_bar, sinew_cord), ruin_spear (made of knapped_edge, wooden_rod, sinew_cord), hunter_gauntlets (made of iron_bar, war_strap, sinew_cord), fiend_scale_bundle (made of fiend_alloy_scale, sinew_cord), scale_bundle (made of iron_scale, sinew_cord), siege_crate (made of scorched_plank, iron_bar, sinew_cord), fiend_gauntlets (made of fiend_alloy, war_strap, sinew_cord), bandage_roll (made of salvage_cloth, sinew_cord), padded_tunic (made of padded_lining, sinew_cord), scrap_buckler (made of scrap_iron, sinew_cord), repair_kit (made of scrap_iron, sinew_cord, oil_flask), scout_satchel (made of salvage_cloth, sinew_cord), warding_charm (made of demon_core_shard, sinew_cord, hellcoal_concentrate), field_journal (made of war_parchment, sinew_cord), chain_net (made of iron_bar, sinew_cord).\nIt has nothing written on it."
  ],
  "native_new_necessary_rule_count": 1,
  "preparation_actions_until_first_necessary_recipe": 0,
  "craft_actions": 0,
  "inspect_actions": 1,
  "consumption": {},
  "production": {},
  "environment_loss_quantities": {},
  "unrelated_key_consumption_quantities": {},
  "repeated_inspect_without_new_public_recipe": 0,
  "craft_without_output_or_new_recipe": 0,
  "public_known_necessary_executions": [],
  "raw_entry_useful": true,
  "native_trace_digest": "23983769fbde4dd45c69c3b1b2d50374b38059efc7e2c11e8211cc79aa19059b"
}
```

第 1 步：`inspect sinew_cord`；拒绝=False；累计必要配方=["padded_tunic"]；消耗={}；环境损失={}。

```text
I inspected sinew_cord: Twisted cord braided from salvaged fibers and dried sinew, surprisingly tough.
It can be used to craft: stitched_panel (made of bandage_roll, sinew_cord), timber_sword (made of scorched_plank, wood_strip, sinew_cord), spiked_club (made of charred_timber, rubble_chunk, sinew_cord), war_strap (made of sinew_cord, bandage_roll), war_codex (made of field_journal, sinew_cord, fiend_strip), cog_crossbow (made of gearwork_frame, iron_bar, sinew_cord), ruin_spear (made of knapped_edge, wooden_rod, sinew_cord), hunter_gauntlets (made of iron_bar, war_strap, sinew_cord), fiend_scale_bundle (made of fiend_alloy_scale, sinew_cord), scale_bundle (made of iron_scale, sinew_cord), siege_crate (made of scorched_plank, iron_bar, sinew_cord), fiend_gauntlets (made of fiend_alloy, war_strap, sinew_cord), bandage_roll (made of salvage_cloth, sinew_cord), padded_tunic (made of padded_lining, sinew_cord), scrap_buckler (made of scrap_iron, sinew_cord), repair_kit (made of scrap_iron, sinew_cord, oil_flask), scout_satchel (made of salvage_cloth, sinew_cord), warding_charm (made of demon_core_shard, sinew_cord, hellcoal_concentrate), field_journal (made of war_parchment, sinew_cord), chain_net (made of iron_bar, sinew_cord).
It has nothing written on it.
```
### c_07db86249dd6

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
  "candidate_id": "c_07db86249dd6",
  "intent": [
    "primitive",
    "enter cellar"
  ],
  "actions_trace": [
    "enter cellar"
  ],
  "feedback_trace": [
    "I entered cellar."
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
  "native_trace_digest": "6ce2a5a94ad797220e8a0594d247903055c6f5afe7f6260e14e22aec1e3a0895"
}
```

第 1 步：`enter cellar`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I entered cellar.
```

## 本轮零 API 补充

[完整补充分支](../../../results/stage13/native_supplements.jsonl.gz)。base_proposal 仍为最多四步；truncation_sensitivity 为独立八步敏感性，前四步逐字段相同。

### base_proposal / c_c53ac1f74f40

```json
{
  "actions": 1,
  "new_key_recipes": [],
  "useful": false,
  "one_step_useful": false,
  "rejections": 1,
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
    "Cannot enter courtyard. There's no path to courtyard."
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
  "native_trace_digest": "541d800ae52a793a9a4acaacabc6b3f6ed0e0d16ea6bf2ef4bbb26aef37a66e2"
}
```
### truncation_sensitivity / c_3005d7648aa4

```json
{
  "actions": 7,
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
    "store 1 sinew_cord inventory",
    "store 1 bandage_roll inventory",
    "craft 2 war_strap",
    "enter cellar",
    "enter courtyard",
    "craft 2 war_strap",
    "inspect war_strap"
  ],
  "feedback_trace": [
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
  "public_known_necessary_executions": [],
  "raw_entry_useful": false,
  "native_trace_digest": "664bb2881acde8e1855df8286b5c8437fb7ce2fc4c42628172681f351c8565e1"
}
```
### truncation_sensitivity / c_d6a4a748f3ca

```json
{
  "actions": 7,
  "new_key_recipes": [
    "padded_lining"
  ],
  "useful": true,
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
    "store 1 bandage_roll inventory",
    "store 1 sinew_cord inventory",
    "craft 2 stitched_panel",
    "enter cellar",
    "enter courtyard",
    "craft 2 stitched_panel",
    "inspect stitched_panel"
  ],
  "feedback_trace": [
    "I stored 1 bandage_roll in my inventory.\nI have acquired a new item: bandage_roll. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), ruin_maul (1 ruin_blade, 1 wooden_rod, 1 bandage_roll), war_strap (1 sinew_cord, 0.25 bandage_roll)",
    "I stored 1 sinew_cord in my inventory.\nI have acquired a new item: sinew_cord. It can be used to craft: stitched_panel (1 bandage_roll, 1 sinew_cord), timber_sword (1 scorched_plank, 1 wood_strip, 1 sinew_cord), spiked_club (2 charred_timber, 2 rubble_chunk, 1 sinew_cord), war_strap (1 sinew_cord, 0.25 bandage_roll), war_codex (2 field_journal, 2 sinew_cord, 1 fiend_strip), cog_crossbow (1 gearwork_frame, 2 iron_bar, 3 sinew_cord), ruin_spear (1 knapped_edge, 1 wooden_rod, 1 sinew_cord), hunter_gauntlets (1 iron_bar, 1 war_strap, 1 sinew_cord), fiend_scale_bundle (6 fiend_alloy_scale, 3 sinew_cord), scale_bundle (6 iron_scale, 2 sinew_cord), siege_crate (4 scorched_plank, 2 iron_bar, 2 sinew_cord), fiend_gauntlets (1 fiend_alloy, 1 war_strap, 2 sinew_cord), bandage_roll (1 salvage_cloth, 2 sinew_cord), padded_tunic (1 padded_lining, 1 sinew_cord), scrap_buckler (2 scrap_iron, 1 sinew_cord), repair_kit (2 scrap_iron, 2 sinew_cord, 1 oil_flask), scout_satchel (3 salvage_cloth, 1 sinew_cord), warding_charm (1 demon_core_shard, 3 sinew_cord, 1 hellcoal_concentrate), field_journal (5 war_parchment, 1 sinew_cord), chain_net (3 iron_bar, 2 sinew_cord)",
    "Cannot craft stitched_panel. Missing necessary war_bench in the current area.",
    "I entered cellar.",
    "I entered courtyard.",
    "Only enough ingredients to craft 1 stitched_panel.\nI successfully crafted 1 stitched_panel. It is now on the ground.",
    "I inspected stitched_panel: A reinforced cloth panel stitched for field armor assembly.\nIt can be used to craft: war_pack (made of stitched_panel, war_strap, iron_bar), padded_lining (made of stitched_panel, salvage_cloth).\nIt has nothing written on it."
  ],
  "native_new_necessary_rule_count": 1,
  "preparation_actions_until_first_necessary_recipe": 6,
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
  "public_known_necessary_executions": [],
  "raw_entry_useful": false,
  "native_trace_digest": "c4c06dcb080054516444635d88d6aae6dfe771d7d1304cb3c92a01b44c0408cd"
}
```

## 公开文本新颖性独立审计

将原反馈中的带数量配方也计为公开信息；不修改策略、Stage12 或主分数。

```json
{
  "initial_public_text_necessary_recipes": [
    "stitched_panel"
  ],
  "selected": {
    "C0": {
      "new_native_necessary_public_text_recipes": [
        "padded_tunic"
      ],
      "useful": true,
      "stage12_parser_useful": true,
      "new_vs_initial_public_text": true
    },
    "C1": {
      "new_native_necessary_public_text_recipes": [
        "padded_tunic"
      ],
      "useful": true,
      "stage12_parser_useful": true,
      "new_vs_initial_public_text": true
    },
    "C2": {
      "new_native_necessary_public_text_recipes": [
        "padded_tunic"
      ],
      "useful": true,
      "stage12_parser_useful": true,
      "new_vs_initial_public_text": true
    },
    "C3": {
      "new_native_necessary_public_text_recipes": [
        "padded_tunic"
      ],
      "useful": true,
      "stage12_parser_useful": true,
      "new_vs_initial_public_text": true
    },
    "L": {
      "new_native_necessary_public_text_recipes": [
        "padded_tunic"
      ],
      "useful": true,
      "stage12_parser_useful": true,
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
