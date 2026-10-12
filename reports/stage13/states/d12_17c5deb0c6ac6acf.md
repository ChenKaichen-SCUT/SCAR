# 冻结状态 d12_17c5deb0c6ac6acf

目标：`craft 1 brimite_blade_blank`。来源 Stage 10 / S1 / `sequence-6849519fb68b5f91-S1-c3876e4fe87c`，零基行号 2，剩余 38 动作。

[原始冻结状态](../../../results/stage12/diagnostic/states.json)、[原始原生分支](../../../results/stage12/diagnostic/native_branches.jsonl.gz)、[本轮公开输入与历史](../../../results/stage13/public_inputs.json)。状态/候选 ID 精确对应这些文件；当前页所有引擎反馈均原样保存。

## 遗漏解释

S1 收集 brimite_ore，遗漏 cellar 的未检查木板；后者两步披露 wood_strip。与另一刀坯 family 共享木材依赖结构，因此不能把这两例当作两个独立游戏的泛化证据。

```json
{
  "A": {
    "supported": true,
    "level": "native_counterfactual",
    "meaning": "unconnected public entry yields necessary new knowledge; actual raw/intermediate identity not inferred by policy",
    "candidates": [
      "c_a1dbeeaaaee7"
    ]
  },
  "B": {
    "supported": true,
    "level": "native_counterfactual",
    "meaning": "multi-action useful alternatives exist; unavoidable only when minimum preparation >0",
    "unavoidable_within_observed_menu": true,
    "minimum_preparation_actions": 1
  },
  "C": {
    "supported": true,
    "level": "public_observation_and_native_counterfactual",
    "meaning": "some useful alternatives require transport/acquisition or encounter a rejection; this alone does not prove S1 could not choose another immediate candidate",
    "evidence": [
      {
        "candidate_id": "c_a1dbeeaaaee7",
        "initial_public_condition": {
          "action": "enter cellar",
          "status": "UNKNOWN",
          "conditions": [
            {
              "kind": "route",
              "status": "UNKNOWN",
              "evidence": {
                "neighbors": [
                  "cellar"
                ],
                "guard": "UNLOCKED"
              },
              "observed_step": 12,
              "valid_until": "relevant public condition changes"
            }
          ]
        },
        "preparatory_first_action": "enter cellar",
        "native_rejections": 0
      }
    ]
  },
  "D": {
    "supported": false,
    "level": "unproven",
    "meaning": "only count when exact frozen base proposal branch is useful and S1 override is not",
    "override_observed": true,
    "base_proposal_useful": false
  },
  "E": {
    "supported": false,
    "level": "public_observation_proxy",
    "meaning": "sustained same public recipe component without new publicly connected recipe; causal overexploitation is not established",
    "weaker_known_branch_action_observed": true
  },
  "F": {
    "supported": false,
    "level": "native_counterfactual_cost",
    "meaning": "actual useful branch uses >=3 actions or consumes resources/exposes loss; scarcity and net full-task harm remain untested",
    "candidates": []
  }
}
```
## 决策时公开证据

```json
{
  "objective": "Obtain at least 2 brimite_blade_blank in your possession in total. You already hold one. The previous craft failed. Any valid route is allowed.",
  "target_action": "craft 1 brimite_blade_blank",
  "current": {
    "location": "barracks",
    "hands": {
      "brimite_blade_blank": 1.0
    },
    "ground": {
      "brimite_ore": 4.0
    },
    "equipment": {
      "scout_satchel_0": 1.0
    },
    "neighbors": [
      "cellar"
    ]
  },
  "confirmed_recipe_relations": {
    "brimite_blade_blank": {
      "ingredients": "UNKNOWN",
      "stations": [
        "war_bench",
        "crucible"
      ]
    },
    "brimite_blade": {
      "ingredients": [
        "brimite_blade_blank",
        "demon_core_shard"
      ],
      "stations": "UNKNOWN"
    },
    "brimite_nugget": {
      "ingredients": [
        "brimite_ore"
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
        "brimite_ore": 4.0
      },
      "step": 12,
      "source": "public_ground_observation"
    },
    "cellar": {
      "objects": {
        "scorched_plank": 1.0
      },
      "step": 8,
      "source": "public_ground_observation"
    },
    "courtyard": {
      "objects": {
        "crucible": 1.0,
        "war_bench": 1.0
      },
      "step": 7,
      "source": "public_ground_observation"
    }
  },
  "inspected": [
    "scout_satchel_0",
    "brimite_blade_blank",
    "brimite_ore"
  ],
  "produced": {},
  "recent_attempts": [
    {
      "action": "inspect brimite_blade_blank",
      "target": "brimite_blade_blank",
      "context": {
        "location": "barracks",
        "stations": {
          "war_bench": false,
          "crucible": false
        },
        "materials": {},
        "visible": true
      },
      "feedback": "I inspected brimite_blade_blank: A forged blank of brimite alloy that glows along hairline fractures.\nIt can be used to craft: brimite_blade (made of brimite_blade_blank, demon_core_shard).\nIt has nothing written on it.",
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
      "action": "inspect brimite_ore",
      "target": "brimite_ore",
      "context": {
        "location": "barracks",
        "stations": {},
        "materials": {},
        "visible": true
      },
      "feedback": "I inspected brimite_ore: A sulfurous ore found near devil forges, glowing faintly with trapped hellfire.\nIt can be used to craft: brimite_nugget (made of brimite_ore).\nIt has nothing written on it.",
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
    "brimite_blade_blank"
  ],
  "uncertainty": "Missing relations are UNKNOWN, not impossible. Production history is not possession. No semantic hypothesis is a confirmed recipe."
}
```

公开持有量下界与是否精确（地面数量另见 current.ground；UNKNOWN 不补成 0）：

```json
{
  "brimite_blade": {
    "lower_bound": 0,
    "exact": true
  },
  "brimite_blade_blank": {
    "lower_bound": 1.0,
    "exact": true
  },
  "brimite_nugget": {
    "lower_bound": 0,
    "exact": true
  },
  "brimite_ore": {
    "lower_bound": 0,
    "exact": true
  },
  "demon_core_shard": {
    "lower_bound": 0,
    "exact": true
  },
  "scout_satchel_0": {
    "lower_bound": 1.0,
    "exact": true
  }
}
```

原始观察：

```text

Current Time: 0001-01-01 10:00:00
Current Location: Ashen Bastion, barracks

I inspected brimite_ore: A sulfurous ore found near devil forges, glowing faintly with trapped hellfire.
It can be used to craft: brimite_nugget (made of brimite_ore).
It has nothing written on it.

I am holding 1 brimite_blade_blank.
I have equipped 1 scout_satchel_0.
I see 4 brimite_ore near me.
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
  "crucible",
  "scorched_plank",
  "war_bench"
]
```

基础提案、FIFO 和实际 S1 选择：

```json
{
  "base_proposal": "enter courtyard",
  "FIFO": "store 4 brimite_ore inventory",
  "actual_S1": "store 4 brimite_ore inventory",
  "reason": "retain_F0",
  "mechanisms": {
    "exploration": {
      "reason": "acquire publicly named trial ingredient",
      "source": {
        "product": "brimite_nugget",
        "ingredient": "brimite_ore"
      },
      "spent": 3,
      "limit": 18
    }
  },
  "queue": [
    "brimite_blade_blank"
  ],
  "graph": {}
}
```

公开特征、覆盖选择、分层入口账本：

```json
{
  "state_id": "d12_17c5deb0c6ac6acf",
  "choices": {
    "C0": "c_afadb45a7165",
    "C1": "c_afadb45a7165",
    "C2": "c_afadb45a7165",
    "C3": "c_afadb45a7165",
    "L": "c_afadb45a7165"
  },
  "features": {
    "incomplete_public_dependencies": true,
    "unknown_goal_recipe": true,
    "public_necessary_knowledge_drought": 2,
    "no_public_progress_streak": 0,
    "same_known_component_last3": false,
    "recent_unconnected_inspection_last4": true,
    "uninspected_independent_entry_intents": 1,
    "fresh_uninspected_product": false,
    "j3_previously_attempted": false,
    "j3_repeat_inspection_or_station": true,
    "j3_public_recipe_support": false,
    "j3_estimated_actions": 3,
    "s1_estimated_actions": null,
    "s1_public_execution_protected": false,
    "C1_trigger": false,
    "C2_trigger": false,
    "L_trigger": false,
    "remaining_actions": 38
  },
  "entry_ledger": [
    {
      "candidate_id": "c_afadb45a7165",
      "intent": [
        "primitive",
        "store 4 brimite_ore inventory"
      ],
      "target": "brimite_ore",
      "entry_states": [
        "inspected_with_public_information"
      ],
      "last_attempt_index": 1,
      "last_feedback": "I inspected brimite_ore: A sulfurous ore found near devil forges, glowing faintly with trapped hellfire.\nIt can be used to craft: brimite_nugget (made of brimite_ore).\nIt has nothing written on it.",
      "attempts": 1,
      "inspected": true,
      "produced": false,
      "unconnected_entry": false,
      "confirmed_necessary": false,
      "public_recipe_support": false,
      "station": false,
      "container": false,
      "first_action": "store 4 brimite_ore inventory",
      "condition": "UNKNOWN",
      "estimated_actions": null,
      "estimate_is_not_native_cost_or_guaranteed_upper_bound": true,
      "menu_order": 0
    },
    {
      "candidate_id": "c_2bd096c0d162",
      "intent": [
        "inspect",
        "brimite_blade_blank"
      ],
      "target": "brimite_blade_blank",
      "entry_states": [
        "inspected_with_public_information",
        "public_necessary_node"
      ],
      "last_attempt_index": 0,
      "last_feedback": "I inspected brimite_blade_blank: A forged blank of brimite alloy that glows along hairline fractures.\nIt can be used to craft: brimite_blade (made of brimite_blade_blank, demon_core_shard).\nIt has nothing written on it.",
      "attempts": 1,
      "inspected": true,
      "produced": false,
      "unconnected_entry": false,
      "confirmed_necessary": true,
      "public_recipe_support": false,
      "station": false,
      "container": false,
      "first_action": "inspect brimite_blade_blank",
      "condition": "UNKNOWN",
      "estimated_actions": 1,
      "estimate_is_not_native_cost_or_guaranteed_upper_bound": true,
      "menu_order": 1
    },
    {
      "candidate_id": "c_9a5fdfafa653",
      "intent": [
        "inspect",
        "crucible"
      ],
      "target": "crucible",
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
      "menu_order": 2
    },
    {
      "candidate_id": "c_a1dbeeaaaee7",
      "intent": [
        "inspect",
        "scorched_plank"
      ],
      "target": "scorched_plank",
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
      "menu_order": 3
    },
    {
      "candidate_id": "c_9d66f9363169",
      "intent": [
        "craft_then_inspect",
        "brimite_nugget"
      ],
      "target": "brimite_nugget",
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
      "first_action": "store 4 brimite_ore inventory",
      "condition": "UNKNOWN",
      "estimated_actions": null,
      "estimate_is_not_native_cost_or_guaranteed_upper_bound": true,
      "menu_order": 4
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
      "menu_order": 5
    }
  ],
  "public_input_digest": "c6c5dfc090f566a57dd0e139efe9d27968a0f956cd23a372ddda53f22d59f6d1",
  "single_supplement_max_actions": 4
}
```

## 历史进展依据

仅用当前决策之前的实际执行行；没有未来反馈。完整前后观察见公开输入文件。


|行号|执行动作|公开新配方|持有量增加/制作/新地点|进展|未关联入口检查|
|---|---|---|---|---|---|
|0|inspect brimite_blade_blank|brimite_blade|False/False/False|True|False|
|1|inspect brimite_ore|brimite_nugget|False/False/False|True|True|

## 完整候选及公开依据

```json
[
  {
    "kind": "primitive",
    "target": "brimite_ore",
    "category": "primitive",
    "evidence": "public method proposal; exact first action retained",
    "first_action": "store 4 brimite_ore inventory",
    "id": "c_afadb45a7165",
    "confirmed_connection": false,
    "next_action": "store 4 brimite_ore inventory",
    "public_condition": "UNKNOWN"
  },
  {
    "kind": "inspect",
    "target": "brimite_blade_blank",
    "category": "other_inspect",
    "evidence": "visible unresolved public prerequisite; repeat",
    "id": "c_2bd096c0d162",
    "confirmed_connection": true,
    "next_action": "inspect brimite_blade_blank",
    "public_condition": "UNKNOWN"
  },
  {
    "kind": "visit",
    "target": "crucible",
    "category": "known_location",
    "location": "courtyard",
    "evidence": "historically seen object; current presence requires reconfirmation",
    "id": "c_9a5fdfafa653",
    "confirmed_connection": false,
    "next_action": "enter cellar",
    "public_condition": "UNKNOWN"
  },
  {
    "kind": "visit",
    "target": "scorched_plank",
    "category": "known_location",
    "location": "cellar",
    "evidence": "historically seen object; current presence requires reconfirmation",
    "id": "c_a1dbeeaaaee7",
    "confirmed_connection": false,
    "next_action": "enter cellar",
    "public_condition": "UNKNOWN"
  },
  {
    "kind": "craft",
    "target": "brimite_nugget",
    "category": "known_craft",
    "ingredients": [
      "brimite_ore"
    ],
    "stations": "UNKNOWN",
    "evidence": "observed recipe and potentially accessible inputs; downstream connection may be unknown",
    "id": "c_9d66f9363169",
    "confirmed_connection": false,
    "next_action": "store 4 brimite_ore inventory",
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
  }
]
```

## J0 与 J3 配对及去重排名

```json
{
  "state_id": "d12_17c5deb0c6ac6acf",
  "family": "brimite_blade_blank",
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
    "candidate_id": "c_afadb45a7165",
    "intent": [
      "primitive",
      "store 4 brimite_ore inventory"
    ],
    "actions_trace": [
      "store 4 brimite_ore inventory"
    ],
    "feedback_trace": [
      "I stored 4 brimite_ore in my inventory.\nemily_frost enters the area.\n\nSide quest completed: collect 2 brimite_ore\nYou earned 3 coins!\nTalk to emily_frost to see your updated tasks.\nI have acquired a new item: brimite_ore. It can be used to craft: brimite_nugget (1 brimite_ore)\nThe malevolent energy of 5 devil-forged objects seeps into my flesh, draining 4 HP. Carrying more than 3 accursed items invites corruption! (96 HP remaining)"
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
    "native_trace_digest": "8fb501f130e6ed3f22015e80df958932bd999d68c9c60917f0a1eeb8d589b413"
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
    "candidate_id": "c_9a5fdfafa653",
    "intent": [
      "inspect",
      "crucible"
    ],
    "actions_trace": [
      "enter cellar",
      "enter courtyard",
      "inspect crucible"
    ],
    "feedback_trace": [
      "I entered cellar.",
      "I entered courtyard.",
      "I inspected crucible: A stone crucible heated by hellcoal embers, hot enough to smelt war-grade metals.\nIt can be used to craft: None.\nIt has nothing written on it."
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
    "native_trace_digest": "a2cd1015a2454ef47cc8dd39d6c5f10a060419cf5d043a6e2401ce4cfc22d731"
  },
  "J3_raw_judgment": {
    "selected_candidate_id": "c_9a5fdfafa653",
    "ranked_candidate_ids": [
      "c_9a5fdfafa653",
      "c_3f33cf002d85",
      "c_2bd096c0d162"
    ],
    "reason": "Need war_bench and crucible to craft blank; courtyard last held both. Go there via cellar.",
    "hypothesized_connection": "War_bench and crucible in courtyard enable crafting brimite_blade_blank.",
    "confidence": 0.6,
    "expected_information": "Confirm current presence of war_bench and crucible in courtyard.",
    "alternative_if_failed": "c_3f33cf002d85"
  },
  "public_features": {
    "incomplete_public_dependencies": true,
    "unknown_goal_recipe": true,
    "public_necessary_knowledge_drought": 2,
    "no_public_progress_streak": 0,
    "same_known_component_last3": false,
    "recent_unconnected_inspection_last4": true,
    "uninspected_independent_entry_intents": 1,
    "fresh_uninspected_product": false,
    "j3_previously_attempted": false,
    "j3_repeat_inspection_or_station": true,
    "j3_public_recipe_support": false,
    "j3_estimated_actions": 3,
    "s1_estimated_actions": null,
    "s1_public_execution_protected": false,
    "C1_trigger": false,
    "C2_trigger": false,
    "L_trigger": false,
    "remaining_actions": 38
  },
  "J3_top3_original_ids": [
    "c_9a5fdfafa653",
    "c_3f33cf002d85",
    "c_2bd096c0d162"
  ],
  "J3_distinct_ranked_ids": [
    "c_9a5fdfafa653",
    "c_3f33cf002d85",
    "c_2bd096c0d162"
  ],
  "removed_alias_ids": [],
  "alias_groups": [],
  "distinct_top3_useful": false,
  "distinct_top2_useful": false,
  "effective_lower_rank_ids": [],
  "no_effective_direction_in_returned_distinct_ranks": true,
  "candidate_pool_has_opportunity": true,
  "new_connection_direction_relative_to_S1": true,
  "new_connection_useful_native_supported": false,
  "public_evidence_class": "disclosed_recipe_or_dependency_direction",
  "co_mentioned_public_recipe_edges": [
    {
      "product": "brimite_blade",
      "ingredient": "brimite_blade_blank"
    }
  ],
  "co_mention_is_not_entailment_or_proof_of_reasoning": true,
  "mentioned_public_goal_station_requirements": [
    "war_bench",
    "crucible"
  ],
  "unconnected_recipe_names_mentioned": [
    "brimite_blade"
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

### c_afadb45a7165

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
  "candidate_id": "c_afadb45a7165",
  "intent": [
    "primitive",
    "store 4 brimite_ore inventory"
  ],
  "actions_trace": [
    "store 4 brimite_ore inventory"
  ],
  "feedback_trace": [
    "I stored 4 brimite_ore in my inventory.\nemily_frost enters the area.\n\nSide quest completed: collect 2 brimite_ore\nYou earned 3 coins!\nTalk to emily_frost to see your updated tasks.\nI have acquired a new item: brimite_ore. It can be used to craft: brimite_nugget (1 brimite_ore)\nThe malevolent energy of 5 devil-forged objects seeps into my flesh, draining 4 HP. Carrying more than 3 accursed items invites corruption! (96 HP remaining)"
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
  "native_trace_digest": "8fb501f130e6ed3f22015e80df958932bd999d68c9c60917f0a1eeb8d589b413"
}
```

第 1 步：`store 4 brimite_ore inventory`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I stored 4 brimite_ore in my inventory.
emily_frost enters the area.

Side quest completed: collect 2 brimite_ore
You earned 3 coins!
Talk to emily_frost to see your updated tasks.
I have acquired a new item: brimite_ore. It can be used to craft: brimite_nugget (1 brimite_ore)
The malevolent energy of 5 devil-forged objects seeps into my flesh, draining 4 HP. Carrying more than 3 accursed items invites corruption! (96 HP remaining)
```
### c_2bd096c0d162

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
  "candidate_id": "c_2bd096c0d162",
  "intent": [
    "inspect",
    "brimite_blade_blank"
  ],
  "actions_trace": [
    "inspect brimite_blade_blank"
  ],
  "feedback_trace": [
    "I inspected brimite_blade_blank: A forged blank of brimite alloy that glows along hairline fractures.\nIt can be used to craft: brimite_blade (made of brimite_blade_blank, demon_core_shard).\nIt has nothing written on it."
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
  "native_trace_digest": "d06c870e0bb2a7c7205657f7d8efde6a355facc289154cd391751154679cc73e"
}
```

第 1 步：`inspect brimite_blade_blank`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I inspected brimite_blade_blank: A forged blank of brimite alloy that glows along hairline fractures.
It can be used to craft: brimite_blade (made of brimite_blade_blank, demon_core_shard).
It has nothing written on it.
```
### c_9a5fdfafa653

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
  "candidate_id": "c_9a5fdfafa653",
  "intent": [
    "inspect",
    "crucible"
  ],
  "actions_trace": [
    "enter cellar",
    "enter courtyard",
    "inspect crucible"
  ],
  "feedback_trace": [
    "I entered cellar.",
    "I entered courtyard.",
    "I inspected crucible: A stone crucible heated by hellcoal embers, hot enough to smelt war-grade metals.\nIt can be used to craft: None.\nIt has nothing written on it."
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
  "native_trace_digest": "a2cd1015a2454ef47cc8dd39d6c5f10a060419cf5d043a6e2401ce4cfc22d731"
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

第 3 步：`inspect crucible`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I inspected crucible: A stone crucible heated by hellcoal embers, hot enough to smelt war-grade metals.
It can be used to craft: None.
It has nothing written on it.
```
### c_a1dbeeaaaee7

```json
{
  "actions": 2,
  "new_key_recipes": [
    "wood_strip"
  ],
  "useful": true,
  "one_step_useful": false,
  "rejections": 0,
  "unrelated_craft": false,
  "unrelated_key_input_consumption": false,
  "environment_key_loss": false,
  "goal": false,
  "stop": "inspection_attempt_completed",
  "candidate_id": "c_a1dbeeaaaee7",
  "intent": [
    "inspect",
    "scorched_plank"
  ],
  "actions_trace": [
    "enter cellar",
    "inspect scorched_plank"
  ],
  "feedback_trace": [
    "I entered cellar.",
    "I inspected scorched_plank: A plank cut from charred timber, still solid beneath the blackened surface.\nIt can be used to craft: timber_plate (made of scorched_plank), timber_sword (made of scorched_plank, wood_strip, sinew_cord), wood_strip (made of scorched_plank), siege_crate (made of scorched_plank, iron_bar, sinew_cord).\nIt has nothing written on it."
  ],
  "native_new_necessary_rule_count": 1,
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
  "native_trace_digest": "8d011d0f2dc7c3062567b2b9b7dbc551950b49907f78916a83c75c064de05fe1"
}
```

第 1 步：`enter cellar`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I entered cellar.
```

第 2 步：`inspect scorched_plank`；拒绝=False；累计必要配方=["wood_strip"]；消耗={}；环境损失={}。

```text
I inspected scorched_plank: A plank cut from charred timber, still solid beneath the blackened surface.
It can be used to craft: timber_plate (made of scorched_plank), timber_sword (made of scorched_plank, wood_strip, sinew_cord), wood_strip (made of scorched_plank), siege_crate (made of scorched_plank, iron_bar, sinew_cord).
It has nothing written on it.
```
### c_9d66f9363169

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
  "candidate_id": "c_9d66f9363169",
  "intent": [
    "craft_then_inspect",
    "brimite_nugget"
  ],
  "actions_trace": [
    "store 4 brimite_ore inventory",
    "craft 2 brimite_nugget",
    "enter cellar",
    "enter courtyard"
  ],
  "feedback_trace": [
    "I stored 4 brimite_ore in my inventory.\nemily_frost enters the area.\n\nSide quest completed: collect 2 brimite_ore\nYou earned 3 coins!\nTalk to emily_frost to see your updated tasks.\nI have acquired a new item: brimite_ore. It can be used to craft: brimite_nugget (1 brimite_ore)\nThe malevolent energy of 5 devil-forged objects seeps into my flesh, draining 4 HP. Carrying more than 3 accursed items invites corruption! (96 HP remaining)",
    "Cannot craft brimite_nugget. Missing necessary crucible in the current area.\n\nThe malevolent energy of 5 devil-forged objects seeps into my flesh, draining 4 HP. Carrying more than 3 accursed items invites corruption! (92 HP remaining)",
    "I entered cellar.\n\nThe malevolent energy of 5 devil-forged objects seeps into my flesh, draining 4 HP. Carrying more than 3 accursed items invites corruption! (88 HP remaining)",
    "I entered courtyard.\n\nThe malevolent energy of 5 devil-forged objects seeps into my flesh, draining 4 HP. Carrying more than 3 accursed items invites corruption! (84 HP remaining)"
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
  "native_trace_digest": "e3cbeb4672887f867a842580efc5058268f03602b6e67491152e82242124e19d"
}
```

第 1 步：`store 4 brimite_ore inventory`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I stored 4 brimite_ore in my inventory.
emily_frost enters the area.

Side quest completed: collect 2 brimite_ore
You earned 3 coins!
Talk to emily_frost to see your updated tasks.
I have acquired a new item: brimite_ore. It can be used to craft: brimite_nugget (1 brimite_ore)
The malevolent energy of 5 devil-forged objects seeps into my flesh, draining 4 HP. Carrying more than 3 accursed items invites corruption! (96 HP remaining)
```

第 2 步：`craft 2 brimite_nugget`；拒绝=True；累计必要配方=[]；消耗={}；环境损失={}。

```text
Cannot craft brimite_nugget. Missing necessary crucible in the current area.

The malevolent energy of 5 devil-forged objects seeps into my flesh, draining 4 HP. Carrying more than 3 accursed items invites corruption! (92 HP remaining)
```

第 3 步：`enter cellar`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I entered cellar.

The malevolent energy of 5 devil-forged objects seeps into my flesh, draining 4 HP. Carrying more than 3 accursed items invites corruption! (88 HP remaining)
```

第 4 步：`enter courtyard`；拒绝=False；累计必要配方=[]；消耗={}；环境损失={}。

```text
I entered courtyard.

The malevolent energy of 5 devil-forged objects seeps into my flesh, draining 4 HP. Carrying more than 3 accursed items invites corruption! (84 HP remaining)
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
  "native_trace_digest": "6b39fe7a4eadab23d7db87bb41448f733b8efbd66920576ec416267082533ce9"
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
### c_c53ac1f74f40

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
  "native_trace_digest": "4d65a667dd41112b88bf83aa82ce79eb5b51176cf32dc870fdbc933e537a75d7"
}
```

第 1 步：`enter courtyard`；拒绝=True；累计必要配方=[]；消耗={}；环境损失={}。

```text
Cannot enter courtyard. There's no path to courtyard.
```

## 本轮零 API 补充

[完整补充分支](../../../results/stage13/native_supplements.jsonl.gz)。base_proposal 仍为最多四步；truncation_sensitivity 为独立八步敏感性，前四步逐字段相同。

### truncation_sensitivity / c_9d66f9363169

```json
{
  "actions": 6,
  "new_key_recipes": [
    "brimite_ingot"
  ],
  "useful": true,
  "one_step_useful": false,
  "rejections": 1,
  "unrelated_craft": false,
  "unrelated_key_input_consumption": false,
  "environment_key_loss": false,
  "goal": false,
  "stop": "inspection_attempt_completed",
  "candidate_id": "c_9d66f9363169",
  "intent": [
    "craft_then_inspect",
    "brimite_nugget"
  ],
  "actions_trace": [
    "store 4 brimite_ore inventory",
    "craft 2 brimite_nugget",
    "enter cellar",
    "enter courtyard",
    "craft 2 brimite_nugget",
    "inspect brimite_nugget"
  ],
  "feedback_trace": [
    "I stored 4 brimite_ore in my inventory.\nemily_frost enters the area.\n\nSide quest completed: collect 2 brimite_ore\nYou earned 3 coins!\nTalk to emily_frost to see your updated tasks.\nI have acquired a new item: brimite_ore. It can be used to craft: brimite_nugget (1 brimite_ore)\nThe malevolent energy of 5 devil-forged objects seeps into my flesh, draining 4 HP. Carrying more than 3 accursed items invites corruption! (96 HP remaining)",
    "Cannot craft brimite_nugget. Missing necessary crucible in the current area.\n\nThe malevolent energy of 5 devil-forged objects seeps into my flesh, draining 4 HP. Carrying more than 3 accursed items invites corruption! (92 HP remaining)",
    "I entered cellar.\n\nThe malevolent energy of 5 devil-forged objects seeps into my flesh, draining 4 HP. Carrying more than 3 accursed items invites corruption! (88 HP remaining)",
    "I entered courtyard.\n\nThe malevolent energy of 5 devil-forged objects seeps into my flesh, draining 4 HP. Carrying more than 3 accursed items invites corruption! (84 HP remaining)",
    "I successfully crafted 2 brimite_nugget. It is now on the ground.\nemily_frost enters the area.\n\nSide quest completed: craft a brimite_nugget\nYou earned 5 coins!\nTalk to emily_frost to see your updated tasks.",
    "I inspected brimite_nugget: A dense nugget smelted from brimite ore, hot to the touch and faintly glowing.\nIt can be used to craft: brimite_ingot (made of brimite_nugget).\nIt has nothing written on it."
  ],
  "native_new_necessary_rule_count": 1,
  "preparation_actions_until_first_necessary_recipe": 5,
  "craft_actions": 2,
  "inspect_actions": 1,
  "consumption": {
    "brimite_ore": 2
  },
  "production": {
    "brimite_nugget": 2
  },
  "environment_loss_quantities": {},
  "unrelated_key_consumption_quantities": {},
  "repeated_inspect_without_new_public_recipe": 0,
  "craft_without_output_or_new_recipe": 1,
  "public_known_necessary_executions": [],
  "raw_entry_useful": false,
  "native_trace_digest": "6144cc4a8440cf5ae64e2ad3e9b22f7243a291fb48a670184c948aa4601f8f58"
}
```

## 公开文本新颖性独立审计

将原反馈中的带数量配方也计为公开信息；不修改策略、Stage12 或主分数。

```json
{
  "initial_public_text_necessary_recipes": [
    "brimite_nugget"
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
